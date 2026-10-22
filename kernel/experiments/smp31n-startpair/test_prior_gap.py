"""Replay original31M against original synthetic interfaces; no target/client."""
from collections import Counter
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'native/boot'))
import test_smp31m as frozen
import test_smp31h as trace_fixture


def prior_gap():
    case = frozen.ControllerTests()
    try:
        fake, _, controller, _ = case.controller()
        fake.arrival = False
        trace = trace_fixture.TraceProxy(fake)
        controller.p = controller.i = trace
        journals = []
        previous = controller.journal
        def journal(state):
            journals.append(len(fake.hw))
            previous(state)
        controller.journal = journal
        try:
            controller.run()
        except frozen.j.Refusal as exc:
            assert str(exc) == 'cpu1_arrival_timeout'
        else:
            raise AssertionError('synthetic negative path unexpectedly passed')
        starts = [i for i, (name, args, _) in enumerate(trace.requests)
                  if name == 'call' and len(args) == 3 and
                  args[1] in (0x280688004, 0x280688008)]
        assert len(starts) == 2
        between = trace.requests[starts[0]+1:starts[1]]
        return dict(result='SYNTHETIC_31M_INTERSTORE_GAP',
                    external_iface_proxy_calls=len(between),
                    calls_by_method=dict(Counter(name for name, _, _ in between)),
                    journal_callbacks=journals.count(1),
                    native_duration_seconds=None, native_execution='NOT RUN')
    finally:
        case.doCleanups()


class GapTests(unittest.TestCase):
    def test_observer_work_separates_31m_stores(self):
        row = prior_gap()
        self.assertEqual(row['external_iface_proxy_calls'], 127)
        self.assertEqual(row['calls_by_method'], {'call':123, 'request':4})
        self.assertEqual(row['journal_callbacks'], 33)
        self.assertIsNone(row['native_duration_seconds'])


if __name__ == '__main__':
    unittest.main()
