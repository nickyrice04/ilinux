"""boot042 contract: boot041 with the keyboard path and the storage drivers as loadable modules.

boot042 (VM job 050, kernel/experiments/boot042-modules) is boot041 plus the MTP keyboard transport, built
so that nothing of the keyboard path or of the storage stack binds while the kernel boots: attempt 26
loads the keyboard modules over SSH, one at a time; the storage modules are a separate set, never in the
attempt-26 image. Three exact deltas against boot041, and nothing else in the package:

* Stage-B DT: boot037's MTP delta (mtp_input.check_delta: the RTKit helper, its mailbox, the DockChannel
  FIFO with its HID child and six interface nodes, the MTP DART enabled with its IOVA window, the
  keyboard alias), on boot041's DT, with the MTP's streams 0-4 (SIDS) instead of boot037's stream 1:
  the ADT remaps streams 1-4 to 0 for macOS, and apple-dart's reset clears a t8110 remap, so each stream
  the MTP may use gets the same table (one boot covers what the E1 probe would have decided). The USB
  part, the NVMe node (disabled, as check_stage_b requires) and every other node stay boot041's.
* kernel.config: APPLE_DOCKCHANNEL, HID_DOCKCHANNEL, NVME_APPLE, NVME_CORE and APPLE_SART from y to m;
  APPLE_RTKIT_HELPER, HID_APPLE and HID_MAGICMOUSE from n to m; HIDRAW (a bool of the built-in HID core)
  from n to y; the two "is not set" lines HIDRAW makes visible. APPLE_DART, APPLE_MAILBOX and APPLE_RTKIT
  stay built in (USB needs the DART; the mailbox already binds the ANS mailbox at boot in boot041, with no
  register access; RTKit is a library).
* Image: job 050's reproducible build (IMAGE_SHA256), with boot040's DART diagnostics and the mailbox,
  and without any keyboard-path or storage driver (their match tables live in the modules).

make-package.py's boot042 entry makes one call here (check_package) and takes its record fields from here
(LINUX_PATCHES, manifest_fields). The package carries no storage: no storage module or script, and an Image
without NVMe, SART or nvme-core code; the storage set is attempt 27's, kept apart.

This module only decides whether a DT, config, Image or package is the contract; it touches no hardware.
"""
import hashlib

import mtp_input
from kconfig_guard import parse_config

SIDS = (0, 1, 2, 3, 4)
IMAGE_SHA256 = "0b6df39566f12bcd5957e649946125a7bb0f42f31690933dc9896a2565b9b69c"   # job 050, two builds equal
# symbol: (boot041, boot042); "n" = "is not set" (kconfig_guard.parse_config)
CONFIG_DELTA = {
    "APPLE_DOCKCHANNEL": ("y", "m"),
    "HID_DOCKCHANNEL": ("y", "m"),
    "APPLE_RTKIT_HELPER": ("n", "m"),
    "HID_APPLE": ("n", "m"),
    "HID_MAGICMOUSE": ("n", "m"),
    "HIDRAW": ("n", "y"),
    "NVME_APPLE": ("y", "m"),
    "NVME_CORE": ("y", "m"),
    "APPLE_SART": ("y", "m"),
}
CONFIG_REVEALED = ("HID_CP2112", "HID_FT260")
CONFIG_KEPT = {"APPLE_DART": "y", "APPLE_MAILBOX": "y", "APPLE_RTKIT": "y", "HID": "y", "MODULES": "y",
               "MODULE_UNLOAD": "y", "USB_LIBCOMPOSITE": "y", "USB_CONFIGFS": "y", "BLK_DEV_NVME": "m"}
# In the Image: boot040's DART diagnostics, the mailbox driver, the HID core's hidraw.
IMAGE_KEEPS = (b"t8110-class DART v", b"without the error flag", b"apple,asc-mailbox-v4\0", b"hidraw")
# Not in the Image: the match tables and messages of the drivers boot042 builds as modules.
IMAGE_LACKS = (b"apple,t6050-dockchannel-hid\0", b"apple,dockchannel-hid\0", b"apple,rtk-helper-asc4\0",
               b"apple,dockchannel\0", b"Ring registered: iova ", b"apple,nvme-ans2\0",
               b"apple,t8103-nvme-ans2\0", b"apple,t6050-sart\0", b"apple,t8103-sart\0",
               b"iLinux read-only mode")


def check_delta(before, after):
    """Raise unless `after` is exactly `before` (boot041's Stage-B DT) plus the MTP delta with streams 0-4."""
    try:
        mtp_input.check_delta(before, after, sids=SIDS)
    except ValueError as exc:
        raise ValueError("boot042 Stage-B DT: %s" % exc) from None


def check_config(before_text, after_text):
    """Raise unless boot042's config is boot041's with exactly CONFIG_DELTA (and the revealed lines)."""
    before, after = parse_config(before_text), parse_config(after_text)
    problems = []
    for name in sorted(set(before) | set(after)):
        b, a = before.get(name), after.get(name)
        if name in CONFIG_DELTA:
            if (b, a) != CONFIG_DELTA[name]:
                problems.append("%s: %r -> %r, the contract says %r -> %r" % ((name, b, a) + CONFIG_DELTA[name]))
            continue
        if b == a and (name in before) == (name in after):
            continue
        if b is None and a == "n" and name in CONFIG_REVEALED:   # a line HIDRAW only makes visible
            continue
        problems.append("%s: %r -> %r" % (name, b, a))
    for name in CONFIG_DELTA:
        if name not in after:
            problems.append("%s missing from boot042's config" % name)
    for name, value in CONFIG_KEPT.items():
        if after.get(name) != value:
            problems.append("%s must stay %s, is %r" % (name, value, after.get(name)))
    if problems:
        raise ValueError("kernel config differs from the boot042 contract: " + "; ".join(problems[:6]))


