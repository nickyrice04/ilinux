# Attempt30 VM evidence qualification — 2026-10-21

This addendum preserves the original records and their source hashes. It does
not change M1's native attempt30 result or authorize a replay.

Review of job054's retained `exact-internal.log` found repeated
`eglQueryDeviceStringEXT` errors, failure to create Aquamarine's DRM renderer,
and `Failed to update renderer state for Virtual-1 on applyCommit` throughout
the VM run. Pinned Aquamarine v0.15.1 source narrows the interpretation: in
`SDRMConnector::commitState`, `applyCommit` follows a successful backend commit;
`applyCommit` logs this error if `updateSecondaryRendererState` fails and does
not turn the successful commit into a failure. On the primary backend the
auxiliary renderer can fail initialization without `shouldBlit()` being true.
Thus these lines **do not prove that display commits failed**. An initial
working diagnosis to that effect was too strong and is withdrawn.

**Qualified interpretation:** the 40 callbacks, CPU samples, IPC measurements,
sanitizers, identity refusals and receiver checks remain observations of those
components. They do not independently establish when the virtual display showed the frames. The repeated auxiliary-renderer retries may also affect VM timing.
The callback timing table in `validation.md` and `vm-observation.json` must not
be used as a successful presentation baseline or a native performance ratio.
The earlier preliminary color-management comparison is also insufficient to
exclude that path as a native contributor.

Attempt30's separate native report records successful visible typing and
persistent delay. Its measured CPU/callback/IPC data remain native evidence;
callbacks still are not photon timestamps. Anonymous executable samples remain
unattributed. No native speedup or energy-parity claim was made or established.

Subsequent tests must distinguish offscreen/headless pixel correctness from
display presentation, distinguish auxiliary-renderer errors from actual commit failures, and preserve failed
harness iterations. The final native display remains a physical-hardware
validation gate.
