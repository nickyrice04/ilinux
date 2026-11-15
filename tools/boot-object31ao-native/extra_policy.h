/* SPDX-License-Identifier: MIT */
#ifndef ILINUX31AO_EXTRA_POLICY_H
#define ILINUX31AO_EXTRA_POLICY_H
#include <stdbool.h>
#include <stddef.h>
#include <CommonCrypto/CommonHMAC.h>

/* Private canonical values. Never serialize this object or its members. */
#define POLICY_EXTRA_COUNT 6
#define POLICY_EXTRA_VALUE 257
typedef struct {
    unsigned seen[POLICY_EXTRA_COUNT];
    char value[POLICY_EXTRA_COUNT][POLICY_EXTRA_VALUE];
} PolicyExtras;

/* 0: not in this finite catalog; 1: stored; -1: duplicate or bad type. */
int policy_extra_set(PolicyExtras *out, const char *tag, const char *value);
void policy_extra_commit(const PolicyExtras *value, CCHmacContext *context);
const char *policy_extra_tag(size_t index);
#endif
