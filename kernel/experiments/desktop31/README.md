# Opt-in final-framebuffer copy

Original Linux experiment; see [PLAN.md](PLAN.md) for the attempt30 diagnosis
and the wider CPU/GPU/network/storage path. Native test instructions are
`tools/m1n1-client/attempt31-instructions.md`.

The pinned Hyprland `OpenGL.cpp::end()` renders its working framebuffer into
the output framebuffer through a passthrough textured quad when no color
conversion or final effect is required. Under llvmpipe that operation runs on
the CPU. `ILinuxCopy31.hpp` substitutes a GLES framebuffer copy only when the
geometry, projection, formats and software renderer meet its narrow contract.
Damage rectangles retain their existing buffer-age semantics. The existing
shader branch remains the fallback.

The first eligible frame for each source/destination framebuffer pair is drawn
both ways and compared across every output byte. Readback stays in memory;
no pixels are saved. Errors or unequal output disable the candidate for that
session. The experiment is limited to eight verified pairs and the 3456x2160
unrotated output. It starts disabled (`debug:ilinux_copy31=0`), leaves visual
effects/color settings intact, and writes only bounded numeric records to a
new mode600 file in the user's RAM runtime directory. An existing log path
refuses activation, including symlinks.

`apply.py` verifies the two source-file digests before applying the patch.
The public upstream commit is
`efb50993780079460b0cbed1363e2166a2de1d9f` (Hyprland 0.56.2). No Apple bytes,
pseudocode, register sequence or copied proprietary algorithm is involved.
Hyprland is BSD-3-Clause; the original helper has that SPDX identifier.
`copybench.c` is a separate original MIT test. Other original files here are
provided under the repository's code license.

The runtime collector uses the unchanged attempt30 client/sampler code, with
off/on/on/off ordering and four warm-up callbacks per control. It verifies
actual native hardware, exact running binary, unchanged keyboard/damage
settings and absence of previous diagnostic modules before enabling the copy.
It then requires successful pixel checks and nonzero copy counts before the
human phase. The finalizer and the supervisor's independent `ExecStopPost`
both reset the option to zero. No automatic module load, frequency change,
desktop restart, installation or persistent filesystem operation is performed.

The new root is the exact retained attempt28 root with `/usr/bin/Hyprland`
replaced and `/usr/local/lib/ilinux-desktop31/` added. Its package database is
unchanged: the executable SHA, not `pacman -Q` alone, identifies this experiment.
The reference run uses the original draw branch in the same experimental
executable; it is not a comparison between two different package builds.

Offline tests found about 25% lower full-frame callback medians in a headless
VM crossover. Small-damage medians remained around 16.7 ms there. This does
not predict elimination of the native 256 ms small-damage floor, prove physical
presentation or explain every application startup. Native responsiveness,
stability and energy use still require measurement. The optimization stays
opt-in even if one native crossover is successful.
