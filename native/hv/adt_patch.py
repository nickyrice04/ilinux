"""Raw ADT walker and in-place property patcher (private iLinux tooling).

The in-tree m1n1 chainload patches the SEPFW memory-map property of the
*running* ADT in place (adt_setprop). The Python proxy flow instead rebuilds
and rewrites the whole ADT, which had never been exercised on t6050. This module
lets the launcher do what the in-tree code does: locate one property in the raw
ADT bytes and rewrite only its value, with every other byte untouched.

ADT layout (src/adt.h, proxyclient/m1n1/adt.py):

    node     := u32 property_count, u32 child_count, property*, node*
    property := char name[32], u32 size_and_flags, value[size], pad to 4
                size = size_and_flags & 0x7fffffff; bit 31 is a flag, kept as is
The node name is the value of its "name" property (a NUL-terminated string);
the root is addressed as "/" and children as "/chosen/memory-map".
"""
import struct

MAX_DEPTH = 32
MAX_NODES = 1 << 16
NAME_LEN = 32


class ADTError(ValueError):
    pass


def _align4(n):
    return (n + 3) & ~3


class Prop:
    __slots__ = ("name", "size", "flags", "value_offset", "prop_offset")

    def __init__(self, name, size, flags, value_offset, prop_offset):
        self.name = name
        self.size = size
        self.flags = flags
        self.value_offset = value_offset
        self.prop_offset = prop_offset


class Node:
    __slots__ = ("path", "props", "children", "offset")

    def __init__(self, path, offset):
        self.path = path
        self.props = []
        self.children = []
        self.offset = offset

    def prop(self, name):
        found = [p for p in self.props if p.name == name]
        if len(found) != 1:
            raise ADTError("expected exactly one property %r in %s, found %d" %
                           (name, self.path, len(found)))
        return found[0]


def _parse_node(blob, off, parent_path, depth, counter):
    if depth > MAX_DEPTH:
        raise ADTError("ADT nesting too deep")
    counter[0] += 1
    if counter[0] > MAX_NODES:
        raise ADTError("ADT has too many nodes")
    if off < 0 or off + 8 > len(blob):
        raise ADTError("node header outside the ADT")
    prop_count, child_count = struct.unpack_from("<II", blob, off)
    node_off = off
    off += 8
    # Cheap plausibility bound before looping: each property is >= 36 bytes.
    if prop_count * 36 > len(blob) - off or child_count * 8 > len(blob) - off:
        raise ADTError("implausible property or child count")
    props = []
    for _ in range(prop_count):
        if off + 36 > len(blob):
            raise ADTError("property header outside the ADT")
        raw_name = blob[off:off + NAME_LEN]
        if b"\0" not in raw_name:
            raise ADTError("unterminated property name")
        name = raw_name.split(b"\0", 1)[0].decode("ascii")
        size_field = struct.unpack_from("<I", blob, off + NAME_LEN)[0]
        size, flags = size_field & 0x7FFFFFFF, size_field >> 31
        value_off = off + 36
        end = value_off + size
        if end > len(blob):
            raise ADTError("property %r runs past the end of the ADT" % name)
        props.append(Prop(name, size, flags, value_off, off))
        off = _align4(end)
    node_name = None
    for p in props:
        if p.name == "name":
            raw = blob[p.value_offset:p.value_offset + p.size]
            node_name = raw.split(b"\0", 1)[0].decode("ascii", "replace")
    if parent_path is None:
        path = "/"
    else:
        if node_name is None:
            raise ADTError("child node without a name property")
        path = (parent_path.rstrip("/") + "/" + node_name)
    node = Node(path, node_off)
    node.props = props
    for _ in range(child_count):
        child, off = _parse_node(blob, off, path, depth + 1, counter)
        node.children.append(child)
    return node, off


def parse(blob):
    """Return (root_node, end_offset). Raises ADTError on malformed data."""
    if len(blob) < 8:
        raise ADTError("ADT too short")
    root, end = _parse_node(blob, 0, None, 0, [0])
    if end > len(blob):
        raise ADTError("ADT parse ran past the end")
    return root, end


def find_node(root, path):
    if path == "/":
        return root
    node = root
    for part in [p for p in path.split("/") if p]:
        matches = [c for c in node.children if c.path.rsplit("/", 1)[-1] == part]
        if len(matches) != 1:
            raise ADTError("expected exactly one node %r under %s, found %d" %
                           (part, node.path, len(matches)))
        node = matches[0]
    return node


def locate(blob, path, prop_name):
    """(value_offset, size, flags) of exactly one property, or ADTError."""
    root, _ = parse(blob)
    p = find_node(root, path).prop(prop_name)
    return p.value_offset, p.size, p.flags


def memory_map(blob):
    """name -> (addr, size) for the 16-byte entries under /chosen/memory-map."""
    root, _ = parse(blob)
    node = find_node(root, "/chosen/memory-map")
    out = {}
    for p in node.props:
        if p.name == "name" or p.size != 16:
            continue
        out[p.name] = struct.unpack_from("<QQ", blob, p.value_offset)
    return out


def patch_value(blob, path, prop_name, new_value):
    """Same-length in-place value patch.

    Returns (new_blob, value_offset, old_value). Every byte outside the one
    property value is identical, and the size/flag word is left alone.
    """
    new_value = bytes(new_value)
    offset, size, _flags = locate(blob, path, prop_name)
    if len(new_value) != size:
        raise ADTError("new value is %d bytes, property is %d" % (len(new_value), size))
    old = bytes(blob[offset:offset + size])
    out = bytearray(blob)
    out[offset:offset + size] = new_value
    return bytes(out), offset, old
