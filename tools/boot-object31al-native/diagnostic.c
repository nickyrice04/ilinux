/* SPDX-License-Identifier: MIT */
#include "diagnostic.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

Diagnostic diagnostic;
static bool capture_observing;
static const char *const stages[]={"CLI","PROFILE","FIXTURE_READ","FIXTURE_FORMAT",
 "TARGET_PATHS","RECOVERY_ENVIRONMENT","TARGET_MOUNTS","LAB_INFO","ORIGINAL_INFO",
 "APFS_LIST","SYSTEM_IDENTITIES","VOLUME_ROLES","PREBOOT_INFO","DATA_INFO",
 "AUX_IDENTITIES","AUX_MOUNTS","LAB_POLICY","ORIGINAL_POLICY","RECOVERY_PAIRING",
 "SECURITY_GUARDS","SELECTED_OBJECT","LAB_POLICY_AFTER","ORIGINAL_POLICY_AFTER",
 "POLICY_COMPARISON","COLLECTION_COMPLETE","INITIAL_ADMISSION","DIAGNOSTIC_VALIDATION"};
static const char *const kinds[]={"NONE","FORMAT","CAPTURE","GUARD","CONSISTENCY"};
static const char *const reasons[]={"NONE","ARGUMENTS","PROFILE_BINDING","FIXTURE_INPUT",
 "PLIST_DICTIONARY","TARGET_PATHS","RECOVERY_ENVIRONMENT","MACHINE_MODEL",
 "MOUNT_PATHS","SYSTEM_IDENTITIES","CONTAINER_MISMATCH","VOLUME_ROLES",
 "AUX_IDENTITIES","METADATA_GUARD","POLICY_INPUT","POLICY_BOUND","DUPLICATE_FIELD",
 "DUPLICATE_OR_MALFORMED","MALFORMED_FIELD","MALFORMED_TAGS","CARDINALITY",
 "MISSING_FIELD","UNSUPPORTED_METADATA","POLICY_CONTRADICTION",
 "NOT_ONE_TRUE_RECOVERY","NOT_PAIRED","LAB_SECURITY_GUARD",
 "ORIGINAL_SECURITY_GUARD","ORIGINAL_CTRR_GUARD","SELECTED_OBJECT",
 "OBJECT_PATH_BOUND","POLICY_CHANGED","CAPTURE_SETUP","CAPTURE_BOUND",
 "CAPTURE_TIMEOUT","CAPTURE_EXIT","CAPTURE_FAILURE","INITIAL_ADMISSION_GUARD",
 "DIAGNOSTIC_INPUT","DIAGNOSTIC_FORMAT","LAB_INFO_PRESENT","ORIGINAL_INFO_PRESENT","APFS_LIST_PRESENT","LAB_INTERNAL_TRUE","ORIGINAL_INTERNAL_TRUE","LAB_NAME","LAB_MOUNT","ORIGINAL_NAME","ORIGINAL_MOUNT","LAB_GROUP_FORMAT","ORIGINAL_GROUP_FORMAT","DISTINCT_GROUPS","LAB_UUID_FORMAT","ORIGINAL_UUID_FORMAT","DISTINCT_UUIDS","LAB_CONTAINER_FORMAT","ORIGINAL_CONTAINER_FORMAT","LAB_SYSTEM_MATCH","ORIGINAL_SYSTEM_MATCH","PREBOOT_ROLE_PRESENT","DATA_ROLE_PRESENT","PREBOOT_DEVICE_FORMAT","DATA_DEVICE_FORMAT","PREBOOT_INFO_MATCH","DATA_INFO_MATCH","PREBOOT_INTERNAL_TRUE","DATA_INTERNAL_TRUE","DATA_GROUP_FORMAT","DATA_GROUP_MATCH","PREBOOT_MOUNT_FORMAT","DATA_MOUNT_FORMAT","PREBOOT_MOUNT_PATH","DATA_MOUNT_PATH","DATA_MOUNT_MATCH","PREBOOT_DISTINCT_MOUNTS","SEMANTIC_SMB0_DUPLICATE","SEMANTIC_SMB1_DUPLICATE","SEMANTIC_SMB2_DUPLICATE","SEMANTIC_SMB3_DUPLICATE","SEMANTIC_SMB4_DUPLICATE","SEMANTIC_SIP0_DUPLICATE","SEMANTIC_SIP1_DUPLICATE","SEMANTIC_SIP3_DUPLICATE","SEMANTIC_SMB0_MALFORMED","SEMANTIC_SMB1_MALFORMED","SEMANTIC_SMB2_MALFORMED","SEMANTIC_SMB3_MALFORMED","SEMANTIC_SMB4_MALFORMED","SEMANTIC_SIP0_MALFORMED","SEMANTIC_SIP1_MALFORMED","SEMANTIC_SIP3_MALFORMED","SEMANTIC_SMB0_MISSING","SEMANTIC_SMB1_MISSING","SEMANTIC_SMB2_MISSING","SEMANTIC_SMB3_MISSING","SEMANTIC_SMB4_MISSING","SEMANTIC_SIP0_MISSING","SEMANTIC_SIP1_MISSING","SEMANTIC_SIP3_MISSING","RPNH_CARDINALITY","RONH_CARDINALITY","SPIH_CARDINALITY","STNG_CARDINALITY","RPNH_MALFORMED","RONH_DUPLICATE","RONH_MALFORMED","SPIH_DUPLICATE","SPIH_MALFORMED","STNG_DUPLICATE","STNG_MALFORMED"};
