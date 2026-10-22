# SPDX-License-Identifier: GPL-2.0-or-later
"""Pinned open-source m1n1 CIVAC dispatch audit; bytes stay in input artifact."""
import hashlib
import struct

IMAGE_SHA = 'ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664'
IMAGE_BYTES = 3932160
GOT_OFFSET = 0x108188
FEATURE_POINTER_OFFSET = 0x1012d0
FEATURES_OFFSET = 0x7fba8
CYCLONE_FLAG_OFFSET = 11
OPCODE = 0x30a
CASE_TABLE_OFFSET = 0x80fb4
CASE_OFFSET = 0x2d454
FUNCTION_OFFSET = 0x277a0
EPILOGUE_OFFSET = 0x2ce48


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def word(image, at):
    return struct.unpack_from('<I', image, at)[0]


def branch_target(image, at, opcode):
    ins = word(image, at)
    need(ins >> 26 == opcode, 'cache_path_branch_opcode')
    relative = ins & 0x3ffffff
    if relative & (1 << 25):
        relative -= 1 << 26
    return at + relative * 4


def verify_image(image):
    need(type(image) is bytes and len(image) == IMAGE_BYTES and
         hashlib.sha256(image).hexdigest() == IMAGE_SHA, 'cache_path_image_digest')
    # Opcode0x30a is normalized by0x300, signed16 table values scaled by4.
    target = 0x2cf54 + 4 * struct.unpack_from('<h', image, CASE_TABLE_OFFSET)[0]
    need(target == CASE_OFFSET, 'cache_path_dispatch_target')
    need(branch_target(image, 0x2d460, 0b100101) == FUNCTION_OFFSET,
         'cache_path_call_target')
    need(branch_target(image, 0x2d46c, 0b000101) == EPILOGUE_OFFSET,
         'cache_path_epilogue_target')
    need((word(image, EPILOGUE_OFFSET), word(image, EPILOGUE_OFFSET+4)) ==
         (0xd5033f9f, 0xd5033fdf), 'cache_path_completion_barriers')
    need(word(image, 0x277b0) == 0x39402c63 and
         word(image, 0x277e8) == 0x39402c00,
         'cache_path_feature_flag')
    need(word(image, 0x2780c) == 0xd50b7e20 and
         word(image, 0x27810) == 0x91010000,
         'cache_path_civac_and_stride')
    relocations = []
    for at in range(0x84d10, 0x8cd98, 24):
        destination, kind, addend = struct.unpack_from('<QQq', image, at)
        if destination == GOT_OFFSET:
            relocations.append((kind, addend))
    need(relocations == [(1027, FEATURE_POINTER_OFFSET)], 'cache_path_got_relocation')
    need(image[FEATURES_OFFSET+CYCLONE_FLAG_OFFSET] == 0, 'cache_path_cyclone_flag')
    return dict(result='PINNED_CIVAC_DISPATCH_AUDIT_PASS',
                input_image_sha256=IMAGE_SHA, opcode=OPCODE,
                issuing_core_only=0, cache_effects_cpu0_only=False,
                required_runtime_got_check=True,
                required_runtime_dispatch_table_check=True,
                required_runtime_feature_check=True,
                temporary_exception_guard_change=False,
                common_epilogue_restores_saved_guard=True,
                completion_barriers=['DSB SY', 'ISB'],
                cache_instructions_for_aligned64_bytes=1,
                cyclone_sysreg_writes_when_verified_flag_zero=0,
                native_execution='NOT RUN')
