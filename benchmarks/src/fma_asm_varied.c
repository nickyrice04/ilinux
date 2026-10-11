#include <stdint.h>
#include <stdio.h>
#include <time.h>
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec*1e-9;}
// 24 independent FMLA chains, fixed instruction stream (compiler-independent).
static void fma_asm(uint64_t iters) {
  __asm__ volatile(
    "movi v30.4s, #0\n fmov v31.4s, #1.0\n fmov v29.4s, #0.5\n"
    "mov v0.16b, v30.16b\n mov v1.16b, v30.16b\n mov v2.16b, v30.16b\n mov v3.16b, v30.16b\n"
    "mov v4.16b, v30.16b\n mov v5.16b, v30.16b\n mov v6.16b, v30.16b\n mov v7.16b, v30.16b\n"
    "mov v16.16b, v30.16b\n mov v17.16b, v30.16b\n mov v18.16b, v30.16b\n mov v19.16b, v30.16b\n"
    "mov v20.16b, v30.16b\n mov v21.16b, v30.16b\n mov v22.16b, v30.16b\n mov v23.16b, v30.16b\n"
    "mov v24.16b, v30.16b\n mov v25.16b, v30.16b\n mov v26.16b, v30.16b\n mov v27.16b, v30.16b\n"
    "mov v28.16b, v30.16b\n mov v8.16b, v30.16b\n mov v9.16b, v30.16b\n mov v10.16b, v30.16b\n mov v11.16b, v31.16b\n mov v12.16b, v31.16b\n mov v13.16b, v31.16b\n mov v14.16b, v29.16b\n mov v15.16b, v29.16b\n"
    "1:\n"
    "fmla v0.4s, v31.4s, v29.4s\nfmla v1.4s, v11.4s, v29.4s\nfmla v2.4s, v12.4s, v29.4s\nfmla v3.4s, v13.4s, v29.4s\nfmla v4.4s, v31.4s, v14.4s\nfmla v5.4s, v11.4s, v14.4s\nfmla v6.4s, v12.4s, v14.4s\nfmla v7.4s, v13.4s, v14.4s\nfmla v16.4s, v31.4s, v15.4s\nfmla v17.4s, v11.4s, v15.4s\nfmla v18.4s, v12.4s, v15.4s\nfmla v19.4s, v13.4s, v15.4s\nfmla v20.4s, v31.4s, v30.4s\nfmla v21.4s, v11.4s, v30.4s\nfmla v22.4s, v12.4s, v30.4s\nfmla v23.4s, v13.4s, v30.4s\nfmla v24.4s, v31.4s, v29.4s\nfmla v25.4s, v11.4s, v29.4s\nfmla v26.4s, v12.4s, v29.4s\nfmla v27.4s, v13.4s, v29.4s\nfmla v28.4s, v31.4s, v14.4s\nfmla v8.4s, v11.4s, v14.4s\nfmla v9.4s, v12.4s, v14.4s\nfmla v10.4s, v13.4s, v14.4s\n"
    "subs %0, %0, #1\n b.ne 1b\n"
    : "+r"(iters) :: "v0","v1","v2","v3","v4","v5","v6","v7","v8","v9","v10","v16","v17","v18","v19","v20",
      "v11","v12","v13","v14","v15","v21","v22","v23","v24","v25","v26","v27","v28","v29","v30","v31","cc");
}
int main(void){ uint64_t n=200000000ull; for(int r=0;r<5;r++){double t=now(); fma_asm(n); double dt=now()-t; printf("fma_asm_varied GFLOP/s %.1f\n", n*192.0/dt/1e9);} return 0; }
