#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline checks for vector-first observation, replay and fault boundaries."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('recorder31f_check', Path(__file__).with_name('recorder_check.py'))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
e = r.e
IMAGE = SYMBOLS = PREPARED = None


class VectorFirstRecorder(unittest.TestCase):
    def test_precise_overlay_only_vector_word_and_body(self):
        self.assertEqual(PREPARED.derived[:4], struct.pack('<I', r.HOOK))
        self.assertEqual(PREPARED.derived[4:r.CODE_START], IMAGE[4:r.CODE_START])
        end = r.CODE_START + r.CODE_BYTES
        self.assertEqual(PREPARED.derived[end:], IMAGE[end:])
        self.assertEqual(len(PREPARED.derived), len(IMAGE))

    def test_image_symbols_mandatory_pins(self):
        for image, symbols, reason in [(IMAGE, None, 'full_symbols_required'),
                                       (IMAGE[:-1], SYMBOLS, 'image_digest'),
                                       (IMAGE, SYMBOLS + b'\n', 'symbol_digest')]:
            with self.assertRaisesRegex(e.Refused, reason):
                r.prepare(image, symbols)

    def test_changed_proposal_refused(self):
        plan, body, hook = r.builder.build(IMAGE, SYMBOLS)
        bad = bytes([body[0] ^ 1]) + body[1:]
        for proposal, reason in [((plan, bad, hook), 'recorder_digest'),
                                 ((plan, body, b'\0' * 4), 'entry_branch_binding'),
                                 ((dict(plan, resume_offset='0x900'), body, hook), 'overlay_binding')]:
            with patch.object(r.builder, 'build', return_value=proposal):
                with self.assertRaisesRegex(e.Refused, reason):
                    r.prepare(IMAGE, SYMBOLS)

    def test_first_store_precedes_every_system_read_and_branch(self):
        body, labels = r.builder.program()
        words = struct.unpack('<' + 'I' * (len(body) // 4), body)
        first = (labels['first_store'] - r.CODE_START) // 4
        self.assertEqual(first, 3)
        self.assertEqual(words[first], 0xf9000008)
        self.assertEqual(words[first-1], 0xd2800028)
        self.assertFalse(any(r.boundary_kind(word) == 'system_register_read' or
                             word & 0x7c000000 == 0x14000000 or
                             word & 0xff000010 == 0x54000000 for word in words[:first]))

    def test_all_thirteen_identity_and_el_cases(self):
        self.assertEqual(len(r.CASES), 13)
        for case, (el, mpidr, fault) in r.CASES.items():
            with self.subTest(case=case):
                result = r.run_case(PREPARED, case)
                expected = [1, 2, 3, 255] if el not in (4, 8, 12) else (
                    [1, 2, 3] if fault else [1, 2, 3, 4])
                self.assertEqual(result['phase_events'], expected)
                self.assertEqual(len(result['checkpoints']), 0 if fault else 6)
                self.assertFalse(result['physical_publication_modeled'])
                self.assertFalse(result['exception_handler_modeled'])

    def test_every_initial_flag_pattern_and_identity_preserves_live_state(self):
        for flags in range(16):
            for case in r.CASES:
                if not r.CASES[case][2]:
                    row = r.run_case(PREPARED, case, initial_nzcv=flags)
                    self.assertTrue(all(point['live_state_equal'] for point in row['checkpoints']))

    def test_x0_x8_flags_ignored_only_before_their_original_definition(self):
        row = r.run_case(PREPARED, 'cpu1_el1')
        self.assertEqual([(int(x['checkpoint_offset'],16), x['x0_included'],
                           x['x8_included'], x['nzcv_included']) for x in row['checkpoints']],
                         list(r.CHECKPOINTS))

    def test_wrong_x9_replay_is_detected_at_vector_resume(self):
        derived = bytearray(PREPARED.derived)
        at = r.CODE_START + r.CODE_BYTES - 8
        self.assertEqual(struct.unpack_from('<I', derived, at)[0], 0xd2800609)
        struct.pack_into('<I', derived, at, 0xd2800629)
        with self.assertRaisesRegex(e.Refused, 'live_state_not_equivalent'):
            r.run_case(r.Prepared(IMAGE, bytes(derived), PREPARED.plan), 'cpu1_el1')

    def test_other_identity_not_filtered_even_when_sctlr_faults(self):
        machine = r.RecorderMachine(PREPARED.derived, r.memory(IMAGE), 4, 0x40002, True)
        r.seed(machine, 10)
        with self.assertRaisesRegex(e.Refused, 'modeled_sctlr_read_fault'):
            r.advance(machine, 4, 256)
        self.assertEqual(machine.memory.read64(e.BASE+r.RECORD), 3)
        self.assertEqual(machine.memory.read64(e.BASE+r.RECORD+16), 0x40002)
        self.assertEqual(machine.sctlr_attempts, 1)

    def test_step_limits_and_unknown_case(self):
        for bound in (0, 1, 4097, True):
            with self.assertRaises(e.Refused):
                r.run_case(PREPARED, 'cpu1_el1', max_steps=bound)
        with self.assertRaisesRegex(e.Refused, 'unknown_recorder_case'):
            r.run_case(PREPARED, 'hardware')

    def test_report_has_no_raw_synthetic_values_or_native_claim(self):
        result = r.check(IMAGE, SYMBOLS)
        serialized = json.dumps(result)
        for value in (e.BASE, e.BASE+r.RECORD, e.BASE+e.FALLBACK_TOP, 0x2929292929292929):
            self.assertNotIn(str(value), serialized)
            self.assertNotIn(hex(value), serialized)
        self.assertFalse(result['hardware_model'])
        self.assertFalse(result['native_deployment_ready'])
        self.assertEqual(result['native_execution'], 'NOT RUN')

    def test_full_layout_audit_and_source_pin(self):
        row = r.builder.audit.audit(IMAGE, SYMBOLS)
        self.assertEqual(row['instructions_before_old_hook'], 2)
        self.assertTrue(row['entry_slot_also_sync_exception_vector'])
        self.assertFalse(row['computed_reference_proof'])
        with self.assertRaisesRegex(ValueError, 'public_source_digest'):
            r.builder.audit.audit(IMAGE, SYMBOLS, b'not the pinned source')

    def test_all_reached_boundary_stops_equal_clean_prefix(self):
        results = [r.run_boundary_matrix(PREPARED, case) for case in r.CASES
                   if not r.CASES[case][2]]
        self.assertEqual(sum(result['stopped_cases'] for result in results), 332)
        self.assertTrue(all(result['all_prefix_states_equal'] for result in results))

    def test_all_static_boundary_sites_reached(self):
        static = {at for at in range(r.CODE_START, r.CODE_START+r.CODE_BYTES, 4)
                  if r.boundary_kind(struct.unpack_from('<I', PREPARED.derived, at)[0])}
        reached = set()
        for case, (el, mpidr, fault) in r.CASES.items():
            if fault:
                continue
            machine = r.RecorderMachine(PREPARED.derived, r.memory(IMAGE), el, mpidr)
            r.seed(machine, 10)
            r.advance(machine, 4, 256)
            reached.update(int(row['offset'],16) for row in machine.trace
                           if int(row['offset'],16) in static)
        self.assertEqual(reached, static)
        self.assertGreater(len(static), 20)

    def test_first_mrs_fault_preserves_pre_mrs_marker(self):
        _, labels = r.builder.program()
        for side in ('before','after'):
            machine = r.RecorderMachine(PREPARED.derived, r.memory(IMAGE), 4, e.CPU1,
                                        fault_at=(labels['first_mrs'],side))
            r.seed(machine, 10)
            with self.assertRaises(r.BoundaryFault):
                r.advance(machine, 4, 256)
            self.assertEqual(machine.phase_events, [1])
            self.assertEqual(machine.memory.read64(e.BASE+r.RECORD), 1)
            self.assertEqual(machine.memory.read64(e.BASE+r.RECORD+16), 0)

    def test_first_store_fault_can_still_leave_zero(self):
        _, labels = r.builder.program()
        for side, expected in [('before',0),('after',1)]:
            machine = r.RecorderMachine(PREPARED.derived, r.memory(IMAGE), 4, e.CPU1,
                                        fault_at=(labels['first_store'],side))
            r.seed(machine, 10)
            with self.assertRaises(r.BoundaryFault):
                r.advance(machine, 4, 256)
            self.assertEqual(machine.memory.read64(e.BASE+r.RECORD), expected)

    def test_fault_latches_no_retry(self):
        _, labels = r.builder.program()
        machine = r.RecorderMachine(PREPARED.derived, r.memory(IMAGE), 8, e.CPU1,
                                    fault_at=(labels['first_mrs'],'after'))
        r.seed(machine, 10)
        with self.assertRaises(r.BoundaryFault):
            r.advance(machine, 4, 256)
        before = r._prefix_state(machine)
        with self.assertRaisesRegex(e.Refused, 'boundary_model_already_stopped'):
            machine.step()
        self.assertEqual(r._prefix_state(machine), before)

    def test_phase4_store_does_not_prove_final_barrier_or_replay(self):
        machine = r.RecorderMachine(PREPARED.derived, r.memory(IMAGE), 8, e.CPU1)
        r.seed(machine, 10)
        r.advance(machine, 4, 256)
        last = [int(row['offset'],16) for row in machine.trace
                if row['instruction'] == 'dsb_sy_model_event'][-1]
        stopped = r.RecorderMachine(PREPARED.derived, r.memory(IMAGE), 8, e.CPU1,
                                    fault_at=(last,'before'))
        r.seed(stopped,10)
        with self.assertRaises(r.BoundaryFault):
            r.advance(stopped,4,256)
        self.assertEqual(stopped.memory.read64(e.BASE+r.RECORD),4)
        self.assertNotEqual(stopped.pc,e.BASE+4)

    def test_fault_boundary_rejects_bad_configuration(self):
        for invalid in (True, (), [], (r.CODE_START,), (r.CODE_START,'during'),
                        (r.CODE_START,True), (r.CODE_START+1,'before'), (0,'before'),
                        (r.CODE_START+r.CODE_BYTES,'after')):
            with self.assertRaisesRegex(e.Refused,'invalid_boundary_fault'):
                r.RecorderMachine(PREPARED.derived,r.memory(IMAGE),4,e.CPU1,fault_at=invalid)
        with self.assertRaisesRegex(e.Refused,'boundary_instruction_not_supported'):
            r.RecorderMachine(PREPARED.derived,r.memory(IMAGE),4,e.CPU1,
                              fault_at=(r.CODE_START,'before'))

    def synthetic_word(self, instruction, el=4):
        image = bytearray(PREPARED.derived)
        struct.pack_into('<I',image,r.CODE_START,instruction)
        machine = r.RecorderMachine(bytes(image),r.memory(IMAGE),el,e.CPU1)
        machine.pc=e.BASE+r.CODE_START
        return machine

    def test_store_scope_rejects_mmio_stack_and_reserved_fields(self):
        for address in (e.BASE+e.FALLBACK_TOP-16,e.BASE+r.RECORD+32,e.BASE+r.RECORD+1,
                        0x280688000):
            machine=self.synthetic_word(0xf9000008)
            machine.x[0],machine.x[8]=address,1
            with self.assertRaisesRegex(e.Refused,'record_write_not_allowlisted'):
                machine.step()
            self.assertEqual(machine.memory.writes,[])

    def test_phase_values_allow_only_named_states(self):
        for value in (1,2,3,4,255):
            machine=self.synthetic_word(0xf9000008)
            machine.x[0],machine.x[8]=e.BASE+r.RECORD,value
            machine.step()
            self.assertEqual(machine.phase_events,[value])
        machine=self.synthetic_word(0xf9000008)
        machine.x[0],machine.x[8]=e.BASE+r.RECORD,5
        with self.assertRaisesRegex(e.Refused,'record_phase_value'):
            machine.step()

    def test_selected_sctlr_level_and_no_privileged_writes(self):
        for instruction,level in ((0xd5381008,4),(0xd53c1008,8),(0xd53e1008,12)):
            machine=self.synthetic_word(instruction,level)
            machine.step()
            self.assertEqual(machine.x[8],r.SCTLR_VALUES[level])
            with self.assertRaisesRegex(e.Refused,'selected_sctlr_level_mismatch'):
                self.synthetic_word(instruction,8 if level==4 else 4).step()
        for instruction in (0xd5380408,0xd5181008,0xffffffff):
            with self.assertRaisesRegex(e.Refused,'instruction_unsupported'):
                self.synthetic_word(instruction).step()

    def test_fetch_cannot_leave_reviewed_scope(self):
        machine=self.synthetic_word(0xd503201f)
        machine.pc=e.BASE+r.CODE_START+r.CODE_BYTES
        with self.assertRaisesRegex(e.Refused,'instruction_scope'):
            machine.fetch()


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image',type=Path,required=True)
    parser.add_argument('--symbols',type=Path,required=True)
    args,remaining=parser.parse_known_args()
    IMAGE,SYMBOLS=args.image.read_bytes(),args.symbols.read_bytes()
    PREPARED=r.prepare(IMAGE,SYMBOLS)
    unittest.main(argv=['test_recorder_check.py']+remaining)
