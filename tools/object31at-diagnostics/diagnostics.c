/* SPDX-License-Identifier: MIT */
#include "diagnostics.h"
/* The builder verifies this original MIT implementation and reader.h against
 * frozen SHA256 pins. It is included unchanged so its private pure framing
 * helpers can explain a refusal without creating a second acceptance parser.
 * Compile this translation unit INSTEAD OF separately compiling core.c. */
#include "core.c"

static const char *identity31at(const char *label) {
    const char *labels[] = {"UNKNOWN", "CANDIDATE", "BOOT021", "31AF", "31AI"};
    for (size_t i = 0; i < sizeof(labels) / sizeof(labels[0]); i++)
        if (!strcmp(label, labels[i])) return labels[i];
    return "UNKNOWN";
}

void object_diagnostics31at(Bytes input, ObjectDiagnostics31AT *out) {
    *out = (ObjectDiagnostics31AT){.stage="INPUT_BOUND_REJECTED",
        .identity="UNKNOWN", .container="UNCLASSIFIED", .codec="NONE"};
    if (!input.p && input.n) return;

    Identity authoritative;
    /* This original function alone decides recognition/exactness. No later
     * diagnostic branch may turn any authoritative result into acceptance. */
    bool completed = identify_object(input, &authoritative);
    out->recognizer_completed = completed;
    out->known_exact = completed && authoritative.exact;
    out->candidate_exact = out->known_exact && !strcmp(authoritative.identity, "CANDIDATE");
    out->identity = identity31at(authoritative.identity);
    if (!input.n || input.n > FILE_LIMIT) return;

    /* Exact own raw bytes take priority even if they resemble malformed DER. */
    if (out->known_exact) {
        out->container = !strcmp(authoritative.framing,"IMG4") ? "IMG4" :
            !strcmp(authoritative.framing,"IM4P") ? "IM4P" : "RAW";
        out->codec = !strcmp(authoritative.codec,"LZFSE") ? "LZFSE" : "NONE";
        out->stage = "KNOWN_MATCHED";
        return;
    }

    Bytes body = input;
    uint64_t declared = 0;
    bool keybag = false;
    out->container = "RAW";
    if (input.p[0] == 0x30) {
        const char *framing = NULL;
        if (!payload(input, &body, &declared, &keybag, &framing)) {
            out->container = "UNCLASSIFIED";
            out->stage = "DER_FRAMING_REJECTED";
            return;
        }
        out->container = !strcmp(framing,"IMG4") ? "IMG4" : "IM4P";
    }
    if (keybag) {
        out->codec = "KEYBAG_BLOCKED";
        out->stage = "KEYBAG_BLOCKED";
        return;
    }
    if (lzfse_magic(body)) {
        out->codec = "LZFSE";
        if (!body.n || body.n > COMPRESSED_LIMIT) {
            out->stage = "COMPRESSED_BOUND_REJECTED";
            return;
        }
        size_t framed = 0;
        if (!lzfse_frame(body, RAW_LIMIT, &framed)) {
            out->stage = "LZFSE_FRAME_REJECTED";
            return;
        }
        if (declared && framed != declared) {
            out->stage = "DECLARED_SIZE_MISMATCH";
            return;
        }
        /* With these exact original preconditions passing, false from the
         * authoritative recognizer means its decoder rejected. Do not decode
         * twice or create a diagnostic-only alternative acceptance rule. */
        out->stage = completed ? "DECODED_UNMATCHED" : "DECODE_REJECTED";
        return;
    }
    if (declared) {
        out->stage = "UNCOMPRESSED_DECLARATION_REJECTED";
        return;
    }
    if (body.n >= 3 && !memcmp(body.p,"\x1f\x8b\x08",3)) {
        out->codec = "GZIP_UNSUPPORTED";
        out->stage = "GZIP_UNSUPPORTED";
        return;
    }
    if (body.n > RAW_LIMIT) {
        out->stage = "UNCOMPRESSED_BOUND_REJECTED";
        return;
    }
    out->stage = "UNCOMPRESSED_UNMATCHED";
}

void print_object_diagnostics31at(const ObjectDiagnostics31AT *d) {
    printf("{\"schema\":\"ilinux31at-object-diagnostics-v1\","
        "\"scope\":\"WORKSPACE_FIXTURE_ONLY\",\"stage\":\"%s\","
        "\"identity\":\"%s\",\"container\":\"%s\",\"codec\":\"%s\","
        "\"recognizer_completed\":%s,\"known_exact\":%s,\"candidate_exact\":%s,"
        "\"read_only\":true,\"host_queries\":false,\"native_ready\":false,"
        "\"selection_verified\":false,\"private_values_returned\":false}\n",
        d->stage, d->identity, d->container, d->codec,
        d->recognizer_completed?"true":"false", d->known_exact?"true":"false",
        d->candidate_exact?"true":"false");
}
