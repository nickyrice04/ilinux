# 31AV: where the Mach-O policy request goes

November 15, 2026. Offline static investigation following the actual 31AU result.
No policy query, private transaction read, installed boot-object read, library
API invocation, mount, security change or boot operation ran. Extracted generic
Apple bytes, LLVM listings and REA output remain in ignored analysis storage.

## Actual observation and question

[31AU's recorded result](../native/boot/attempt31au-recovery-2026-11-15-result.json)
establishes a changed selected reference, a successful selected-file read and
IMG4/LZFSE `DECODE_REJECTED`. It separately records lab Kernel CTRR **disabled**
and passing preservation checks. The original recognizer did not complete;
neither exact candidate enrollment nor native entry was established. The human
confirmed independent boot021 restoration and Macintosh HD desktop/default
return. These are the stated evidence levels, without a new target check.

[31AU's earlier REA pass](attempt31au-ctrr-2026-11-15.md) qualified the current
generic kmutil's Mach-O path selecting option `0x80` for
`bootpolicy_update_local_policy_for_custom_os_ex`. The remaining question was
whether libbootpolicy itself clears an existing SIP2 setting or delegates that
decision elsewhere. This pass crosses that specific library boundary.

## Input and analysis controls

**Observed:** the current generic `/usr/lib/libbootpolicy.dylib` image resides
in the readable arm64e dyld cache. An original bounded reader used cache mappings
and the library's load commands to copy only its segments and relevant linkedit
tables. The public [Apple dyld format declarations](https://github.com/apple-oss-distributions/dyld/blob/main/include/mach-o/dyld_cache_format.h)
provide the mapping and image formats. No complete shared cache was copied.

The original TEXT range is `0x1affab000`–`0x1affe42c8`: 234,184 bytes, SHA-256
`6a81bceb45e079d5dd57b27b7f3d4e9713da32a5dcb923f67d787bfe7efe73db`.
Its export trie identifies 105 exports; its function-start table contains 807
entries. A 310,091-byte, analysis-only compact Mach-O preserves code/virtual
addresses while rewriting file offsets and compacting symbol/linkedit storage.
Its SHA-256 is `71e45ee3913b3ab0da69ea6c38f6fb0429065f649fadb1095f15b2ea143e2a81`.
It is not an executable replacement. Cached data pointers were not rebased;
unresolved pointer interpretations are not used as evidence.

REA 6.4.0/Ghidra 12.1.4 queried one exported function in the existing diskless
2-vCPU/8-GiB Linux VM. Explicit `--no-net` and a guest assertion established
loopback only; no disks or physical USB were attached. VM/query exited zero.
The prior lab job was restored byte for byte and the quiet lock released.

Independent checks compare 712 instruction words across five nonoverlapping
function ranges against both original cache bytes and LLVM output: zero
mismatches. The REA body is 1,080 bytes/270 instructions, with 584 untruncated
high-pcode operations inside that range. All 584 are marked dead. Whole-function
pseudocode is therefore **not admitted**; only independently checked, bounded
instruction flow and original metadata support the findings below.

## Qualified request and receiver boundary

**Confirmed for this generic library:** export
`bootpolicy_update_local_policy_for_custom_os_ex` begins at `0x1affc1644`, ending
at the next function start, `0x1affc1a7c`. The options argument arrives in `x3`.
At `0x1affc17e8`, an exact comparison with `0x80` controls setting request byte
offset `0x22` to 1 at `0x1affc17f4`. This is an equality test, not a general
bit-presence test. The older custom-OS API passes zero to this options argument
at its call `0x1affc14f8`; it does not independently establish the new mode's
meaning.

The function obtains the linked manifest and existing LocalPolicy through
named input helpers, then calls `_sep_command` at `0x1affc180c` with command
`0x2f`. Its success path passes the returned policy to
`write_local_policy_with_nonce_hash` at `0x1affc1830`.

`_sep_command`, `0x1affad3f8`–`0x1affad780`, constructs a request header and calls
`_sep_send` at `0x1affad458`. Its header initialization does not overwrite the
mode byte at offset `0x22`. `_sep_send`, `0x1afface2c`–`0x1affaced4`, submits the
buffer through `IOConnectCallStructMethod` with selector zero at `0x1afface84`.
The checked initializer `0x1affaced4`–`0x1affacf54` selects the **BootPolicy**
IOKit service and opens its user client. The service name comes from the
original constant and import identities from the copied indirect-symbol table.

**Unknown:** the service-side interpretation of command `0x2f`'s mode byte,
including its effect on an already disabled SIP2/Kernel CTRR state. This library
trace qualifies a request/response boundary; it does not qualify a local SIP2
clear, establish the resulting secure policy, or prove that a successful
request must enable Kernel CTRR on every firmware version. The private kernel
CTRR flag and hardware enforcement must remain distinct observations.

## Engineering consequence and next discriminator

Keep the exact candidate and enabled-CTRR guard, and the independent boot021
restore. No alternate writer, option combination, force/reset, guard relaxation
or new native boot is qualified. Fixing the independently investigated codec
defect cannot alone satisfy the separate CTRR postcondition.

The current desktop library is now qualified; **the actual Recovery kmutil,
libbootpolicy and runtime service used for 31AU are not**. A useful future
combined diagnostic should bind generic tool/library versions or code hashes to
the actual Recovery session and identify the runtime request capability. It
should report finite capability/result classes without policy values or device
identifiers. A version mismatch would narrow an environmental explanation;
matching callers alone would still leave server-side semantics open. Do not
spend a Recovery visit solely to repeat the unchanged failed transaction.

The accessible BootPolicy kext metadata names `com.apple.security.BootPolicy`
and its AppleSEPManager/IOSlaveProcessor dependencies. Tracing that small kernel
receiver, if needed, is a bounded next static question; it was not analyzed in
this pass, and no SEP firmware or credentials were accessed.

The exact-board public reference's newer, matched firmware/Aura/kernel stack
remains a deliberate alternative requiring an owner-approved update plan.
Neither the actual 31AU refusal nor this request trace establishes an Apple-only
CPU blocker. Native Linux, SMP, GPU and performance-parity validation remain
**NOT RUN** for this attempt. Machine-readable evidence accompanies this note.
