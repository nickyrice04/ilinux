#!/usr/bin/env python3
"""Extract the candidate's actual target/get callbacks for mocked-MMIO C tests.
Runs only in the isolated Linux build VM. No physical MMIO is mapped.
"""
import argparse
from pathlib import Path
import subprocess
import resource


def function(source, name):
    start = source.index("static " + ("unsigned int " if name.endswith("get_rate") else "int ") + name + "(")
    opening = source.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("output")
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    source = Path(args.source).read_text()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    # Assertions bind tested callbacks to the intended guarded SoC and init behavior.
    guarded = source.split("static const struct apple_soc_cpufreq_info soc_t6050_info", 1)[1].split("};", 1)[0]
    assert ".cur_pstate_mask = 0" in guarded and ".ilinux_guarded = true" in guarded
    init = source.split("static int apple_soc_cpufreq_init(", 1)[1].split("static void apple_soc_cpufreq_exit", 1)[0]
    assert "APPLE_DVFS_STATUS" not in init
    assert "ret = -ERANGE" in init and "boot p-state absent" in init
    assert "policy->fast_switch_possible = !info->ilinux_guarded" in init
    assert "static bool ilinux_enable_writes;" in source
    assert "module_param(ilinux_enable_writes, bool, 0444)" in source
    assert "module_param(ilinux_max_pstate, uint, 0444)" in source
    callbacks = "\n".join(function(source, n) for n in ("apple_soc_cpufreq_get_rate", "apple_soc_cpufreq_set_target"))
    harness = Path(__file__).with_name("test_driver.c").read_text().replace("/* ACTUAL_DRIVER_CALLBACKS */", callbacks)
    cfile = out / "test_driver_generated.c"
    cfile.write_text(harness)
    binary = out / "test_driver"
    subprocess.run(["cc", "-O1", "-g", "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter", "-fsanitize=address,undefined", str(cfile), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
    mutants = {
        "fake_dry_run_success": ("if (!ilinux_enable_writes)\n\t\t\treturn -EPERM;", "if (!ilinux_enable_writes)\n\t\t\treturn 0;"),
        "writes_allowed_by_default": ("if (!ilinux_enable_writes)", "if (false)"),
        "cap_ignored": ("pstate > ilinux_max_pstate)", "false)"),
        "wrong_state_written": ("reg |= pstate << priv->info->ps1_shift;", "reg |= (pstate + 1) << priv->info->ps1_shift;"),
        "unknown_state_fabricated": ('pstate);\n\treturn 0;', 'pstate);\n\treturn policy->freq_table[0].frequency;'),
        "acknowledgement_ignored": ("FIELD_GET(APPLE_DVFS_CMD_PS1, reg) != pstate", "false"),
    }
    for name, (before, after) in mutants.items():
        assert before in harness, name
        changed = harness.replace(before, after, 1)
        mutant_c = out / (name + ".c")
        mutant_c.write_text(changed)
        mutant_binary = out / name
        subprocess.run(["cc", "-O1", "-g", "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter", "-fsanitize=address,undefined", str(mutant_c), "-o", str(mutant_binary)], check=True)
        result = subprocess.run([str(mutant_binary)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            raise AssertionError("regression not caught: " + name)
        print("PASS mutation rejected:", name)
    print("PASS six regression mutations rejected")


if __name__ == "__main__":
    main()
