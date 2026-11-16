/* SPDX-License-Identifier: MIT */
#ifndef ILINUX31AW_CODEC_H
#define ILINUX31AW_CODEC_H
#include "reader.h"
typedef struct {
    bool recognizer_completed,known_exact,candidate_exact;
    const char *stage,*identity,*container,*codec,*decode_reason;
} ObjectDiagnostics31AW;
typedef struct {
    bool attempted,positive_exact,negative_refused,passed;
    const char *reason;
} CodecCapability31AW;
void object_diagnostics31aw(Bytes input,ObjectDiagnostics31AW *out);
CodecCapability31AW codec_capability31aw(void);
#endif
