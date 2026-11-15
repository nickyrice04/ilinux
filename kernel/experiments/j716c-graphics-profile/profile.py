#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only pre-build admission of the frozen, public J716c graphics config.

This checks configuration data, not Kconfig resolution, hardware, deployment,
firmware ownership, or authorization to boot. It runs no external program.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat


SCHEMA = "ilinux-j716c-graphics-config-v1"
PUBLICATION = "5e11068a1c6d8fccb155bc6e0159cc16107e53ec"
KERNEL = "a59e709c737777495c84541c6afb6c862bb79227"
AURA_GRAPHICS_STAGE2 = "9da61857f9d9262bd64c023fbc1b18315b12d0af"
REFERENCE_SHA256 = "3c11e751cb6d6e0358429230d28121c7f383aa5437a2e0b7d181b85f6dd7dbe8"
REFERENCE_BYTES = 330809
DIAGNOSTIC_SHA256 = "bba7ce251238c3cb6779d884a3442373443f7eed97e19f638afc08fdb9779fd8"
MAX_BYTES = 1024 * 1024
BOARD_CPUS = 18

# A reviewed subset of the full reference: pre-build error localization only.
# Exact-byte admission below still requires the complete published file.
REQUIRED_Y = """ARM64 SMP MODULES ARCH_APPLE APPLE_AIC ARM64_16K_PAGES
ARM64_CTXR_EXECMEM ARM64_ACTLR_STATE PAGE_SIZE_16KB MMU IOMMU_SUPPORT
APPLE_DART APPLE_SART APPLE_PMGR_PWRSTATE APPLE_MAILBOX APPLE_RTKIT
APPLE_RTKIT_HELPER APPLE_DOCKCHANNEL ARM_APPLE_CPUIDLE NVME_APPLE RUST DRM
FW_LOADER RUST_FW_LOADER_ABSTRACTIONS RUST_APPLE_MAILBOX RUST_APPLE_RTKIT
RUST_DRM_GPUVM RUST_DRM_GEM_SHMEM_HELPER RUST_DRM_SCHED RUST_OVERFLOW_CHECKS
DRM_ASAHI_G16 DRM_ASAHI_G15 DRM_ASAHI_M3_T8122 DRM_APPLE_DCP_T8132
DRM_SIMPLEDRM SYSFB_SIMPLEFB FRAMEBUFFER_CONSOLE THERMAL_OF APPLE_CLPC
APPLE_PMP_REPORT APPLE_T6030_GPU_PMP_LINK MFD_MACSMC ARM_SMC_WATCHDOG
WLAN APPLE_CENTAURI_T6050_WIFI""".split()
REQUIRED_M = """DRM_ASAHI DRM_APPLE DRM_APPLE_FABRIC_CORE APPLE_PMP
APPLE_PMP_THERMAL SENSORS_MACSMC_HWMON ARM_APPLE_SOC_CPUFREQ
APPLE_CENTAURI_T6050 CFG80211 MAC80211""".split()
REQUIRED_N = """ARM64_4K_PAGES ARM64_64K_PAGES DRM_ASAHI_M5 DRM_ASAHI_G18
DRM_ASAHI_DEBUG_ALLOCATOR MODULE_SIG""".split()
REQUIRED_EMPTY = "INITRAMFS_SOURCE EXTRA_FIRMWARE CMDLINE SYSTEM_TRUSTED_KEYS".split()
EXPECTED = dict.fromkeys(REQUIRED_Y, "y")
EXPECTED.update(dict.fromkeys(REQUIRED_M, "m"))
EXPECTED.update(dict.fromkeys(REQUIRED_N, "n"))
EXPECTED.update(dict.fromkeys(REQUIRED_EMPTY, '""'))
EXPECTED["PAGE_SHIFT"] = "14"

