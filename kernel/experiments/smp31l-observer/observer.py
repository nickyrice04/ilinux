# SPDX-License-Identifier: GPL-2.0-or-later
"""Original Normal-memory observation and CPU0 control; no transport or writes.

Only caller-supplied callbacks access the target. A positive committed identity
proves the prefix executed, not a reset route or failure of the Device record.
Negative reads cannot exclude CPU1 execution or dirty/private cached stores.
"""
import copy
import math

RECORDS = {'vector': 0x1000, 'cold': 0x1080}
CONTROL_OFFSET = 0x1100
BYTES = 64
MARKER = 0x314c435055304f4b
RETURN_VALUE = 0x314b  # The unchanged, independently assembled 31K store leaf.
MAX_SAMPLES = 2048


class ObservationError(ValueError):
    """Only original fixed reason codes may be emitted in public reports."""


def need(ok, reason):
    if not ok:
        raise ObservationError(reason)


def u64(value):
    return type(value) is int and 0 <= value < 1 << 64


def record_address(helper, name):
    need(u64(helper) and 0 < helper < (1 << 41) - 0x4000 and helper % 0x4000 == 0,
         'normal_helper_address')
    need(name in RECORDS, 'normal_record_name')
    return helper + RECORDS[name]


def probes(helper):
    record_address(helper, 'vector')
    return tuple(dict(name='normal_%s_%s_%s' % (name, end, 'write' if write else 'read'),
                      address=helper+offset+delta, physical=helper+offset+delta,
                      write=write, permission_fault=False, attr=0xff, shareability=2)
                 for name, offset in (*RECORDS.items(), ('control', CONTROL_OFFSET))
                 for end, delta in (('first', 0), ('last', BYTES-8))
                 for write in (False, True))


class Tracker:
    def __init__(self):
        self.closed = False
        self.state = dict(samples_attempted=0, samples_completed=0,
                          reads_attempted=0, reads_completed=0,
                          highest_phase_seen=0, any_record_seen=False,
                          identity_status='not_committed', error=None,
                          cpu1_execution='UNVERIFIED', device_visibility='UNTESTED')

    def sample(self, read64, address):
        need(not self.closed, 'normal_tracker_closed')
        need(u64(address) and address % 128 == 0, 'normal_record_alignment')
        if self.state['samples_attempted'] >= MAX_SAMPLES:
            self.closed = True
            self.state['error'] = 'normal_sample_budget'
            raise ObservationError('normal_sample_budget')
        self.state['samples_attempted'] += 1
        values = []
        try:
            for index, offset in enumerate((0, 8, 0)):
                self.state['reads_attempted'] += 1
                value = read64(address + offset)
                need(u64(value), 'normal_read_value')
                self.state['reads_completed'] += 1
                values.append(value)
                # A visible uncommitted identity is partial evidence too. It
                # never proves whose execution occurred, but must stop reuse.
                self.state['any_record_seen'] |= bool(value)
                if index != 1:
                    need(value in (0, 1, 2), 'normal_phase_invalid')
                    self.state['highest_phase_seen'] = max(self.state['highest_phase_seen'], value)
            before, identity, after = values
            need(after >= before, 'normal_phase_regression')
            if before >= 2:
                self.state['identity_status'] = ('expected_cpu1' if identity == 0x40001
                                                  else 'unexpected_cpu')
                need(identity == 0x40001, 'normal_identity_unexpected')
                self.state['cpu1_execution'] = 'PREFIX_IDENTITY_OBSERVED'
            self.state['samples_completed'] += 1
            self.closed = self.state['any_record_seen']
        except BaseException as exc:
            self.closed = True
            self.state['error'] = str(exc) if isinstance(exc, ObservationError) else 'normal_read_interrupted'
            raise
        return copy.deepcopy(self.state)


def cpu0_control(read64, store, journal, starts, clock):
    """One marker/restoration control,24 reads/2 stores, all before CPU1 starts.

The caller binds read64(offset) to the owned64-byte Normal control span and
store(value) to its +32 word using the existing returning CPU0 leaf. A failure
never invokes another target callback, including restoration.
"""
    state = dict(result='RUNNING', scope='cpu0_normal_ram_observer',
                 read_intents=0, write_intents=0,
                 reads_attempted=0, reads_completed=0, writes_attempted=0,
                 writes_acknowledged=0, marker_observed=False,
                 canaries_preserved=False, original_restored=False,
                 cpu1_visibility='NOT_TESTED', error=None)
    initial = last = None

    def budget():
        nonlocal initial, last
        count, now = starts(), clock()
        need(type(count) is int and count == 0, 'normal_control_after_start')
        need(type(now) in (float, int) and math.isfinite(now), 'normal_control_clock')
        need(last is None or now >= last, 'normal_control_clock_regression')
        initial = now if initial is None else initial
        last = now
        need(now - initial < 2.0, 'normal_control_deadline')

    def read_block():
        words = []
        for offset in range(0, BYTES, 8):
            budget()
            state['read_intents'] += 1
            journal(copy.deepcopy(state))
            budget()
            state['reads_attempted'] += 1
            value = read64(offset)
            need(u64(value), 'normal_control_read_value')
            state['reads_completed'] += 1
            budget()
            words.append(value)
        return words

    def write(value):
        budget()
        state['write_intents'] += 1
        journal(copy.deepcopy(state))
        budget()
        state['writes_attempted'] += 1
        returned = store(value)
        need(type(returned) is int and returned == RETURN_VALUE, 'normal_control_return')
        state['writes_acknowledged'] += 1
        budget()

    try:
        need(read_block() == [0]*8, 'normal_control_initial_nonzero')
        write(MARKER)
        expected = [0]*8
        expected[4] = MARKER
        need(read_block() == expected, 'normal_control_marker_or_canary')
        state.update(marker_observed=True, canaries_preserved=True)
        write(0)
        need(read_block() == [0]*8, 'normal_control_restore')
        state.update(result='CPU0_NORMAL_CONTROL_PASS', original_restored=True)
        budget()
        journal(copy.deepcopy(state))
        budget()
        return state
    except BaseException as exc:
        state.update(result='STOP', error=str(exc) if isinstance(exc, ObservationError) else 'normal_control_interrupted')
        # Persist only local state. Preserve interruption even if journaling fails.
        try:
            journal(copy.deepcopy(state))
        except BaseException:
            pass
        raise
