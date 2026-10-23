# SPDX-License-Identifier: MIT
"""Original offline reference for user GPU VA binding decisions, no I/O."""
from dataclasses import dataclass

U64_MAX = (1 << 64) - 1
MAX_OPS = MAX_OBJECTS = 64
UNBIND, READ, WRITE, SINGLE_PAGE = 1, 2, 4, 8


class Refusal(ValueError):
    pass


@dataclass(frozen=True)
class Space:
    page_size: int
    vm_start: int
    vm_end: int
    kernel_start: int
    kernel_end: int
    kernel_min_size: int


@dataclass(frozen=True)
class Object:
    handle: int
    size: int


@dataclass(frozen=True)
class Op:
    flags: int
    handle: int
    offset: int
    size: int
    addr: int


@dataclass(frozen=True)
class Planned:
    op: Op
    object_bytes_accessed: int


def uint(value, bits=64):
    if type(value) is not int or value < 0 or value >= 1 << bits:
        raise Refusal("INTEGER")
    return value


def validate_space(space):
    if type(space) is not Space:
        raise Refusal("SPACE_TYPE")
    for value in vars(space).values():
        uint(value)
    page = space.page_size
    if not page or page & (page - 1):
        raise Refusal("ALIGNMENT")
    if space.vm_start >= space.vm_end:
        raise Refusal("WINDOW")
    if any(x % page for x in (space.vm_start, space.vm_end,
                              space.kernel_start, space.kernel_end)):
        raise Refusal("ALIGNMENT")
    if (space.kernel_min_size == 0 or
        not space.vm_start <= space.kernel_start < space.kernel_end <= space.vm_end or
        space.kernel_end - space.kernel_start < space.kernel_min_size):
        raise Refusal("RESERVATION")
    return space


def plan(space, objects, ops):
    """Return immutable ordered plans only after every input validates.

    The local result is transactional. This makes no statement about ioctl
    atomicity, live mappings, object lifetime, firmware readiness or G17C UAT.
    """
    validate_space(space)
    if type(objects) not in (list, tuple) or type(ops) not in (list, tuple):
        raise Refusal("SEQUENCE")
    if len(objects) > MAX_OBJECTS or len(ops) > MAX_OPS:
        raise Refusal("LIMIT")
    sizes = {}
    for obj in objects:
        if type(obj) is not Object:
            raise Refusal("OBJECT_TYPE")
        uint(obj.handle, 32)
        uint(obj.size)
        if obj.handle == 0 or obj.size == 0 or obj.handle in sizes:
            raise Refusal("OBJECT")
        sizes[obj.handle] = obj.size
    pending = []
    for op in ops:
        if type(op) is not Op:
            raise Refusal("OP_TYPE")
        uint(op.flags, 32)
        uint(op.handle, 32)
        for value in (op.offset, op.size, op.addr):
            uint(value)
        is_unbind = bool(op.flags & UNBIND)
        if is_unbind:
            if op.flags != UNBIND or op.handle != 0 or op.offset != 0:
                raise Refusal("FLAGS")
            accessed = 0
        else:
            if op.flags & ~(READ | WRITE | SINGLE_PAGE) or not op.flags & (READ | WRITE):
                raise Refusal("FLAGS")
            accessed = space.page_size if op.flags & SINGLE_PAGE else op.size
        if any(value % space.page_size for value in (op.addr, op.offset, op.size)):
            raise Refusal("ALIGNMENT")
        if (op.size == 0 or op.addr + op.size > U64_MAX or
            op.addr < space.vm_start or op.addr + op.size > space.vm_end):
            raise Refusal("RANGE")
        if op.addr < space.kernel_end and space.kernel_start < op.addr + op.size:
            raise Refusal("RESERVATION")
        if not is_unbind:
            if op.handle not in sizes or op.offset + accessed > sizes[op.handle]:
                raise Refusal("OBJECT")
        pending.append(Planned(op, accessed))
    return tuple(pending)


@dataclass(frozen=True)
class GPTBATPageNumber:
    """Only a static 32-meaningful-bit page-number format, no live register."""
    value: int


@dataclass(frozen=True)
class GPTBATBase:
    """46-bit aligned format domain; CPU PA/GPU VA qualification is unknown."""
    value: int


def decode_gptbat(page_number):
    if type(page_number) is not GPTBATPageNumber:
        raise Refusal("GPTBAT_DOMAIN")
    return GPTBATBase(uint(page_number.value, 32) * 16384)


def encode_gptbat(base):
    if type(base) is not GPTBATBase:
        raise Refusal("GPTBAT_DOMAIN")
    uint(base.value, 46)
    if base.value % 16384:
        raise Refusal("GPTBAT_ALIGNMENT")
    return GPTBATPageNumber(base.value // 16384)
