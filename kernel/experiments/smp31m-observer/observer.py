# SPDX-License-Identifier: GPL-2.0-or-later
"""Original paired Normal-memory observer; callback-only, no native runner.

CPU0 issues bounded clean/invalidate maintenance. Its architectural effects
can extend to other PEs in the shareability domain; this is not a local-only
operation. Qualifying the issuing CPU does not qualify CPU1's execution state.
The caller owns, zeroes and cleans each entire128-byte record span before any
CPU1 start, and makes no subsequent CPU0 store to any of those spans.
"""
import copy
from dataclasses import dataclass
import struct

RECORDS = {'vector': 0x1000, 'cold': 0x1080}
CONTROL_OFFSET = 0x1100
ALLOCATION_BYTES = 0x4000
RECORD_BYTES = 64
OWNED_BYTES = 128
CTR_LEAF_OFFSET = 0x220
CTR_WORDS = (0xd53b0020, 0xd65f03c0)  # MRS CTR_EL0,X0; RET.
CTR_LEAF = struct.pack('<2I', *CTR_WORDS)
MAX_SAMPLES = 2048
HCR_MASK = (1 << 34) | (1 << 27) | 1
HCR_VHE_HOST = (1 << 34) | (1 << 27)


class ObservationError(ValueError):
    """Fixed public diagnostics only; foreign error text is never serialized."""


def need(ok, reason):
    if not ok:
        raise ObservationError(reason)


def u64(value):
    return type(value) is int and 0 <= value < 1 << 64


@dataclass(frozen=True)
class Qualification:
    """Private address binding. Use public(), never serialize this object."""
    helper: int
    data_min_line_bytes: int
    writeback_granule_bytes: int

    def public(self):
        validate_qualification(self)
        return dict(result='CPU0_MAINTENANCE_LAYOUT_QUALIFIED',
                    data_min_line_bytes=self.data_min_line_bytes,
                    writeback_granule_bytes=self.writeback_granule_bytes,
                    issuing_cpu=0, issuing_exception_level=2,
                    issuing_regime='VHE_host_stage2_disabled',
                    record_bytes=RECORD_BYTES, owned_bytes=OWNED_BYTES,
                    maintenance='DC_CIVAC_to_PoC',
                    effects_limited_to_cpu0=False,
                    cpu1_cache_state='UNKNOWN',
                    native_success_established=False)


def validate_qualification(value):
    need(type(value) is Qualification, 'maintenance_qualification_type')
    need(u64(value.helper) and 0 < value.helper < (1 << 41)-ALLOCATION_BYTES
         and value.helper % ALLOCATION_BYTES == 0, 'maintenance_helper')
    need(type(value.data_min_line_bytes) is int and
         value.data_min_line_bytes in (64, 128), 'maintenance_min_line')
    need(type(value.writeback_granule_bytes) is int and
         value.writeback_granule_bytes in (64, 128) and
         value.data_min_line_bytes <= value.writeback_granule_bytes,
         'maintenance_writeback_granule')
    need(CTR_LEAF_OFFSET + len(CTR_LEAF) <= RECORDS['vector'],
         'maintenance_leaf_overlap')
    for name, start in RECORDS.items():
        need(start % OWNED_BYTES == 0 and start + OWNED_BYTES <= CONTROL_OFFSET,
             'maintenance_record_ownership')
        need(all(name == other or start + OWNED_BYTES <= at or
                 at + OWNED_BYTES <= start for other, at in RECORDS.items()),
             'maintenance_record_overlap')
    return value


def qualify(helper, current_el, hcr, ctr):
    """Decode a pre-start CTR reading; unknown CWG and larger layouts refuse.

DMinLine is a minimum, not the maximum affected granule. CWG supplies the
maximum writeback bound used here. Zero CWG is not silently treated as64.
The64-byte pinned m1n1 range stride is safe for this single operation only
after line sizes64/128 and complete128-byte ownership have been established.
"""
    need(type(current_el) is int and current_el == 8, 'maintenance_requires_cpu0_el2')
    need(u64(hcr) and hcr & HCR_MASK == HCR_VHE_HOST, 'maintenance_cpu0_regime')
    need(u64(ctr), 'maintenance_ctr_type')
    dmin, cwg = (ctr >> 16) & 15, (ctr >> 24) & 15
    need(cwg != 0, 'maintenance_cwg_unknown')
    return validate_qualification(Qualification(helper, 4 << dmin, 4 << cwg))


