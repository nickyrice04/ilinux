# Attempt30 — independent M1 offline readiness

**Offline ready with documented limits, 2026-10-20. Native/live NOT RUN.**

M1 pulled **`cfebfb7`**, verified the 163,840-byte desktop30 bundle
(`26a36600…1f07`), all four regular members, asset manifest and byte-identical
collector source without extraction/execution. Retained attempt28 images freshly
rehashed with embedded pins PASS; boot042 thirteen files and all 37 source pins
PASS. Desktop-latency eight-line offline launcher and root sender dry-run PASS;
clean client `57a9339`, eleven helper pins, SSH config/operator key and fresh
no-forwarding config checks PASS. **127 methods PASS / 2 absent legacy-fixture
SKIPS**, no source/test repairs. Native/live/latency NOT RUN; launches/root/
bundle sends 0 and no real window armed. Human confirms M1 restart and proxy,
cable/power/unlocked/lid/recording/timer. One new authorized run follows this
published readiness; no earlier collector replay or module/settings operation.
Evidence: `native/boot/attempt30-m1-offline-2026-10-20.md`.

## Exact checks and scope

* Bundle 163,840 bytes, SHA-256
  `26a36600de24360b744728aef2af1cf0b8176be172fd51b0b58f48a8bbee1f07`.
  Four regular members only: frameprobe, samplecpu, collect.py, assets.json.
  Member hashes equal `attempt30/assets.json`; collector byte-identical to Git.
  Verified before moving the root-delivered archive into ignored build/attempt30.
  No bundle binary executed, file extracted, VM or proprietary artifact opened.
* Stage one 60,671,683 bytes,
  `65ea381524f266c78da0f98d42451f46fd48c94455d0734f1f6022c1d8f08c39`;
  root 2,469,319,544 bytes,
  `59a7383e4b6cd47712e5dc05998ab34a58d511edc0b7ee016b267a15d4fb2b78`.
  Whole hashes, embedded root/Image pin, 215,521 entries and 11,012,784,128-byte
  expanded budget PASS. The previously native-tested pair is reused, not rebuilt.
* Boot042's 13 files reverified against manifest
  `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd`;
  installed boot021 remains unchanged. Clean client pinned to
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
* All 37 source/procedure pins PASS, including the source-pinned checklist,
  receiver/client/sampler/collector, bundle/REA/VM records and additive launcher
  change. New launcher `77846bc7ecd1a73aca92f031d377be800314d5b1b9e9ceebbe3fa452daf018e1`.
  Diff adds desktop-latency to the same exact payload/DT/one-core safety guards.
* Offline launcher exactly eight expected lines: package/root/key/profile PASS,
  OFFLINE ONLY, same userspace governor/one-core arguments and m1n1 append,
  105,351,258 upload bytes, 300s deadline. Sender dry-run verifies the root
  without opening a connection. No actual USB/SSH, known-host clearing,
  sampler event or observation window during intake.
* Eleven retained reader/pipe/helper digests, exact SSH config, derived operator
  public-key equality and fresh `ssh -G` no-agent/X11/control-master/forwarding
  assertions PASS. No private key or fingerprint is printed or published.

| M1 suite |Pass |Skip |Process exit |
|---|---:|---:|---:|
|CPU/memory/desktop observation profiles |57 |0 |0 |
|Earlier RAM-root profiles |43 |2 |0 |
|Desktop bundle/frame/timeout/native guards |14 |0 |0 |
|M1 collector/key/deadline |13 |0 |0 |

The two missing legacy fixtures are boot035 Image and boot040 Image/DT; they
remain skips. Current exact-payload/fake-handoff desktop-profile tests execute.
All eight independent checks exit 0. No test/code correction or failed check.
M5's separate VM sanitizer/receiver/REA evidence and retained harness failures
remain separately labeled; they were read, not independently rerun on M1.
Sampler support, native callbacks/IPC/sample categories, timings and human
responses remain unknown. Missing CPU sampler support is a supported limited
result, not permission to enable kernel or hardware-PMU features.

## Authorized next step

The human already restarted M1, booted the existing lab to Running proxy and
confirmed cable/power/unlocked/open-lid/video/timer readiness. This readiness
record itself has launches/root sends/bundle sends 0; publishing it precedes
execution. Follow only the attempt30 checklist and the human's current start.
One desktop-latency boot, one root send, one userspace bundle delivery; no CPU28
or memory29 module. Fixed 600s window armed at root switch, with a visible human
return timer. Two automatic fullscreen controls precede exactly one 45s human
menu/terminal/type omarchy (without Enter)/file-manager observation. Preserve
all warm-ups, outliers, partial/unavailable/lost/unmapped evidence.

No frequency, renderer-policy, idle, controller, module, extra-core, storage,
Wi-Fi, boot/security/default/volume or firmware change. Macintosh HD/default/
Full and lab Permissive remain last reported; routine checks waived. No native
speedup, energy/thermal headroom or macOS parity claimed. Raw receipts, archive,
images and any future journals/video/keys remain private in ignored build.
