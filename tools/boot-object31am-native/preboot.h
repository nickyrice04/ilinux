/* SPDX-License-Identifier: MIT */
#ifndef ILINUX31AM_PREBOOT_H
#define ILINUX31AM_PREBOOT_H
#include "diagnostic.h"
enum PBStage {PS_CLI,PS_PROFILE,PS_ENVIRONMENT,PS_SCRATCH,PS_IDENTITIES,PS_STATE,
 PS_REOBSERVATION,PS_MOUNT,PS_MOUNT_VERIFICATION,PS_DIAGNOSTIC,PS_CLEANUP,
 PS_COMPLETE,PS_VALIDATION,PS_COUNT};
enum PBReason {PR_ARGUMENTS,PR_PROFILE_BINDING,PR_ENVIRONMENT,PR_SCRATCH_BINDING,
 PR_METADATA,PR_MOUNTED_FIELD,PR_PATH_FORMAT,PR_PATH_UNSAFE,PR_STATE_CONTRADICTION,
 PR_IDENTITY_CHANGED,PR_TOOL_UNAVAILABLE,PR_CHILD_EXISTS,PR_MOUNT_COMMAND,
 PR_MOUNT_NOT_OBSERVED,PR_MOUNT_BINDING,PR_NOT_READ_ONLY,PR_DIAGNOSTIC_REFUSED,
 PR_CLEANUP_BINDING,PR_UNMOUNT_COMMAND,PR_UNMOUNT_NOT_OBSERVED,PR_RESULT_FORMAT,
 PR_KERNEL_MOUNT_STATE,PR_INTERRUPTED,PR_NONE,PR_COUNT};
enum PBInitial {PI_UNOBSERVED,PI_MOUNTED_VALID,PI_UNMOUNTED_EMPTY,PI_INVALID,PI_COUNT};
enum PBCleanup {PC_NOT_NEEDED,PC_UNMOUNTED,PC_FAILED,PC_REFUSED,PC_COUNT};
typedef struct {
 bool synthetic,complete,attempted,created,readonly,uncertain,has_diagnostic;
 int stage,reason,initial,cleanup,mount_exit,unmount_exit;
 Diagnostic diagnostic;
} PBResult;
void pb_reset(PBResult *result,bool synthetic);
bool pb_run(const char *target,const char *original,const char *scratch,
            const char *fixture,const Profile *profile,PBResult *result);
bool pb_print(const PBResult *result);
bool pb_load(const char *path,PBResult *result);
#endif
