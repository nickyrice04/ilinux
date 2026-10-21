"""Original, non-identifying raw BootArgs/ADT fixture. No Apple bytes.

Offsets are independently taken from the pinned C boot_args declaration.
This deliberately avoids using Construct to build inputs for Construct tests.
"""
import struct

DRAM_BASE, DRAM_SIZE = 0x10000000000, 0x2000000000
PHYS = DRAM_BASE + 0x4000
VIRT = 0xfffffe0000000000
ADT_OFFSET = 0x600000


def node(properties, children=()):
    data = struct.pack('<II', len(properties), len(children))
    for name, value in properties.items():
        key = name.encode('ascii')
        assert len(key) < 32
        data += key.ljust(32, b'\0') + struct.pack('<I', len(value))
        data += value + bytes((-len(value)) % 4)
    return data + b''.join(children)


def adt(base=DRAM_BASE, size=DRAM_SIZE, omit=None):
    props = {'name': b'chosen\0', 'dram-base': struct.pack('<Q', base),
             'dram-size': struct.pack('<Q', size)}
    if omit is not None: del props[omit]
    # load_adt initializes PMGR metadata even for a chosen-only consumer.
    # It inspects the first two 48-byte device records to choose an ID format.
    # Zero-valued synthetic records satisfy that parser prerequisite only.
    pmgr = node({'name': b'pmgr\0', 'compatible': b'pmgr,t6050\0', 'devices': bytes(96)})
    arm_io = node({'name': b'arm-io\0'}, [pmgr])
    return node({'name': b'device-tree\0'}, [node(props), arm_io])


def bootargs(revision=3, phys=PHYS, size=DRAM_SIZE - 0x8000, adt_size=None):
    if adt_size is None: adt_size = len(adt())
    data = bytearray(736 if revision == 2 else 1152)
    struct.pack_into('<HH', data, 0, revision, 2)
    struct.pack_into('<QQQQ', data, 8, VIRT, phys, size, phys + 0x800000)
    struct.pack_into('<QI', data, 96, VIRT + ADT_OFFSET, adt_size)
    struct.pack_into('<Q', data, len(data) - 8, DRAM_SIZE)
    return bytes(data)
