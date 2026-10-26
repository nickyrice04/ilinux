# 31AF: continue with a different observer, not an unchanged boot

2026-10-25 Eastern. **Decision: a meaningful software test remains. The current
evidence does not establish that an Apple update is required.**

## What changed in the evidence

The [31AE result](../native/boot/attempt31ae-recovery-2026-10-25-result.md)
establishes actual Recovery installation success: configure, capture and block
exits were all zero, with the original Full/lab Permissive postcheck. The
previous format error did not recur. One lab boot then showed an Apple logo;
diagnostic entry is unconfirmed. Human-reported exact rollback and original
desktop/default restoration succeeded. The reported observation exceeded the
30-second cap; the next procedure must use a timer and stop at that bound.

A logo by itself identifies neither a firmware restriction nor an execution
stage. There is also a concrete weakness in our diagnostic: before it can show
anything it clears its record and uses its stack in a region whose name and
runtime role are reserved for the monitor. All subsequent refusal paths write
private RAM and park. The old emulator supplies writable RAM there, so its
passing cases did not test this ownership assumption.

## Why the memory role matters

The [public-source review](native31af-public-contract.md) independently identifies
XNU's separate ordinary data, bootstrap stacks and `__DATA_SPTM` reservation.
The latter has a macOS reference footprint of `0x54000`; this is a comparator,
not a proven minimum for our firmware.

Local REA and independent byte/LLVM checks identify the retained monitor's
`BootKC-rs` initialization at `0xfffffff0270bcee8`. A bounded window at
`0xfffffff0270bd084..0xfffffff0270bd114` initializes the reserved area, places
bootstrap fields at its beginning and sets a page-table workspace beginning
one 16 KiB page later. Its capacity check is not evidence that `0x54000` is
the minimum size. The relevant input is the retained SPTM, SHA-256
`da2ad8d4ecbf3e29fbaaa07e8c7d291ed20d296044494e00303c7a780d190666`.

The local iBoot property callback and range-publisher windows associate the
reserved range with the supplied collection properties. Under the intended
SPTM profile, 31AE's record overlaps reserved page zero and its stack overlaps
reserved pages one and two. Complete runtime profile selection and actual first
store behavior are unobserved. This is a strong testable ownership hypothesis,
not a retrospective assertion that we observed a native protection fault.

New REA queries cover range lookup `0xfffffff0270bc07c` and region initialization
`0xfffffff0270bcee8`. The larger initializer reaches the provider's 3000-operation
value-flow limit; whole-function pseudocode is not accepted as verified source.
The independent six-window audit covers 304 instruction words with zero original
byte/LLVM mismatches. Extracted Apple code and decompiler output remain private.

## What the new test removes

31AF's original entry observer uses registers and boot code only. It does not
use a stack, clear a record or issue an explicit store into its image/reserved data area.
The only intended stores are the bounded marker in the supplied, validated
framebuffer and the required cache maintenance. AT may have architectural
access-flag/dirty-table effects under incoming controls; this does not claim that
all translations are universally free of those effects. It does not change protection
registers, page tables or the monitor lifecycle, or call a monitor service.

The dedicated on-disk monitor reservation uses the public reference footprint;
the original image declares its permissions consistently with the accepted
format, while software never treats it as scratch memory. The emulator models
that reservation as populated and read-only, independently of the Mach-O
declaration, and checks it byte-for-byte after execution. A separately hash-pinned
old-image control tests the previous first-store assumption in that model.

All reachable instructions remain in the initially executable boot region.
The new centered marker is larger than 31AE's 32×16 top-left pattern, reducing
visibility ambiguity. Input and framebuffer addresses still need bounded
translation, attribute and arithmetic checks before a store. The exact
implemented profiles, cases and results are in the new source and validation
receipt; standard ARM emulation is not Apple firmware emulation.

## Interpreting the next native result

A visible marker would establish that the new immutable entry path reached
validated framebuffer stores without requiring observer-owned RAM. That would
support continuing the resident software adapter using properly separated data
and stack storage. It would not establish service readiness, physical CPU1
execution, full Linux, GPU or performance parity.

A missing marker would remain ambiguous: pre-entry failure, an unsupported entry
profile, unavailable argument/table mappings, an exception or scanout visibility
could still account for it. It would not prove an Apple-only stop. No finite set
of unrelated silent probes can justify that conclusion without a qualified
prohibiting contract or a demonstrated failing hardware requirement.

The justified next action is an independently reviewed **new** image, one
guarded lab installation, one timed observation only on installation success,
then exact boot021 rollback and original/default restoration. No unchanged
retry, new security reduction, volume operation, firmware modification or native
write is authorized by this preparation. Macintosh HD stays Full Security.
