// gpubench.swift - Metal GPU baseline for the macOS reference system.
//   swiftc -O gpubench.swift -o gpubench
// Usage: gpubench [all|info|fma|bw|gemm|graph|latency|unified]
//
// Shaders are compiled at runtime from source (no offline Metal toolchain
// needed).  GPU time comes from MTLCommandBuffer GPUStartTime/GPUEndTime.
// Output: one JSON object per measurement.
// The Linux counterpart (Vulkan compute) lives in benchmarks/linux/.

import Foundation
import Metal
import MetalPerformanceShaders
import MetalPerformanceShadersGraph

let device = MTLCreateSystemDefaultDevice()!
let queue = device.makeCommandQueue()!

let shaderSource = """
#include <metal_stdlib>
using namespace metal;

#define CHAINS(T) \
    T a0 = T(gid) * T(1e-7), a1 = a0 + T(1), a2 = a0 + T(2), a3 = a0 + T(3); \
    T a4 = a0 + T(4), a5 = a0 + T(5), a6 = a0 + T(6), a7 = a0 + T(7);

kernel void fma_f32(device float *out [[buffer(0)]], constant uint &iters [[buffer(1)]],
                    constant float2 &bc [[buffer(2)]], uint gid [[thread_position_in_grid]]) {
    CHAINS(float)
    float b = bc.x, c = bc.y;
    for (uint i = 0; i < iters; i++) {
        a0 = fma(a0, b, c); a1 = fma(a1, b, c); a2 = fma(a2, b, c); a3 = fma(a3, b, c);
        a4 = fma(a4, b, c); a5 = fma(a5, b, c); a6 = fma(a6, b, c); a7 = fma(a7, b, c);
    }
    out[gid] = a0 + a1 + a2 + a3 + a4 + a5 + a6 + a7;
}

kernel void fma_f16(device half *out [[buffer(0)]], constant uint &iters [[buffer(1)]],
                    constant float2 &bc [[buffer(2)]], uint gid [[thread_position_in_grid]]) {
    CHAINS(half)
    half b = half(bc.x), c = half(bc.y);
    for (uint i = 0; i < iters; i++) {
        a0 = fma(a0, b, c); a1 = fma(a1, b, c); a2 = fma(a2, b, c); a3 = fma(a3, b, c);
        a4 = fma(a4, b, c); a5 = fma(a5, b, c); a6 = fma(a6, b, c); a7 = fma(a7, b, c);
    }
    out[gid] = a0 + a1 + a2 + a3 + a4 + a5 + a6 + a7;
}

kernel void copy4(device const float4 *src [[buffer(0)]], device float4 *dst [[buffer(1)]],
                  uint gid [[thread_position_in_grid]]) {
    dst[gid] = src[gid];
}

// Read bandwidth: each thread sums `per` float4s strided by grid size.
kernel void read4(device const float4 *src [[buffer(0)]], device float *dst [[buffer(1)]],
                  constant uint &per [[buffer(2)]], uint gid [[thread_position_in_grid]],
                  uint n [[threads_per_grid]]) {
    float4 s = 0;
    for (uint i = 0; i < per; i++) s += src[gid + i * n];
    dst[gid] = s.x + s.y + s.z + s.w;
}

kernel void empty_kernel(device float *out [[buffer(0)]], uint gid [[thread_position_in_grid]]) {
    if (gid == 0xffffffff) out[0] = 1;
}
"""

func emit(_ d: [String: Any]) {
    let data = try! JSONSerialization.data(withJSONObject: d, options: [.sortedKeys])
    print(String(data: data, encoding: .utf8)!)
    fflush(stdout)
}

func median(_ v: [Double]) -> Double { let s = v.sorted(); return s[s.count / 2] }

let opts = MTLCompileOptions()
opts.mathMode = .safe
let library = try! device.makeLibrary(source: shaderSource, options: opts)
func pipeline(_ name: String) -> MTLComputePipelineState {
    try! device.makeComputePipelineState(function: library.makeFunction(name: name)!)
}

/// Runs `encode` in one command buffer `reps` times; returns GPU seconds per rep.
func gpuTime(reps: Int, _ encode: (MTLCommandBuffer) -> Void) -> [Double] {
    var out: [Double] = []
    for _ in 0..<reps {
        let cb = queue.makeCommandBuffer()!
        encode(cb)
        cb.commit()
        cb.waitUntilCompleted()
        if let e = cb.error { fatalError("GPU error: \(e)") }
        out.append(cb.gpuEndTime - cb.gpuStartTime)
    }
    return out
}

