"""Fail closed on the observed J716c main-GPIO exclusion contract.

Only public controller geometry and a non-identifying pin list are inspected.
No MMIO, transport writes, ADT changes or dumps occur here.
"""
import struct

PATH = '/soc/pinctrl@29c000000'
PINS = frozenset((5, 6, 7, 112, 141))
RANGES = struct.pack('>6I', 5, 3, 112, 1, 141, 1)


def check_tree(tree):
    node = tree.get(PATH, {})
    if (node.get('compatible') != b'apple,t6050-pinctrl\0apple,t8103-pinctrl\0' or
            node.get('reg') != struct.pack('>QQ', 0x29c000000, 0x44000) or
            node.get('apple,npins') != struct.pack('>I', 221) or
            node.get('status', b'okay\0') not in (b'okay\0', b'ok\0') or
            node.get('gpio-reserved-ranges') != RANGES):
        raise ValueError('main GPIO DT geometry/exclusions differ from boot032 contract')


def check_adt(adt):
    try:
        node = adt['/arm-io/gpio0']
        compatible = node.getprop('compatible')
        npins = node.getprop('#gpio-pins')
        groups = node.getprop('#gpio-int-groups')
        raw = node.getprop('no-restore-gpio-pins')
    except (KeyError, AttributeError, TypeError):
        raise ValueError('main GPIO ADT metadata unavailable') from None
    if (not isinstance(compatible, (list, tuple)) or
            list(compatible) != ['gpio,t8101'] or
            type(npins) is not int or npins != 221 or
            type(groups) is not int or groups != 7 or
            not isinstance(raw, bytes) or len(raw) != 20):
        raise ValueError('main GPIO ADT geometry/exclusions differ from observed hardware')
    values = struct.unpack('<5I', raw)
    if len(set(values)) != len(values) or frozenset(values) != PINS:
        raise ValueError('main GPIO ADT reserved pins differ from boot032 exclusions')
