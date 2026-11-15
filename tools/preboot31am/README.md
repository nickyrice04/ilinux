# 31AL Preboot-path result: focused offline regression

The physical 31AL result is `AUX_IDENTITIES / GUARD / PREBOOT_MOUNT_PATH`.
The actual Preboot `MountPoint` was intentionally not returned. It is unknown
whether it was empty, relative, root-only, ended with a separator or contained
an empty/dot component. A missing or non-string field would instead have
produced `PREBOOT_MOUNT_FORMAT`. The result is before policy, pairing, security,
selected-object and native CPU checks; it supplies no new firmware result.

The unchanged collector already identified Preboot by unique role, volume UUID,
device, APFS container and internal-volume metadata. It then assumes its
`MountPoint` is an already mounted, lexically safe path. It does not mount it.
The prior successful fixture uses `/Volumes/Preboot` throughout. An unmounted
Preboot with an empty field is a plausible explanation, **not a finding about
the actual Recovery state**.

## Reuse a known open-source preparation sequence

Asahi's MIT-licensed installer at revision
`e93743d52178b3e26e428fa05174ef549abf30cb` explicitly mounts the role-selected
Preboot before collecting its fresh mount point:

- [OS enumeration, lines 183–188](https://github.com/AsahiLinux/asahi-installer/blob/e93743d52178b3e26e428fa05174ef549abf30cb/src/osenum.py#L183-L188):
  prepares Preboot, Recovery and System by role-selected device.
- [Mount routine, lines 195–198](https://github.com/AsahiLinux/asahi-installer/blob/e93743d52178b3e26e428fa05174ef549abf30cb/src/diskutil.py#L195-L198):
  performs a mount and then obtains a new `info -plist` response.

Direct pinned-source reads, without execution or saving, yielded:

| Source | Bytes | SHA-256 |
| --- | ---: | --- |
| `src/osenum.py` | 10014 | `e467caaf1516f41973ccf8e7fb0950e5d668fa87813767e0157f6c34fc594389` |
| `src/diskutil.py` | 10253 | `e62a15a807dba8148d757be2e082014d954fa8a538d10790df9ea2d151e60fed` |

This supports borrowing the **identity selection → preparation → fresh
observation** sequence. Do not execute or transplant the full installer: its
mount helper uses a normal mount and other installer operations perform writes.
The installed `diskutil(8)` manual documents `mount readOnly`; it also notes
Disk Arbitration may perform a minimal filesystem check before mounting.

A future minimal proposal can first classify the existing field and mount state
with finite, non-sensitive labels. If it is positively identified as unmounted,
an explicitly authorized read-only mount of only the identity-bound Preboot,
followed by fresh UUID/device/container/read-only/mount-path checks, can satisfy
the unchanged path guard. Other invalid classes should remain stops. In this
project the lab and Original share a container, so do not describe this as a
separate lab-only Preboot volume or use an unverified `/Volumes/Preboot` name.

No mount or preparation controller is implemented here. New mount operations
need explicit host-change authorization; current diagnostic authorization does
not grant them. Neither mounting nor a passing snapshot would authorize
installation or a native boot. Original Full Security, strict no-follow reads,
all policy/identity checks and frozen 31AL files remain in force.

## Focused tests

```bash
python3 -I tools/preboot31am/test_preboot.py
python3 -I tools/preboot31am/test_preboot.py --sanitize
```

The six new methods compose the existing original C build/fixture harness and
run only synthetic CF fixtures. They do not inherit or rerun its 29 methods.
They test empty/unmounted-like input, lexical refusal classes, missing/non-string
format errors, canonical-path progression to a deliberately invalid policy and
the fact that the lexical guard does not consume a `Mounted` boolean. No actual
Recovery state, disk metadata, mount, policy command or host backend is used.
Passing them demonstrates possible control flow, not the unknown physical cause.

November 14 offline results: **6/6 normal PASS** (2.271 s) and **the same 6/6
under ASan/UBSan PASS** (1.504 s), including original C compilation. No old suite
was rerun, no source predicate changed and no live operation ran.
