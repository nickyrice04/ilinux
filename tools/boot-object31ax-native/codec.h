/* SPDX-License-Identifier: MIT */
#ifndef ILINUX31AX_CODEC_H
#define ILINUX31AX_CODEC_H
#include "reader.h"
typedef struct {
    bool recognizer_completed,known_exact,candidate_exact;
    const char *stage,*identity,*container,*codec,*decode_reason;
} ObjectDiagnostics31AX;
typedef struct {
    bool attempted,positive_exact,negative_refused,passed;
    const char *reason;
} CodecCapability31AX;
void object_diagnostics31ax(Bytes input,ObjectDiagnostics31AX *out);
CodecCapability31AX codec_capability31ax(void);
#endif
