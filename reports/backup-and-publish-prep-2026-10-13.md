# Backup and publish preparation (goal 6)

Prepared 2026-10-13 by agent A. This is a plan for the user to act on, not an
executed change. It separates two targets with very different requirements:

* **Private backup repo** (the safety net the user asked for): blocked on
  **one** thing — a history rewrite to drop oversized generated blobs.
* **Public repo**: additionally needs a scrub, licences, and a decision on
  Apple-derived data.

## 1. The one hard blocker (both targets): oversized blobs in history

Three synthetic Core ML weight files are in git history. GitHub rejects any
push containing a file over 100 MB **anywhere in history**, even to a private
repo, so the backup cannot be pushed until they are removed from history.

| File | HEAD size | In pack |
|---|---|---|
| `…/macos-2026-10-11-coreml/ffn.mlpackage/…/weight.bin` | 512 MB | shared |
| `…/macos-2026-10-11-power/coreml-pkgs/ffn.mlpackage/…/weight.bin` | 512 MB | (dedup) |
| `…/macos-2026-10-11-coreml/conv.mlpackage/…/weight.bin` | 128 MB | |

Total pack is ~590 MB; these blobs are nearly all of it.

**They are safe to drop:** they are synthetic, built with a fixed seed
(`np.random.default_rng(0)`) by `benchmarks/ai/coreml_ane_bench.py`, so they
regenerate byte-identically. AGENTS.md already forbids committing models; the
only reason they were committed is that `.gitignore` covered
`benchmarks/ai/models/` but not `.mlpackage` under `results/`.

**Done already this session (safe, reversible):**

* `.gitignore` now ignores `*.mlpackage/`, `*.mlmodelc/`, `weight.bin`.
* The 9 tracked `.mlpackage` files are untracked from HEAD (`git rm --cached`;
  they remain on disk and regenerate). HEAD no longer carries 1.1 GB.

This does **not** fix history — old commits still contain the blobs. The
rewrite below is still required before any push.

### History rewrite procedure (needs user approval + the `git-history` lock)

A history rewrite changes **every commit hash**. On this shared working tree
it is destructive to any other agent mid-commit, so it must run only when:

1. the user approves;
2. `tools/lock.sh acquire git-history …` is held;
3. the other agents are idle and told (coordination.md);
4. it is the last step before adding the remote and pushing.

Preferred tool is `git-filter-repo` (not installed; `pip install
git-filter-repo` into the workspace venv, or `brew install git-filter-repo`
— a host install, so user-approved):

```sh
# from a fresh clone or with everyone idle, lock held:
git filter-repo --invert-paths \
  --path-glob '*.mlpackage/*' --path-glob '*/weights/weight.bin'
```

Fallback without installing anything (slower, keep a backup clone first):

```sh
git filter-branch --index-filter \
  "git rm -r --cached --ignore-unmatch '*.mlpackage'" \
  --prune-empty -- --all
```

After either: `git reflog expire --expire=now --all && git gc --prune=now
--aggressive` → pack should drop to a few tens of MB. Verify with
`git rev-list --objects --all | git cat-file --batch-check='%(objectsize) %(rest)'
| sort -rn | head`.

**Alternative that avoids a rewrite entirely:** start the backup from a fresh
`git init` snapshot of the current tree (one commit, no history). Loses the
commit history but is simplest and carries zero oversized blobs. Reasonable
for a pure safety-net backup; the rewrite is better if the history matters.

## 2. Scrub (needed only for a public repo)

A private backup does **not** need this. For public:

* **Local path / email** in 4 tracked files — replace `/Users/nickyrice` and
  the email with a neutral placeholder:
  * `benchmarks/results/macos-2026-10-11-ac-lpm/ai-llamacpp.jsonl`
  * `benchmarks/results/macos-2026-10-11-mlx/mlx.log`
  * `benchmarks/results/macos-2026-10-11-power/power.jsonl`
  * `research/rea/rea-analysis.md`
* **Test VM password** `omarchy:omarchy` (set in
  `virtualization/jobs/009-omarchy-install/run.sh`, referenced in two READMEs
  and the autologin conf). It is a throwaway for a local, NAT-only test VM, so
  low risk, but for a public repo either note it as a default users must
  change, or parameterise it.
* **Hardware identifiers: verified clean.** `hardware/scripts/adt_extract.py`
  redacts the values of `serial|uuid|udid|nonce|…|die-id|mac-address`; those
  strings appear in `adt-sanitized.json` only as denied-key *names*, never
  values. No serial, ECID, UUID or MAC is present.

If the scrub strings must also leave history, fold them into the same
`git-filter-repo` run (`--replace-text`).

## 3. Licences

| Part | Licence | Why |
|---|---|---|
| `virtualization/qemu/patches/qemu/*` | GPL-2.0 | diffs against QEMU (GPL-2.0-or-later) |
| `virtualization/qemu/patches/virglrenderer/*` | MIT | virglrenderer is MIT |
| `omarchy-arm64/packages/mesa-virgl-video/patches/*` | MIT | Mesa components here are MIT |
| `omarchy-arm64/kernel/vmpoll/*` | GPL-2.0 | Linux kernel module (already SPDX-tagged) |
| `kernel/patches/t6050/*` | GPL-2.0 | Linux kernel patches |
| Our tools, benchmarks, docs | **user's choice** (MIT is simplest) | original work |

**To do:** add a top-level `LICENSE` (e.g. MIT for our own code) and a short
`NOTICE`/README section stating the per-directory licences above, so the
GPL/MIT derivative patches are correctly attributed. SPDX headers on our
source files are nice-to-have.

## 4. Apple-derived data (public-repo decision)

`hardware/adt/adt-sanitized.json`, `hardware/macos/*.tsv`,
`reverse-engineering/findings/rea-native-2026-10-13/*` and similar are
sanitized metadata derived from the user's macOS install. They contain no
secrets (verified), but for a public repo the user may prefer to publish the
summaries and keep the raw inventories private. No blocker either way.

## 5. README framing for a public repo

State plainly: this is a **VM toolkit on macOS**, not native Linux; it is
**AI-assisted** (so not upstreamable to Asahi or QEMU as-is); and it is
**unaffiliated** with Asahi, Omarchy, Apple or Mesa.

## Recommended order

1. **Private backup now:** user approves → either (a) fresh-snapshot `git
   init` (simplest), or (b) history rewrite under the `git-history` lock with
   agents idle. Then create a **private** GitHub repo and push.
2. **Public later:** scrub (section 2) + `LICENSE`/`NOTICE` (section 3) +
   Apple-data decision (section 4) + README framing (section 5).

Creating and pushing to GitHub needs the user's account and go-ahead; agents
do not push to remotes without it.
