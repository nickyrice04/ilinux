# 31AN policy-schema observation

31AM's read-only Preboot mount and cleanup succeeded. The unchanged collector
then refused lab policy at `UNSUPPORTED_METADATA`. The finite physical result
does not identify its tag or value. This tool obtains the missing **schema
metadata**, from the current macOS desktop, without another Recovery visit.
It changes no parser acceptance rule, policy, boot object, mount or setting.

Default/help is inert. An explicitly invoked `--live` requires local root on
Darwin, the exact target model and current Macintosh HD. It loads the frozen
31AM package only after a no-follow, same-FD hash check, admits its111 source
closure, and reuses the unchanged target/stager metadata guard. The guard checks
the lab, Original and lab Data role/group/container/internal identities. Private
identities remain only in memory. A fresh observation after all reads must
produce the same binding; the original dictionary is not reused as new evidence.

For each LAB and ORIGINAL group, one fixed read-only `bputil -d -v` request
captures human text and one adds `-j` for JSON. The frozen capture primitive
limits each to65536 stdout bytes and20 seconds, drains/discards stderr and
returns only its fixed capture classification. Neither raw result is saved or
printed. Normal read/format failures still permit the other role to be observed;
an interruption stops further requests. A JSON refusal does not erase a useful
text observation. Overall unexpected errors produce a fixed redacted refusal,
without a traceback or command detail.

Text scanning follows the original C row grammar: first parentheses, colon,
one to four comma-separated four-character ASCII alphanumeric tags, case-sensitive
field names and case-insensitive `absent`. It reports:

- the first **unsupported candidate**, not authoritative native-parser failure;
- counts for non-absent protected auxiliary fields, published extra tags and
  all other unknown tags;
- presence/count/syntax classes for only `auxp`, `auxi`, `auxr`, `prot`, `hrlp`,
  `losv`, `lobo` and `love`;
- aggregate supported/unknown/malformed row counts, without unknown tag names.

The native parser may have an earlier semantic or identity-value error which
this schema scanner does not validate. Two legitimate `rpnh` rows are not
called a duplicate-format failure. Boolean syntax is reported as `BOOLEAN`,
never its true/false value; hexadecimal/decimal classes reveal no digits.

The JSON summary reports root/container shape, types of only fixed published
catalog keys, array cardinality and aggregate unknown-key/node/depth counts.
It never returns unknown dictionary keys, UUIDs, hashes, strings, numbers or
boolean values. Duplicate JSON keys, nonfinite constants, depth over16 or over
2048 value nodes refuse the JSON summary. Repeated known shapes are deduplicated
so repeated fields cannot create an unnecessarily large display. These shapes
are context for a future typed parser, not validated policy or target admission.

The fixed extra names `lobo` and `love` are documented in
[Asahi's boot-policy notes](https://github.com/AsahiLinux/docs/blob/main/docs/fw/boot.md).
Apple documents protected auxiliary concepts in its
[LocalPolicy description](https://support.apple.com/en-ca/guide/security/secc745a0845/web).
These references justify a finite observation catalog, not acceptance of those
fields. All previously supported native tags retain their exact case.

For a later authorized owner-run observation from the checkout:

```bash
sudo /usr/bin/python3 -I tools/policy31an/probe.py --live
```

Authenticate only in Terminal. Paste only the tool's finite JSON, never raw
`bputil` text/JSON or identifiers. `scope` remains a desktop schema observation;
it does not establish one-true-Recovery pairing, Full/Permissive mode, selected
payload identity or native readiness. `admission_verified` and `native_ready`
remain false, even when both roles' metadata was obtained.

## Offline checks

```bash
python3 -I tools/policy31an/test_probe.py
```

The focused tests use synthetic text/JSON, workspace fixtures, mocked metadata
backends and own child processes. They cover grouped rows, each unsupported
class, redaction, legitimate repeated identities, JSON bounds/duplicates,
changed after-observation binding, both-role captures, interruption, immutable
imports and error redaction. No test invokes a live Apple inspection command,
mount, policy write or host setting change. The old capture suite and native
50-method suite are reused and not rerun.

`--fixture` accepts only a synthetic JSON file below workspace `build/`, with
schema `ilinux31an-synthetic-policy-fixture-v1` and exactly LAB/ORIGINAL text
strings under `roles`. It is labeled `SYNTHETIC_CONTROL`; it never constructs
the live backend or promotes synthetic evidence into a desktop/Recovery claim.
