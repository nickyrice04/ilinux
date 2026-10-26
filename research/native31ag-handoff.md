# 31AG offline handoff qualification: protection context and observable limits

2026-10-26 Eastern. **Offline only; no new native image or restart is ready.**
This pass uses REA/Ghidra on retained generic local firmware and tools to narrow
the producer-to-entry contract after the human's logo-only 31AF result. It does
not identify the native failure stage, establish an Apple-only dependency or
qualify a new monitor call.

The earlier [direct result](../native/boot/attempt31af-human-2026-10-26-result.md)
retains its unknown numeric exits, observation timing, exact rollback and default
restoration. The existing restoration-only instructions remain applicable.

## Fresh analysis and limits

Eight fresh queries completed with CLI exit 0 in the existing diskless Linux
lab, using REA 6.4.0 and Ghidra 12.1.4. Guests exposed loopback only; no physical
device was forwarded. Apple bytes, instructions and decompiler output remain in
ignored local storage. Independent Apple LLVM checks cover **751 instruction
words in 22 bounded ranges, zero mismatches**. The current generic kmutil file
still matches the retained arm64e slice, and the iBoot carrier matches its retained
decoded input. The exact Recovery tool and executing native firmware are not
thereby identified. [Sanitized validation](../reverse-engineering/findings/cpu-startup31ag/validation.json).

| Target | Fresh result | Accepted scope |
| --- | --- | --- |
| kmutil configure body `0x100143a50` | 1158 instructions; 3000 P-code operations, truncated; six removed-block warnings | Bounded call-site and argument checks only |
| Property-method references `0x1000f849c` | Two provider references | Static reference inventory, not actual runtime dispatch |
| iBoot normal handoff `0x100c1ae53b8` | 702 instructions; 3000 P-code operations, truncated | Independently checked caller/consumer windows |
| iBoot wrapper `0x100c1ad1058` | 162 instructions; one removed-block warning | Identifies the preceding wrapper, not the desired selector |
| SPTM PAPT registration `0xfffffff0270dffac` | 80 instructions, 111 P-code operations; no removal/truncation/outside-body issue | Bounded registration conditions and descriptor writes |
| kmutil protection helper `0x100144cbc` | 151 instructions, 93 P-code operations; four removed-block warnings and an injection annotation | Actual-byte success path and enum comparison only |
| iBoot selector requested at `0x100c1ad15a4`, actual entry `0x100c1ad12e0` | 1169 instructions, 2181 P-code operations; 120 removed-block warnings | Actual-byte descriptor gate only |
| SPTM fatal entry `0xfffffff0270feccc` | Provider body eight instructions; 44 of 48 P-code operations outside it | The decompiled function is refused; no failure-channel contract |

Successful query exit does not override these gates. Whole-function pseudocode
is refused for every affected body. The small PAPT routine was initially queried
under a failure-report hypothesis; it is actually a range-registration routine.
That correction is preserved rather than treating its name as evidence.

An initial wrapper precondition stopped before any VM or query because it
incorrectly required the diskless shell job to be executable. Correcting it to a
regular-file check permitted the first VM. That VM's 240-second aggregate job
bound then interrupted its third request: the two completed kmutil results were
retained, the zero-byte interrupted result supplies no finding, and the fourth
request never started. Later batches used total query bounds at most 225 seconds;
both completed setup/job with exit 0. All VMs stopped, the prior lab job was
restored byte-for-byte, and both workspace locks were released.

## The collection kind and protection profile are distinct

The normal configure call site at `0x100144668` supplies two separate values:

- A fixed **collection kind 1**, corresponding to the Boot collection path.
- A **protection-profile Boolean** obtained by comparing the platform context's
  PageProtectionType result to enum value 2, whose generated name is SPTM.
  The other recognized enum names are none and PPL.

The argument forwarding chain preserves both. The analyzer stores the collection
kind separately and compares it with 1/2/3 for its collection-specific address
handling. Its RO/RX split tests the separate protection-profile bit. The property
wrapper also uses that protection bit to choose extended versus older property
serialization. A fixed Boot collection kind does **not** prove the split profile
is true. An intermediate private interpretation confused these parameters;
independent parameter-slot and enum-dispatch checks corrected it before any
native proposal or public finding.

