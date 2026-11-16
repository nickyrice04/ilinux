/* SPDX-License-Identifier: MIT */
#ifndef ILINUX31AX_POLICY_CONTRACT_H
#define ILINUX31AX_POLICY_CONTRACT_H
#include "reader.h"
#include "extra_policy.h"
/* Typed private observations only. Never serialize any input value. */
typedef struct {
 unsigned seen[12];char identity[5][97],lpnh[2][97];
} PolicyIdentity31AX;
typedef struct {
 bool observed,bound,lab_manifest_present;
 char original_identity[65],lab_identity[65],lab_manifest[65];
} PolicyView31AX;
extern PolicyView31AX ax_policy_view;
int policy_identity_set31ax(PolicyIdentity31AX *out,const char *tag,const char *value);
bool policy_identity_complete31ax(const PolicyIdentity31AX *value);
void policy_view_reset31ax(void);
bool policy_view_capture31ax(const PolicyIdentity31AX *lab,const PolicyIdentity31AX *original,
 const PolicyExtras *lab_extra,const PolicyExtras *original_extra,const char *lab_nsih,
 const char *original_nsih,const char *original_coih,const char *lab_group,const char *original_group,
 const Profile *profile,const ComparisonKey *key);
#endif
