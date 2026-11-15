# M1: offline review of the complete 31AP read-only diagnostic

No restart yet. Do not stage files, start a page server/camera/proxy, run live
inspection, enter Recovery, mount anything, install/restore or change settings.
M5 owns the next physical handoff after this review.

## Why this is the next check

31AM's actual owned read-only Preboot mount and cleanup passed, then its policy
parser refused. REA qualified the missing fields and exact true conjunction.
The owner ran 31AO against both complete desktop outputs: both proposed C
parsers pass, both old parsers reject; unknown/malformed text rows are zero.
See the safe result in native/boot/attempt31ao/desktop-result-2026-11-15.json.
Do not request another partial desktop probe or repeated routine policy check.

31AP integrates that exact repair into the full read-only companion. The core,
admission rules, Preboot engine, CLI, outer validator and old diagnostic support
stay exact. It has genuine complete positive initial-admission/cleanup fixture
coverage using original 31AF bytes inside synthetic framing, not mocked identity.
Actual Recovery pairing/security/selected-path checks still remain physical.

## Review and verify

1. Pull the commit containing this handoff. Verify
   native/boot/attempt31ap/source-sha256.txt: all 140 entries, including the
   111 retained AM inputs, 14 AO inputs and both retained inventory hashes.
   Preserve all old evidence, profiles, kits, receipts and consumed state.
2. Review native/boot/attempt31ap/findings.md and build.json, the three new
   files under tools/boot-object31ap-native, and five under tools/recovery31ap.
   Check exact source reversal and unchanged mount/cleanup/CLI/result behavior.
3. Inspect the scratch-name contract: the original `ilinux31am.` WORK_BLOCK
   must remain byte-identical. A 31AP temporary-name substitution would refuse
   in the frozen engine. New kit destination/shell/page names are intentional.
4. Review the focused 19 native controls, including real 31AF recognition,
   final admission, actual result validation, renderer-derived scratch path,
   stable reread mutations and cleanup-failure override. The M5 record includes
   normal and ASan/UBSan runs. Prior engine and 31AO suites are reused.
5. Review/run the 9 package and 6 renderer controls as useful. Avoid repeated
   old suites, production default/help invocations or unrelated artifact builds.
   If you independently compile native tests, use a new output directory and
   an already held verified original 31AF reference. Never synthesize a fake
   identity or use real Apple manifest data to manufacture a positive result.

## Exact two-file kit and inert page

The new M5-local kit is `build/ilinux-31ap-diagnostic`. Git contains original
source/public profile and receipts, not compiled binaries. If the exact kit is
not already available on M1, report that transfer is pending; use the established
private file-sharing method. It is a tiny original-helper/profile kit, not the
large Linux image. Verify bytes and hashes against delivery.json before use.
Do not substitute your compiler's helper for the M5 pin.

After that kit is privately present, prepare a new workspace page path and
check it inertly. These commands do not start a server or run the helper:

```bash
python3 -I tools/recovery31ap/package.py --prepare \
  --kit build/ilinux-31ap-diagnostic --output build/31ap-m1-review-page
python3 -I tools/recovery31ap/package.py \
  --page build/31ap-m1-review-page/recovery.html --check-only
```

Compare the generated profile, whole paste and page to M5's offline preparation
receipt. The page must be titled **31AP typed-policy Preboot check**, contain
one complete box and pass bash syntax. No clipboard demonstration is needed.
The later human flow is one whole-box copy, browser quit and one Terminal paste.
Native 31AM/31AL output-schema labels are expected; the shell/page say31AP and
the exact helper/profile hashes identify the new integration.

Record source/kit/page verification, focused test outcomes, limits and findings
in a new M1 review. Keep actual Recovery/mount/install/restore/Linux/SMP and
performance marked NOT RUN. Do not publish private paths, LAN addresses, raw
policies, identifiers or media. Boot021 restoration is still OUTSTANDING;
Macintosh HD remains the human-confirmed desktop/default and Full invariant.

A PASS requests no physical action. M5 first assesses your review and prepares
the concrete staging/paired-Recovery handoff. This read-only package cannot
install a boot object, restore boot021 or authorize a Linux boot by itself.
