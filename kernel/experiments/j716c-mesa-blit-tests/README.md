# Exact Mesa blit-test policy correction, test-only derivative

The unchanged Mesa `10161a78e60e4057257e116d404a92bd9b78bb3c` build compiles
all 2,356 targets, but its first retained Asahi suite reports **175 pass / 4
fail**. The four failures are `asahi-t6041-gallium-blit`,
`asahi-g17p-gallium-blit`, `asahi-t6041x-gallium-blit` and
`asahi-g17p-gallium-blit-encode`. Each reports the same assertion message:
`Accelerated texture transfers were disabled`. V1 retained the text log; its
full Meson JSON was not exported before guest cleanup. V3 retains both logs.
Do not relabel that baseline as an all-pass result.

## Finding

The exact driver's [`agx_pipe.c` transfer policy](https://github.com/aurora-silicon/mesa/blob/10161a78e60e4057257e116d404a92bd9b78bb3c/src/gallium/drivers/asahi/agx_pipe.c#L2639)
deliberately advertises `PIPE_TEXTURE_TRANSFER_DEFAULT` on AGX3 and preserves
`PIPE_TEXTURE_TRANSFER_BLIT` on AGX2. Its source explains that the GPU path's
BGRA-to-RGBA conversion returned zero on hardware even when CPU mapping was
byte-exact. That is the author's hardware finding, not a new local hardware
measurement. Forcing BLIT would remove a correctness fallback.

The same revision's [blit test](https://github.com/aurora-silicon/mesa/blob/10161a78e60e4057257e116d404a92bd9b78bb3c/src/gallium/drivers/asahi/tests/test-agx-g17p-blit.c#L1719)
still unconditionally requires BLIT. This is a stale test expectation relative
to the shipping source contract. The no-op shim's successful shader encoding
cannot establish the real GPU's pixel-conversion behavior. The underlying
accelerated readback limitation remains separate from this assertion mismatch.

## Derivative

`test-only.patch` changes only `test-agx-g17p-blit.c`:

* Assert the existing generation-specific advertisement: AGX2 BLIT, AGX3 DEFAULT.
* Upload, CPU-map and validate two uncompressed 4×8 texture patterns, in BGRA8
  and RGBA8, using the actual Gallium driver transfer functions.
* Run Mesa's CPU format translator into RGBA and back, checking all 64 pixels,
  distinct channel values, transparent alpha and untouched padded row bytes.
* Keep every existing crash, shader/encode, skipped-draw, compression and
  command-stream assertion. No test is skipped and no driver capability changes.

This exercises CPU storage/tiling/detiling plus the CPU conversion primitive;
it does not execute GLES `glReadPixels`, emulate GPU shaders, verify native
compressed rendering or establish accelerated transfer correctness.

The direct `agx_texture_subdata` implementation uses CPU tiling for uncompressed
twiddled resources on all generations. Its generic linear fallback maps,
`util_copy_box` copies, and unmaps; `agx_transfer_map` CPU-maps or detiles
uncompressed storage. The new test refuses compressed resources so that a
staging blit cannot masquerade as CPU coverage. It runs before the original
test's draw operations. Thus the AGX2 control does not depend on the shim
executing a GPU upload.
[Transfer implementation](https://github.com/aurora-silicon/mesa/blob/10161a78e60e4057257e116d404a92bd9b78bb3c/src/gallium/drivers/asahi/agx_pipe.c#L1069),
[generic subdata implementation](https://github.com/aurora-silicon/mesa/blob/10161a78e60e4057257e116d404a92bd9b78bb3c/src/gallium/auxiliary/util/u_transfer.c#L74).

## Reproduction boundary

`prepare_test.py` is original data-only tooling. It requires exact hashes of the
unchanged driver and test, then writes a fresh, separate C file. It never edits
the input source or a shipping driver. The generated test has SHA-256
`1c974a166a06f1996458a735886cf7c3ef50d33c18d319fac79aadbd4695db40`.
Only third-party execution and compilation inside the isolated Linux VM are
permitted. Preserve the exact baseline logs and installed artifacts **before**
any derivative compilation.

```sh
python3 -I kernel/experiments/j716c-mesa-blit-tests/prepare_test.py \
  --source-root "$EXACT_MESA_SOURCE" --output "$FRESH_SEPARATE_TEST_C"
python3 -I kernel/experiments/j716c-mesa-blit-tests/test_prepare.py \
  --source-root "$EXACT_MESA_SOURCE" -v
```

Six original transform controls pass against the already held exact source,
including unchanged driver/source, all original non-policy assertions,
substituted/symlinked source refusals, separate output enforcement and exact
published-patch equivalence. Missing genuine source is an error, not a pass or
silent skip. These controls execute no third-party code.

For a separate VM derivative run, retain the exact baseline artifact/test
receipts, back up the original test, temporarily substitute only the generated
test in the disposable source tree, rebuild its test executable and repeat the
Asahi suite. Record its results separately, restore the exact original test,
and do not put the derivative test in shipping artifacts. The graphics job owns
that VM integration and its final receipts.

Native GPU execution and performance remain NOT RUN. No policy, firmware, boot,
macOS, shipping driver or baseline result changes are authorized by this patch.

## Attributed graphics V3 result

Graphics job 097 V3 completed the exact Mesa build, preserving its unchanged
baseline at **175 OK / 4 FAIL**. The separate test-only derivative then passed
**179/179**, and all six transform/refusal controls passed. The producer reports
that the original test C was restored, with the shipping driver unchanged; its
shipping archive was exported before derivative substitution. No new VM run was
performed by this investigating agent.

I independently read both retained Meson JSON logs and confirmed those counts,
and compared the derivative/original-test/driver hashes to the exact inputs and
our generated derivative. All four copied probe source hashes remain unchanged.
The receipts are in ignored
`build/j716c-community-graphics/build-v3/job/out/mesa/`: `result.json`,
`blit-derivative-source.json`, `blit-transform-tests.log`, `mesa-testlog.json`
and `blit-derivative-testlog.json`. Their hashes are retained in `findings.json`.

This confirms the stale advertisement assertion accounts for the four baseline
failures in this shim environment. It does not qualify GPU pixels, GLES
`glReadPixels`, hardware readback performance, or macOS parity. The production
AGX3 CPU-transfer fallback and all native validation requirements remain.
