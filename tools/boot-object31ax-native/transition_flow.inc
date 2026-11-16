/* SPDX-License-Identifier: MIT */
static bool mutate_reset_ax(Transaction *t){
 if(!state_binding(t)||!work_binding(t)||stop_requested||!persist(t,"reset-attempt","SPENT\n",6,"reset_marker_sync"))
  return refused_at(t,"MARKER","SPENT_OR_DURABILITY");
 Target current;if(!target_metadata(t,&current)||!same_target(&current,&t->target)||
  !mount_binding_ar(t,&current,false)||!work_binding(t)||!state_binding(t)||!trusted_parent(t->parent_fd)||stop_requested)
  return refused_at(t,"PREWRITE","POLICY_OR_IDENTITY_CHANGED");
 t->attempted=t->reset_attempted=true;t->writer_exit=run_writer(t,"reset");
 char text[16];int n=snprintf(text,sizeof(text),"%d\n",t->writer_exit);
 bool exit_saved=n>0&&persist(t,"reset-exit",text,(size_t)n,"exit_sync");
 memset(&t->diagnostic,0,sizeof(t->diagnostic));Snapshot after;
 bool observed=phase(t,"reset")&&observe(t,&after,&t->key);
 if(observed){transition_observation_ax(t,&after);diagnostic_ax(t,&after,"reset");}
 bool saved=observed&&save_snapshot(t,"reset.json",&after)&&save_diagnostic_ax(t,"reset");
 if(!exit_saved||!saved)return refused_at(t,"READBACK","READBACK_OR_DURABILITY");
 if(t->writer_exit||stop_requested)return refused_at(t,"WRITER","NONZERO_OR_INTERRUPTED");
 if(!validate_current_ax(t,&after,"reset"))return refused_at(t,"POSTCONDITION","POLICY_OR_OBJECT");
 t->baseline=after;
 /* A valid observation is insufficient: no candidate writer until both new
  * snapshot and ready marker are durably retained. Rescue uses neither file. */
 if(failpoint(t,"new_baseline_sync")||!save_snapshot(t,"candidate-baseline.json",&after)||
    !persist(t,"reset-ready","READY\n",6,"new_baseline_sync"))return refused_at(t,"BASELINE","STATE_OR_DURABILITY");
 t->baseline_ready=true;return true;
}
static bool run_transaction(Transaction *t,const char *profile_path){
 Snapshot admission,current;char path[PATH_MAX];
 if(t->synthetic){if(!option_bool(t,"recovery",false)||!option_bool(t,"root",false)||!equals(field(t->fixture,"model"),"Mac17,6"))return refused_at(t,"ENVIRONMENT","RECOVERY_REQUIRED");}
 else if(!recovery_admission())return refused_at(t,"ENVIRONMENT","RECOVERY_REQUIRED");
 t->codec_capability=codec_capability31ax();
 if(failpoint(t,"codec_positive")){t->codec_capability.positive_exact=false;t->codec_capability.passed=false;t->codec_capability.reason="POSITIVE_CONTROL_FAILED";}
 if(failpoint(t,"codec_negative")){t->codec_capability.negative_refused=false;t->codec_capability.passed=false;t->codec_capability.reason=t->codec_capability.positive_exact?"NEGATIVE_CONTROL_FAILED":"POSITIVE_CONTROL_FAILED";}
 if(t->install&&!t->codec_capability.passed)return refused_at(t,"CODEC","CAPABILITY_FAILED");
 if(!work_binding(t)||!phase(t,t->install?"initial":"before-restore")||!target_metadata(t,&t->target))return refused_at(t,"IDENTITIES","TARGET_BINDING");
 if(t->target.mounted||t->target.mount[0])return refused_at(t,"MOUNT","FOREIGN_MOUNT");
 if(!path_join(path,t->scratch,"m1n1-boot021.bin")||!file_matches(path,ROLLBACK_BYTES,ROLLBACK_SHA))return refused_at(t,"ARTIFACTS","ROLLBACK_PIN");
 if(t->install&&(!path_join(path,t->scratch,"candidate.macho")||!file_matches(path,CANDIDATE_BYTES,CANDIDATE_SHA256)))return refused_at(t,"ARTIFACTS","CANDIDATE_PIN");
 if(mkdirat(t->work_fd,"preboot",0700))return refused_at(t,"SCRATCH","CHILD_EXISTS");
 t->child_created=true;t->child_fd=openat(t->work_fd,"preboot",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
 if(t->child_fd<0||!private_fd(t->child_fd,true)||fstat(t->child_fd,&t->child_stat)||!underlying_child_ar(t))return refused_at(t,"SCRATCH","CHILD_BINDING");
 if(!acquire_mount(t,true))return refused_at(t,"MOUNT_RO","MOUNT_OR_BINDING");
 if(t->install){
  if(!observe(t,&admission,NULL)||!common_snapshot_ax(t,&admission,false)||
     !validate_snapshot(&admission,NULL,&t->profile,NULL,"initial-admission",t->synthetic))return refused_at(t,"ADMISSION","POLICY_OR_OBJECT");
  if(!prepare_state(t,profile_path)||!enroll(t))return refused_at(t,"ENROLLMENT","STATE_OR_DURABILITY");
 }else{
  if(!prepare_state(t,profile_path)||!load_enrollment(t))return refused_at(t,"ENROLLMENT","STATE_OR_TARGET_COMMITMENT");
  if(!observe(t,&current,&t->key)||!validate_current_ax(t,&current,"before-restore"))return refused_at(t,"RESTORE_ADMISSION","POLICY_OR_OBJECT");
  transition_observation_ax(t,&current);t->rescue_anchor=current;t->rescue_contract=ax_policy_view;t->rescue_anchor_ready=true;
  /* An existing or partial rescue anchor cannot be bypassed by presenting a
   * final-looking payload after an earlier refused writer. */
  if(!rescue_anchor_ax(t,false))return refused_at(t,"RESCUE_ANCHOR","STATE_OR_DURABILITY");
  if(validate_current_ax(t,&current,"restored")){diagnostic_ax(t,&current,"restored");t->rollback_verified=true;return true;}
  if(t->rescue_anchor_durable&&(strcmp(current.lab_metadata_hmac,t->rescue_anchor.lab_metadata_hmac)||
     memcmp(current.lab_semantics,t->rescue_anchor.lab_semantics,sizeof(current.lab_semantics))||
     strcmp(ax_policy_view.lab_manifest,t->rescue_contract.lab_manifest)))return refused_at(t,"RESTORE_ADMISSION","POLICY_OR_OBJECT");
  if(!t->rescue_anchor_durable&&!rescue_anchor_ax(t,true))return refused_at(t,"RESCUE_ANCHOR","STATE_OR_DURABILITY");
 }
 if(!release_mount(t))return refused_at(t,"RELEASE_RO","CLEANUP_UNCERTAIN");
 if(!phase(t,t->install?"prewrite":"before-restore")||!acquire_mount(t,false))return refused_at(t,"MOUNT_RW","MOUNT_OR_BINDING");
 if(!prewrite(t,t->install?"pre-reset":"before-restore"))return refused_at(t,"PREWRITE","POLICY_OR_IDENTITY_CHANGED");
 if(t->install){
  if(!mutate_reset_ax(t))return false;
  if(!phase(t,"candidate-prewrite")||!prewrite(t,"candidate-base"))return refused_at(t,"PREWRITE","POLICY_OR_IDENTITY_CHANGED");
  if(!mutate(t,"candidate","candidate","candidate.json"))return false;t->candidate_verified=true;
 }else{
  /* The current rescue anchor was established from the guarded read-only
   * observation. It is not replaced after an unexpected policy delta. */
  if(!observe(t,&current,&t->key)||!validate_current_ax(t,&current,"before-restore")||
     strcmp(current.lab_metadata_hmac,t->rescue_anchor.lab_metadata_hmac)||
     strcmp(ax_policy_view.lab_manifest,t->rescue_contract.lab_manifest)||
     memcmp(current.lab_semantics,t->rescue_anchor.lab_semantics,sizeof(current.lab_semantics)))return refused_at(t,"RESTORE_ADMISSION","POLICY_OR_OBJECT");
  if(!strcmp(current.lab_ctrr,"enabled")){
   if(!mutate(t,"ctrr","raw-policy","raw-policy.json"))return false;
  }else if(!strcmp(current.lab_ctrr,"disabled")){
   if(!validate_current_ax(t,&current,"raw-policy"))return refused_at(t,"RAW_POLICY","POLICY_CHANGED");
  }else return refused_at(t,"RAW_POLICY","UNKNOWN_CTRR");
  if(!prewrite(t,"raw-policy"))return refused_at(t,"RAW_POLICY","PREWRITE_CHANGED");
  if(!mutate(t,"boot021","restored","restored.json"))return false;t->rollback_verified=true;
 }
 return true;
}
