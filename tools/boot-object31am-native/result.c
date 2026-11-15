/* SPDX-License-Identifier: MIT */
/* The frozen observer/validator remains byte-identical in generated sources. */
#include "diagnostic.c"
#include "preboot.h"
static const char *const pb_stages[]={"CLI","PROFILE","ENVIRONMENT","SCRATCH","IDENTITIES","STATE","REOBSERVATION","MOUNT","MOUNT_VERIFICATION","DIAGNOSTIC","CLEANUP","COMPLETE","VALIDATION"};
static const char *const pb_reasons[]={"ARGUMENTS","PROFILE_BINDING","ENVIRONMENT","SCRATCH_BINDING","METADATA","MOUNTED_FIELD","PATH_FORMAT","PATH_UNSAFE","STATE_CONTRADICTION","IDENTITY_CHANGED","TOOL_UNAVAILABLE","CHILD_EXISTS","MOUNT_COMMAND","MOUNT_NOT_OBSERVED","MOUNT_BINDING","NOT_READ_ONLY","DIAGNOSTIC_REFUSED","CLEANUP_BINDING","UNMOUNT_COMMAND","UNMOUNT_NOT_OBSERVED","RESULT_FORMAT","KERNEL_MOUNT_STATE","INTERRUPTED","NONE"};
static const char *const pb_initials[]={"UNOBSERVED","MOUNTED_VALID","UNMOUNTED_EMPTY","INVALID"};
static const char *const pb_cleanups[]={"NOT_NEEDED","UNMOUNTED","FAILED","REFUSED"};
_Static_assert(sizeof(pb_stages)/sizeof(*pb_stages)==PS_COUNT,"stage table");
_Static_assert(sizeof(pb_reasons)/sizeof(*pb_reasons)==PR_COUNT,"reason table");
_Static_assert(sizeof(pb_initials)/sizeof(*pb_initials)==PI_COUNT,"initial table");
_Static_assert(sizeof(pb_cleanups)/sizeof(*pb_cleanups)==PC_COUNT,"cleanup table");
void pb_reset(PBResult *r,bool synthetic){memset(r,0,sizeof(*r));r->synthetic=synthetic;r->mount_exit=r->unmount_exit=-1;r->stage=PS_CLI;r->reason=PR_ARGUMENTS;}
static bool pb_valid(const PBResult *r){
 if(r->stage<0||r->stage>=PS_COUNT||r->reason<0||r->reason>=PR_COUNT||r->initial<0||r->initial>=PI_COUNT||r->cleanup<0||r->cleanup>=PC_COUNT||r->mount_exit< -1||r->mount_exit>255||r->unmount_exit< -1||r->unmount_exit>255)return false;
 if(r->readonly&&!r->created)return false;
 if(r->created&&(!r->attempted||r->initial!=PI_UNMOUNTED_EMPTY))return false;
 if(r->created&&r->cleanup==PC_NOT_NEEDED)return false;
 if(r->unmount_exit>=0&&!r->created)return false;
 bool conservative=r->stage==PS_VALIDATION&&r->reason==PR_RESULT_FORMAT&&r->initial==PI_UNOBSERVED&&r->attempted&&r->uncertain&&!r->created&&!r->readonly&&!r->has_diagnostic&&r->cleanup==PC_REFUSED;
 if(r->attempted&&r->initial!=PI_UNMOUNTED_EMPTY&&!conservative)return false;
 if(!r->attempted&&(r->created||r->readonly||r->uncertain||r->mount_exit!=-1||r->unmount_exit!=-1||r->cleanup!=PC_NOT_NEEDED))return false;
 if((r->cleanup==PC_UNMOUNTED||r->cleanup==PC_FAILED)&&!r->created)return false;
 if(r->uncertain&&(!r->attempted||r->cleanup!=PC_REFUSED))return false;
 if(r->has_diagnostic){
  if(!valid(&r->diagnostic)||r->synthetic!=r->diagnostic.synthetic)return false;
  if(r->stage!=PS_DIAGNOSTIC&&r->stage!=PS_CLEANUP&&r->stage!=PS_COMPLETE)return false;
  if(r->initial!=PI_MOUNTED_VALID&&!(r->attempted&&r->created&&r->readonly&&r->mount_exit==0))return false;
  if(r->diagnostic.valid&&!r->complete&&r->stage!=PS_CLEANUP&&r->reason!=PR_INTERRUPTED)return false;
 }
 if(r->reason==PR_DIAGNOSTIC_REFUSED&&(!r->has_diagnostic||r->diagnostic.valid))return false;
 if(r->complete)return r->has_diagnostic&&r->diagnostic.valid&&r->stage==PS_COMPLETE&&r->reason==PR_NONE&&!r->uncertain&&(!r->attempted||(r->cleanup==PC_UNMOUNTED&&r->unmount_exit==0));
 return r->reason!=PR_NONE&&r->stage!=PS_COMPLETE;
}
bool pb_print(const PBResult *input){
 PBResult fallback;const PBResult *r=input;
 bool input_valid=pb_valid(r);
 if(!input_valid){
  pb_reset(&fallback,input->synthetic);fallback.stage=PS_VALIDATION;fallback.reason=PR_RESULT_FORMAT;
  if(input->attempted||input->created||input->readonly||input->uncertain||input->mount_exit>=0||input->unmount_exit>=0||input->cleanup!=PC_NOT_NEEDED){fallback.attempted=true;fallback.uncertain=true;fallback.cleanup=PC_REFUSED;}
  r=&fallback;
 }
 char m[16]="null",u[16]="null";if(r->mount_exit>=0)snprintf(m,sizeof(m),"%d",r->mount_exit);if(r->unmount_exit>=0)snprintf(u,sizeof(u),"%d",r->unmount_exit);
 printf("{\"schema\":\"ilinux31am-preboot-result-v1\",\"scope\":\"%s\",\"status\":\"%s\",\"stage\":\"%s\",\"reason\":\"%s\",\"initial_state\":\"%s\",\"mount_attempted\":%s,\"mount_created\":%s,\"mount_read_only_verified\":%s,\"mount_state_uncertain\":%s,\"mount_exit\":%s,\"unmount_exit\":%s,\"cleanup\":\"%s\",\"diagnostic\":",r->synthetic?"SYNTHETIC_CONTROL":"RECOVERY_CONDITIONAL_PREBOOT",r->complete?"DIAGNOSTIC_COMPLETE":"REFUSED",pb_stages[r->stage],pb_reasons[r->reason],pb_initials[r->initial],r->attempted?"true":"false",r->created?"true":"false",r->readonly?"true":"false",r->uncertain?"true":"false",m,u,pb_cleanups[r->cleanup]);
 if(r->has_diagnostic)diagnostic_print(&r->diagnostic);else fputs("null",stdout);
 puts(",\"preboot_write_requested\":false,\"boot_object_installed\":false,\"security_settings_changed\":false,\"native_ready\":false,\"identifiers_returned\":false,\"policy_values_returned\":false}");
 return input_valid;
}
static bool getbool(const Json *j,const char *key,bool *out){if(boolean(j,key,true)){*out=true;return true;}if(boolean(j,key,false)){*out=false;return true;}return false;}
static bool parse_diagnostic(const Json *input,int node,Diagnostic *out){
 Json local=*input;local.nodes[0]=input->nodes[node];const Json *j=&local;Diagnostic d={.command_exit=-1};
 const char *const keys[]={"schema","scope","status","stage","failure_kind","reason","command","command_exit","stdout_bytes","snapshot_collected","initial_admission_valid","read_only","writes_authorized","native_ready","identifiers_returned","policy_values_returned"};
 if(!json_keys(j,0,keys,16)||!json_string(j,json_get(j,0,"schema"),"ilinux31al-snapshot-diagnostic-v1"))return false;
 if(json_string(j,json_get(j,0,"scope"),"SYNTHETIC_CONTROL"))d.synthetic=true;else if(!json_string(j,json_get(j,0,"scope"),"RECOVERY_READ_ONLY_DIAGNOSTIC"))return false;
 if(json_string(j,json_get(j,0,"status"),"INITIAL_ADMISSION_PASS"))d.valid=true;else if(!json_string(j,json_get(j,0,"status"),"REFUSED"))return false;
 d.stage=label(j,"stage",stages,DS_COUNT);d.kind=label(j,"failure_kind",kinds,DK_COUNT);d.reason=label(j,"reason",reasons,DR_COUNT);d.command=label(j,"command",commands,DC_COUNT);
 int n=json_get(j,0,"command_exit"),size=0;
 if(j->nodes[n].type!=J_NULL&&!number(j,n,255,&d.command_exit))return false;
 if(!number(j,json_get(j,0,"stdout_bytes"),1048577,&size))return false;d.stdout_bytes=(size_t)size;
 if(!getbool(j,"snapshot_collected",&d.collected)||!boolean(j,"initial_admission_valid",d.valid)||!boolean(j,"read_only",true)||!boolean(j,"writes_authorized",false)||!boolean(j,"native_ready",false)||!boolean(j,"identifiers_returned",false)||!boolean(j,"policy_values_returned",false)||!valid(&d))return false;
 *out=d;return true;
}
bool pb_load(const char *path,PBResult *out){
 uint8_t *data=NULL;size_t bytes=0;Json j;bool ok=false;PBResult r;pb_reset(&r,false);
 const char *const keys[]={"schema","scope","status","stage","reason","initial_state","mount_attempted","mount_created","mount_read_only_verified","mount_state_uncertain","mount_exit","unmount_exit","cleanup","diagnostic","preboot_write_requested","boot_object_installed","security_settings_changed","native_ready","identifiers_returned","policy_values_returned"};
 if(!read_file(path,8192,false,&data,&bytes)||!json_parse((Bytes){data,bytes},&j)||!json_keys(&j,0,keys,20)||!json_string(&j,json_get(&j,0,"schema"),"ilinux31am-preboot-result-v1"))goto done;
 if(json_string(&j,json_get(&j,0,"scope"),"SYNTHETIC_CONTROL"))r.synthetic=true;else if(!json_string(&j,json_get(&j,0,"scope"),"RECOVERY_CONDITIONAL_PREBOOT"))goto done;
 if(json_string(&j,json_get(&j,0,"status"),"DIAGNOSTIC_COMPLETE"))r.complete=true;else if(!json_string(&j,json_get(&j,0,"status"),"REFUSED"))goto done;
 r.stage=label(&j,"stage",pb_stages,PS_COUNT);r.reason=label(&j,"reason",pb_reasons,PR_COUNT);r.initial=label(&j,"initial_state",pb_initials,PI_COUNT);r.cleanup=label(&j,"cleanup",pb_cleanups,PC_COUNT);
 if(!getbool(&j,"mount_attempted",&r.attempted)||!getbool(&j,"mount_created",&r.created)||!getbool(&j,"mount_read_only_verified",&r.readonly)||!getbool(&j,"mount_state_uncertain",&r.uncertain))goto done;
 int n=json_get(&j,0,"mount_exit");if(j.nodes[n].type!=J_NULL&&!number(&j,n,255,&r.mount_exit))goto done;
 n=json_get(&j,0,"unmount_exit");if(j.nodes[n].type!=J_NULL&&!number(&j,n,255,&r.unmount_exit))goto done;
 n=json_get(&j,0,"diagnostic");if(j.nodes[n].type==J_OBJECT){if(!parse_diagnostic(&j,n,&r.diagnostic))goto done;r.has_diagnostic=true;}else if(j.nodes[n].type!=J_NULL)goto done;
 for(size_t i=14;i<20;i++)if(!boolean(&j,keys[i],false))goto done;
 if(!pb_valid(&r))goto done;*out=r;ok=true;
 done:free(data);return ok;
}
