#!/usr/bin/env python3
"""Which PMGR domains can Linux register, and which can genpd release?

usage: python3 -I audit_domains.py DTB [DTB ...]   (prints JSON)

Model of the pinned pmgr-pwrstate probe and genpd (third_party/asahi-linux,
drivers/pmdomain/apple/pmgr-pwrstate.c and drivers/pmdomain/core.c):
* a disabled node is never probed, so Linux never writes its register;
* an available node writes AUTO_ENABLE if the domain is on, then looks up its
  parents; a missing parent becomes -EPROBE_DEFER and the domain is removed
  again, so it never registers ("defers forever", but its register was written);
* only registered domains reach sync_state or the boot034/035 release ladder;
  always-on domains and domains an available device claims are never released.

`dt_unclaimed` is the count the boot034/035 notes used (every pwrstate node that is
neither always-on nor claimed, disabled ones included); `releasable` is the same set
restricted to domains that actually register.
"""
import json
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fdtedit  # noqa: E402

PWRSTATE = "apple,t8103-pmgr-pwrstate"
ATC_PORT = re.compile(r"^atc[0-2]_")


def texts(value):
    return value[:-1].decode("ascii").split("\0") if value else []


def audit(blob):
    tree = fdtedit.parse(blob)
    nodes = fdtedit.flat(tree)

    def available(path):
        while True:
            if nodes.get(path, {}).get("status", b"okay\0") not in (b"okay\0", b"ok\0"):
                return False
            if path == "/":
                return True
            path = path.rsplit("/", 1)[0] or "/"

    by_phandle = {struct.unpack(">I", p["phandle"])[0]: path
                  for path, p in nodes.items() if "phandle" in p}

    def refs(props):
        value = props.get("power-domains", b"")
        return [by_phandle[x] for x in struct.unpack(">%dI" % (len(value) // 4), value)]

    domains = {path for path, p in nodes.items() if PWRSTATE in texts(p.get("compatible", b""))}
    label = {path: texts(nodes[path]["label"])[0] for path in domains}
    always_on = {d for d in domains if "apple,always-on" in nodes[d]}
    claimed = {r for path, p in nodes.items()
               if path not in domains and available(path) for r in refs(p)}

    registered, changed = set(), True
    while changed:
        changed = False
        for d in sorted(domains - registered):
            if available(d) and all(parent in registered for parent in refs(nodes[d])):
                registered.add(d)
                changed = True
    defers = {d for d in domains if available(d)} - registered

    def names(paths):
        return sorted(label[p] for p in paths)

    releasable = registered - always_on - claimed
    return {
        "pwrstate_nodes": len(domains),
        "disabled": len([d for d in domains if not available(d)]),
        "always_on": len(always_on),
        "claimed": names(claimed & domains),
        "dt_unclaimed": len(domains - always_on - claimed),
        "registered": len(registered),
        "defers_forever": names(defers),
        "releasable": len(releasable),
        "releasable_atc0_2": names({d for d in releasable if ATC_PORT.match(label[d])}),
        "registered_atc0_2": names({d for d in registered if ATC_PORT.match(label[d])}),
        "available_atc0_2": names({d for d in domains if available(d) and ATC_PORT.match(label[d])}),
    }


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    print(json.dumps({p: audit(Path(p).read_bytes()) for p in argv[1:]}, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