def check_image(image):
    """Raise unless the Image is job 050's boot042 build, with and without the expected strings."""
    if hashlib.sha256(image).hexdigest() != IMAGE_SHA256:
        raise ValueError("Image is not job 050's boot042 build")
    missing = [m for m in IMAGE_KEEPS if m not in image]
    if missing:
        raise ValueError("boot042 Image lacks %r" % missing[0])
    present = [m for m in IMAGE_LACKS if m in image]
    if present:
        raise ValueError("boot042 Image still carries %r (a driver it builds as a module)" % present[0])


LINUX_PATCHES = ("; boot041's tree, DT wiring and diagnostic initramfs; the MTP keyboard path "
                 "(kernel/experiments/mtp-input: driver-contracts dockchannel-hid 0001 + patches/0002 ring transport) "
                 "built as loadable modules, loaded over SSH one at a time, with HIDRAW built in; the storage drivers "
                 "(NVMe, SART) also built as modules, none of them in this package: they, the nvme-core read-only patch "
                 "and the load script are attempt 27's separate set, and the Image has none of their code; the Stage-B DT "
                 "adds the MTP nodes with DART streams 0-4 and keeps the NVMe node disabled; job-050")


def check_package(previous_package, authorized_key_path, baseline, data):
    """make-package.py's boot042 rule, after its baseline comparison (only the Image, kernel.config and the
    Stage-B DT differ from boot041's record): boot041's DT and config from --previous-package, checked against
    that record; the three exact deltas above; the control channel's contract on the unchanged initramfs
    with the --authorized-key it must hold; boot040's DART diagnostics in the Image. Returns the key's bytes."""
    import control_channel
    from fdt import properties
    if previous_package is None or authorized_key_path is None:
        raise ValueError("boot042 needs --previous-package (boot041's) and --authorized-key")
    prior = {}
    for name in ("t6050-j716c-stage-b.dtb", "kernel.config"):
        prior[name] = (previous_package / name).read_bytes()
        if hashlib.sha256(prior[name]).hexdigest() != baseline["files"][name]["sha256"]:
            raise ValueError("prior digest mismatch: " + name)
    check_delta(properties(prior["t6050-j716c-stage-b.dtb"]), properties(data["t6050-j716c-stage-b.dtb"]))
    check_config(prior["kernel.config"].decode(), data["kernel.config"].decode())
    check_image(data["Image"])
    authorized_key = authorized_key_path.read_bytes()
    entries = control_channel.check_initramfs(data["initramfs-stage-b.cpio.gz"], authorized_key)
    control_channel.check_bulk_only_init(data["diag-init.c"], entries["init"][3])
    control_channel.check_dart_diag_init(entries["init"][3])
    control_channel.check_dart_both_init(entries["init"][3])
    control_channel.check_dart_diag_image(data["Image"])
    return authorized_key


def manifest_fields():
    """The boot042 fields of package-manifest.json; boot041's USB wiring and DART diagnostics carry over unchanged
    (check_delta keeps every node but the MTP's)."""
    import usb_dt
    return {
        "control_channel_function": {"configfs": "gser.GS0", "bcdDevice": "0x0139", "interface_class": "0xff",
                                     "endpoints": ["bulk IN", "bulk OUT"]},
        "modules_instead_of_built_in": {"config_delta": {k: list(v) for k, v in CONFIG_DELTA.items()},
                                        "kept": dict(sorted(CONFIG_KEPT.items())),
                                        "image_as_job_050": IMAGE_SHA256,
                                        "contract": "native/boot/boot042_modules.py"},
        "mtp_input": {"dt_nodes": list(mtp_input.NEW_NODES), "dart": mtp_input.DART, "stream_ids": list(SIDS),
                      "modules_loaded_over_ssh": ["apple-rtkit-helper", "apple-dockchannel", "hid-apple",
                                                  "dockchannel-hid"]},
        "dart_diagnostics": {"kernel_patches": ["kernel/experiments/usb-gadget/dart-diag/dart-diag.patch",
                                                "kernel/experiments/usb-gadget/dart-diag/dart-diag-2-gen22.patch"],
                             "apple_dart_c_after": "b3eb0da83235164e2d514c106ec134d6e24c335ba6e36e0124534fb60ca9b288",
                             "init_reads_dart_registers": "through /dev/mem, 32-bit loads, instances 0 and 1 of each "
                                                         "port's dart-usbN, both layouts by PARAMS3 version; the "
                                                         "pending-fault word of both every heartbeat"},
        "dart_wiring": {"iommus": "<dart0 0>, <dart1 1>", "dart_instance_0_enabled": list(usb_dt.DART0),
                        "dwc3_cores": [port[0] for port in usb_dt.PORTS],
                        "contract": "boot041's (native/boot/usb_dt.py check_both_darts_delta), unchanged"},
    }
