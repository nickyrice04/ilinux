# SPDX-License-Identifier: MIT
import dataclasses
import importlib.util
from pathlib import Path
import random
import sys
import unittest

SPEC = importlib.util.spec_from_file_location("gpu31q_reference", Path(__file__).with_name("reference.py"))
R = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = R
SPEC.loader.exec_module(R)
P = 0x4000
SPACE = R.Space(P, P, 0x1000000000, 0x800000, 0x900000, 0x100000)
OBJ = R.Object(1, 0x1000000)
OP = R.Op(R.READ, 1, 0, 2 * P, 0x100000000)


class PlannerTests(unittest.TestCase):
    def refuse(self, space=SPACE, objects=(OBJ,), ops=(OP,)):
        with self.assertRaises(R.Refusal):
            R.plan(space, objects, ops)

    def test_regular_high_address(self):
        result = R.plan(SPACE, [OBJ], [OP])
        self.assertEqual(result, (R.Planned(OP, 2 * P),))
        self.assertEqual(result[0].op.addr, 1 << 32)

    def test_read_write_permissions(self):
        for flags in (R.READ, R.WRITE, R.READ | R.WRITE):
            op = dataclasses.replace(OP, flags=flags)
            self.assertEqual(R.plan(SPACE, [OBJ], [op])[0].op.flags, flags)

    def test_kernel_adjacency(self):
        for addr in (SPACE.kernel_start - OP.size, SPACE.kernel_end):
            self.assertEqual(len(R.plan(SPACE, [OBJ], [dataclasses.replace(OP, addr=addr)])), 1)

    def test_kernel_overlap(self):
        for addr in (SPACE.kernel_start - P, SPACE.kernel_start, SPACE.kernel_end - P):
            self.refuse(ops=[dataclasses.replace(OP, addr=addr)])
        self.refuse(ops=[dataclasses.replace(OP, addr=SPACE.kernel_start - P, size=SPACE.kernel_min_size + 2 * P)])

    def test_window_boundaries(self):
        for addr in (SPACE.vm_start, SPACE.vm_end - OP.size):
            self.assertTrue(R.plan(SPACE, [OBJ], [dataclasses.replace(OP, addr=addr)]))
        for addr in (0, SPACE.vm_end - P, SPACE.vm_end):
            self.refuse(ops=[dataclasses.replace(OP, addr=addr)])

    def test_single_page(self):
        op = dataclasses.replace(OP, flags=R.READ | R.SINGLE_PAGE)
        self.assertEqual(R.plan(SPACE, [R.Object(1, P)], [op])[0].object_bytes_accessed, P)
        self.refuse(objects=[R.Object(1, P - 1)], ops=[op])

    def test_single_page_offset(self):
        op = dataclasses.replace(OP, offset=P, flags=R.WRITE | R.SINGLE_PAGE)
        self.assertTrue(R.plan(SPACE, [R.Object(1, 2 * P)], [op]))
        self.refuse(objects=[R.Object(1, 2 * P - 1)], ops=[op])

    def test_unbind(self):
        op = R.Op(R.UNBIND, 0, 0, P, P)
        self.assertEqual(R.plan(SPACE, [], [op]), (R.Planned(op, 0),))

    def test_unbind_fields(self):
        op = R.Op(R.UNBIND, 0, 0, P, P)
        for changes in ({"flags": 3}, {"flags": 9}, {"handle": 1}, {"offset": P}):
            self.refuse(objects=[], ops=[dataclasses.replace(op, **changes)])

    def test_unbind_protects_kernel(self):
        self.refuse(objects=[], ops=[R.Op(R.UNBIND, 0, 0, P, SPACE.kernel_start)])

    def test_ordered_replace(self):
        ops = (OP, R.Op(R.UNBIND, 0, 0, OP.size, OP.addr), dataclasses.replace(OP, flags=R.WRITE))
        self.assertEqual(tuple(x.op for x in R.plan(SPACE, [OBJ], ops)), ops)

    def test_alignment(self):
        for field in ("addr", "size", "offset"):
            self.refuse(ops=[dataclasses.replace(OP, **{field: getattr(OP, field) + 1})])

    def test_unknown_flags(self):
        for flags in (0, R.SINGLE_PAGE, 16, R.READ | (1 << 31)):
            self.refuse(ops=[dataclasses.replace(OP, flags=flags)])

    def test_object_bounds(self):
        self.assertTrue(R.plan(SPACE, [R.Object(1, 2 * P)], [OP]))
        self.refuse(objects=[R.Object(1, 2 * P - 1)])
        self.refuse(objects=[R.Object(1, 2 * P)], ops=[dataclasses.replace(OP, offset=P)])

    def test_unknown_duplicate_object(self):
        self.refuse(objects=[])
        self.refuse(objects=[OBJ, OBJ])
        self.refuse(objects=[dataclasses.replace(OBJ, handle=2)])
        self.refuse(objects=[dataclasses.replace(OBJ, handle=0)])

    def test_u64_bounds(self):
        space = R.Space(1, 0, R.U64_MAX, 0x100, 0x200, 1)
        op = R.Op(R.READ, 1, 0, 1, R.U64_MAX - 1)
        self.assertTrue(R.plan(space, [OBJ], [op]))
        self.refuse(space=space, ops=[dataclasses.replace(op, addr=R.U64_MAX)])
        self.refuse(space=space, ops=[dataclasses.replace(op, size=2)])
        self.refuse(space=space, objects=[R.Object(1, R.U64_MAX)], ops=[R.Op(R.READ, 1, R.U64_MAX, 1, 0)])
        aligned_end = R.U64_MAX & ~(P - 1)
        aligned_space = R.Space(P, 0, aligned_end, P, 2 * P, P)
        last_page = R.Op(R.READ, 1, 0, P, aligned_end - P)
        self.assertTrue(R.plan(aligned_space, [OBJ], [last_page]))
        self.refuse(space=aligned_space, ops=[dataclasses.replace(last_page, addr=aligned_end)])

    def test_zero_spans(self):
        self.refuse(ops=[dataclasses.replace(OP, size=0)])
        self.refuse(objects=[dataclasses.replace(OBJ, size=0)])

    def test_space_shape(self):
        for changes in ({"page_size": 0}, {"page_size": 3}, {"vm_end": P}, {"vm_end": 0}, {"vm_end": SPACE.vm_end - 1}):
            self.refuse(space=dataclasses.replace(SPACE, **changes))

    def test_space_reservation(self):
        for changes in ({"kernel_start": 0}, {"kernel_end": SPACE.vm_end + P}, {"kernel_end": SPACE.kernel_start}, {"kernel_min_size": 0}, {"kernel_min_size": SPACE.kernel_min_size + 1}, {"kernel_start": SPACE.kernel_start + 1}):
            self.refuse(space=dataclasses.replace(SPACE, **changes))

    def test_variable_page_sizes(self):
        for shift in range(17):
            page = 1 << shift
            space = R.Space(page, page, 32 * page, 16 * page, 20 * page, 4 * page)
            op = R.Op(R.READ | R.SINGLE_PAGE, 1, 0, 4 * page, 2 * page)
            self.assertEqual(R.plan(space, [R.Object(1, page)], [op])[0].object_bytes_accessed, page)

    def test_integer_width_and_type(self):
        for bad in (-1, True, 1.5, "1", None, 1 << 64):
            self.refuse(ops=[dataclasses.replace(OP, addr=bad)])
            self.refuse(space=dataclasses.replace(SPACE, page_size=bad))
        self.refuse(ops=[dataclasses.replace(OP, handle=1 << 32)])
        self.refuse(ops=[dataclasses.replace(OP, flags=1 << 32)])
        self.refuse(objects=[dataclasses.replace(OBJ, handle=True)])

    def test_bounded_collections(self):
        self.assertEqual(len(R.plan(SPACE, [OBJ], [OP] * 64)), 64)
        self.refuse(ops=[OP] * 65)
        self.refuse(objects=[R.Object(i + 1, P) for i in range(65)])

    def test_empty_batch(self):
        self.assertEqual(R.plan(SPACE, [], []), ())
        self.refuse(space=dataclasses.replace(SPACE, page_size=0), objects=[], ops=[])

    def test_input_types(self):
        for objects, ops in (({}, [OP]), ([OBJ], iter([OP])), ([1], [OP]), ([OBJ], [dict(vars(OP))])):
            self.refuse(objects=objects, ops=ops)
        self.refuse(space=dict(vars(SPACE)))

    def test_late_failure_preserves_inputs(self):
        ops = [OP, OP, dataclasses.replace(OP, addr=SPACE.kernel_start)]
        before = list(ops)
        self.refuse(ops=ops)
        self.assertEqual(ops, before)
        self.assertEqual(R.plan(SPACE, [OBJ], [OP]), (R.Planned(OP, 2 * P),))

    def test_spaces_remain_independent(self):
        first = R.plan(SPACE, [OBJ], [OP])
        second = R.plan(SPACE, [OBJ], [OP])
        self.assertEqual(first, second)
        # Identical user VA in two calls is not a global allocation collision.
        other = dataclasses.replace(SPACE, kernel_start=OP.addr, kernel_end=OP.addr + SPACE.kernel_min_size)
        self.refuse(space=other)
        self.assertEqual(R.plan(SPACE, [OBJ], [OP]), first)

    def test_dense_page_grid_oracle(self):
        space = R.Space(P, P, 33 * P, 16 * P, 20 * P, 4 * P)
        # Independent integer-page oracle, with all flags and boundaries.
        for addr in range(36):
            for count in range(11):
                for offset in range(11):
                    for flags in range(32):
                        span = count > 0 and addr >= 1 and addr + count <= 33 and (addr + count <= 16 or addr >= 20)
                        if flags & 1:
                            form = flags == 1 and offset == 0
                        else:
                            form = flags & ~14 == 0 and flags & 6 != 0 and offset + (1 if flags & 8 else count) <= 8
                        op = R.Op(flags, 0 if flags & 1 else 1, offset * P, count * P, addr * P)
                        try:
                            R.plan(space, [R.Object(1, 8 * P)], [op])
                            actual = True
                        except R.Refusal:
                            actual = False
                        self.assertEqual(actual, bool(span and form))

    def test_seeded_high_width_translation_invariance(self):
        rng = random.Random(0x31)
        # Translating only a VA space and all VA operands cannot affect object
        # extents; this catches truncation/accidental BO-versus-VA arithmetic.
        for _ in range(500):
            base = rng.randrange(1 << 20, 1 << 45) * P
            small = R.Space(P, P, 33 * P, 16 * P, 20 * P, 4 * P)
            shifted = dataclasses.replace(small, vm_start=base + P, vm_end=base + 33 * P, kernel_start=base + 16 * P, kernel_end=base + 20 * P)
            op = R.Op(R.READ, 1, 0, P, rng.choice((P, 15 * P, 20 * P, 32 * P)))
            a = R.plan(small, [OBJ], [op])[0]
            b = R.plan(shifted, [OBJ], [dataclasses.replace(op, addr=op.addr + base)])[0]
            self.assertEqual(a.object_bytes_accessed, b.object_bytes_accessed)
            self.assertEqual(a.op.addr + base, b.op.addr)


