#!/usr/bin/env python3
"""Join this Mac's ADT nodes -> live macOS driver classes -> kext bundles (REA plist
inventory) -> IOKit-launched daemons, grouped into hardware blocks.  Metadata only."""
import collections, csv, re, sys

ROOT = sys.argv[1]
csv.field_size_limit(10**7)
def tsv(p):
    with open(p) as f:
        return list(csv.DictReader(f, delimiter="\t"))

SECURITY = re.compile(r"(\bsep|sep,|secure|exclave|keystore|fairplay|hdcp|\baes|sio-dma|sacm|trng|pke|ccs|"
                      r"repair|authcp|biometric|\bmesa\b|smartio|iboot|boot-policy)", re.I)
# (block, regex over "nodename compatible") -- first match wins
RULES = [
    ("CPU complex / cluster PMU / cpufreq", r"^(cpu\d|/cpus|cpu-cluster|cpm|acc-impl|pmu,|cluster|ptd|ppm|soc-tuner|pmgrtools|clpc)"),
    ("Interrupts (AIC) / timers / watchdog", r"(^aic|aic,|wdt|timer)"),
    ("IOMMU (DART) / SART", r"(dart|iommu-mapper|mapper-|^sart|sart,)"),
    ("Power manager (PMGR) / PMP coprocessor / telemetry", r"(pmgr|pmp|power-manager|ptd,)"),
    ("Memory controller / caches", r"(mcc|dcs|amcc|mcs)"),
    ("GPU (AGX)", r"(^gfx|gpu|agx|sgx)"),
    ("Neural Engine (ANE)", r"(^ane|ane,)"),
    ("Display (DCP) / display pipe / DisplayPort / HDMI", r"(dcp|disp|dptx|dpxbar|dp-|display|dpin|atc-dpin|dpphy|parade|dp855|hdmi)"),
    ("Camera ISP", r"(^isp|isp,|camera)"),
    ("Video decode (AVD)", r"(^avd|avd,)"),
    ("Video encode (AVE)", r"(^ave|ave2|ave,)"),
    ("ProRes (APR)", r"(^apr|apr,|prores)"),
    ("JPEG codec", r"(jpeg)"),
    ("2D scaler / M2R", r"(scaler|m2r|msr)"),
    ("NVMe storage (ANS)", r"(^ans|ans,|nvme|nand)"),
    ("PCIe root / Wi-Fi+BT link / SD", r"(apcie|pciec|pcie|pci106b|pci17a0|pcic)"),
    ("USB / Thunderbolt / USB-PD", r"(usb|atc|acio|atcrt|retimer|tps|usbc|hpm|dock|thunderbolt|nhi|auss)"),
    ("Audio (MCA/ADMAC/codecs/amps)", r"(audio|admac|mca|iisaudio|i2s|codec|amp|speaker|cs42|tas|sn01|leap)"),
    ("Always-on processor (AOP) / sensors", r"(aop|aod|als|accel|gyro|lid|temperature|tempsensor|motion|hall|prox)"),
    ("SMC / charging / battery", r"(smc|charger|battery|gas-gauge|pmu|spmi|pmic)"),
    ("Keyboard / trackpad (MTP) / buttons", r"(mtp|multitouch|keyboard|trackpad|hid-transport|dockchannel|buttons|btm)"),
    ("Low-speed buses (I2C/SPI/UART/GPIO/PWM/NOR)", r"(i2c|spi|uart|gpio|pinctrl|pwm|qspi|nor-flash|nvram)"),
    ("Wireless (Wi-Fi/BT/NFC)", r"(wlan|bluetooth|wifi|nfc|proxima|centauri|fillmore)"),
    ("SoC diagnostics / RAS / tracing", r"(error-handler|event-log|processor-trace|diagnostic|debugcpu)"),
    ("Coprocessor framework (IOP/RTKit/mailbox)", r"(^iop|iop,|iop-nub|mailbox|asc|rtkit|dockchannel)"),
]

def main():
    nodes = tsv(f"{ROOT}/hardware/adt/adt-nodes.tsv")
    dmap = {r["adt_node"]: [c for c in r["macos_driver_classes(depth<=3)"].split(",") if c]
            for r in tsv(f"{ROOT}/hardware/adt/driver-map.tsv")}
    kinv = tsv(f"{ROOT}/hardware/macos/kext-inventory.tsv")
    daemons = tsv(f"{ROOT}/hardware/macos/iokit-launched-daemons.tsv")
    by_class = collections.defaultdict(set)
    rtkit = set()
    for r in kinv:
        if r["io_class"]:
            by_class[r["io_class"]].add(r["bundle_id"])
        if "com.apple.driver.RTBuddy" in r["libraries"].split(","):
            rtkit.add(r["bundle_id"])
    blocks = collections.OrderedDict((b, {"nodes": [], "compat": set(), "classes": set(), "bundles": set(),
                                          "rtkit": set(), "daemons": set(), "excluded": 0}) for b, _ in RULES)
    blocks["Other / unclassified"] = {"nodes": [], "compat": set(), "classes": set(), "bundles": set(),
                                      "rtkit": set(), "daemons": set(), "excluded": 0}
    seen = set()
    for n in nodes:
        path, compat = n["path"], n["compatible"]
        if not compat or path in seen:
            continue
        seen.add(path)
        name = path.rsplit("/", 1)[-1]
        key = f"{name} {compat}"
        blk = next((b for b, rx in RULES if re.search(rx, key, re.I)), "Other / unclassified")
        hits = {m.group(0).lower() for m in SECURITY.finditer(key)}
        # The ANE is a compute block that macOS happens to assign to an exclave:
        # keep the hardware row, drop only exclave/security classes below.
        if hits and not (blk == "Neural Engine (ANE)" and hits <= {"exclave"}):
            blocks[blk]["excluded"] += 1
            continue
        b = blocks[blk]
        b["nodes"].append(name)
        b["compat"].update(c for c in compat.split(";") if c)
        # driver-map is keyed by node name with unit address
        for k, classes in dmap.items():
            if k == name or k.split("@")[0] == name:
                for c in classes:
                    if SECURITY.search(c):
                        continue
                    b["classes"].add(c)
                    b["bundles"].update(by_class.get(c, ()))
    for b in blocks.values():
        b["rtkit"] = {x for x in b["bundles"] if x in rtkit}
        b["daemons"] = {d["label"] for d in daemons if d["provider_class"] in b["classes"]}
    out = f"{ROOT}/hardware/macos/block-map.tsv"
    with open(out, "w") as f:
        f.write("block\tadt_nodes\tsecurity_nodes_excluded\tcompatibles\tlive_macos_classes\tkext_bundles\trtkit_coprocessor_kexts\tiokit_launched_daemons\n")
        for blk, b in blocks.items():
            if not b["nodes"] and not b["excluded"]:
                continue
            f.write("\t".join([blk, str(len(b["nodes"])), str(b["excluded"]),
                               ",".join(sorted(b["compat"])), ",".join(sorted(b["classes"])),
                               ",".join(sorted(x.replace("com.apple.", "") for x in b["bundles"])),
                               ",".join(sorted(x.replace("com.apple.", "") for x in b["rtkit"])),
                               ",".join(sorted(x.replace("com.apple.", "") for x in b["daemons"]))]) + "\n")
    print(out)
main()
