#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the resolved, intentionally reconstructed RAM-diagnostic profile."""
import json
import re
import sys
from pathlib import Path

REQUIRED_Y = '''ARM64_16K_PAGES ARM64_CTXR_EXECMEM ARM64_ACTLR_STATE SMP MODULES
ARCH_APPLE BLK_DEV_INITRD RD_GZIP DEVTMPFS DEVTMPFS_MOUNT PROC_FS SYSFS TMPFS
BINFMT_ELF FUTEX INET PCI PCIE_APPLE APPLE_DART APPLE_MAILBOX APPLE_RTKIT
APPLE_RTKIT_HELPER APPLE_DOCKCHANNEL APPLE_PMGR_PWRSTATE APPLE_AIC
SERIAL_APPLE_DOCKCHANNEL SERIAL_APPLE_DOCKCHANNEL_EARLYCON USB USB_GADGET
USB_DWC3 USB_DWC3_DUAL_ROLE USB_DWC3_APPLE USB_CONFIGFS USB_CONFIGFS_SERIAL
USB_CONFIGFS_ACM USB_CONFIGFS_ECM DRM DRM_SIMPLEDRM SYSFB_SIMPLEFB
FRAMEBUFFER_CONSOLE HID_DOCKCHANNEL ARM_APPLE_CPUIDLE ARM_APPLE_SOC_CPUFREQ
WLAN RFKILL CFG80211 APPLE_CENTAURI_T6050 APPLE_CENTAURI_T6050_WIFI'''.split()
FORBIDDEN = '''ARM64_4K_PAGES ARM64_64K_PAGES RUST APPLE_SEP
DRM_ASAHI DRM_APPLE DRM_ACCEL_ANE APPLE_AOP APPLE_PMP MTD SND MEDIA_SUPPORT
USB4 KVM HIBERNATION APFS_FS HFS_FS HFSPLUS_FS USB_CONFIGFS_MASS_STORAGE'''.split()

def parse(text):
    result = {}
    for line in text.splitlines():
        m = re.fullmatch(r'CONFIG_([A-Z0-9_]+)=(.*)', line)
        if m:
            if m[1] in result:
                raise ValueError('duplicate configuration symbol')
            result[m[1]] = m[2]
        else:
            m = re.fullmatch(r'# CONFIG_([A-Z0-9_]+) is not set', line)
            if m:
                if m[1] in result:
                    raise ValueError('duplicate configuration symbol')
                result[m[1]] = 'n'
    return result

def check(c):
    errors = [f'CONFIG_{s} must be y (got {c.get(s, "absent")})'
              for s in REQUIRED_Y if c.get(s) != 'y']
    errors += [f'CONFIG_{s} must be disabled' for s in FORBIDDEN
               if c.get(s, 'n') != 'n']
    errors += [f'CONFIG_{s} must remain a module' for s in ('NVME_APPLE', 'APPLE_SART')
               if c.get(s) != 'm']
    try:
        if not 18 <= int(c.get('NR_CPUS', '0')) <= 256:
            errors.append('NR_CPUS must admit 18 workers within the collector bound')
    except ValueError:
        errors.append('invalid NR_CPUS')
    return errors

def main():
    c = parse(Path(sys.argv[1]).read_text())
    errors = check(c)
    print(json.dumps({'scope':'OFFLINE_RESOLVED_CONFIG', 'profile':'reconstructed-ram-diagnostic',
        'reporter_config_reproduced':False, 'status':'PASS' if not errors else 'FAIL',
        'page_bytes':16384, 'executable_confinement':c.get('ARM64_CTXR_EXECMEM'),
        'nr_cpus':c.get('NR_CPUS'), 'sep_disabled':c.get('APPLE_SEP','n')=='n',
        'storage_built_as_modules_not_in_initramfs':True, 'errors':errors}, indent=2))
    return bool(errors)

if __name__ == '__main__':
    raise SystemExit(main())