class GPTBATTests(unittest.TestCase):
    def test_literal_vectors_including_zero(self):
        for page, base in ((0, 0), (1, 0x4000), (0x10000, 0x40000000),
                           (0x80000000, 0x200000000000), (0xffffffff, 0x3fffffffc000)):
            self.assertEqual(R.decode_gptbat(R.GPTBATPageNumber(page)), R.GPTBATBase(base))
            self.assertEqual(R.encode_gptbat(R.GPTBATBase(base)), R.GPTBATPageNumber(page))

    def test_single_bit_vectors(self):
        for bit in range(32):
            self.assertEqual(R.decode_gptbat(R.GPTBATPageNumber(1 << bit)), R.GPTBATBase(1 << (bit + 14)))

    def test_width_boundaries(self):
        for value in (1 << 32, (1 << 32) + 1, R.U64_MAX):
            with self.assertRaises(R.Refusal):
                R.decode_gptbat(R.GPTBATPageNumber(value))
        for value in (1 << 46, (1 << 46) + 0x4000, R.U64_MAX):
            with self.assertRaises(R.Refusal):
                R.encode_gptbat(R.GPTBATBase(value))

    def test_every_nonzero_page_offset(self):
        for offset in range(1, 16384):
            with self.assertRaisesRegex(R.Refusal, "^GPTBAT_ALIGNMENT$"):
                R.encode_gptbat(R.GPTBATBase(0x3fffffffc000 + offset))

    def test_integer_types(self):
        for bad in (True, False, -1, 1.0, "1", None):
            with self.assertRaises(R.Refusal):
                R.decode_gptbat(R.GPTBATPageNumber(bad))
            with self.assertRaises(R.Refusal):
                R.encode_gptbat(R.GPTBATBase(bad))

    def test_distinct_domains(self):
        for bad in (1, R.GPTBATBase(1), OP, None):
            with self.assertRaisesRegex(R.Refusal, "^GPTBAT_DOMAIN$"):
                R.decode_gptbat(bad)
        for bad in (0x4000, R.GPTBATPageNumber(1), OP, None):
            with self.assertRaisesRegex(R.Refusal, "^GPTBAT_DOMAIN$"):
                R.encode_gptbat(bad)

    def test_seeded_roundtrips(self):
        rng = random.Random(0x31)
        for _ in range(10000):
            page = R.GPTBATPageNumber(rng.randrange(1 << 32))
            self.assertEqual(R.encode_gptbat(R.decode_gptbat(page)), page)

    def test_no_implicit_planner_conversion(self):
        base = R.decode_gptbat(R.GPTBATPageNumber(1))
        with self.assertRaisesRegex(R.Refusal, "^INTEGER$"):
            R.plan(SPACE, [OBJ], [dataclasses.replace(OP, addr=base)])
        # Format representability makes no validity/readiness assertion.
        self.assertEqual(set(vars(R.decode_gptbat(R.GPTBATPageNumber(0)))), {"value"})


if __name__ == "__main__":
    unittest.main()
