/* SPDX-License-Identifier: MIT */
#include "extra_policy.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>

enum ScalarKind {BOOL_VALUE, UINT64_HEX, VERSION_VECTOR};
typedef struct {const char *tag; enum ScalarKind kind;} ExtraSpec;

/* Qualified TEXT spellings. The JSON key CRPO is deliberately not an alias. */
static const ExtraSpec catalog[POLICY_EXTRA_COUNT] = {
    {"CEPO", UINT64_HEX}, {"SDOM", UINT64_HEX}, {"CPRO", BOOL_VALUE},
    {"CSEC", BOOL_VALUE}, {"lobo", BOOL_VALUE}, {"love", VERSION_VECTOR}
};

const char *policy_extra_tag(size_t index) {
    return index < POLICY_EXTRA_COUNT ? catalog[index].tag : NULL;
}

static bool canonical(const char *input, enum ScalarKind kind,
                      char out[POLICY_EXTRA_VALUE]) {
    /* This formatter emits typed values unconditionally for these six fields.
       Do not invent an explicit ABSENT representation for them. */
    if (kind == BOOL_VALUE) {
        if (!strcmp(input, "1") || !strcasecmp(input, "true")) {
            strcpy(out, "true"); return true;
        }
        if (!strcmp(input, "0") || !strcasecmp(input, "false")) {
            strcpy(out, "false"); return true;
        }
        return false;
    }
    if (kind == UINT64_HEX) {
        const char *p = input;
        unsigned base = 16;
        if (p[0] != '0' || p[1] != 'x') return false;
        p += 2;
        size_t length = strlen(p);
        if (!length || length > 16) return false;
        uint64_t value = 0;
        for (size_t i = 0; i < length; i++) {
            unsigned char c = (unsigned char)p[i];
            unsigned digit;
            if (c >= '0' && c <= '9') digit = c - '0';
            else if (base == 16 && c >= 'a' && c <= 'f') digit = c - 'a' + 10;
            else if (base == 16 && c >= 'A' && c <= 'F') digit = c - 'A' + 10;
            else return false;
            if (digit >= base || value > (UINT64_MAX - digit) / base) return false;
            value = value * base + digit;
        }
        snprintf(out, POLICY_EXTRA_VALUE, "0x%016llx", (unsigned long long)value);
        return true;
    }
    /* Qualified bputil TEXT rendering is six unsigned decimal components,
       D.D.D.D.D,D. Do not treat it as a Boolean or accept arbitrary strings.
       Generic Image4 LOVE's string type does not define this display grammar. */
    const char *p = input;
    uint32_t components[6];
    for (size_t i = 0; i < 6; i++) {
        uint32_t value = 0;
        unsigned digits = 0;
        while (*p >= '0' && *p <= '9') {
            unsigned digit = (unsigned)(*p++ - '0');
            if (++digits > 10 || value > (UINT32_MAX - digit) / 10) return false;
            value = value * 10 + digit;
        }
        if (!digits) return false;
        components[i] = value;
        if (i < 5) {
            char separator = i < 4 ? '.' : ',';
            if (*p++ != separator) return false;
        } else if (*p) return false;
    }
    snprintf(out, POLICY_EXTRA_VALUE, "%u.%u.%u.%u.%u,%u", components[0],
             components[1], components[2], components[3], components[4], components[5]);
    return true;
}

int policy_extra_set(PolicyExtras *out, const char *tag, const char *value) {
    for (size_t i = 0; i < POLICY_EXTRA_COUNT; i++) {
        if (strcmp(tag, catalog[i].tag)) continue;
        if (out->seen[i] || !canonical(value, catalog[i].kind, out->value[i])) return -1;
        out->seen[i] = 1;
        return 1;
    }
    return 0;
}

void policy_extra_commit(const PolicyExtras *value, CCHmacContext *context) {
    const char *label = "ilinux31ao-finite-extra-fields-v1";
    CCHmacUpdate(context, label, strlen(label) + 1);
    for (size_t i = 0; i < POLICY_EXTRA_COUNT; i++) {
        const char *parts[] = {catalog[i].tag, value->seen[i] ? "1" : "0",
                              value->value[i]};
        for (size_t j = 0; j < sizeof(parts) / sizeof(parts[0]); j++)
            CCHmacUpdate(context, parts[j], strlen(parts[j]) + 1);
    }
}
