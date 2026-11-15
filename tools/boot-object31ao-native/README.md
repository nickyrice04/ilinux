# Original 31AO policy extension and desktop syntax checker

This directory adds six formatter-qualified private metadata fields and the
exact true `smb0 && smb1` expression to the frozen reader. It does not add an
installer, change a boot object or bypass Recovery admission. The shipped build
command compiles a **pure desktop syntax checker**, not a Recovery collector.

`generate.py` hash-checks the frozen 31AL generator, generates its exact observed
source, applies once-only anchored changes and proves exact reversal. The
original `reader.h`, core, JSON and 31AM Preboot engine stay unchanged. The
declared acceptance extension is real: do not call all predicates byte-identical.

The finite TEXT metadata catalog is `CEPO`, `SDOM`, `CPRO`, `CSEC`, `lobo`,
`love`. The first two have a fixed `0x` prefix and at most 16 hexadecimal
digits. Three are Boolean; the version contains six unsigned 32-bit decimal
components `D.D.D.D.D,D`. Each optional field may be unseen, or occur once
with its qualified type. Explicit `absent` is unqualified for these six and
refuses. Unseen presence is stored and bound, so removal across observations
is detectable. Unknown fields and the old protected auxiliary refusals remain.

The combined security expression is accepted only with a true value. AND true
establishes both operands true; AND false does not establish their individual
values and is refused. Existing semantic duplicates and mode consistency
checks then run normally. The old four-tag group limit is unchanged.

Private canonical values and presence counters are part of `Policy`, including
its before/after comparison. The new v3 HMAC retains all old components and
binds every fixed extra tag, presence and canonical value using NUL separators.
The public snapshot layout is unchanged. Existing intended nonce/custom-object/
CTRR transitions are not turned into a blanket unchanged-field requirement.
Old baseline/key/state files must not be reused for a future new helper.

`build.py` extracts the exact pure parser regions from the old and proposed
sources. Reversible line marks record rejection locations without changing
predicates. No disk/policy collection, process creation or host inspection API
is compiled into the parser. `parse_check.c --stdin` accepts at most 65,536
private bytes and emits only acceptance flags and fixed generated-source line
numbers. Default/help is inert; `native_ready` and `admission_verified` always
remain false. There is no `--live` or policy-write mode.

Build into a new workspace directory with the installed SDK:

```bash
python3 -I tools/boot-object31ao-native/build.py --output build/policy31ao/desktop-review
```

Focused tests:

```bash
python3 -I tools/boot-object31ao-native/test_native.py \
  --compiled build/policy31ao/desktop-review/desktop-parser \
  --harness-output build/policy31ao/native-harness-review
```

The test runner supports reuse of a compiled checker. Normal and sanitizer
builds use distinct directories; all inputs are explicitly synthetic. See
`reverse-engineering/findings/policy31ao/README.md` for the qualified behavior,
offsets, confidence and independent source context. The runtime desktop wrapper
pins the reviewed M5 binary; another machine's compiler output is not silently
substituted for that pin.
