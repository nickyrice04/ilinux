#!/usr/bin/env python3
"""Prepare an OFFLINE m1n1 candidate; never modify the pinned source tree.

No deployment command is supplied. Raw reset-entry and Linux SMP handoff must
be reviewed from the separate census before this candidate can be deployed.
"""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess

PIN = '57a9339ffd1876e78297b17d34dece8cff8fa1ba'
SHA = '4b000be8d4e6437fc24351a57db5277785cc2e427045fb45d1750b158f2b8766'
HERE = Path(__file__).resolve().parent


def replace_once(s, old, new):
    if s.count(old) != 1:
        raise ValueError('source anchor differs')
    return s.replace(old, new)


def patch_source(s):
    if hashlib.sha256(s.encode()).hexdigest() != SHA:
        raise ValueError('smp.c differs from pinned source')
    s = replace_once(s, '#include "smp.h"', '#include "smp.h"\n#include "layout31.h"')
    s = replace_once(s, 'static struct cpu_info cpu_info[MAX_CPUS];', '''static struct cpu_info cpu_info[MAX_CPUS];
static unsigned short smp31_desc[6];
static bool smp31_attempted;

static u32 smp31_start_mask(const struct cpu_info *cpu)
{
    if (chip_id == T6050)
        return smp31_mask(smp31_desc, sizeof(smp31_desc), cpu->cluster, cpu->core);
    return 1u << (4 * cpu->cluster + cpu->core);
}''')
    s = replace_once(s, '    printf("Starting CPU %d (%d:%d:%d)... ", index, cpu->die, cpu->cluster, cpu->core);', '''    /* Refuse unknown reset entry before changing stacks or PMGR. */
    if (chip_id == T6050 &&
        (!smp31_start_mask(cpu) || cpu_features->apple_sysregs_unlocked ||
         (read64(cpu->impl_reg) & (RVBAR_ADDR | RVBAR_LOCK)) !=
             ((u64)_vectors_start | RVBAR_LOCK)))
        return;

    printf("Starting CPU %d (%d:%d:%d)... ", index, cpu->die, cpu->cluster, cpu->core);''')
    # Remove the original warning-only, double-read path on t6050.
    s = replace_once(s, '    if (!cpu_features->apple_sysregs_unlocked &&',
                     '    if (chip_id != T6050 && !cpu_features->apple_sysregs_unlocked &&')
    s = s.replace('1 << (4 * cpu->cluster + cpu->core)', 'smp31_start_mask(cpu)')
    s = replace_once(s, '    _reset_stack = dummy_stack + DUMMY_STACK_SIZE;', '''    /* A timed-out core can still arrive late. Keep its dedicated stack. */
    if (chip_id == T6050 && i >= 100)
        return;
    _reset_stack = dummy_stack + DUMMY_STACK_SIZE;''')
    s = replace_once(s, '    cpu_start_base = pmgr_reg + cpu_start_off;', '''    if (chip_id == T6050) {
        u32 length = 0;
        int pmgr = adt_path_offset(adt, pmgr_name);
        const void *desc = pmgr < 0 ? NULL : adt_getprop(adt, pmgr, "clusters", &length);
        if (desc && length == sizeof(smp31_desc))
            memcpy(smp31_desc, desc, sizeof(smp31_desc));
    }
    cpu_start_base = pmgr_reg + cpu_start_off;''')
    s = replace_once(s, 'void smp_start_secondaries(void)\n{', '''/* Offline candidate API: 0 = entered, negative = refused/timeout.
 * One same-cluster secondary only. No power-off, idle, IPI or frequency test.
 * A flag proves arrival, NOT timer/coherency/IPI correctness or Linux online.
 */
int smp31_start_one(void) __attribute__((used, retain));
int smp31_start_one(void)
{
    if (chip_id != T6050 || !smp_initialized || smp31_attempted ||
        boot_cpu_idx != 0 || (boot_cpu_mpidr & 0xffffff) != 0x40000 || has_el3() ||
        cpu_start_base != 0x280688000ULL || !cpu_info[0].valid ||
        cpu_info[0].die || cpu_info[0].cluster || cpu_info[0].core ||
        cpu_info[0].impl_reg != 0x210050000ULL)
        return -1;
    const struct cpu_info *cpu = &cpu_info[1];
    if (!cpu->valid || cpu->die != 0 || cpu->cluster != 0 || cpu->core != 1 ||
        cpu->impl_reg != 0x210150000ULL || !smp31_start_mask(cpu) ||
        cpu_features->apple_sysregs_unlocked)
        return -2;
    for (int i = 0; i < MAX_CPUS; i++)
        if (spin_table[i].flag)
            return -3;
    if ((read64(cpu_info[0].impl_reg) & (RVBAR_ADDR | RVBAR_LOCK)) !=
        ((u64)_vectors_start | RVBAR_LOCK))
        return -4;
    /* No retries, even after timeout; preserve WFE parking until power-off. */
    smp31_attempted = true;
    smp_set_wfe_mode(true);
    smp_start_cpu(1, cpu);
    return spin_table[1].flag && spin_table[1].mpidr == 0x40001 ? 0 : -5;
}

void smp_start_secondaries(void)
{
    if (chip_id == T6050) {
        printf("smp31: bulk startup refused; use separately reviewed single-core API\\n");
        return;
    }''')
    # Do not let generic stop or mode toggles enter unvalidated deep idle.
    s = replace_once(s, 'void smp_stop_secondaries(bool deep_sleep)\n{', '''void smp_stop_secondaries(bool deep_sleep)
{
    if (chip_id == T6050)
        return;''')
    s = replace_once(s, 'void smp_set_wfe_mode(bool new_mode)\n{', '''void smp_set_wfe_mode(bool new_mode)
{
    if (chip_id == T6050 && !new_mode)
        return;''')
    return s


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('out', type=Path)
    a = p.parse_args()
    if subprocess.check_output(['git', '-C', str(a.source), 'rev-parse', 'HEAD'], text=True).strip() != PIN:
        raise ValueError('unexpected source revision')
    if subprocess.check_output(['git', '-C', str(a.source), 'status', '--porcelain', '--untracked-files=no']):
        raise ValueError('source is dirty')
    patched = patch_source((a.source / 'src/smp.c').read_text())
    shutil.copytree(a.source, a.out, symlinks=True, ignore=shutil.ignore_patterns('.git', 'build'))
    (a.out / 'src/smp.c').write_text(patched)
    shutil.copyfile(HERE / 'layout31.h', a.out / 'src/layout31.h')
    header = a.out / 'src/smp.h'
    header.write_text(replace_once(header.read_text(), '#endif',
        '/* Offline experiment, no proxy opcode. */\nint smp31_start_one(void);\n\n#endif'))
    print('PREPARED OFFLINE: no target, no deployment')


if __name__ == '__main__':
    main()
