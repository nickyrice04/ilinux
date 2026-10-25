# M1 handoff: 31AB original resident-host entry and observer components

**Offline review only. No restart or native invocation follows from this package.**
M5 incorporated both M1 31AA reviews in `c4a794f`. macOS, installed boot objects,
security, volumes, the retained boot package and the client remain unchanged.
No repeated boot-policy check or external outreach is requested.

## Read the new work

Preserve local changes, inspect `git status --short`, and pull with
`git pull --ff-only`. Report divergence without resetting anything. Record the
exact reviewed commit. Read:

- `native/boot/attempt31ab/validation.json`
- `virtualization/jobs/086-offline31ab/validation.json`
- `research/native31ab-route.md`
- `research/native31ab-entry.md`, `native31ab-public-contract.md` and the
  `native31ab-observer*.md` notes
- The READMEs and original code under `kernel/experiments/sptm31ab-host/`,
  `bootimage31ab/`, `observer31ab/` and `translation31ab/`.

The entry image is now actually linked and its ordinary ARM instructions were
executed under emulation. It captures full incoming arguments without reading
them, owns its stack/vector record and has a fatal recorder. Three bootstrap
transports exist but are uncalled. The observer and translation work is separate;
do not treat their tests as an integrated native screen-output path.

## Focused checks using existing tools

From the repository root, choose fresh ignored output directories:

```sh
shasum -a 256 -c native/boot/attempt31ab/source-sha256.txt
python3 -I -m unittest discover -s kernel/experiments/bootimage31ab -p 'test_image.py'
python3 -I kernel/experiments/sptm31ab-host/run.py \
  --output build/31ab-entry-m1-review --cc clang \
  --target aarch64-none-elf --compile-only
python3 -I kernel/experiments/observer31ab/run.py \
  --output build/31ab-observer-m1-review --sanitize --freestanding
python3 -I kernel/experiments/translation31ab/run.py \
  --output build/31ab-translation-m1-review --cc clang \
  --target aarch64-none-elf --compile-only
```

Execute the translation QEMU fixture only in an already available isolated environment with the documented
toolchain. Do not install tools or launch a shared VM without the project locks.
If unavailable, record that execution as NOT RUN on M1; independently review the
M5 source-bound result instead. None of the VM scripts is a macOS shell setup.

Entry source bindings must match the M5 link and host-object runs. Object bytes
may differ by compiler. A compile-only result does not repeat the ELF link audit.
If an existing suitable Linux/ELF toolchain is available, the entry README gives
the link/audit command; otherwise record that limitation. The actual linked
payload and packaged-image hashes are in the validation record.

Check the separation of evidence:

- Six unique ELF/instruction audit groups include 16 mutation refusals per
  linked base. Repeating them at two bases is not 12 unique groups.
- The nine entry cases execute EL1, EL2 and VHE fixtures, including three actual
  BRKs. They never execute GENTER or Apple firmware. Only vector slot 4 has the
  deliberate runtime fault test; the other slots are statically audited.
- Image-property derivation is parser behavior, not firmware acceptance.
- A range-table address match is not write permission or scanout visibility.
  AT/PAR tests also do not establish every native protection or device behavior.
- Native CPU startup, Linux SMP, GPU and performance remain NOT RUN here.

Do not repeat old executable suites, the old inspector matrix, REA queries or
private Apple artifact checks merely to increase counts. Preserve the 22 prior
source closures and all consumed M1 review records.

## Report the result

Publish the usual dated `native/boot/attempt31ab-m1-offline-YYYY-MM-DD.md` and
`.json` pair, plus progress/coordination. Include the commit, manifest result,
actual tool versions, group counts, sanitizer outcomes, source bindings, compile
scope and actionable review findings. Keep raw artifacts in ignored storage.
Mark REA, private instruction comparisons, SDK measurements and M5 VM execution
NOT RUN on M1 unless actually repeated. Push the review under the existing
workflow; do not message external projects.

The next engineering task is to integrate an observable resident-host entry and
prepare a bounded acceptance test. No working local multicore solution exists
yet, and an Apple-only dependency has not been proved. A silent screen or a raw
start failure alone cannot establish that conclusion. No boot command is supplied
by this handoff.
