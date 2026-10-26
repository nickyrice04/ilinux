# Read the policy-selected lab custom boot object

This original standard-library diagnostic performs no installation, mount,
authentication change, boot/default change or file write. Default invocation
prints help. `--fixture` processes synthetic workspace fixtures offline. Tests
never invoke live commands.

`--live` is an explicit local-root diagnostic for **Mac17,6 only**. It queries
disk metadata for `/Volumes/iLinux Boot Lab`, the running root and their APFS
container roles. It refuses an unexpected lab name/mount, the current OS's volume
group, a missing System role, ambiguous volume/container, mismatched Preboot
identity or an unmounted Preboot. It does not mount anything or scan other boot
objects. The M1 helper is refused before any policy query.

The single policy read is for the validated lab volume group. Its output stays
in memory; identifiers, hashes and private paths are neither printed nor saved.
No original Macintosh HD policy is queried. Duplicate/malformed keys are refused.
The original case of hexadecimal path components is preserved. The supported
component safety grammar is 32–128 hexadecimal characters in byte pairs; this
is a conservative local path guard, not a universal Apple hash-format claim.

The public Asahi installer contract selects:

```text
<Preboot mount>/<lab volume-group>/boot/<nsih>/System/Library/Caches/com.apple.kernelcaches/kernelcache.custom.<coih>
```

No symlink component is followed. Only a regular selected file up to 8 MiB is
read, with stable inode/size/timestamps checked across the read. A regular file
changing during observation is refused. Read-only observations are snapshots,
not an atomic transaction with future boot selection.

Two workspace copies are authenticated against fixed public artifact pins:

| Label | Default ROOT-relative reference | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| `31AF` | `build/research31af/published-check/ilinux-31af-immutable.macho` | 442368 | `166bea74bf515473057dfd29dc89127d04768945a451e497cc80a9fc53d4951b` |
| `BOOT021` | `build/research31af/package/m1n1-boot021.bin` | 3932160 | `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664` |

Reference overrides must remain inside the project workspace, with the same
fixed sizes/hashes and no symlinks. No staged private Data-volume copy is used.

Classification requires either exact whole-file equality or an exact direct
IM4P payload, optionally carried by IMG4. The minimal reader checks definite
canonical outer lengths, file/depth/node bounds and supported payload framing.
Optional IMG4 context a0/a1 metadata is opaque: only its outer TLV extent is
checked; inner manifest/private tags and cryptographic metadata are not parsed
or validated. Optional keybag bytes are ignored. It never decrypts,
decompresses, authenticates Apple's signatures or searches arbitrary byte
substrings. Compressed, encrypted and unrecognized representations stay UNKNOWN.

The only result fields are:

```json
{"match": "BOOT021", "read_only": true}
```

Other labels are `31AF`, `UNKNOWN`, `NO_CUSTOM_OBJECT` and `REFUSED`. A controlled
refusal exits 2 without printing an exception or captured stderr. Successful
read/classification exits 0, including UNKNOWN. A match establishes configured
object/payload identity at observation time. It does **not** establish default
Startup Disk, historical execution, SPTM activation, original/lab protection
levels or completion of the full rollback procedure.

Host-safe checks:

```sh
python3 -I tools/boot-object31ag/test_read_selected.py
python3 -I tools/boot-object31ag/read_selected.py --help
```

The coordinating agent supplies any live command for the target's local Terminal
after reviewing this exact source. Credentials stay in the local sudo prompt.
Do not run live mode on M1 or turn a refusal into a policy/volume change.

Public implementation sources only:
[Asahi installer `osenum.py` at e93743d](https://github.com/AsahiLinux/asahi-installer/blob/e93743d52178b3e26e428fa05174ef549abf30cb/src/osenum.py#L235),
[APFS role enumeration](https://github.com/AsahiLinux/asahi-installer/blob/e93743d52178b3e26e428fa05174ef549abf30cb/src/osenum.py#L125),
[disk metadata helper](https://github.com/AsahiLinux/asahi-installer/blob/e93743d52178b3e26e428fa05174ef549abf30cb/src/diskutil.py).
This tool does not import or execute the installer, whose mount/write behavior
is deliberately excluded. Local metadata key names were confirmed separately;
no private values or Apple decompiler output were supplied to this implementation.
