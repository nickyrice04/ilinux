/* SPDX-License-Identifier: MIT */
#ifndef ILINUX31AT_OBJECT_DIAGNOSTICS_H
#define ILINUX31AT_OBJECT_DIAGNOSTICS_H
#include "reader.h"

/* Finite labels only. No input pointer, private byte, hash or filename escapes. */
typedef struct {
    bool recognizer_completed, known_exact, candidate_exact;
    const char *stage, *identity, *container, *codec;
} ObjectDiagnostics31AT;

/* Pure memory adapter. Caller owns input bounds/lifetime. No I/O or allocation
 * beyond the unchanged original recognizer's bounded decoder/hash allocation. */
void object_diagnostics31at(Bytes input, ObjectDiagnostics31AT *out);
void print_object_diagnostics31at(const ObjectDiagnostics31AT *diagnostic);
#endif
