"""Exercise Recovery guards using shell stand-ins; no real disk/policy calls."""
import os
from pathlib import Path
import re
import subprocess
import unittest

HELPER = Path(__file__).with_name('recovery-preflight.sh')
HARNESS = r'''
source "$HELPER"
# Synthetic identifiers, never obtained from a real machine.
ilinux_field() {
    local kind=lab
    [[ "$1" == *' - Data' ]] && kind=data
    [[ "$1" == *'Macintosh HD' ]] && kind=original
    case "$2" in
        VolumeName) [[ "$CASE" == wrong_name ]] && { echo wrong; return; }; echo "${1##*/}" ;;
        MountPoint) [[ "$CASE" == wrong_mount ]] && { echo /wrong; return; }; echo "$1" ;;
        Internal) [[ "$CASE" == external ]] && echo false || echo true ;;
        FilesystemType) [[ "$CASE" == wrong_fs ]] && echo hfs || echo apfs ;;
        FileVault) [[ "$CASE" == encrypted_lab ]] && echo true || echo false ;;
        APFSVolumeGroupID)
            [[ "$CASE" == field_failure ]] && return 1
            [[ "$CASE" == empty_group ]] && return 0
            if [[ "$kind" == original && "$CASE" != same_group ]]; then echo ORIGINAL
            elif [[ "$kind" == data && "$CASE" == data_mismatch ]]; then echo OTHER
            else echo LAB; fi ;;
        *) return 99 ;;
    esac
}
test() {
    [[ "$1" == -f ]] && { [[ "$CASE" != missing_payload ]]; return; }
    [[ "$1" == '!' && "$2" == -L ]] && { [[ "$CASE" != symlink_payload ]]; return; }
    builtin test "$@"
}
plutil() { [[ "$CASE" == wrong_build ]] && echo wrong || echo 25G83; }
stat() { [[ "$CASE" == wrong_size ]] && echo 0 || echo 3932160; }
shasum() { [[ "$CASE" == wrong_hash ]] && echo wrong || echo "$ILINUX_HASH"; }
bputil() {
    [[ "$1" == --display-policy && "$2" == --vuid && "$#" == 3 ]] || return 99
    [[ "$CASE" == policy_error ]] && return 1
    if [[ "$3" == ORIGINAL ]]; then
        [[ "$CASE" == original_reduced ]] && echo 'Security Mode: Reduced (smb1)' || echo 'Security Mode: Full (smb0): absent'
    else
        [[ "$CASE" == unknown_policy ]] && { echo 'New format'; return; }
        [[ "$CASE" == lab_reduced ]] && echo 'Security Mode: Reduced (smb1)' || echo "Security Mode: ${LAB_MODE:-Full} (smb0): absent"
        [[ "$CASE" == unpaired ]] && echo 'Recovery: Not Paired' || echo 'Recovery: Paired'
        [[ "$CASE" == not_1tr ]] || echo 'Boot: one true recoveryOS'
    fi
    return 0
}
ilinux_preflight
result=$?
if [[ "$EXPECT" == pass ]]; then
    [[ "$result" == 0 && "$ILINUX_READY" == yes ]] || exit 20
    LAB_MODE=Permissive
    ilinux_check_policies Permissive || exit 21
    CASE=original_reduced
    ilinux_check_policies Permissive && exit 22
    CASE=valid
    LAB_MODE=Full
    ilinux_check_policies Permissive && exit 23
else
    [[ "$result" != 0 && "$ILINUX_READY" == no && "$ILINUX_POLICY_OK" == no ]] || exit 24
fi
exit 0
'''


class PreflightTests(unittest.TestCase):
    def test_syntax(self):
        subprocess.run(['/bin/bash', '-n', str(HELPER)], check=True)

    def test_guards(self):
        cases = ['valid', 'wrong_name', 'wrong_mount', 'external', 'wrong_fs',
                 'encrypted_lab', 'field_failure', 'empty_group', 'same_group',
                 'data_mismatch', 'missing_payload', 'symlink_payload',
                 'wrong_build', 'wrong_size', 'wrong_hash', 'policy_error',
                 'original_reduced', 'lab_reduced', 'unknown_policy',
                 'unpaired', 'not_1tr']
        for case in cases:
            with self.subTest(case=case):
                env = dict(os.environ, HELPER=str(HELPER), CASE=case,
                           EXPECT='pass' if case == 'valid' else 'fail')
                result = subprocess.run(['/bin/bash', '--noprofile', '--norc', '-c', HARNESS],
                                        env=env, text=True, capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertNotIn('ORIGINAL', result.stdout)
                self.assertNotIn('Security Mode:', result.stdout)

    def test_documented_write_gates_with_stand_ins(self):
        document = HELPER.with_name('boot-entry-setup.md').read_text()
        blocks = re.findall(r'```sh\n(.*?)```', document, re.S)
        policy = next(b for b in blocks if b.startswith('ILINUX_POLICY_OK=no'))
        install = next(b for b in blocks if b.startswith('ILINUX_INSTALLED=no'))
        harness = r'''
ILINUX_READY=yes
[[ "$CASE" == bad_ready ]] && ILINUX_READY=no
ILINUX_VG=LAB
ILINUX_OS='/Volumes/iLinux Boot Lab'
ILINUX_BOOT='/Volumes/iLinux Boot Lab - Data/Users/Shared/iLinuxBoot/m1n1.bin'
bp_calls=0; km_calls=0; check_calls=0
bputil() {
    [[ "$*" == '--permissive-security --disable-kernel-ctrr --vuid LAB' ]] || exit 90
    bp_calls=$((bp_calls+1))
    [[ "$CASE" != policy_failed ]]
}
ilinux_check_policies() {
    check_calls=$((check_calls+1))
    [[ "$1" == Permissive ]] || exit 91
    [[ "$CASE" == postcheck_failed ]] && return 1
    [[ "$CASE" == finalcheck_failed && "$check_calls" == 3 ]] && return 1
    return 0
}
ilinux_payload_ok() { [[ "$CASE" != payload_failed ]]; }
kmutil() {
    [[ "$#" == 10 && "$1" == configure-boot && "$2" == --custom-boot-object &&
       "$3" == "$ILINUX_BOOT" && "$4" == --raw && "$5" == --entry-point &&
       "$6" == 2048 && "$7" == --lowest-virtual-address && "$8" == 0 &&
       "$9" == --volume && "${10}" == "$ILINUX_OS" ]] || exit 92
    km_calls=$((km_calls+1))
    [[ "$CASE" != kmutil_failed ]]
}
'''
        expectations = {
            'valid': (1, 1, 'yes'), 'bad_ready': (0, 0, 'no'),
            'policy_failed': (1, 0, 'no'), 'postcheck_failed': (1, 0, 'no'),
            'payload_failed': (1, 0, 'no'), 'kmutil_failed': (1, 1, 'no'),
            'finalcheck_failed': (1, 1, 'no'),
        }
        for case, (bp, km, installed) in expectations.items():
            with self.subTest(case=case):
                assertions = (f'[[ "$bp_calls" == {bp} && "$km_calls" == {km} '
                              f'&& "$ILINUX_INSTALLED" == {installed} ]]')
                result = subprocess.run(
                    ['/bin/bash', '--noprofile', '--norc', '-c',
                     harness + '\n' + policy + '\n' + install + '\n' + assertions],
                    env=dict(os.environ, CASE=case), text=True,
                    capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
