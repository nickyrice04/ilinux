# Current native handoff — 31A reviewed; 31B planning only

Read [attempt31b-planning-update.md](attempt31b-planning-update.md).
M1's census 31A is consumed and reviewed: both reset-vector mirrors match the
installed entry; zero cores were started. Do not replay the census.

The next selected experiment is CPU1-only entry and park-loop validation using
the existing installed m1n1. Its RAM controller and bounded request path still
need implementation and offline validation. **No new executable handoff is
ready. Stay in macOS; do not restart or open the proxy for 31B yet.**

The old copy-only 31 pair/profile/collector and full-image SMP candidate remain
held. No Linux launch, chainload, installation, security/default/volume change
or routine policy recheck is requested by this update.

The 31A source manifest is historical and pins the previous version of this
pointer. Its original handoff is retained at `964aaac`; do not rewrite its
hashes or mistake it for a 31B release manifest.
