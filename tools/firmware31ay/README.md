# Narrow generic firmware version observation

`read_versions.py` reads only `firmware-version` and
`system-firmware-version` from the running OS's single
`IODeviceTree:/chosen` registry node. It performs no enumeration, recursive
search, policy/boot-object/volume access, subprocess, write or setting change.
It does not identify the selected firmware of another macOS installation.

The two fixed system frameworks are loaded through ctypes. CFData/CFString
inputs are bounded before reading their contents; output admits only strict
ASCII numeric `mBoot-` / `iBoot-` version strings. Unexpected types, lengths,
bytes or API failures return fixed `UNKNOWN`/reason labels, without raw data
or exception text. Fixed shape metadata reports the two properties' supported
type, bounded length and NUL counts, ASCII/prefix/numeric-shape booleans only.
It can diagnose padding or a numeric build suffix without admitting or printing
the rejected version. The command accepts no arguments. No authentication is
requested by the script.

```sh
python3 -I tools/firmware31ay/read_versions.py
```

`OBSERVED` exits 0; incomplete observation exits 1; extra arguments exit 2
before any framework/query. A failed sandbox query is not evidence that a
firmware version is absent.

The signatures and reference ownership were checked against Apple's installed
SDK IOKitLib/CoreFoundation headers and public
[IOKitLib reference](https://developer.apple.com/documentation/iokit/iokitlib_h),
[CFData length](https://developer.apple.com/documentation/corefoundation/cfdatagetlength(_:))
and [byte pointer](https://developer.apple.com/documentation/corefoundation/cfdatagetbyteptr(_:))
interfaces. No private API or broad property-dictionary copy is used.

```sh
python3 -I tools/firmware31ay/test_read_versions.py
```

The 19 pure tests use synthetic bytes and fake IOKit/CoreFoundation objects;
they load no host framework. They cover numeric-only admission, malformed and
private-looking string refusal, exact one-node/two-key scope, bounds before
pointer access, embedded NUL refusal, unsupported types, missing data,
sanitized failure output, argument refusal and handle release. These tests
do not establish successful live access or firmware compatibility.