The protection helper obtains its mode through a context-dependent witness
method. A static data reference connects the known property-method thunk to its
matching witness-table location, but this does not establish which context or
mode the historical Recovery invocation supplied. No private selector or
metadata override is appropriate. The exact installed dictionary or a qualified
matching runtime context is still needed to close that fact.

This matters because the earlier read-only inspector ran with deliberately
absent System/Aux collection inputs. Its measured false split profile must not
be promoted to the actual Recovery installation profile. Conversely, current
hardware support for SPTM alone does not prove what that historical context
returned. The [31Y producer finding](native31y-firmware.md) remains valid within
its earlier bounded scope; this pass adds argument/context provenance.

## A conditional reserved-range check, not a diagnosed installer bug

The independently rechecked iBoot publisher uses the image load base plus the
descriptor's RO-prefix size for the reserved-region base, and the descriptor's
reserved-size field for its extent. The associated property callback maps these
to kcrz and kcsz. kcsf is parsed separately; it is not used in that bounded
publication sequence.

For the intended split profile, the RO prefix ends where the reservation starts.
For the measured false-profile inspector dictionary, those values differ. A
conditional auditor can therefore detect a relationship inconsistent with an
explicitly supplied affine image layout. It must label the dictionary's origin,
selected profile and load-extent assumptions. This is not evidence that actual
Recovery emitted the false dictionary, that iBoot used that branch, or that the
native logo result was a reserved-range fault.

The new iBoot selector query independently rechecks the descriptor `+0x38` gate
previously associated with kcbz. Nonzero selects additional preparation and also
requires a separate expected/current-state equality check. Complete state and
caller binding remain unknown; this does not justify forcing a flag or replaying
an internal operation. Later iBoot handoff references to literal TEXT/DATA segment
names occur in a conditional arm-io/sapt object path and are not established as
checks of our custom OS image.

## Required ranges do not imply a missing Mach-O segment is the cause

The retained SPTM primary initializer passes the required flag when looking up
BootKC-ro, BootKC-rx, BootKC-bx, BootKC-rw and BootKC-le in the memory map; its
reservation lookup is separately qualified in 31AF. A missing required map record
reaches the failure path. A present record still has further registration rules.

The freshly queried PAPT registration routine validates bootstrap stage, type,
range count and flag combinations. A zero mapped-page count is rejected unless
its explicit optional flag permits omission. These checks happen before an OS
entry observation could be expected.

However, the absence of an ordinary DATA or BOOTDATA segment in 31AF is not alone
a diagnosis. Its derived dictionary already has a nonzero writable-tail extent;
firmware map records are derived from those extents, rather than requiring every
role to be justified by a matching literal segment name in this bounded trace.
Actual permissions, ownership and profile still require qualification. Do not
rename metadata as usable RAM or treat a Mach-O RW declaration as sufficient
proof of normal-world write access.

## Installed-object identity and an independent observation

Bounded generic-tool path checks establish a volume-group/boot/active-identity
relative root and the type-selected `kernelcache.custom.` filename prefix. They
do not establish a particular personalized path, active identity or currently
selected file. This analysis reads no personalized boot object or LocalPolicy.
A separate read-only check may use a correctly identified lab Preboot subtree
and compare only known original payload hashes in memory; a historical matching
file's presence must not be confused with the active selection. Identifiers and
personalized envelopes must not enter public output.

No safe independent native early-output or persistent-failure channel is
qualified by these queries. In particular, the fatal-entry decompilation crosses
its provider boundary and cannot justify intentionally invoking it. A blank
framebuffer test still combines pre-entry failure, unsupported entry/mappings,
an exception and scanout visibility. The original offline evidence classifier
must retain these alternatives.

The meaningful next evidence is a qualified actual loader/property context,
verified active original object, matching positive entry control or independent
entry/failure observation. Further marker-only native variants remain on hold.
This checkpoint supplies no installed-object write, security change, physical
CPU release, SMP workaround or macOS-performance claim.