RUNTIME_GATES = (
    "matching_board_and_loader_filled_DT",
    "matching_firmware_and_GPU_text_identity",
    "RTC_runtime_DT_disabled_and_no_unqualified_writeback",
    "external_ATC2_runtime_DT_disabled",
    "bounded_CPU_clock_profile_with_valid_SMC_temperature_telemetry",
    "firmware_owned_fan_control",
    "physical_watchdog_and_separately_deployed_host_guardian",
    "default_off_shallow_WFI_and_no_deep_idle_or_suspend_claim",
    "matching_graphics_Stage2_not_merely_installed_Stage1",
    "matching_modules_Mesa_firmware_and_RAM_root",
    "online_CPU_topology_core_types_IPIs_and_cache_coherency",
)

ASSIGNMENT = re.compile(r"CONFIG_([A-Za-z0-9_]+)=(.*)")
DISABLED = re.compile(r"# CONFIG_([A-Za-z0-9_]+) is not set")
VALUE = re.compile(r'(?:y|m|[0-9]+|0x[0-9a-fA-F]+|"(?:[^"\\\x00-\x1f]|\\[^\x00-\x1f])*")')


class ConfigError(ValueError):
    """A bounded, non-executable input is not a resolved Linux config."""


def read_config(path):
    """Read at most 1 MiB from a regular final path, without following symlinks.

    Parent directories are chosen by the caller; this is not a pathname sandbox.
    The file is opened once and checked again after reading to reject changes.
    """
    flags = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ConfigError("CONFIG_OPEN_FAILED") from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_BYTES:
            raise ConfigError("CONFIG_NOT_BOUNDED_REGULAR_FILE")
        chunks = []
        remaining = MAX_BYTES + 1
        while remaining:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(fd)
        data = b"".join(chunks)
        if len(data) > MAX_BYTES or len(data) != before.st_size:
            raise ConfigError("CONFIG_SIZE_CHANGED_OR_TOO_LARGE")
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ConfigError("CONFIG_CHANGED_DURING_READ")
        return data
    finally:
        os.close(fd)


def parse(data):
    if not data or len(data) > MAX_BYTES:
        raise ConfigError("CONFIG_EMPTY_OR_TOO_LARGE")
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise ConfigError("CONFIG_NOT_UTF8") from exc
    if "\x00" in text or "\r" in text or not text.endswith("\n"):
        raise ConfigError("CONFIG_BINARY_CR_OR_MISSING_FINAL_NEWLINE")
    values = {}
    for number, line in enumerate(text.splitlines(), 1):
        m = ASSIGNMENT.fullmatch(line)
        if m:
            symbol, value = m.groups()
            if not VALUE.fullmatch(value):
                raise ConfigError(f"CONFIG_VALUE_SYNTAX_LINE_{number}")
        else:
            m = DISABLED.fullmatch(line)
            if m:
                symbol, value = m[1], "n"
            elif line.startswith("#") or not line:
                # Reject misspelled/partial disabled records, not normal comments.
                if line.startswith("# CONFIG_"):
                    raise ConfigError(f"CONFIG_DISABLED_SYNTAX_LINE_{number}")
                continue
            else:
                raise ConfigError(f"CONFIG_RECORD_SYNTAX_LINE_{number}")
        if symbol in values:
            raise ConfigError(f"CONFIG_DUPLICATE_{symbol}")
        values[symbol] = value
    if not values:
        raise ConfigError("CONFIG_NO_SYMBOLS")
    return values


def invariants(config):
    errors = []
    for symbol, expected in sorted(EXPECTED.items()):
        actual = config.get(symbol)
        if actual != expected:
            errors.append({"symbol": "CONFIG_" + symbol, "expected": expected,
                           "actual": actual})
    # This is a capacity range from the pinned arm64 Kconfig, not a topology.
    nr_cpus = config.get("NR_CPUS", "")
    if not nr_cpus.isdecimal() or not BOARD_CPUS <= int(nr_cpus) <= 4096:
        errors.append({"symbol": "CONFIG_NR_CPUS", "expected": "integer 18..4096",
                       "actual": config.get("NR_CPUS")})
    return errors


def compare(before, after):
    changes = []
    for symbol in sorted(before.keys() | after.keys()):
        old, new = before.get(symbol), after.get(symbol)
        if old != new:
            changes.append({"symbol": "CONFIG_" + symbol, "before": old,
                            "after": new})
    return changes


