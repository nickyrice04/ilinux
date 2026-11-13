/* SPDX-License-Identifier: MIT */
#ifndef ILINUX31AJ_READER_H
#define ILINUX31AJ_READER_H
#include <CoreFoundation/CoreFoundation.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <limits.h>
#ifndef WORKSPACE_ROOT
#error WORKSPACE_ROOT must be supplied by the workspace builder
#endif
#ifndef CANDIDATE_BYTES
#define CANDIDATE_BYTES 0
#define CANDIDATE_SHA256 ""
#endif
#define RAW_LIMIT ((size_t)160*1024*1024)
#define COMPRESSED_LIMIT ((size_t)32*1024*1024)
#define FILE_LIMIT (RAW_LIMIT+1024*1024)
#define METADATA_LIMIT ((size_t)1024*1024)
#define POLICY_LIMIT ((size_t)65536)
#define LAB_VOLUME "/Volumes/iLinux Boot Lab"
#define LAB_DATA_NAME "iLinux Boot Lab - Data"
#define LAB_DATA_MOUNT "/Volumes/iLinux Boot Lab - Data"
#define ORIGINAL_NAME "Macintosh HD"
#define ROLLBACK_BYTES 3932160
#define ROLLBACK_SHA "ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664"
typedef struct {const uint8_t *p;size_t n;} Bytes;
typedef struct {char identity[16],framing[12],codec[16];size_t raw_bytes;bool exact;} Identity;
bool read_file(const char *path,size_t cap,bool workspace_only,uint8_t **data,size_t *size);
bool sha_hex(const uint8_t *data,size_t size,char out[65]);
bool valid_sha(const char *s);
bool identify_object(Bytes data,Identity *out);
bool codec_selftest(void);
bool safe_directory(const char *path);
typedef struct {uint8_t bytes[32];char id[65];bool loaded;} ComparisonKey;
bool load_comparison_key(const char *path,bool fixture,ComparisonKey *out);

enum {J_OBJECT=1,J_STRING,J_TRUE,J_FALSE,J_NUMBER,J_NULL};
typedef struct {int type,first,next;char key[80],value[256];} JNode;
typedef struct {JNode nodes[512];int count;} Json;
bool json_parse(Bytes bytes,Json *out);
int json_get(const Json *j,int object,const char *key);
bool json_keys(const Json *j,int object,const char *const *keys,size_t n);
bool json_string(const Json *j,int node,const char *expected);

typedef struct {char sha[65],helper_sha[65];uint64_t helper_bytes;} Profile;
bool load_profile(const char *path,const char *executable,Profile *out);
typedef struct {
    bool synthetic,guarded,paired,original_full,lab_permissive,policy_complete;
    char profile_sha[65],lab_ctrr[12],selected[16];bool selected_exact;
    char original_semantics[8][24],lab_semantics[8][24];
    bool metadata_bound;
    char comparison_key_id[65],lab_metadata_hmac[65],original_metadata_hmac[65];
} Snapshot;
bool collect_snapshot(const char *target,const char *original,const Profile *profile,
                      const char *fixture,const ComparisonKey *key,Snapshot *out,char private_group[37]);
void print_snapshot(const Snapshot *snapshot);
bool parse_snapshot(const char *path,Snapshot *out,bool workspace_only);
bool validate_snapshot(const Snapshot *snapshot,const Snapshot *baseline,
                       const Profile *profile,const ComparisonKey *key,const char *phase,bool synthetic_control);
bool recovery_admission(void);
void refused(void);
extern const char *refusal_reason;
#endif
