# Job055: final-copy experiment

Uses the existing workspace Arch VM; no native hardware access. All output is
ignored/private. Source patches are original; downloaded upstream code executes
only inside the VM. Do not run while another agent holds `vm` or `quiet`.

Select `build`, `bench`, `integration`, `images` or `checks` by placing that
single word in `out/mode`, then use `tools/vm-job.sh` with owner
`codex-desktop31`. `integration` needs `VZRUN_EXTRA='--gui --size 3456x2160'`.
Acquire/release the quiet lock for timing runs. Always check the guest exit in
`out/run.log` as well as the host wrapper's status.

* `build.sh`: GCC Release/O3 CMake build of the pinned Hyprland source with
  `NO_HYPRPM=ON`; installs a missing scanner tool only in the VM. Resolves the
  pinned udis86/protocol submodule archives; CMake uses glaze v7.2.0. Source
  and toolchain details accompany the public validation record.
* `bench.sh`: original GLES3 conformance/timing matrix, 64 comparisons across
  two sizes, both Y orientations, RGBA/RGB output and eight damage rectangles.
  Timing uses 2 warm-ups and 6 samples in each arm of an off/on/on/off sequence.
* `integration.sh`: exact retained Omarchy userspace in a RAM chroot, compiled
  candidate, software GL on vCPU0. A headless output avoids relying on the
  VZ virtual-DRM presentation path. Startup settles for 25 seconds, then the
  crossover and FP16/resolution/rotation fallback controls run. The original
  client/sampler are reused from job054. This is not a native GPU test.
* `images.sh`: unpack the verified attempt28 pair into VM RAM, replace only
  Hyprland and add the six experiment assets plus their manifest; pack a new
  root and update stage one's pairing pin. No package upgrade or login change.
* `checks.sh`: offline launcher/collector tests and artifact/toolchain checks.

The full two-stage boot test reuses job049's existing harness with `JOB_OUT`
pointing at this job's private pair-test directory. It uses a VM test kernel
and dummy USB, never the real M5 controller. Its framebuffer is 3456x2234,
which correctly leaves the candidate ineligible; native-sized copy correctness
is checked separately by the 3456x2160 headless integration.

Source inputs are local, ignored downloads:

| Project | Revision |
|---|---|
| Hyprland | `efb50993780079460b0cbed1363e2166a2de1d9f` |
| udis86 | `5336633af70f3917760a6d441ff02d93477b0c86` |
| hyprland-protocols | `bd153e76f751f150a09328dbdeb5e4fab9d23622` |

Failed early harness/build iterations are retained privately and described in
`native/boot/attempt31/validation.md`. No timing result is promoted merely
because callbacks completed; path activation and equality are required.
