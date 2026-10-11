#!/usr/bin/env python3
"""Core ML compute-unit benchmark: Neural Engine vs GPU vs CPU on macOS.

Builds two FP16 ML Program models with coremltools' MIL builder (no model
downloads):
  * ffn:  transformer-FFN-like stack, x[1,S,D] -> (linear D->F, gelu, linear F->D) x L
  * conv: 1x1-convolution stack in [1,C,1,S] layout (the layout ANE favours)
and times prediction under each MLComputeUnits setting.  Where available,
MLComputePlan reports the device Core ML *plans* for each op, which is the
evidence that a run used the ANE (results are never inferred from GPU runs).

Usage: tools/venv/bin/python benchmarks/ai/coreml_ane_bench.py OUT_DIR
Output: OUT_DIR/coreml.jsonl and the generated .mlpackage files.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import coremltools as ct
from coremltools.converters.mil import Builder as mb
from coremltools.converters.mil.mil import types

S, D, F, L = 512, 2048, 8192, 8          # tokens, model dim, ffn dim, layers
C = 2048                                   # conv channels


def build_ffn():
    rng = np.random.default_rng(0)
    ws = [((rng.standard_normal((F, D)) * 0.02).astype(np.float16),
           (rng.standard_normal((D, F)) * 0.02).astype(np.float16)) for _ in range(L)]

    @mb.program(input_specs=[mb.TensorSpec(shape=(1, S, D), dtype=types.fp16)],
                opset_version=ct.target.macOS15)
    def prog(x):
        for w1, w2 in ws:
            h = mb.linear(x=x, weight=w1)
            h = mb.gelu(x=h, mode="TANH_APPROXIMATION")
            x = mb.add(x=x, y=mb.linear(x=h, weight=w2))
        return x
    flops = 2 * S * (D * F * 2) * L
    return prog, {"x": np.random.rand(1, S, D).astype(np.float16)}, flops


def build_conv():
    rng = np.random.default_rng(1)
    ws = [(rng.standard_normal((C, C, 1, 1)) * 0.02).astype(np.float16) for _ in range(2 * L)]

    @mb.program(input_specs=[mb.TensorSpec(shape=(1, C, 1, S), dtype=types.fp16)],
                opset_version=ct.target.macOS15)
    def prog(x):
        for w in ws:
            x = mb.relu(x=mb.conv(x=x, weight=w))
        return x
    flops = 2 * S * C * C * 2 * L
    return prog, {"x": np.random.rand(1, C, 1, S).astype(np.float16)}, flops


UNITS = {
    "cpu_and_ne": ct.ComputeUnit.CPU_AND_NE,
    "cpu_and_gpu": ct.ComputeUnit.CPU_AND_GPU,
    "cpu_only": ct.ComputeUnit.CPU_ONLY,
    "all": ct.ComputeUnit.ALL,
}


def planned_devices(pkg_path, unit):
    """Count ops per planned device using MLComputePlan (macOS 14.4+)."""
    try:
        from coremltools.models.compute_plan import MLComputePlan
        from coremltools.models.compute_device import (MLCPUComputeDevice,
                                                       MLGPUComputeDevice,
                                                       MLNeuralEngineComputeDevice)
        compiled = ct.utils.compile_model(str(pkg_path))
        plan = MLComputePlan.load_from_path(path=compiled, compute_units=unit)
        counts = {}
        program = plan.model_structure.program
        for fn in program.functions.values():
            for op in fn.block.operations:
                usage = plan.get_compute_device_usage_for_mlprogram_operation(op)
                if usage is None:
                    continue
                dev = usage.preferred_compute_device
                name = ("ane" if isinstance(dev, MLNeuralEngineComputeDevice) else
                        "gpu" if isinstance(dev, MLGPUComputeDevice) else
                        "cpu" if isinstance(dev, MLCPUComputeDevice) else type(dev).__name__)
                counts[name] = counts.get(name, 0) + 1
        return counts
    except Exception as e:  # API availability differs across versions
        return {"error": repr(e)[:200]}


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    results = out / "coreml.jsonl"
    for name, builder in (("ffn", build_ffn), ("conv", build_conv)):
        prog, inputs, flops = builder()
        model = ct.convert(prog, convert_to="mlprogram",
                           compute_precision=ct.precision.FLOAT16,
                           minimum_deployment_target=ct.target.macOS15)
        pkg = out / f"{name}.mlpackage"
        model.save(str(pkg))
        for uname, unit in UNITS.items():
            m = ct.models.MLModel(str(pkg), compute_units=unit)
            t_load = time.time()
            m.predict(inputs)                      # first call: compile/plan
            first = time.time() - t_load
            for _ in range(3):
                m.predict(inputs)
            times = []
            for _ in range(15):
                t0 = time.perf_counter()
                m.predict(inputs)
                times.append(time.perf_counter() - t0)
            times.sort()
            med = times[len(times) // 2]
            rec = {"bench": "coreml", "model": name, "compute_units": uname,
                   "gflop_per_inference": flops / 1e9, "median_ms": med * 1e3,
                   "best_ms": times[0] * 1e3, "tflops_median": flops / med / 1e12,
                   "first_call_s": first,
                   "planned_ops_by_device": planned_devices(pkg, unit)}
            print(json.dumps(rec), flush=True)
            with results.open("a") as f:
                f.write(json.dumps(rec) + "\n")


if __name__ == "__main__":
    main()