func info() {
    var families: [String] = []
    let fam: [(String, MTLGPUFamily)] = [("apple7", .apple7), ("apple8", .apple8),
                                         ("apple9", .apple9), ("metal3", .metal3)]
    for (n, f) in fam where device.supportsFamily(f) { families.append(n) }
    if #available(macOS 26.0, *) {
        if device.supportsFamily(.apple10) { families.append("apple10") }
        if device.supportsFamily(.metal4) { families.append("metal4") }
    }
    emit(["bench": "gpu", "test": "info", "name": device.name,
          "unified_memory": device.hasUnifiedMemory,
          "recommended_max_working_set_GB": Double(device.recommendedMaxWorkingSetSize) / 1e9,
          "max_buffer_GB": Double(device.maxBufferLength) / 1e9,
          "max_threads_per_threadgroup": device.maxThreadsPerThreadgroup.width,
          "families": families])
}

func fma(_ name: String, bytesPerElem: Int) {
    let p = pipeline(name)
    let threads = 40 * 1024 * 64  // ample occupancy for a 40-core GPU
    let out = device.makeBuffer(length: threads * bytesPerElem, options: .storageModePrivate)!
    var iters: UInt32 = 4096
    var bc = SIMD2<Float>(1.0000001, 0.9999999)
    let t = gpuTime(reps: 7) { cb in
        let e = cb.makeComputeCommandEncoder()!
        e.setComputePipelineState(p)
        e.setBuffer(out, offset: 0, index: 0)
        e.setBytes(&iters, length: 4, index: 1)
        e.setBytes(&bc, length: 8, index: 2)
        e.dispatchThreads(MTLSize(width: threads, height: 1, depth: 1),
                          threadsPerThreadgroup: MTLSize(width: 256, height: 1, depth: 1))
        e.endEncoding()
    }.dropFirst()
    let flops = Double(threads) * Double(iters) * 8 * 2
    emit(["bench": "gpu", "test": name, "unit": "TFLOP/s",
          "median": flops / median(Array(t)) / 1e12, "best": flops / t.min()! / 1e12])
}

func bandwidth() {
    let bytes = 1 << 30
    let n4 = bytes / 16
    for mode in [("shared", MTLResourceOptions.storageModeShared),
                 ("private", MTLResourceOptions.storageModePrivate)] {
        let a = device.makeBuffer(length: bytes, options: mode.1)!
        let b = device.makeBuffer(length: bytes, options: mode.1)!
        let cp = pipeline("copy4")
        let t = gpuTime(reps: 8) { cb in
            let e = cb.makeComputeCommandEncoder()!
            e.setComputePipelineState(cp)
            e.setBuffer(a, offset: 0, index: 0)
            e.setBuffer(b, offset: 0, index: 1)
            e.dispatchThreads(MTLSize(width: n4, height: 1, depth: 1),
                              threadsPerThreadgroup: MTLSize(width: 256, height: 1, depth: 1))
            e.endEncoding()
        }.dropFirst()
        emit(["bench": "gpu", "test": "copy_bw_\(mode.0)", "unit": "GB/s", "bytes_moved": 2 * bytes,
              "median": 2 * Double(bytes) / median(Array(t)) / 1e9,
              "best": 2 * Double(bytes) / t.min()! / 1e9])
        let rp = pipeline("read4")
        var per: UInt32 = 16
        let grid = n4 / Int(per)
        let r = gpuTime(reps: 8) { cb in
            let e = cb.makeComputeCommandEncoder()!
            e.setComputePipelineState(rp)
            e.setBuffer(a, offset: 0, index: 0)
            e.setBuffer(b, offset: 0, index: 1)
            e.setBytes(&per, length: 4, index: 2)
            e.dispatchThreads(MTLSize(width: grid, height: 1, depth: 1),
                              threadsPerThreadgroup: MTLSize(width: 256, height: 1, depth: 1))
            e.endEncoding()
        }.dropFirst()
        emit(["bench": "gpu", "test": "read_bw_\(mode.0)", "unit": "GB/s",
              "median": Double(bytes) / median(Array(r)) / 1e9,
              "best": Double(bytes) / r.min()! / 1e9])
    }
}

func gemm() {
    for (dt, name, esz) in [(MPSDataType.float32, "f32", 4), (MPSDataType.float16, "f16", 2)] {
        for n in [2048, 4096, 8192] {
            let rowBytes = n * esz
            let desc = MPSMatrixDescriptor(rows: n, columns: n, rowBytes: rowBytes, dataType: dt)
            let bufs = (0..<3).map { _ in device.makeBuffer(length: n * rowBytes, options: .storageModePrivate)! }
            let A = MPSMatrix(buffer: bufs[0], descriptor: desc)
            let B = MPSMatrix(buffer: bufs[1], descriptor: desc)
            let C = MPSMatrix(buffer: bufs[2], descriptor: desc)
            let mm = MPSMatrixMultiplication(device: device, transposeLeft: false, transposeRight: false,
                                             resultRows: n, resultColumns: n, interiorColumns: n,
                                             alpha: 1, beta: 0)
            let inner = n >= 8192 ? 2 : 8
            let t = gpuTime(reps: 5) { cb in
                for _ in 0..<inner { mm.encode(commandBuffer: cb, leftMatrix: A, rightMatrix: B, resultMatrix: C) }
            }.dropFirst()
            let flops = 2.0 * pow(Double(n), 3) * Double(inner)
            emit(["bench": "gpu", "test": "mps_gemm_\(name)", "n": n, "unit": "TFLOP/s",
                  "median": flops / median(Array(t)) / 1e12, "best": flops / t.min()! / 1e12])
        }
    }
}