def report(data, diagnostic_data=None, all_differences=False):
    candidate = parse(data)
    errors = invariants(candidate)
    digest = hashlib.sha256(data).hexdigest()
    exact = digest == REFERENCE_SHA256 and len(data) == REFERENCE_BYTES
    accepted = exact and not errors
    result = {
        "schema": SCHEMA,
        "scope": "OFFLINE_FULL_CONFIG_DATA_ONLY",
        "status": "PASS_EXACT_REFERENCE_CONFIG" if accepted else "FAIL_CONFIG_ADMISSION",
        "reference_config_accepted": accepted,
        "critical_config_invariants_pass": not errors,
        "exact_reference_bytes_match": exact,
        "input": {"sha256": digest, "bytes": len(data), "symbols": len(candidate)},
        "sources": {"publication": PUBLICATION, "kernel": KERNEL,
                    "graphics_Stage2": AURA_GRAPHICS_STAGE2},
        "configuration_errors": errors,
        "CPU_capacity": {
            "configured_maximum_logical_ID_count": candidate.get("NR_CPUS"),
            "published_board_physical_CPU_count": BOARD_CPUS,
            "observed_online_CPU_count": None,
            "measurement_worker_count": None,
            "requires_runtime_online_topology_before_assigning_workers": True,
        },
        "GPU_backend": {
            "DRM_ASAHI": candidate.get("DRM_ASAHI"),
            "DRM_ASAHI_M5": candidate.get("DRM_ASAHI_M5"),
            "M5_option_is_not_the_Max_G17C_admission_gate": True,
            "runtime_GPU_bound_or_accelerated": None,
        },
        "runtime_gates": {key: "NOT_VERIFIED_BY_CONFIG" for key in RUNTIME_GATES},
        "Kconfig_resolved_with_matching_toolchain": False,
        "kernel_or_modules_built": False,
        "boot_object_installed": False,
        "native_ready": False,
        "restart_ready": False,
        "performance_or_efficiency_parity_demonstrated": False,
    }
    if diagnostic_data is not None:
        diagnostic = parse(diagnostic_data)
        changes = compare(diagnostic, candidate)
        interesting = set(EXPECTED) | {"NR_CPUS", "RUSTC_VERSION_TEXT", "CC_VERSION_TEXT",
                                       "BINDGEN_VERSION_TEXT", "LOCALVERSION"}
        result["diagnostic_delta"] = {
            "baseline_matches_31AH_published_manifest": (
                hashlib.sha256(diagnostic_data).hexdigest() == DIAGNOSTIC_SHA256),
            "baseline_sha256": hashlib.sha256(diagnostic_data).hexdigest(),
            "changed_symbol_count": len(changes),
            "added": sum(row["before"] is None for row in changes),
            "removed": sum(row["after"] is None for row in changes),
            "changed_existing": sum(row["before"] is not None and row["after"] is not None
                                    for row in changes),
            "focused_changes": [row for row in changes
                                if row["symbol"].removeprefix("CONFIG_") in interesting],
            "scope": "DATA_COMPARISON_NOT_AN_APPLIED_PATCH_OR_KCONFIG_RESOLUTION",
        }
        if all_differences:
            result["diagnostic_delta"]["all_changes"] = changes
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True,
                        help="Complete frozen published config; never executed or installed")
    parser.add_argument("--diagnostic-config", type=Path,
                        help="Optional existing resolved diagnostic config for an exact delta")
    parser.add_argument("--all-differences", action="store_true",
                        help="Include every symbol change rather than only the reviewed subset")
    args = parser.parse_args(argv)
    try:
        data = read_config(args.config)
        baseline = read_config(args.diagnostic_config) if args.diagnostic_config else None
        result = report(data, baseline, args.all_differences)
    except ConfigError as exc:
        result = {"schema": SCHEMA, "status": "FAIL_INPUT", "reason": str(exc),
                  "scope": "OFFLINE_FULL_CONFIG_DATA_ONLY", "native_ready": False,
                  "restart_ready": False, "boot_object_installed": False}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("reference_config_accepted") else 1


if __name__ == "__main__":
    raise SystemExit(main())