def record_address(qualification, name):
    validate_qualification(qualification)
    need(type(name) is str and name in RECORDS, 'maintenance_record_name')
    return qualification.helper + RECORDS[name]


class PairedTracker:
    """Cached triad, optionally one CIVAC, then maintained triad; fail-stop.

Read64 returns an exact integer. Maintain(address,64) must return exact0 only
after the pinned proxy's DSB SY/ISB epilogue and an immediate guard check.
The callbacks must not retry, remap, write records or clear exception evidence.
Journal writes only local state. Intent is persisted before dispatch. Any
callback failure permanently closes this observer without cleanup callbacks.
"""
    def __init__(self, qualification, name, *, initialized_clean, cpu0_stores_frozen):
        self.address = record_address(qualification, name)
        need(initialized_clean is True, 'maintenance_record_not_clean')
        need(cpu0_stores_frozen is True, 'maintenance_cpu0_stores_not_frozen')
        self.closed = False
        self.state = dict(samples_attempted=0, samples_completed=0,
                          reads_attempted=0, reads_completed=0,
                          maintenance_intents=0, maintenance_attempted=0,
                          maintenance_acknowledged=0, cached={}, maintained={},
                          highest_phase_seen=0, any_record_seen=False,
                          identity_status='not_committed', error=None,
                          cpu1_execution='UNVERIFIED', observation_channel=None,
                          journal_failed=False, visibility_cause='UNKNOWN',
                          effects_limited_to_cpu0=False,
                          negative_excludes_execution=False)

    def _triad(self, read64, channel):
        part = dict(reads_completed=0, highest_phase_seen=0, any_record_seen=False,
                    identity_status='not_committed', complete=False)
        self.state[channel] = part
        values = []
        for index, offset in enumerate((0, 8, 0)):
            self.state['reads_attempted'] += 1
            value = read64(self.address + offset)
            need(u64(value), 'maintenance_read_value')
            self.state['reads_completed'] += 1
            part['reads_completed'] += 1
            values.append(value)
            part['any_record_seen'] |= bool(value)
            self.state['any_record_seen'] |= bool(value)
            if value:
                self.state['observation_channel'] = channel
            if index != 1:
                need(value in (0, 1, 2), 'maintenance_phase_invalid')
                part['highest_phase_seen'] = max(part['highest_phase_seen'], value)
                self.state['highest_phase_seen'] = max(self.state['highest_phase_seen'], value)
        before, identity, after = values
        need(after >= before, 'maintenance_phase_regression')
        if before >= 2:
            part['identity_status'] = 'expected_cpu1' if identity == 0x40001 else 'unexpected_cpu'
            self.state['identity_status'] = part['identity_status']
            need(identity == 0x40001, 'maintenance_identity_unexpected')
            self.state['cpu1_execution'] = 'PREFIX_IDENTITY_OBSERVED'
        part['complete'] = True

    def sample(self, read64, maintain, journal):
        need(not self.closed, 'maintenance_tracker_closed')
        if self.state['samples_attempted'] >= MAX_SAMPLES:
            self.closed = True
            self.state['error'] = 'maintenance_sample_budget'
            raise ObservationError('maintenance_sample_budget')
        self.state['samples_attempted'] += 1
        self.state['cached'], self.state['maintained'] = {}, {}

        def persist():
            try:
                journal(copy.deepcopy(self.state))
            except BaseException:
                self.state['journal_failed'] = True
                raise

        try:
            self._triad(read64, 'cached')
            if not self.state['any_record_seen']:
                self.state['maintenance_intents'] += 1
                persist()
                self.state['maintenance_attempted'] += 1
                returned = maintain(self.address, RECORD_BYTES)
                need(type(returned) is int and returned == 0, 'maintenance_return')
                self.state['maintenance_acknowledged'] += 1
                persist()
                self._triad(read64, 'maintained')
            self.state['samples_completed'] += 1
            self.closed = self.state['any_record_seen']
            return copy.deepcopy(self.state)
        except BaseException as exc:
            self.closed = True
            self.state['error'] = str(exc) if isinstance(exc, ObservationError) else 'maintenance_interrupted'
            # No journal or target callback here: the failing callback may be
            # the journal itself, and uncertain target state must stay stopped.
            raise