static const char *const commands[]={"NONE","SYSCTL_MODEL","DISK_INFO","APFS_LIST","POLICY_READ"};
_Static_assert(sizeof(stages)/sizeof(*stages)==DS_COUNT,"stage table");
_Static_assert(sizeof(kinds)/sizeof(*kinds)==DK_COUNT,"kind table");
_Static_assert(sizeof(reasons)/sizeof(*reasons)==DR_COUNT,"reason table");
_Static_assert(sizeof(commands)/sizeof(*commands)==DC_COUNT,"command table");
void diagnostic_reset(bool synthetic){capture_observing=false;memset(&diagnostic,0,sizeof(diagnostic));diagnostic.synthetic=synthetic;diagnostic.command_exit=-1;diagnostic.stage=DS_CLI;diagnostic.kind=DK_FORMAT;diagnostic.reason=DR_ARGUMENTS;}
void diagnostic_note(int stage,int kind,int reason){if(diagnostic.locked)return;if(stage!=DS_KEEP)diagnostic.stage=stage;diagnostic.kind=kind;diagnostic.reason=reason;}
void diagnostic_fail(int stage,int kind,int reason){if(diagnostic.locked)return;diagnostic_note(stage,kind,reason);diagnostic.locked=true;}
void diagnostic_seal(void){diagnostic.locked=true;}
bool diagnostic_test(bool condition,int stage,int kind,int reason){if(condition)diagnostic_fail(stage,kind,reason);return condition;}
bool diagnostic_false(int stage,int kind,int reason){diagnostic_fail(stage,kind,reason);return false;}
void diagnostic_source(const char *name){
 const char *const names[]={"lab_info","original_info","preboot_info","data_info","lab_policy","original_policy","lab_policy_after","original_policy_after"};
 const int at[]={DS_LAB_INFO,DS_ORIGINAL_INFO,DS_PREBOOT_INFO,DS_DATA_INFO,DS_LAB_POLICY,DS_ORIGINAL_POLICY,DS_LAB_POLICY_AFTER,DS_ORIGINAL_POLICY_AFTER};
 for(size_t i=0;i<8;i++)if(!strcmp(name,names[i])){diagnostic_note(at[i],DK_FORMAT,i<4?DR_PLIST_DICTIONARY:DR_POLICY_INPUT);return;}
 diagnostic_note(DS_KEEP,DK_FORMAT,DR_FIXTURE_INPUT);
}
void diagnostic_capture_begin(const char *const argv[]){
 capture_observing=!diagnostic.locked;if(!capture_observing)return;
 diagnostic.command=DC_NONE;diagnostic.command_exit=-1;diagnostic.stdout_bytes=0;
 if(!strcmp(argv[0],"/usr/sbin/sysctl"))diagnostic.command=DC_SYSCTL_MODEL;
 else if(!strcmp(argv[0],"/usr/bin/bputil"))diagnostic.command=DC_POLICY_READ;
 else if(!strcmp(argv[0],"/usr/sbin/diskutil")&&argv[1])diagnostic.command=!strcmp(argv[1],"info")?DC_DISK_INFO:!strcmp(argv[1],"apfs")?DC_APFS_LIST:DC_NONE;
}
void diagnostic_capture_status(int status){if(capture_observing&&WIFEXITED(status))diagnostic.command_exit=WEXITSTATUS(status);}
void diagnostic_capture_end(size_t bytes,bool ok){if(!capture_observing)return;diagnostic.stdout_bytes=bytes>1048577?1048577:bytes;if(!ok)diagnostic_fail(DS_KEEP,DK_CAPTURE,diagnostic.command_exit>0?DR_CAPTURE_EXIT:DR_CAPTURE_FAILURE);}
static int reason_kind(int reason){
 switch(reason){
 case DR_NONE:return DK_NONE;
 case DR_CAPTURE_SETUP:case DR_CAPTURE_BOUND:case DR_CAPTURE_TIMEOUT:case DR_CAPTURE_EXIT:case DR_CAPTURE_FAILURE:return DK_CAPTURE;
 case DR_POLICY_CONTRADICTION:case DR_POLICY_CHANGED:return DK_CONSISTENCY;
 case DR_TARGET_PATHS:case DR_RECOVERY_ENVIRONMENT:case DR_MACHINE_MODEL:case DR_MOUNT_PATHS:case DR_SYSTEM_IDENTITIES:case DR_CONTAINER_MISMATCH:case DR_VOLUME_ROLES:case DR_AUX_IDENTITIES:case DR_METADATA_GUARD:case DR_NOT_ONE_TRUE_RECOVERY:case DR_NOT_PAIRED:case DR_LAB_SECURITY_GUARD:case DR_ORIGINAL_SECURITY_GUARD:case DR_ORIGINAL_CTRR_GUARD:case DR_SELECTED_OBJECT:case DR_INITIAL_ADMISSION_GUARD:
 case DR_LAB_INTERNAL_TRUE:case DR_ORIGINAL_INTERNAL_TRUE:case DR_LAB_NAME:case DR_LAB_MOUNT:case DR_ORIGINAL_NAME:case DR_ORIGINAL_MOUNT:case DR_DISTINCT_GROUPS:case DR_DISTINCT_UUIDS:case DR_LAB_SYSTEM_MATCH:case DR_ORIGINAL_SYSTEM_MATCH:case DR_PREBOOT_ROLE_PRESENT:case DR_DATA_ROLE_PRESENT:case DR_PREBOOT_INFO_MATCH:case DR_DATA_INFO_MATCH:case DR_PREBOOT_INTERNAL_TRUE:case DR_DATA_INTERNAL_TRUE:case DR_DATA_GROUP_MATCH:case DR_PREBOOT_MOUNT_PATH:case DR_DATA_MOUNT_PATH:case DR_DATA_MOUNT_MATCH:case DR_PREBOOT_DISTINCT_MOUNTS:return DK_GUARD;
 default:return DK_FORMAT;
 }
}
static bool valid(const Diagnostic *d){
 if(d->stage<0||d->stage>=DS_COUNT||d->kind<0||d->kind>=DK_COUNT||d->reason<0||d->reason>=DR_COUNT||d->command<0||d->command>=DC_COUNT||d->command_exit< -1||d->command_exit>255||d->stdout_bytes>1048577)return false;
 if(d->kind!=reason_kind(d->reason)||d->collected!=(d->stage==DS_INITIAL_ADMISSION)||d->stage==DS_COLLECTION_COMPLETE)return false;
 if(d->reason==DR_CAPTURE_EXIT&&d->command_exit<=0)return false;
 if(d->valid)return (d->command_exit<1)&&d->collected&&d->stage==DS_INITIAL_ADMISSION&&d->kind==DK_NONE&&d->reason==DR_NONE;
 return d->kind!=DK_NONE&&d->reason!=DR_NONE&&(!d->collected||d->stage==DS_INITIAL_ADMISSION);
}
void diagnostic_print(const Diagnostic *value){
 Diagnostic d=*value;if(!valid(&d)){diagnostic_reset(value->synthetic);diagnostic_fail(DS_DIAGNOSTIC_VALIDATION,DK_FORMAT,DR_DIAGNOSTIC_FORMAT);d=diagnostic;}
 char exit[16]="null";if(d.command_exit>=0)snprintf(exit,sizeof(exit),"%d",d.command_exit);
 printf("{\"schema\":\"ilinux31al-snapshot-diagnostic-v1\",\"scope\":\"%s\",\"status\":\"%s\",\"stage\":\"%s\",\"failure_kind\":\"%s\",\"reason\":\"%s\",\"command\":\"%s\",\"command_exit\":%s,\"stdout_bytes\":%zu,\"snapshot_collected\":%s,\"initial_admission_valid\":%s,\"read_only\":true,\"writes_authorized\":false,\"native_ready\":false,\"identifiers_returned\":false,\"policy_values_returned\":false}\n",d.synthetic?"SYNTHETIC_CONTROL":"RECOVERY_READ_ONLY_DIAGNOSTIC",d.valid?"INITIAL_ADMISSION_PASS":"REFUSED",stages[d.stage],kinds[d.kind],reasons[d.reason],commands[d.command],exit,d.stdout_bytes,d.collected?"true":"false",d.valid?"true":"false");
}
static bool boolean(const Json *j,const char *key,bool expected){int n=json_get(j,0,key);return n>=0&&j->nodes[n].type==(expected?J_TRUE:J_FALSE);}
static bool number(const Json *j,int n,unsigned long limit,int *out){if(n<0||j->nodes[n].type!=J_NUMBER)return false;char *end;unsigned long v=strtoul(j->nodes[n].value,&end,10);char canonical[32];snprintf(canonical,sizeof(canonical),"%lu",v);if(*end||v>limit||strcmp(canonical,j->nodes[n].value))return false;*out=(int)v;return true;}
static int label(const Json *j,const char *key,const char *const *labels,int count){int n=json_get(j,0,key);if(n<0||j->nodes[n].type!=J_STRING)return -1;for(int i=0;i<count;i++)if(!strcmp(j->nodes[n].value,labels[i]))return i;return -1;}
bool diagnostic_load(const char *path,Diagnostic *out){
 uint8_t *data=NULL;size_t bytes=0;Json j;bool ok=false;Diagnostic d={.command_exit=-1};
 const char *const keys[]={"schema","scope","status","stage","failure_kind","reason","command","command_exit","stdout_bytes","snapshot_collected","initial_admission_valid","read_only","writes_authorized","native_ready","identifiers_returned","policy_values_returned"};
 if(!read_file(path,8192,false,&data,&bytes)||!json_parse((Bytes){data,bytes},&j)||!json_keys(&j,0,keys,16)||!json_string(&j,json_get(&j,0,"schema"),"ilinux31al-snapshot-diagnostic-v1"))goto done;
 if(json_string(&j,json_get(&j,0,"scope"),"SYNTHETIC_CONTROL"))d.synthetic=true;else if(!json_string(&j,json_get(&j,0,"scope"),"RECOVERY_READ_ONLY_DIAGNOSTIC"))goto done;
 if(json_string(&j,json_get(&j,0,"status"),"INITIAL_ADMISSION_PASS"))d.valid=true;else if(!json_string(&j,json_get(&j,0,"status"),"REFUSED"))goto done;
 d.stage=label(&j,"stage",stages,DS_COUNT);d.kind=label(&j,"failure_kind",kinds,DK_COUNT);d.reason=label(&j,"reason",reasons,DR_COUNT);d.command=label(&j,"command",commands,DC_COUNT);
 int n=json_get(&j,0,"command_exit"),size=0;if(j.nodes[n].type!=J_NULL&&!number(&j,n,255,&d.command_exit))goto done;
 if(!number(&j,json_get(&j,0,"stdout_bytes"),1048577,&size))goto done;d.stdout_bytes=(size_t)size;
 d.collected=boolean(&j,"snapshot_collected",true);if(!d.collected&&!boolean(&j,"snapshot_collected",false))goto done;
 if(!boolean(&j,"initial_admission_valid",d.valid)||!boolean(&j,"read_only",true)||!boolean(&j,"writes_authorized",false)||!boolean(&j,"native_ready",false)||!boolean(&j,"identifiers_returned",false)||!boolean(&j,"policy_values_returned",false)||!valid(&d))goto done;
 *out=d;ok=true;
 done:free(data);return ok;
}
