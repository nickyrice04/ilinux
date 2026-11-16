# Stage1 storage and RAM routes without a new partition for 31AY

Reviewed November 16, 2026, using exact public Aura9da source as data. No
host volume, object, transport or hardware query and no VM action ran.


The newly built generic `RELEASE=1 CHAINLOADING=1` Stage1 is not a drop-in
boot package for the current Lab. Exact9da's factory configuration block has
no ESP target; a **bare** factory image is therefore a proxy image. Filling
it requires a private ESP PARTUUID and relative Stage2 path (normally
`m1n1/boot-ctxr.bin`). Its storage chainloader and direct `boot=` path read
an NVMe/FAT partition. The Lab's APFS Data directory is not that ESP, and no
new Linux ESP/partition has been approved. Do not invent an ESP binding or
silently substitute the Lab APFS path.
[Factory/filled configuration](https://github.com/cameroncooper/aura/blob/9da61857f9d9262bd64c023fbc1b18315b12d0af/src/stage1_config.c),
[NVMe chainloader](https://github.com/cameroncooper/aura/blob/9da61857f9d9262bd64c023fbc1b18315b12d0af/src/chainload.c#L361),
[storage boot loader](https://github.com/cameroncooper/aura/blob/9da61857f9d9262bd64c023fbc1b18315b12d0af/src/boot_storage.c#L207),
[actual FAT/NVMe backend](https://github.com/cameroncooper/aura/blob/9da61857f9d9262bd64c023fbc1b18315b12d0af/rust/src/chainload.rs#L162).

Two public source mechanisms could avoid a new partition for a future RAM
experiment, but neither is a qualified launcher in this work:

1. **Bare proxy plus RAM upload.** The code contains CDC/KIS proxy fallback
   and a matching host chainloader. Its T6050 run-base mode explicitly checks
   J716c/model/board, EL2, revision-3 BootArgs, parked secondary CPUs, inherited
   CTXR bounds and memory/firmware placement before staging raw Aura above the
   live heap and executing it at the resident base. This is useful existing
   implementation to adapt, not permission to run the upstream script. The
   current boot021 host ABI, new Aura ABI, actual M1 carrier/routing, upload
   readback and one-shot ownership must first be matched and reviewed.
   [Public board-guarded RAM chainloader](https://github.com/cameroncooper/aura/blob/9da61857f9d9262bd64c023fbc1b18315b12d0af/proxyclient/tools/chainload.py),
   [fallback decisions](https://github.com/cameroncooper/aura/blob/9da61857f9d9262bd64c023fbc1b18315b12d0af/src/stage1_proxy.c).
2. **A new direct composite Mach-O.** The payload parser supports an inline
   kernel, compatible DTB, initramfs and chosen-variable records without
   `chainload=` or `boot=`. A reviewed image composed from the matching
   graphics Aura and a minimal RAM root could therefore load without an ESP
   or a live upload channel. It would be a new candidate with its own
   parser/layout/build/enrollment receipts, not the bare generic Stage1 or a
   relabeled historical image. Kernel placement, CTXR reservations and
   DT/initrd overlap require explicit validation. Inline DT/initrd pointers
   are not universally relocated automatically; supported compression paths
   can allocate decoded payloads in the heap, but their actual composition
   and bounds still need tests. Do not simply append the large Omarchy root
   to the current 153 MB artifact.
   [Inline and compressed payload behavior](https://github.com/cameroncooper/aura/blob/9da61857f9d9262bd64c023fbc1b18315b12d0af/src/payload.c).

Aura's T6050 CDC implementation exists but explicitly logs its link as
unverified. The documented guarded CDC hardware workflows qualify J813 and
J873g, not J716c. Conversely, the publisher's **Linux** USB serial failure is
not proof that Aura's distinct KIS proxy cannot work. Keep these transport
layers separate and require live evidence for the actual chosen carrier.
[T6050 CDC source](https://github.com/cameroncooper/aura/blob/9da61857f9d9262bd64c023fbc1b18315b12d0af/src/usb.c#L193),
[qualified CDC workflow scope](https://github.com/cameroncooper/aura/blob/9da61857f9d9262bd64c023fbc1b18315b12d0af/docs/cdc-boot.md).

Both options still need the matched firmware, safe runtime DT, private local
firmware provisioning, physical watchdog/manual rescue and a new reviewed
transaction. The [watchdog contract](../native/stack/j716c-community/watchdog-contract.md)
documents the separate pre-Linux coverage gap. Build success for a generic
Stage1 or Stage2 establishes none of these deployment conditions.
