#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Sequential, partial-preserving PS observations. No transport/target code."""
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('ps_plan',Path(__file__).with_name('plan.py'))
p=importlib.util.module_from_spec(spec); spec.loader.exec_module(p)


class Tracker:
    def __init__(self):
        self.rows=[]; self.reads_attempted=0; self.reads_completed=0; self.error=None

    def report(self):
        return dict(samples=self.rows, reads_attempted=self.reads_attempted,
                    reads_completed=self.reads_completed, error=self.error,
                    entry_execution='NOT_ESTABLISHED', reset_release='NOT_ESTABLISHED',
                    effective_reset_destination='NOT_ESTABLISHED')

    def sample(self, phase, read32, persist):
        p.require(self.error is None and len(self.rows)<4 and
                  phase == p.PHASES[len(self.rows)], 'ps_sample_order')
        row=dict(phase=phase, complete=False, cpu0=None, cpu1=None)
        self.rows.append(row)
        for cpu in (0,1):
            self.reads_attempted+=1
            persist(self.report())  # durable intent before each read, including baseline
            try:
                value=read32(cpu)
                decoded=p.fields(value)
            except BaseException as exc:
                self.error='read_or_decode_failed'
                persist(self.report())
                raise
            row['cpu'+str(cpu)]=decoded
            self.reads_completed+=1
            persist(self.report())
        row['complete']=True
        persist(self.report())
        return self.report()
