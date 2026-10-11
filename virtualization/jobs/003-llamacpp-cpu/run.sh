#!/bin/sh
# Job 003: build llama.cpp at the same commit as the host's Homebrew build
# (61881b1f7 = b10280) with a CPU-only backend matching ggml's "apple_m4"
# variant features (DOTPROD, I8MM, SME, no SVE) and benchmark the synthetic
# Llama-3-8B models shared read-only from the host (virtiofs tag "models").
set -x
OUT=/mnt/job/out
pacman -Sy --noconfirm --needed cmake git ninja 2>&1 | tail -2
mkdir -p /mnt/models && mount -t virtiofs models /mnt/models || exit 1
cd /root && rm -rf llama.cpp && mkdir llama.cpp && cd llama.cpp
git init -q && git remote add origin https://github.com/ggml-org/llama.cpp
git fetch -q --depth 1 origin 61881b1f7f0b13d9e46d561fc25afcd6bbaec479 && git checkout -q FETCH_HEAD || exit 1
git log -1 --format='%H %ad' > $OUT/llamacpp-commit.txt
CC=clang CXX=clang++ cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DGGML_NATIVE=OFF -DGGML_CPU_ARM_ARCH=armv8.6-a+dotprod+i8mm+sme -DGGML_BLAS=OFF \
  -DGGML_LTO=ON -DLLAMA_CURL=OFF -DLLAMA_OPENSSL=OFF -DLLAMA_BUILD_TESTS=OFF > $OUT/cmake.log 2>&1 || exit 1
cmake --build build --target llama-bench -j 18 > $OUT/build.log 2>&1 || { tail -30 $OUT/build.log; exit 1; }
set +x
B=build/bin/llama-bench
$B --list-devices > $OUT/devices.txt 2>&1
for q in q4_0 q4_k_m; do
  m=/mnt/models/synth-llama3-8b-$q.gguf
  $B -m $m -t 6,12,18 -p 512 -n 64 -r 3 -o jsonl >> $OUT/llamacpp-cpu.jsonl 2>> $OUT/llamacpp-cpu.log
done
