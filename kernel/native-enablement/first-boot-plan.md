# t6050 first-boot observation and staged-test plan

* **Date:** 2026-10-13 (agent A, goal 5). Builds on
  [`plan.md`](plan.md) §1.2 and §3(a), and the job 020 build artifacts.
* **Status:** preparation only. **No native boot has happened.** Nothing here
  is executed without the user's explicit per-gate approval (coordination.md
  gates N1–N4). Nothing is written to the Mac's storage in the early stages.
* **Separating history from this machine:** m1n1 single-core boot and the SMP
  failure are reported on **M5 Pro** hardware (PRs #610/#652/#661), chip-id
  0x6050. This unit is an **M5 Max**, also chip-id 0x6050. So single-core boot
  here is **Likely, not Confirmed**, and the SMP failure is an inherited
  report, **not** an observation on this machine. The first native session
  tests both.

## 1. What can actually observe an early boot (and what cannot)

The internal UART is not reachable on laptops, so the usual serial console is
out. The channels that work, in order of availability:

| Channel | Works when | Needs | Role |
|---|---|---|---|
| **m1n1 USB proxy** (second machine, USB-C) | before Linux, and alongside it | m1n1 running as the boot object; `m1n1/proxyclient` on the 2nd machine | Primary pre-Linux channel: read registers, load Image/initramfs/DTB into RAM, chainload, trace |
| **Framebuffer console** (simpledrm on mBoot's framebuffer) | once the kernel reaches `simpledrm` + fbcon | our kernel config (`DRM_SIMPLEDRM`, `FRAMEBUFFER_CONSOLE`), the diag initramfs | Primary early-Linux channel: kernel log + diag output appear **on the Mac's own screen** |
| **m1n1 `phram` MTD / its own log** | throughout | m1n1 | Secondary: captures m1n1's and the kernel's early log in RAM for read-back over the proxy |

**Explicitly NOT assumed to work** (each needs a driver or a boot-policy
change we will not make, so none is a bring-up dependency):

* **dockchannel-UART serial console** — needs a Linux `dockchannel-uart`
  driver (does not exist) **and** `csrutil authenticated-root disable` (a
  boot-policy change, out of scope).
* **USB Ethernet / USB host** — needs the t6050 ATC PHY + XHCI bring-up.
* **Keyboard / trackpad** — needs `dockchannel-hid` + DART + MTP firmware
  startup (the parser is hardened; the transport is not up).
* **SSH / network of any kind** — nothing above the framebuffer exists yet.

So the first boots are **non-interactive**: the diag initramfs prints to the
framebuffer and heartbeats; the second machine drives and reads over the m1n1
proxy. No input from the Mac's own keyboard is expected or needed.

## 2. Prerequisites (gate N1 — all user actions)

1. A **current full macOS backup** (Time Machine or equivalent).
2. A **second computer** (Linux or macOS) with Python 3, and a **USB-C
   cable** between the two machines. This is the only way to drive and read
   early boots.
3. In **recoveryOS**, set **Permissive Security** for a **dedicated m1n1 boot
   entry** on a **small separate APFS volume** created in the existing
   container. **No repartitioning, no change to the macOS volume.** This is
   Asahi's normal stub arrangement; the user performs it.
4. Install `m1n1` (pinned `57a9339f…`, `third_party/m1n1`) as that entry's
   boot object, per Asahi's documented procedure.

Recovery from any failure in the RAM stages is the same and total: **hold the
power button to force off, then boot macOS normally.** The RAM stages write
nothing to storage, and the m1n1 stub is on its own volume, so the macOS
install is untouched.

## 3. Staged tests

Each stage lists goal, method, **expected output**, **failure checkpoint**
(what a failure looks like and what it most likely means), and recovery.
Do not proceed to the next stage until the current one passes.

### Stage A — m1n1 proxy connectivity (no Linux)

* **Goal:** confirm the second machine can drive this Mac through m1n1 before
  risking a kernel.
* **Method:** boot the m1n1 entry; on the second machine run the
  `m1n1.proxyclient` shell; read chip-id and a few PMGR registers.
* **Expected:** proxy connects; chip-id reads **0x6050**; `EARLY_UART_BASE`
  and PMGR reads succeed; m1n1 prints the ADT it parsed.
* **Failure checkpoint:** no proxy handshake → m1n1 did not boot or USB device
  mode is down (re-check the stub entry and cable; M5 Max device-mode fix is
  in current m1n1). A hang in m1n1 before the proxy → RVBAR/boot-object issue
  (H1), to be read from m1n1's own log.
* **Recovery:** force off → macOS.

### Stage B — single-core RAM diagnostic boot (the first Linux)

* **Goal:** prove our kernel + DT reach userspace on one core, and read the
  first observables.
* **Method:** over the proxy, load into **RAM only**: `Image` (job 020),
  `t6050-j716c.dtb` (job 020), `initramfs.cpio.gz` (diag). Cmdline:
  `earlycon=... console=tty0 idle=nop arm64.nowfxt pd_ignore_unused
  clk_ignore_unused loglevel=8` (m1n1 adds `idle=nop arm64.nowfxt`
  automatically on M4+). Boot.
* **Expected (on the Mac's framebuffer):** kernel banner, then the diag
  initramfs:
  * `PID 1 reached: the kernel booted and ran userspace.`
  * DT model shows the MacBook Pro / t6050 J716c string (confirms our DT
    loaded, not a stale one).
  * `online_cpus=1`.
  * `MemTotal` roughly the machine's RAM.
  * a 5-second heartbeat that keeps updating.
* **Failure checkpoints:**
  * *Nothing on screen* → kernel did not reach simpledrm, or panicked before
    fbcon. Read the kernel log from m1n1 `phram` over the proxy.
  * *Early SError / panic in AIC init* → the **AIC VM-timer FIQ register may
    be locked on t6050** (plan §3(a) risk #5, H-level). Next action: proxy
    `mrs`/`msr` test of `SYS_IMP_APL_VM_TMR_FIQ_ENA_EL2`; if locked, build the
    capability-guard mitigation and retry.
  * *Hang after "PID 1 reached" with no heartbeat* → userspace stuck (unlikely
    for a static init); re-read the log.
  * *Wrong/garbled framebuffer* → mBoot framebuffer format vs simpledrm
    mismatch; fall back to reading `phram` only.
* **Recovery:** force off → macOS. Nothing persisted.

### Stage C — SMP register observation (diagnose, don't fix)

* **Goal:** find why secondaries don't run, on **this** machine (the plan's
  ranked H1–H4). This is observation, not a register-poking fix.
* **Method:** over the proxy, before/after a secondary-start attempt, read:
  per-core RVBAR / `cpu_impl_reg` (H1), CPU_START `+0x0..+0x14` and the
  per-core PMGR PS registers (H2), and watch m1n1's `cpu_reset` 'O'/'K' output
  (H4). Retest on current m1n1 `main` first (H3 is free).
* **Expected:** one of the hypotheses is confirmed by the register reads
  (e.g. RVBAR locked to a non-m1n1 address → H1).
* **Failure checkpoint:** all reads look correct yet cores still don't run →
  escalates to m1n1-hypervisor tracing of macOS's own secondary start (needs
  0x6050 in the hypervisor CPUSTART table; interpretation must be human per
  Asahi's AI policy, so this is a hand-off to the user, not an agent step).
* **Recovery:** force off → macOS.

### Stage D — NVMe read-only identify (first storage touch, read-only)

* **Goal:** confirm the SARTv4 + M4+ register-split patches bring up ANS far
  enough to *identify* the controller. **Read-only. No writes to the SSD.**
* **Method:** once a single-core shell is reachable (extend the initramfs with
  read-only tools), load `nvme-apple`, read controller identify and namespace
  list. Do **not** mount, write, or touch the macOS APFS volumes.
* **Expected:** the Apple NVMe controller identifies; namespaces enumerate.
* **Failure checkpoint:** ANS init timeout → NVMMU/register-split offsets
  wrong (patch 0005), or SARTv4 shift wrong (0002/0003); compare against the
  macOS-15 firmware-ABI series already in `asahi`.
* **Recovery:** force off → macOS. No writes were issued.

### Stage E and later — input, display, power

Only after C/D. Input needs `dockchannel-hid` (parser hardened this pass) +
DART + MTP firmware; display beyond the framebuffer needs the DCP ABI; power
needs the DVFS/idle work. Each is its own staged effort with its own RAM-first
test. Not detailed here.

## 4. The exact next physical test requiring user approval

**Gate N1 + Stage A:** with a fresh macOS backup, a second computer and USB-C
cable, and Permissive Security set for a dedicated m1n1 stub volume (user
actions), boot m1n1 and confirm the proxy reads **chip-id 0x6050**. This
writes nothing to the Mac and is fully reverted by a power-cycle. It is the
prerequisite for Stage B (the first Linux boot).

Agents do not perform any of gate N1 or any boot. When the user is ready, the
build artifacts from job 020 (`Image`, `t6050-j716c.dtb`, `initramfs.cpio.gz`)
are the RAM payload for Stage B.
