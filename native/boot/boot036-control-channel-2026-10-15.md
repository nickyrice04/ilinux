# boot036: the USB control channel, prepared offline

2026-10-15, M5 agent. **Native boot036 NOT RUN. It must not run before attempt
16 (boot035) reports a stable baseline. Not published, not committed.** Design
and evidence: `kernel/experiments/usb-gadget/README.md`. Draft M1 steps:
`tools/m1n1-client/control-channel-draft.md`. Labels: Confirmed / Likely /
Hypothesis / Unknown.

## What it is

boot035 plus a network link into native Linux over the M1's USB cable, so the
M1 can run commands, read logs and later send the Arch RAM root (roadmap Phase
3, step 2).

| Part | boot036 |
|---|---|
| Kernel | boot034 tree plus `USB_LIBCOMPOSITE=y` and `USB_CONFIGFS=y` (the 14 gadget lines from m to y, nothing else). Genpd ladder and every earlier patch unchanged. |
| Stage-B DT | Three `snps,dwc3` device-mode cores at high speed, DMA through each port's second USB DART (stream 1, as m1n1's own gadget does); those DARTs enabled; all 39 ATC 0–2 power domains disabled so Linux never touches the ports' PHY or power state |
| `/init` | The old diagnostics, then one CDC-EEM gadget per UDC (`1d6b:0104`), IPv6 link-local only, dropbear (root, key only, no forwarding, host keys in RAM), a per-heartbeat status line |
| Unchanged | m1n1, the full DT, the generic initramfs, the launcher and its fixed arguments |

The Linux end of port N is `fe80::69:6cff:fe69:6e0N`. No IPv4, no routes, no
DHCP: the M1 needs no configuration.

## Results

### Build (VM job 041), all Confirmed

* **Config:** against the config that built boot035's Image, exactly the 14
  gadget symbols changed, all m to y.
* **A finding about earlier packages:** the `kernel.config` shipped since
  boot024 is job 020's. The tree that built boot024–035 re-detected the
  toolchain, so it differs from the shipped file in 8 rustc-detection lines
  (`RUSTC_VERSION`, `RUSTC_LLVM_VERSION`, `RUSTC_LLVM_MAJOR_VERSION`, five
  `RUSTC_HAS_*`) and in no real option. boot036 ships its true build config;
  the manifest lists those 8 lines. The packager now enforces this for every package
  (`native/boot/kernel-config-provenance-2026-10-15.md`).
* **Image:** 44,681,728 bytes (+80 KiB). ELF/Image roundtrip, and the gadget,
  configfs, dwc3 gadget and genpd ladder symbols are all present.
* **DT:** byte-identical built in the VM and on this Mac
  (`a676087b…`, 62,043 bytes). `dt-validate` reports nothing, before or after.
  The other session's domain audit (`kernel/experiments/usb-gadget-dt/audit_domains.py`)
  reports no ATC 0–2 domain registered or releasable and none deferring
  forever; 137 domains register and 101 remain for the release ladder.
* **Packages:** from the official ALARM mirror. All 9 shipped packages are
  signature-validated: busybox 1.36.1-4 (static), dropbear 2026.94-1, glibc
  2.43, libxcrypt 4.5.2, zlib 1.3.2, plus filesystem, iana-etc,
  linux-api-headers and tzdata.
* **16 KiB pages:** every ELF file in the initramfs and the overlay (22) is
  aligned to 64 KiB.
* **Initramfs:** 2,392,573 bytes (boot035: 302,464). That adds about 0.4–0.5 s
  of upload over the proxy at 4–5 MB/s. It passes the contract: static `/init`,
  merged `/usr`, root-only files, no set-id file, no self-test, no private key,
  exactly one authorized key.

### Package, Confirmed offline

`ilinux-j716c-boot036.tar.gz`, 18,902,665 bytes, SHA-256
`521ffd6db16de49cd7a47fe30ed8930b33354bd7b0449e83b5cf8b5cd16acb60`, in ignored
`build/native-boot036/` (manifest and digests in `build/native-boot036/record/`;
the committed boot035 handoff files are untouched).

* `make-package.py` checks the exact DT, config, init-source and initramfs
  deltas against boot035.
* The unchanged launcher's offline verification reports `Package PASS`.

### Boots on this Mac (Virtualization.framework, one CPU, no disk or network)

These are generic VMs. They test our kernel and userspace, not the M5's dwc3
cores, DARTs, PHY or AIC.

| Run | Result |
|---|---|
| Shipped Image + shipped initramfs, launcher arguments with `console=hvc0` | **PASS.** PID 1 at 0.19 s, one CPU, the control channel reports no UDC (expected: no dwc3 here) after its 10 s wait, dropbear started, heartbeats every 5 s, the 60-second message at 70.2 s |
| Test Image (adds dummy_hcd, usbnet, cdc_eem) + shipped initramfs + overlay | **PASS** (`[selftest] PASS`, `selftest exit=0`). Details below. |

Self-test details:

* The gadget bound to `dummy_udc.0` (port 4) as EEM `1d6b:0104`. The kernel's
  own `cdc_eem` host driver enumerated it, and the UDC reached `configured`.
* The gadget side got `fe80::69:6cff:fe69:6e04`. From a separate network
  namespace, ping worked.
* SSH with the key returned `SSH-OK 7.1.9-g863199d8b4a3-dirty ilinux-j716c uid=0`.
  dropbear logged a host key generated in RAM and "Pubkey auth succeeded for
  'root'".
* Without the key: "No auth methods could be used", with no password prompt.
* An 8 MiB random file arrived intact over SSH.

## Independent review

A separate reviewer read every new file before the boots. Its findings:

* The only one that would have misled us: the test runner expected the SSH
  line to start with `SSH-OK`, but dbclient prints its host-key note first.
  The runner pattern is fixed; the self-test itself was right.
* Two job-script hardenings were applied: the signature count no longer
  depends on pacman's exact wording, and the hook comment is accurate.
* Nothing serious in `init.c`, the staging, the checks or the self-test.

## Open before attempt 17

1. **Attempt 16 first.** If it shows another domain that resets the SoC,
   boot036 is rebuilt on the fix.
2. **SSH key (the user's decision).** This package authorizes a test key
   generated by job 041 (`SHA256:Ql34eFTM…`), whose private half is only on
   this Mac. Proposed: the M1 makes its own key and commits only the public
   half as `kernel/experiments/usb-gadget/authorized_keys`; job 041 then
   rebuilds and only the initramfs changes.
3. **M1's macOS** must have `AppleUSBEEM.kext` (2/12/7) like this M5 (Unknown).
4. **Hypotheses that only attempt 17 can test:**
   * the dwc3 cores probe on the PHY state m1n1 leaves;
   * one DART instance suffices. If not, use both instances as the other
     session's candidate does (`kernel/experiments/usb-gadget-dt`);
   * the DARTs work without `apple,dma-range`;
   * macOS binds EEM and configures IPv6 on the new interface.
