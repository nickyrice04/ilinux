#!/usr/bin/env python3
"""Metadata-only inventory of macOS driver bundles and IOKit-launched daemons via REA.

Reads Info.plist / launchd plists through `rea inspect-plist` (REA output is
treated as untrusted data: parsed as JSON, never executed or followed).
Security components (SEP, keystore, exclaves, boot policy, DRM, biometrics)
are dropped before anything is recorded. Writes TSVs for the gap matrix.
"""
import concurrent.futures as cf, json, os, re, subprocess, sys

REA = sys.argv[1]            # tools/rea.sh
OUT = sys.argv[2]            # output directory
EXCLUDE = re.compile(r"(\bsep\b|sepos|SEP[A-Z_]|SEPManager|SecureEnclave|KeyStore|Keystore|Exclave|Image4|BootPolicy|"
                     r"FairPlay|HDCP|CredentialManager|Biometric|\bMesa\b|AppleSSE|ApNonce|"
                     r"Sandbox|AMFI|MobileFileIntegrity|CoreTrust|Seatbelt|TrustedAccessory|EmbeddedOS|eoshostd|"
                     r"Effaceable|AppleSecure|Lockdown|corecrypto|AppleCrypto|xart|passd|AuthCP|mobilerepair|"
                     r"trm_|TRM_)", re.I)

def redact_libs(libs):
    keep = [l for l in libs if not EXCLUDE.search(l)]
    n = len(libs) - len(keep)
    return ",".join(sorted(keep)) + (f",+{n}-security-deps" if n else "")

def rea_plist(path):
    p = subprocess.run([REA, "inspect-plist", path, "--relative-path", path, "--format", "json"],
                       capture_output=True, text=True, timeout=120)
    try:
        doc = json.loads(p.stdout)
    except json.JSONDecodeError:
        return None
    nr = doc.get("normalized_result") or {}
    return nr.get("value") if isinstance(nr.get("value"), dict) else None

def clean(s):
    return re.sub(r"[\t\r\n]+", " ", str(s))[:300]

def kext_rows(bundle):
    info = os.path.join(bundle, "Contents", "Info.plist")
    if not os.path.isfile(info):
        info = os.path.join(bundle, "Info.plist")
        if not os.path.isfile(info):
            return [], None
    v = rea_plist(info)
    if not v:
        return [], ("unreadable", bundle)
    bid = v.get("CFBundleIdentifier", "")
    if EXCLUDE.search(bid) or EXCLUDE.search(os.path.basename(bundle)):
        return [], ("excluded", bid)
    libs = redact_libs(list((v.get("OSBundleLibraries") or {}).keys()))
    rows = []
    pers = v.get("IOKitPersonalities") or {}
    if not pers:
        rows.append([bid, v.get("CFBundleVersion", ""), "", "", "", "", "", libs])
    for name, p in sorted(pers.items()):
        if not isinstance(p, dict):
            continue
        ioclass = p.get("IOClass", "")
        if EXCLUDE.search(str(ioclass)) or EXCLUDE.search(str(name)):
            continue
        match = p.get("IONameMatch", p.get("IOCompatibilityMatch", ""))
        if isinstance(match, list):
            match = ",".join(map(str, match))
        if EXCLUDE.search(str(match)) or re.search(r"(sep-|-sep)", str(match), re.I):
            continue
        prop = p.get("IOPropertyMatch", "")
        if isinstance(prop, (dict, list)):
            prop = json.dumps(prop, sort_keys=True, separators=(",", ":"))
        rows.append([bid, v.get("CFBundleVersion", ""), clean(name), clean(ioclass), clean(p.get("IOProviderClass", "")),
                     clean(match), clean(prop), libs])
    return rows, None

def daemon_rows(path):
    v = rea_plist(path)
    if not v:
        return []
    label = v.get("Label", os.path.basename(path))
    prog = v.get("Program") or (v.get("ProgramArguments") or [""])[0]
    if EXCLUDE.search(label) or EXCLUDE.search(str(prog)):
        return []
    ev = (v.get("LaunchEvents") or {}).get("com.apple.iokit.matching") or {}
    rows = []
    for name, m in sorted(ev.items()):
        if not isinstance(m, dict):
            continue
        if EXCLUDE.search(str(m.get("IOProviderClass", ""))) or EXCLUDE.search(json.dumps(m.get("IOPropertyMatch", ""))):
            continue
        rows.append([label, clean(prog), clean(name), clean(m.get("IOProviderClass", "")),
                     clean(m.get("IONameMatch", "")),
                     clean(json.dumps(m.get("IOPropertyMatch", ""), sort_keys=True, separators=(",", ":")) if m.get("IOPropertyMatch") else "")])
    return rows

def main():
    os.makedirs(OUT, exist_ok=True)
    bundles = []
    for root in ("/System/Library/Extensions", "/System/Library/DriverExtensions"):
        if os.path.isdir(root):
            bundles += [os.path.join(root, d) for d in sorted(os.listdir(root)) if d.endswith((".kext", ".dext"))]
    excluded, unreadable, krows = 0, 0, []
    with cf.ThreadPoolExecutor(8) as ex:
        for rows, note in ex.map(kext_rows, bundles):
            krows += rows
            if note and note[0] == "excluded":
                excluded += 1
            elif note:
                unreadable += 1
    with open(os.path.join(OUT, "kext-inventory.tsv"), "w") as f:
        f.write("bundle_id\tversion\tpersonality\tio_class\tprovider_class\tname_match\tproperty_match\tlibraries\n")
        for r in sorted(krows):
            f.write("\t".join(map(str, r)) + "\n")
    plists = []
    for root in ("/System/Library/LaunchDaemons", "/System/Library/LaunchAgents"):
        plists += [os.path.join(root, d) for d in sorted(os.listdir(root)) if d.endswith(".plist")]
    drows = []
    with cf.ThreadPoolExecutor(8) as ex:
        for rows in ex.map(daemon_rows, plists):
            drows += rows
    with open(os.path.join(OUT, "iokit-launched-daemons.tsv"), "w") as f:
        f.write("label\tprogram\tevent\tprovider_class\tname_match\tproperty_match\n")
        for r in sorted(drows):
            f.write("\t".join(map(str, r)) + "\n")
    print(json.dumps({"bundles": len(bundles), "kext_rows": len(krows), "excluded_bundles": excluded,
                      "unreadable": unreadable, "launchd_plists": len(plists), "iokit_daemon_rows": len(drows)}))

main()
