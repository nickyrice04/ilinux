# Direct31AH kernel reproduction — offline build

This job builds the exact public Linux source revision named by the November 11
J716c operator, with a **reconstructed diagnostic configuration**. The operator's
resolved config and original image hashes are unavailable. A successful build
therefore does not reproduce their binary image or prove native compatibility.

Inputs:

- Linux `dc8f6f77934b471a13c91e7780e2d91ebc904b3d`, source archive SHA-256
  `0a8ae9d9529a4ff1754bcc4294d68cffbd449d82cc1a4a1ecf3aaec1a63a46dd`.
- `arch/arm64/configs/asahi.config` from that revision, merged after ARM64
  `defconfig`, then this job's `diagnostic.config`.
- The matching Aura track is revision
  `bd9f3e8273dc79ae9095c19c2c4f32218446ad4e`; its build and handoff are separate.
- Exact board/chip tuple `Mac17,6 / J716c / T6050`; this job rejects a different
  static CPU inventory. It preserves twelve M cores and six P cores, and their
  upstream capacity distinction. Those capacities are source values, not local
  measurements.

Run only inside the existing isolated ARM64 Linux build VM. Mount the repository
read-only as `/mnt/ilinux`, the source archive read-only as `/mnt/inputs`, and a
writable job directory as `/mnt/job`. Do not put the build on the nearly full
guest root. `run.sh` uses `/mnt/job/work/direct31ah-kernel/linux` and
`/mnt/job/work/tmp`; it preserves existing build trees outside that directory.

The caller writes `/mnt/job/out/inputs.json`:

```json
{
  "source_commit": "dc8f6f77934b471a13c91e7780e2d91ebc904b3d",
  "archive": "/mnt/inputs/linux-dc8f6f77934b.tar.gz",
  "archive_sha256": "0a8ae9d9529a4ff1754bcc4294d68cffbd449d82cc1a4a1ecf3aaec1a63a46dd"
}
```

Dependencies are native AArch64 GCC/binutils, make, flex, bison, bc, OpenSSL
headers, dtc, Python 3.14+, tar/gzip, and static libc/pthread development files.
Python 3.14's tar data filter bounds archive extraction. The job records actual
tool versions and compiler elapsed time; `JOBS` defaults to six. All third-party
source execution/compilation takes place in the VM.

```bash
JOBS=6 bash /mnt/ilinux/virtualization/jobs/095-direct31ah-kernel/run.sh
```

Outputs include the full ARM64 16 KiB `Image`, resolved config, upstream board
DTB, diagnostic derivative DTB, all built modules in a separate review archive,
and a tiny original static diagnostic initramfs. They remain ignored build
artifacts. The upstream DTB contains a publisher's embedded per-unit Thunderbolt
DROM: **do not publish or ship that upstream artifact**. The diagnostic derivative
removes both that property and the placeholder DROM, and disables USB4, SEP and
ISP nodes while retaining the USB2 control path. It does not modify source.

The profile enables `ARM64_CTXR_EXECMEM`, ARM64 ACTLR state, SMP, spin-table DT,
Apple CPU frequency/idle, USB gadget and simpledrm paths. `RFKILL=y` is explicit:
an inherited `RFKILL=m` silently caps CFG80211 and the T6050 N1 driver at modules.
The resolved config check rejects that loss of built-in support.

**Confirmed source gap:** this exact revision's `dwc3_apple_host_only()` rejects
T6050 device mode. Its T6040/T6050 PHY support is host-only. The operator reported
an additional local USB2 CDC change that has not been provided, so the USB log
gadget is prepared but **not a reproduced working control connection**. The
T6040 host PHY remains a separate module outside the root. Do not remove the
host-only guard as a shortcut: device-mode PHY initialization must be qualified.
The initial CPU observation can also use the framebuffer/webcam, independently
of USB. A real native candidate needs that observability reviewed first.

The SEP driver, Rust/GPU/ANE, audio/camera, USB4, hibernation and APFS/HFS drivers
are disabled. The exact public SEP Kconfig warns about automatic keybag/xART
writes; it is intentionally excluded. Apple NVMe/SART are compiled as modules
for later review but **no modules are shipped in the diagnostic root**, and no
module loader or storage mount exists there. There is no Wi-Fi firmware,
calibration, credentials, DHCP client or SSH server in this root; N1 runtime
networking remains a separate qualification.

Checks include resolved policy, source archive pin, static eighteen-core DT
topology, malformed-input rejection tests, a real static C collector selftest
inside generic Linux, image header/page size and a deterministic root whitelist.
The 128 MiB image fit check is necessary but does not qualify Aura's live
executable-window allocation, relocations or module execution.

No command in this job installs a boot object, modifies a policy/volume, restarts
a machine, or boots the produced kernel. Native readiness is explicitly false
in `artifacts.json`. Follow the separate reviewed M1 handoff after the remaining
firmware, exact recovery/rollback and loader gates are satisfied.

`input-source-files.json` binds the recipe and original helper bytes at job
start. A final comparison refuses output publication if those inputs changed
during compilation; rerun the cached job after any necessary source fix.
