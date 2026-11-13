/* SPDX-License-Identifier: MIT */
#include "reader.h"
#include <mach-o/dyld.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>

void refused(void){printf("{\"status\":\"REFUSED\",\"reason\":\"%s\",\"read_only\":true,\"writes_authorized\":false,\"native_ready\":false}\n",refusal_reason);}
static void help(void){puts("ilinux31aj-reader: original read-only Recovery companion\nModes: --codec-selftest; --fixture FILE; --snapshot; --snapshot-fixture PLIST;\n --validate-snapshot FILE; --validate-fixture-snapshot FILE;\n --snapshot-value FILE --key lab_ctrr; --target-group-private;\n --generate-comparison-key (32 own random bytes to empty private regular stdout file);\n --verify-file FILE --expected-bytes N --expected-sha256 SHA;\n --capability-check recovery-transaction-v2\nRecovery modes require --profile FILE, --target-volume LAB and --original-volume ORIGINAL.\nValidation requires --phase initial-admission|initial|candidate|before-restore|raw-policy|restored;\nall except initial-admission require --comparison-key FILE; later phases require --baseline FILE. Default only displays help.");}
static bool generate_key(void){
    struct stat before,after;int flags=fcntl(STDOUT_FILENO,F_GETFL);
    if(flags<0||(flags&O_ACCMODE)==O_RDONLY||fstat(STDOUT_FILENO,&before)||!S_ISREG(before.st_mode)||before.st_uid!=geteuid()||(before.st_mode&07777)!=0600||before.st_size!=0||before.st_nlink!=1||lseek(STDOUT_FILENO,0,SEEK_CUR)!=0)return false;
    uint8_t own_random[32];arc4random_buf(own_random,sizeof(own_random));size_t n=0;bool ok=false;
    while(n<sizeof(own_random)){ssize_t got=write(STDOUT_FILENO,own_random+n,sizeof(own_random)-n);if(got<0&&errno==EINTR)continue;if(got<=0)goto done;n+=(size_t)got;}
    if(fsync(STDOUT_FILENO)||fstat(STDOUT_FILENO,&after)||after.st_dev!=before.st_dev||after.st_ino!=before.st_ino||after.st_uid!=before.st_uid||after.st_mode!=before.st_mode||after.st_nlink!=1||after.st_size!=32)goto done;ok=true;
done:for(size_t i=0;i<sizeof(own_random);i++)((volatile uint8_t *)own_random)[i]=0;return ok;
}
int main(int argc,char **argv){
    const char *mode=NULL,*input=NULL,*profile_path=NULL,*target=LAB_VOLUME,*original="/Volumes/Macintosh HD",*phase=NULL,*baseline_path=NULL,*key=NULL,*expected_bytes=NULL,*expected_sha=NULL,*comparison_key_path=NULL;
    unsigned seen_options=0;
    if(argc==1){help();return 0;}
    for(int i=1;i<argc;i++){
        const char *a=argv[i];if(!strcmp(a,"--help")||!strcmp(a,"-h")){if(argc!=2)goto fail;help();return 0;}
        bool val=!strcmp(a,"--fixture")||!strcmp(a,"--snapshot-fixture")||!strcmp(a,"--validate-snapshot")||!strcmp(a,"--validate-fixture-snapshot")||!strcmp(a,"--snapshot-value")||!strcmp(a,"--verify-file")||!strcmp(a,"--capability-check");
        if(val||!strcmp(a,"--snapshot")||!strcmp(a,"--target-group-private")||!strcmp(a,"--codec-selftest")||!strcmp(a,"--generate-comparison-key")){if(mode)goto fail;mode=a;if(val){if(++i==argc)goto fail;input=argv[i];}continue;}
        const char **destination=NULL;unsigned bit=0;
        if(!strcmp(a,"--profile")){destination=&profile_path;bit=1;}else if(!strcmp(a,"--target-volume")){destination=&target;bit=2;}else if(!strcmp(a,"--original-volume")){destination=&original;bit=4;}else if(!strcmp(a,"--phase")){destination=&phase;bit=8;}else if(!strcmp(a,"--baseline")){destination=&baseline_path;bit=16;}else if(!strcmp(a,"--key")){destination=&key;bit=32;}else if(!strcmp(a,"--expected-bytes")){destination=&expected_bytes;bit=64;}else if(!strcmp(a,"--expected-sha256")){destination=&expected_sha;bit=128;}else if(!strcmp(a,"--comparison-key")){destination=&comparison_key_path;bit=256;}else goto fail;
        if(seen_options&bit)goto fail;seen_options|=bit;
        if(++i==argc)goto fail;*destination=argv[i];
    }
    if(!mode)goto fail;
    if(!strcmp(mode,"--codec-selftest")){if(argc!=2||!codec_selftest())goto fail;puts("{\"status\":\"SYNTHETIC_CODEC_PASS\",\"controls\":4,\"real_lzfse_api\":true,\"host_queried\":false,\"writes_authorized\":false,\"native_ready\":false}");return 0;}
    char exe_input[PATH_MAX],executable[PATH_MAX];uint32_t capacity=sizeof(exe_input);if(_NSGetExecutablePath(exe_input,&capacity)||!realpath(exe_input,executable))goto fail;
    Profile profile={0};
    if(profile_path){if(!load_profile(profile_path,executable,&profile))goto fail;}
    else if(strcmp(mode,"--fixture"))goto fail;
    if(!strcmp(mode,"--generate-comparison-key")){if(seen_options!=1||!generate_key())goto fail;return 0;}
    ComparisonKey comparison={0};
    if(comparison_key_path&&!load_comparison_key(comparison_key_path,!strcmp(mode,"--snapshot-fixture")||!strcmp(mode,"--validate-fixture-snapshot"),&comparison))goto fail;
    const ComparisonKey *comparison_ptr=comparison.loaded?&comparison:NULL;
    if(!strcmp(mode,"--fixture")){uint8_t *data;size_t n;if(!read_file(input,FILE_LIMIT,true,&data,&n))goto fail;Identity id;bool ok=identify_object((Bytes){data,n},&id);free(data);if(!ok)goto fail;
        printf("{\"status\":\"OFFLINE_IDENTITY\",\"payload_identity\":\"%s\",\"payload_exact\":%s,\"framing\":\"%s\",\"codec\":\"%s\",\"raw_bytes\":%zu,\"selection_verified\":false,\"wrapper_authentication_verified\":false,\"restoration_verified\":false,\"read_only\":true,\"writes_authorized\":false,\"native_ready\":false}\n",id.identity,id.exact?"true":"false",id.framing,id.codec,id.raw_bytes);return 0;}
    if(!strcmp(mode,"--verify-file")){if(!expected_bytes||!valid_sha(expected_sha))goto fail;char *end;unsigned long long n=strtoull(expected_bytes,&end,10);if(*end||!n||n>FILE_LIMIT)goto fail;char canonical[32];snprintf(canonical,sizeof(canonical),"%llu",n);if(strcmp(canonical,expected_bytes))goto fail;
        bool allowed=(n==CANDIDATE_BYTES&&!strcmp(expected_sha,CANDIDATE_SHA256))||(n==ROLLBACK_BYTES&&!strcmp(expected_sha,ROLLBACK_SHA))||(n==profile.helper_bytes&&!strcmp(expected_sha,profile.helper_sha));if(!allowed)goto fail;
        uint8_t *data;size_t size;char hash[65];if(!read_file(input,FILE_LIMIT,false,&data,&size))goto fail;bool ok=size==n&&sha_hex(data,size,hash)&&!strcmp(hash,expected_sha);free(data);if(!ok)goto fail;puts("{\"status\":\"EXACT_PROFILE_FILE\",\"verified\":true,\"read_only\":true,\"writes_authorized\":false}");return 0;}
    if(!strcmp(mode,"--capability-check")){if(strcmp(input,"recovery-transaction-v2")||!recovery_admission()||!codec_selftest())goto fail;puts("{\"status\":\"RECOVERY_CAPABILITY_PASS\",\"snapshot\":true,\"private_metadata_comparison\":true,\"strict_phase_validation\":true,\"lzfse_streaming\":true,\"recovery_execution_admitted\":true,\"target_state_verified\":false,\"target_state_requires_snapshot\":true,\"read_only\":true,\"writes_authorized\":false,\"native_ready\":false}");return 0;}
    if(!strcmp(mode,"--snapshot")||!strcmp(mode,"--snapshot-fixture")||!strcmp(mode,"--target-group-private")){Snapshot state;char group[37];if(!strcmp(mode,"--target-group-private")&&!comparison_ptr)goto fail;if(!collect_snapshot(target,original,&profile,!strcmp(mode,"--snapshot-fixture")?input:NULL,comparison_ptr,&state,group))goto fail;
        if(!strcmp(mode,"--target-group-private")){if(state.synthetic)goto fail;printf("%s\n",group);return 0;}print_snapshot(&state);return 0;}
    if(!strcmp(mode,"--snapshot-value")){Snapshot state;if(!key||strcmp(key,"lab_ctrr")||!comparison_ptr||!parse_snapshot(input,&state,false)||state.synthetic||!state.metadata_bound||strcmp(state.comparison_key_id,comparison.id)||strcmp(state.profile_sha,profile.sha))goto fail;printf("%s\n",state.lab_ctrr);return 0;}
    if(!strcmp(mode,"--validate-snapshot")||!strcmp(mode,"--validate-fixture-snapshot")){Snapshot state,baseline;bool synthetic=!strcmp(mode,"--validate-fixture-snapshot");if(!phase||!parse_snapshot(input,&state,synthetic))goto fail;
        Snapshot *b=NULL;if(baseline_path){if(!parse_snapshot(baseline_path,&baseline,synthetic))goto fail;b=&baseline;}if(!validate_snapshot(&state,b,&profile,comparison_ptr,phase,synthetic))goto fail;
        printf("{\"status\":\"%s\",\"phase_valid\":%s,\"synthetic_control_pass\":%s,\"read_only\":true,\"writes_authorized\":false,\"native_ready\":false}\n",synthetic?"SYNTHETIC_PHASE_PASS":"EXPECTED_PHASE_PASS",synthetic?"false":"true",synthetic?"true":"false");return 0;}
fail:
    if(mode&&(!strcmp(mode,"--target-group-private")||!strcmp(mode,"--generate-comparison-key"))){fputs("REFUSED\n",stderr);return 2;}refused();return 2;
}
