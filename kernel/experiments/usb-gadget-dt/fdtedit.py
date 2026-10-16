"""Ordered flattened-device-tree reader and writer for this experiment (stdlib only).

`native/boot/fdt.py` is the reviewed, read-only decoder the launcher uses; editing
lives here so that controller code is never touched. `encode(parse(blob))`
reproduces a packed dtc/libfdt blob byte for byte: the original strings block is
kept as is, new property names are appended (found the way libfdt finds them), and
the alignment padding of untouched names and values is kept, stale bytes included
(libfdt's in-place edits can leave old data there; parsers ignore it).
"""
import struct

MAGIC = 0xD00DFEED
BEGIN_NODE, END_NODE, PROP, NOP, END = 1, 2, 3, 4, 9


class Node:
    def __init__(self, name):
        self.name = name
        self.pad = None      # original name padding (None = zeros)
        self.props = []      # [name, value, padding] in blob order (padding None = zeros)
        self.children = []   # Node objects in blob order

    def get(self, name, default=None):
        for key, value, _ in self.props:
            if key == name:
                return value
        return default

    def has(self, name):
        return any(key == name for key, _, _ in self.props)

    def set(self, name, value):
        for entry in self.props:
            if entry[0] == name:
                entry[1], entry[2] = value, None
                return
        self.props.append([name, value, None])

    def delete(self, name):
        kept = [entry for entry in self.props if entry[0] != name]
        if len(kept) == len(self.props):
            raise KeyError("%s has no property %s" % (self.name, name))
        self.props = kept

    def child(self, name):
        for node in self.children:
            if node.name == name:
                return node
        raise KeyError("no node %s under %s" % (name, self.name or "/"))


class Tree:
    def __init__(self, root, memrsv, boot_cpuid, strings):
        self.root = root
        self.memrsv = memrsv
        self.boot_cpuid = boot_cpuid
        self.strings = strings

    def node(self, path):
        node = self.root
        for part in path.strip("/").split("/"):
            if part:
                node = node.child(part)
        return node

    def walk(self):
        """Yield (path, node) in blob (pre-)order."""
        stack = [("/", self.root)]
        while stack:
            path, node = stack.pop()
            yield path, node
            for child in reversed(node.children):
                stack.append((path.rstrip("/") + "/" + child.name, child))


def parse(blob):
    if len(blob) < 40:
        raise ValueError("short FDT")
    (magic, total, off_struct, off_strings, off_rsv, version, last_comp,
     boot_cpuid, size_strings, size_struct) = struct.unpack_from(">10I", blob)
    if magic != MAGIC or version != 17 or last_comp != 16 or total != len(blob):
        raise ValueError("unsupported FDT header")
    if not (off_rsv == 40 and off_rsv < off_struct
            and off_struct + size_struct <= off_strings
            and off_strings + size_strings <= total):
        raise ValueError("unsupported FDT layout")
    memrsv, off = [], off_rsv
    while True:
        if off + 16 > off_struct:
            raise ValueError("memory reserve map overruns the structure block")
        addr, size = struct.unpack_from(">QQ", blob, off)
        off += 16
        if addr == 0 and size == 0:
            break
        memrsv.append((addr, size))
    strings = blob[off_strings:off_strings + size_strings]
    end = off_struct + size_struct
    off, stack, root = off_struct, [], None
    while off + 4 <= end:
        token, = struct.unpack_from(">I", blob, off)
        off += 4
        if token == BEGIN_NODE:
            stop = blob.index(b"\0", off, end)
            node = Node(blob[off:stop].decode("ascii"))
            node.pad = blob[stop + 1:(stop + 4) & ~3]
            off = (stop + 4) & ~3
            if stack:
                stack[-1].children.append(node)
            elif root is None and node.name == "":
                root = node
            else:
                raise ValueError("misplaced root node")
            stack.append(node)
        elif token == END_NODE:
            if not stack:
                raise ValueError("unbalanced END_NODE")
            stack.pop()
        elif token == PROP:
            if not stack:
                raise ValueError("property outside a node")
            length, nameoff = struct.unpack_from(">2I", blob, off)
            off += 8
            stop = strings.index(b"\0", nameoff)
            name = strings[nameoff:stop].decode("ascii")
            if off + length > end or stack[-1].has(name):
                raise ValueError("bad property %s" % name)
            padded = (off + length + 3) & ~3
            stack[-1].props.append([name, blob[off:off + length], blob[off + length:padded]])
            off = padded
        elif token == END:
            if stack or root is None or off != end:
                raise ValueError("FDT_END in the wrong place")
            return Tree(root, memrsv, boot_cpuid, strings)
        else:
            # NOP tokens would break the byte-for-byte round trip; none are expected.
            raise ValueError("unsupported token %d" % token)
    raise ValueError("missing FDT_END")


def encode(tree):
    strings = bytearray(tree.strings)

    def nameoff(name):
        key = name.encode("ascii") + b"\0"
        found = strings.find(key)      # libfdt reuses any exact match, suffixes included
        if found >= 0:
            return found
        strings.extend(key)
        return len(strings) - len(key)

    body = bytearray()

    def emit(node):
        name = node.name.encode("ascii") + b"\0"
        pad = node.pad if node.pad is not None else bytes(-len(name) % 4)
        body.extend(struct.pack(">I", BEGIN_NODE) + name + pad)
        for key, value, pad in node.props:
            body.extend(struct.pack(">3I", PROP, len(value), nameoff(key)))
            body.extend(value + (pad if pad is not None else bytes(-len(value) % 4)))
        for child in node.children:
            emit(child)
        body.extend(struct.pack(">I", END_NODE))

    emit(tree.root)
    body.extend(struct.pack(">I", END))
    rsv = b"".join(struct.pack(">QQ", a, s) for a, s in tree.memrsv) + bytes(16)
    off_struct = 40 + len(rsv)
    off_strings = off_struct + len(body)
    total = off_strings + len(strings)
    header = struct.pack(">10I", MAGIC, total, off_struct, off_strings, 40, 17, 16,
                         tree.boot_cpuid, len(strings), len(body))
    return header + rsv + bytes(body) + bytes(strings)


def flat(tree):
    """{path: {property: value}} for comparisons."""
    return {path: {k: v for k, v, _ in node.props} for path, node in tree.walk()}
