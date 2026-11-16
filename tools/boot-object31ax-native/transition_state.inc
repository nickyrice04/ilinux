/* SPDX-License-Identifier: MIT */
/* Original AX contract/state logic. Included only after the unchanged trusted
 * filesystem/target/observer primitives have been defined. */
static bool safe_lab_semantics_ax(const Snapshot *s){
 if(strcmp(s->lab_semantics[0],"true")||strcmp(s->lab_semantics[1],"true"))return false;
 for(unsigned i=2;i<8;i++){
  const char *v=s->lab_semantics[i];
  if(!strcmp(v,"ABSENT"))continue;
  if(i==5?!strcmp(v,"0x0000000000000000"):!strcmp(v,"false"))continue;
  return false;
 }
 return true;
}
static bool common_snapshot_ax(Transaction *t,const Snapshot *s,bool bound){
 if(s->synthetic!=t->synthetic||!s->guarded||!s->paired||!s->original_full||!s->lab_permissive||!s->policy_complete||
    strcmp(s->profile_sha,t->profile.sha)||!safe_lab_semantics_ax(s)||!ax_policy_view.observed)return false;
 if(!bound)return !s->metadata_bound&&!ax_policy_view.bound;
 return t->key.loaded&&s->metadata_bound&&ax_policy_view.bound&&!strcmp(s->comparison_key_id,t->key.id);
}
static bool immutable_original_ax(Transaction *t,const Snapshot *s){
 return common_snapshot_ax(t,s,true)&&t->enrolled&&
  !memcmp(s->original_semantics,t->original_anchor.original_semantics,sizeof(s->original_semantics))&&
  !strcmp(s->original_metadata_hmac,t->original_anchor.original_metadata_hmac)&&
  !strcmp(ax_policy_view.original_identity,t->pre_contract.original_identity)&&
  !strcmp(ax_policy_view.lab_identity,t->pre_contract.lab_identity);
}
static bool strict_lab_ax(Transaction *t,const Snapshot *s){
 return immutable_original_ax(t,s)&&!strcmp(s->lab_metadata_hmac,t->original_anchor.lab_metadata_hmac)&&
  !strcmp(ax_policy_view.lab_manifest,t->pre_contract.lab_manifest);
}
static void transition_observation_ax(Transaction *t,const Snapshot *s){
 t->transition_observed=true;
 t->lab_private_changed|=strcmp(s->lab_metadata_hmac,t->original_anchor.lab_metadata_hmac)!=0;
 t->lab_manifest_changed|=strcmp(ax_policy_view.lab_manifest,t->pre_contract.lab_manifest)!=0;
 t->protected_identity_changed|=strcmp(ax_policy_view.original_identity,t->pre_contract.original_identity)||
  strcmp(ax_policy_view.lab_identity,t->pre_contract.lab_identity)||
  memcmp(s->original_semantics,t->original_anchor.original_semantics,sizeof(s->original_semantics))||
  strcmp(s->original_metadata_hmac,t->original_anchor.original_metadata_hmac);
}
static bool validate_current_ax(Transaction *t,const Snapshot *s,const char *phase_name){
 if(!immutable_original_ax(t,s))return false;
 if(!strcmp(phase_name,"pre-reset"))return strict_lab_ax(t,s)&&s->selected_exact&&!strcmp(s->selected,"BOOT021")&&!strcmp(s->lab_ctrr,"disabled");
 if(!strcmp(phase_name,"reset"))return strict_lab_ax(t,s)&&!strcmp(s->lab_ctrr,"enabled")&&
  ((!strcmp(s->selected,"NONE")&&!s->selected_exact)||(!strcmp(s->selected,"BOOT021")&&s->selected_exact));
 if(!strcmp(phase_name,"candidate-base"))return t->baseline_ready&&strict_lab_ax(t,s)&&!memcmp(s,&t->baseline,sizeof(*s));
 if(!strcmp(phase_name,"candidate"))return t->baseline_ready&&strict_lab_ax(t,s)&&
  !memcmp(s->lab_semantics,t->baseline.lab_semantics,sizeof(s->lab_semantics))&&
  !strcmp(s->lab_metadata_hmac,t->baseline.lab_metadata_hmac)&&s->selected_exact&&!strcmp(s->selected,"CANDIDATE")&&!strcmp(s->lab_ctrr,"enabled");
 /* Functional rescue never reuses pre-reset LAB opaque equality as admission.
  * It still requires the immutable Original/identity and typed safe LAB view. */
 if(!strcmp(phase_name,"before-restore"))return !strcmp(s->lab_ctrr,"enabled")||!strcmp(s->lab_ctrr,"disabled");
 if(!t->rescue_anchor_ready||strcmp(s->lab_metadata_hmac,t->rescue_anchor.lab_metadata_hmac)||
    memcmp(s->lab_semantics,t->rescue_anchor.lab_semantics,sizeof(s->lab_semantics)))return false;
 bool same_manifest=!strcmp(ax_policy_view.lab_manifest,t->rescue_contract.lab_manifest);
 if(!strcmp(phase_name,"raw-policy"))return same_manifest&&!strcmp(s->lab_ctrr,"disabled")&&
  t->selection_before_available&&ax_object_read.reference_commitment_bound&&
  !memcmp(t->selection_before,ax_object_read.reference_commitment,64);
 if(!strcmp(phase_name,"restored")){
  bool recovered_manifest=!t->rescue_contract.lab_manifest_present&&ax_policy_view.lab_manifest_present&&
   !strcmp(ax_policy_view.lab_manifest,t->pre_contract.lab_manifest);
  return (same_manifest||recovered_manifest)&&s->selected_exact&&!strcmp(s->selected,"BOOT021")&&!strcmp(s->lab_ctrr,"disabled");
 }
 return false;
}
static void anchor_auth_ax(Transaction *t,const PolicyView31AX *view,char out[65]){
 CCHmacContext c;CCHmacInit(&c,kCCHmacAlgSHA256,t->key.bytes,sizeof(t->key.bytes));
 const char *parts[]={"ilinux31ax-pre-anchor-auth-v1",t->profile.sha,t->key.id,
  view->original_identity,view->lab_identity,view->lab_manifest,view->lab_manifest_present?"PRESENT":"ABSENT",
  "PRE_ORIGINAL_PRIVATE",t->original_anchor.original_metadata_hmac,"PRE_LAB_PRIVATE",t->original_anchor.lab_metadata_hmac};
 for(size_t i=0;i<sizeof(parts)/sizeof(parts[0]);i++)CCHmacUpdate(&c,parts[i],strlen(parts[i])+1);
 const char *roles[]={"PRE_ORIGINAL_SEMANTICS_8","PRE_LAB_SEMANTICS_8"};
 const char (*vectors[])[24]={t->original_anchor.original_semantics,t->original_anchor.lab_semantics};
 for(unsigned role=0;role<2;role++){
  CCHmacUpdate(&c,roles[role],strlen(roles[role])+1);
  for(unsigned i=0;i<8;i++)CCHmacUpdate(&c,vectors[role][i],strlen(vectors[role][i])+1);
 }
 unsigned char digest[32];CCHmacFinal(&c,digest);static const char hex[]="0123456789abcdef";
 for(unsigned i=0;i<32;i++){out[i*2]=hex[digest[i]>>4];out[i*2+1]=hex[digest[i]&15];}out[64]=0;memset(digest,0,sizeof(digest));
}
static bool save_anchor_contract_ax(Transaction *t){
 char auth[65],bytes[1024];anchor_auth_ax(t,&t->pre_contract,auth);
 int n=snprintf(bytes,sizeof(bytes),"{\"schema\":\"ilinux31ax-pre-policy-anchor-v1\",\"profile\":\"%s\",\"key\":\"%s\",\"original_identity\":\"%s\",\"lab_identity\":\"%s\",\"lab_manifest\":\"%s\",\"lab_manifest_present\":%s,\"authentication\":\"%s\"}\n",
  t->profile.sha,t->key.id,t->pre_contract.original_identity,t->pre_contract.lab_identity,t->pre_contract.lab_manifest,t->pre_contract.lab_manifest_present?"true":"false",auth);
 return n>0&&(size_t)n<sizeof(bytes)&&persist(t,"pre-policy-anchor.json",bytes,(size_t)n,"anchor_sync");
}
static bool load_anchor_contract_ax(Transaction *t){
 uint8_t *bytes=NULL;size_t n=0;Json j;bool ok=false;
 if(!read_state(t,"pre-policy-anchor.json",1024,&bytes,&n)||!json_parse((Bytes){bytes,n},&j))goto done;
 const char *keys[]={"schema","profile","key","original_identity","lab_identity","lab_manifest","lab_manifest_present","authentication"};
 if(!json_keys(&j,0,keys,8)||!json_string(&j,json_get(&j,0,"schema"),"ilinux31ax-pre-policy-anchor-v1")||
    !json_string(&j,json_get(&j,0,"profile"),t->profile.sha)||!json_string(&j,json_get(&j,0,"key"),t->key.id))goto done;
 char *values[]={t->pre_contract.original_identity,t->pre_contract.lab_identity,t->pre_contract.lab_manifest};
 for(unsigned i=0;i<3;i++){int node=json_get(&j,0,keys[3+i]);if(node<0||j.nodes[node].type!=J_STRING||!valid_sha(j.nodes[node].value))goto done;strcpy(values[i],j.nodes[node].value);}
 t->pre_contract.lab_manifest_present=node_bool(&j,0,"lab_manifest_present",true);
 if(!t->pre_contract.lab_manifest_present&&!node_bool(&j,0,"lab_manifest_present",false))goto done;
 char auth[65];anchor_auth_ax(t,&t->pre_contract,auth);
 if(!json_string(&j,json_get(&j,0,"authentication"),auth))goto done;
 t->pre_contract.observed=t->pre_contract.bound=true;ok=true;
done:free(bytes);return ok;
}
static bool enroll(Transaction *t){
 if(!observe(t,&t->original_anchor,&t->key)||!common_snapshot_ax(t,&t->original_anchor,true)||
    !validate_snapshot(&t->original_anchor,NULL,&t->profile,&t->key,"initial",t->synthetic))return false;
 t->pre_contract=ax_policy_view;
 if(!t->pre_contract.lab_manifest_present)return false;
 char commitment[65];
 if(!identity_commitment(t,&t->target,commitment)||!persist(t,"target.hmac",commitment,64,"target_sync")||
    !save_snapshot(t,"pre-reset.json",&t->original_anchor)||!save_anchor_contract_ax(t)||
    !persist(t,"enrolled","ENROLLED\n",9,"enrolled_sync"))return false;
 t->enrolled=true;return true;
}
static bool load_enrollment(Transaction *t){
 uint8_t *bytes=NULL;size_t n=0;char commitment[65];
 if(!read_state(t,"enrolled",32,&bytes,&n))return false;bool ok=n==9&&!memcmp(bytes,"ENROLLED\n",9);free(bytes);if(!ok)return false;
 if(!read_state(t,"target.hmac",64,&bytes,&n))return false;
 ok=n==64&&identity_commitment(t,&t->target,commitment)&&!memcmp(bytes,commitment,64);free(bytes);if(!ok)return false;
 char path[PATH_MAX];if(!path_join(path,t->state_path,"pre-reset.json"))return false;
 int fd=openat(t->state_fd,"pre-reset.json",O_RDONLY|O_NOFOLLOW|O_CLOEXEC);if(fd<0)return false;ok=private_fd(fd,false);close(fd);
 if(!ok||!parse_snapshot(path,&t->original_anchor,t->synthetic)||
    !validate_snapshot(&t->original_anchor,NULL,&t->profile,&t->key,"initial",t->synthetic)||
    !safe_lab_semantics_ax(&t->original_anchor)||!load_anchor_contract_ax(t))return false;
 t->enrolled=true;return true;
}
static void rescue_auth_ax(Transaction *t,const PolicyView31AX *v,const Snapshot *s,char out[65]){
 char pre[65];anchor_auth_ax(t,&t->pre_contract,pre);
 CCHmacContext c;CCHmacInit(&c,kCCHmacAlgSHA256,t->key.bytes,sizeof(t->key.bytes));
 const char *parts[]={"ilinux31ax-current-rescue-anchor-v1",t->profile.sha,t->key.id,pre,
  v->original_identity,v->lab_identity,v->lab_manifest,v->lab_manifest_present?"PRESENT":"ABSENT",
  s->original_metadata_hmac,s->lab_metadata_hmac};
 for(size_t i=0;i<sizeof(parts)/sizeof(parts[0]);i++)CCHmacUpdate(&c,parts[i],strlen(parts[i])+1);
 for(unsigned i=0;i<8;i++){CCHmacUpdate(&c,s->original_semantics[i],strlen(s->original_semantics[i])+1);CCHmacUpdate(&c,s->lab_semantics[i],strlen(s->lab_semantics[i])+1);}
 unsigned char digest[32];CCHmacFinal(&c,digest);static const char hex[]="0123456789abcdef";
 for(unsigned i=0;i<32;i++){out[i*2]=hex[digest[i]>>4];out[i*2+1]=hex[digest[i]&15];}out[64]=0;memset(digest,0,sizeof(digest));
}
static bool rescue_anchor_ax(Transaction *t,bool create){
 struct stat ready;bool exists=fstatat(t->state_fd,"rescue-ready",&ready,AT_SYMLINK_NOFOLLOW)==0;
 if(!exists&&errno!=ENOENT)return false;
 if(!exists){
  struct stat prior;
  if(fstatat(t->state_fd,"rescue-anchor.json",&prior,AT_SYMLINK_NOFOLLOW)==0||errno!=ENOENT)return false;
  if(fstatat(t->state_fd,"rescue-policy-anchor.json",&prior,AT_SYMLINK_NOFOLLOW)==0||errno!=ENOENT)return false;
  if(!create)return true;
  if(!save_snapshot(t,"rescue-anchor.json",&t->rescue_anchor))return false;
  char auth[65],bytes[1024];rescue_auth_ax(t,&t->rescue_contract,&t->rescue_anchor,auth);
  int n=snprintf(bytes,sizeof(bytes),"{\"schema\":\"ilinux31ax-rescue-policy-anchor-v1\",\"original_identity\":\"%s\",\"lab_identity\":\"%s\",\"lab_manifest\":\"%s\",\"lab_manifest_present\":%s,\"authentication\":\"%s\"}\n",
   t->rescue_contract.original_identity,t->rescue_contract.lab_identity,t->rescue_contract.lab_manifest,t->rescue_contract.lab_manifest_present?"true":"false",auth);
  if(n<1||(size_t)n>=sizeof(bytes)||!persist(t,"rescue-policy-anchor.json",bytes,(size_t)n,"rescue_contract_sync")||
     !persist(t,"rescue-ready","READY\n",6,"rescue_ready_sync"))return false;
 }else{
  uint8_t *bytes=NULL;size_t n=0;Json j;char path[PATH_MAX],auth[65];
  if(!read_state(t,"rescue-ready",16,&bytes,&n))return false;bool ok=n==6&&!memcmp(bytes,"READY\n",6);free(bytes);if(!ok)return false;
  if(!path_join(path,t->state_path,"rescue-anchor.json"))return false;
  int fd=openat(t->state_fd,"rescue-anchor.json",O_RDONLY|O_NOFOLLOW|O_CLOEXEC);if(fd<0)return false;ok=private_fd(fd,false);close(fd);
  if(!ok||!parse_snapshot(path,&t->rescue_anchor,t->synthetic)||!immutable_original_ax(t,&t->rescue_anchor))return false;
  if(!read_state(t,"rescue-policy-anchor.json",1024,&bytes,&n))return false;
  ok=json_parse((Bytes){bytes,n},&j);free(bytes);if(!ok)return false;
  const char *keys[]={"schema","original_identity","lab_identity","lab_manifest","lab_manifest_present","authentication"};
  if(!json_keys(&j,0,keys,6)||!json_string(&j,json_get(&j,0,"schema"),"ilinux31ax-rescue-policy-anchor-v1"))return false;
  char *values[]={t->rescue_contract.original_identity,t->rescue_contract.lab_identity,t->rescue_contract.lab_manifest};
  for(unsigned i=0;i<3;i++){int node=json_get(&j,0,keys[1+i]);if(node<0||j.nodes[node].type!=J_STRING||!valid_sha(j.nodes[node].value))return false;strcpy(values[i],j.nodes[node].value);}
  t->rescue_contract.lab_manifest_present=node_bool(&j,0,"lab_manifest_present",true);
  if(!t->rescue_contract.lab_manifest_present&&!node_bool(&j,0,"lab_manifest_present",false))return false;
  rescue_auth_ax(t,&t->rescue_contract,&t->rescue_anchor,auth);
  if(!json_string(&j,json_get(&j,0,"authentication"),auth)||
     strcmp(t->rescue_contract.original_identity,t->pre_contract.original_identity)||
     strcmp(t->rescue_contract.lab_identity,t->pre_contract.lab_identity))return false;
 }
 t->rescue_anchor_durable=true;return true;
}
static bool prewrite(Transaction *t,const char *phase_name){
 if(stop_requested||!state_binding(t)||!work_binding(t))return false;Snapshot current;
 if(!observe(t,&current,&t->key)||!validate_current_ax(t,&current,phase_name))return false;
 if(!strcmp(phase_name,"pre-reset")&&memcmp(&current,&t->original_anchor,sizeof(current)))return false;
 t->selection_before_available=ax_object_read.reference_commitment_bound;
 if(t->selection_before_available)memcpy(t->selection_before,ax_object_read.reference_commitment,sizeof(t->selection_before));
 else memset(t->selection_before,0,sizeof(t->selection_before));return true;
}
static void diagnostic_ax(Transaction *t,const Snapshot *s,const char *phase_name){
 Diagnostic31AX *d=&t->diagnostic;*d=(Diagnostic31AX){.available=true,.phase=phase_name,.read=ax_object_read};
 d->comparison_available=t->selection_before_available&&ax_object_read.reference_commitment_bound;
 d->selection_changed=d->comparison_available&&memcmp(t->selection_before,ax_object_read.reference_commitment,64)!=0;
 memset(d->read.reference_commitment,0,sizeof(d->read.reference_commitment));d->read.reference_commitment_bound=false;
 bool reset=!strcmp(phase_name,"reset"),candidate=!strcmp(phase_name,"candidate");
 d->preservation=(reset||candidate)?strict_lab_ax(t,s):immutable_original_ax(t,s);
 if(!reset&&!candidate&&t->rescue_anchor_ready)d->preservation=d->preservation&&
  !strcmp(s->lab_metadata_hmac,t->rescue_anchor.lab_metadata_hmac)&&
  !memcmp(s->lab_semantics,t->rescue_anchor.lab_semantics,sizeof(s->lab_semantics));
 d->selected=!strcmp(phase_name,"raw-policy")||(reset?
  ((!strcmp(s->selected,"NONE")&&!s->selected_exact)||(!strcmp(s->selected,"BOOT021")&&s->selected_exact)):
  (s->selected_exact&&!strcmp(s->selected,candidate?"CANDIDATE":"BOOT021")));
 d->ctrr_enabled=!strcmp(s->lab_ctrr,"enabled");d->ctrr_disabled=!strcmp(s->lab_ctrr,"disabled");d->ctrr_unknown=!strcmp(s->lab_ctrr,"unknown");
 d->ctrr=(reset||candidate)?d->ctrr_enabled:d->ctrr_disabled;
 d->passed=validate_current_ax(t,s,phase_name);
 /* Manifest continuity participates in preservation, including the one bounded
  * absent-to-preknown-manifest exception in the final raw rescue observation. */
 if(d->preservation&&d->selected&&d->ctrr&&!d->passed)d->preservation=false;
}