func graphMatmul() {
    // MPSGraph may route to newer matrix hardware paths than MPSMatrixMultiplication.
    for (dt, name) in [(MPSDataType.float16, "f16"), (MPSDataType.bFloat16, "bf16"), (MPSDataType.float32, "f32")] {
        let n = 4096
        let g = MPSGraph()
        let shape: [NSNumber] = [NSNumber(value: n), NSNumber(value: n)]
        let a = g.placeholder(shape: shape, dataType: dt, name: "a")
        let b = g.placeholder(shape: shape, dataType: dt, name: "b")
        let c = g.matrixMultiplication(primary: a, secondary: b, name: "c")
        let esz = dt == .float32 ? 4 : 2
        let mk = { () -> MPSGraphTensorData in
            let buf = device.makeBuffer(length: n * n * esz, options: .storageModePrivate)!
            return MPSGraphTensorData(buf, shape: shape, dataType: dt)
        }
        let feeds = [a: mk(), b: mk()]
        var times: [Double] = []
        for i in 0..<8 {
            let t0 = Date()
            _ = g.run(with: queue, feeds: feeds, targetTensors: [c], targetOperations: nil)
            let dt = Date().timeIntervalSince(t0)
            if i > 1 { times.append(dt) }  // skip compile + warm-up
        }
        let flops = 2.0 * pow(Double(n), 3)
        emit(["bench": "gpu", "test": "mpsgraph_matmul_\(name)", "n": n, "unit": "TFLOP/s",
              "timing": "wall (includes submit + sync)",
              "median": flops / median(times) / 1e12, "best": flops / times.min()! / 1e12])
    }
}

func latency() {
    let p = pipeline("empty_kernel")
    let out = device.makeBuffer(length: 4, options: .storageModeShared)!
    var wall: [Double] = []
    for _ in 0..<2000 {
        let t0 = DispatchTime.now().uptimeNanoseconds
        let cb = queue.makeCommandBuffer()!
        let e = cb.makeComputeCommandEncoder()!
        e.setComputePipelineState(p)
        e.setBuffer(out, offset: 0, index: 0)
        e.dispatchThreads(MTLSize(width: 1, height: 1, depth: 1),
                          threadsPerThreadgroup: MTLSize(width: 1, height: 1, depth: 1))
        e.endEncoding()
        cb.commit()
        cb.waitUntilCompleted()
        wall.append(Double(DispatchTime.now().uptimeNanoseconds - t0) / 1000)
    }
    let w = Array(wall.dropFirst(100)).sorted()
    emit(["bench": "gpu", "test": "dispatch_roundtrip_latency", "unit": "us",
          "median": w[w.count / 2], "p99": w[Int(Double(w.count) * 0.99)], "min": w[0]])
}

func unified() {
    // Zero-copy CPU->GPU handoff vs explicit blit into a GPU-private buffer.
    let bytes = 1 << 30
    let shared = device.makeBuffer(length: bytes, options: .storageModeShared)!
    let priv = device.makeBuffer(length: bytes, options: .storageModePrivate)!
    memset(shared.contents(), 1, bytes)  // fault pages in first
    let t0 = Date()
    memset(shared.contents(), 2, bytes)
    let cpuFill = Date().timeIntervalSince(t0)
    let t = gpuTime(reps: 6) { cb in
        let b = cb.makeBlitCommandEncoder()!
        b.copy(from: shared, sourceOffset: 0, to: priv, destinationOffset: 0, size: bytes)
        b.endEncoding()
    }.dropFirst()
    emit(["bench": "gpu", "test": "unified_memory", "buffer_GiB": 1,
          "cpu_memset_shared_1thread_GBps": Double(bytes) / cpuFill / 1e9,
          "blit_shared_to_private_GBps_median": Double(bytes) / median(Array(t)) / 1e9,
          "blit_cost_ms_per_GiB_median": median(Array(t)) * 1e3,
          "note": "zero-copy (shared storage) avoids the blit entirely on unified memory"])
}

let arg = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "all"
if arg == "info" || arg == "all" { info() }
if arg == "fma" || arg == "all" { fma("fma_f32", bytesPerElem: 4); fma("fma_f16", bytesPerElem: 2) }
if arg == "bw" || arg == "all" { bandwidth() }
if arg == "gemm" || arg == "all" { gemm() }
if arg == "graph" || arg == "all" { graphMatmul() }
if arg == "latency" || arg == "all" { latency() }
if arg == "unified" || arg == "all" { unified() }
