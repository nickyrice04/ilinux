/* SPDX-License-Identifier: MIT */
#include "reader.h"
#include <sys/wait.h>
#include <sys/stat.h>
#include <sys/poll.h>
#include <signal.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <time.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <ctype.h>
#include <CommonCrypto/CommonHMAC.h>

const char *refusal_reason="preflightRefused";
static const char *semantic_keys[]={"smb0","smb1","smb2","smb3","smb4","sip0","sip1","sip3"};
typedef struct {char mode[16],ctrr[12],semantic[8][24],coih[129],nsih[129];bool paired,one_true;char rpnh[2][97],ronh[97],spih[97],stng[24];unsigned metadata_seen[4];} Policy;
typedef struct {CFDictionaryRef fixture;} Backend;
static uint64_t ms(void){struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))return 0;return (uint64_t)t.tv_sec*1000+(uint64_t)t.tv_nsec/1000000;}
static bool capture(const char *const argv[],size_t cap,uint8_t **out,size_t *length){
    int pipefd[2];*out=NULL;*length=0;if(pipe(pipefd))return false;
    for(int i=0;i<2;i++)fcntl(pipefd[i],F_SETFD,FD_CLOEXEC);
    pid_t child=fork();if(child<0){close(pipefd[0]);close(pipefd[1]);return false;}
    if(!child){int null=open("/dev/null",O_RDWR);if(null<0)_exit(126);dup2(null,0);dup2(pipefd[1],1);dup2(null,2);close(pipefd[0]);close(pipefd[1]);if(null>2)close(null);
        char *const env[]={"PATH=/usr/bin:/usr/sbin:/bin:/sbin","LANG=C","LC_ALL=C",NULL};execve(argv[0],(char *const *)argv,env);_exit(127);}
    close(pipefd[1]);fcntl(pipefd[0],F_SETFL,O_NONBLOCK);uint8_t *data=malloc(cap+1);size_t n=0;bool ok=false,eof=false;uint64_t deadline=ms()+20000;int status=0;
    if(!data)goto done;
    while(!eof&&ms()<deadline){struct pollfd poller={pipefd[0],POLLIN|POLLHUP,0};int p=poll(&poller,1,100);if(p<0&&errno==EINTR)continue;if(p<0)goto done;
        if(p){ssize_t got=read(pipefd[0],data+n,cap+1-n);if(got>0){n+=(size_t)got;if(n>cap)goto done;}else if(!got)eof=true;else if(errno!=EAGAIN&&errno!=EINTR)goto done;}}
    if(!eof)goto done;
    while(ms()<deadline){pid_t r=waitpid(child,&status,WNOHANG);if(r==child){child=-1;ok=WIFEXITED(status)&&WEXITSTATUS(status)==0;break;}if(r<0)goto done;struct timespec t={0,10000000};nanosleep(&t,NULL);}
done:if(child>0){kill(child,SIGKILL);while(waitpid(child,&status,0)<0&&errno==EINTR){}}
    close(pipefd[0]);if(ok){data[n]=0;*out=data;*length=n;}else free(data);return ok;
}
static CFTypeRef field(CFDictionaryRef d,const char *key){if(!d||CFGetTypeID(d)!=CFDictionaryGetTypeID())return NULL;CFStringRef k=CFStringCreateWithCString(NULL,key,kCFStringEncodingUTF8);if(!k)return NULL;CFTypeRef v=CFDictionaryGetValue(d,k);CFRelease(k);return v;}
static bool cstring(CFTypeRef v,char *out,size_t cap){return v&&CFGetTypeID(v)==CFStringGetTypeID()&&CFStringGetCString(v,out,(CFIndex)cap,kCFStringEncodingUTF8);}
static bool equals(CFTypeRef v,const char *s){char text[PATH_MAX];return cstring(v,text,sizeof(text))&&!strcmp(text,s);}
static CFPropertyListRef plist(Bytes data){CFDataRef b=CFDataCreate(NULL,data.p,(CFIndex)data.n);if(!b)return NULL;CFPropertyListRef p=CFPropertyListCreateWithData(NULL,b,kCFPropertyListImmutable,NULL,NULL);CFRelease(b);return p;}
static CFDictionaryRef disk(Backend *b,const char *which,const char *arg){
    if(b->fixture){CFTypeRef v=field(b->fixture,which);return v&&CFGetTypeID(v)==CFDictionaryGetTypeID()?CFRetain(v):NULL;}
    const char *argv[]={"/usr/sbin/diskutil","info","-plist",arg,NULL};uint8_t *data;size_t n;if(!capture(argv,METADATA_LIMIT,&data,&n))return NULL;CFPropertyListRef p=plist((Bytes){data,n});free(data);if(p&&CFGetTypeID(p)!=CFDictionaryGetTypeID()){CFRelease(p);p=NULL;}return (CFDictionaryRef)p;
}
static CFDictionaryRef apfs(Backend *b){if(b->fixture){CFTypeRef v=field(b->fixture,"apfs_list");return v&&CFGetTypeID(v)==CFDictionaryGetTypeID()?CFRetain(v):NULL;}const char *argv[]={"/usr/sbin/diskutil","apfs","list","-plist",NULL};uint8_t *data;size_t n;if(!capture(argv,METADATA_LIMIT,&data,&n))return NULL;CFPropertyListRef p=plist((Bytes){data,n});free(data);if(p&&CFGetTypeID(p)!=CFDictionaryGetTypeID()){CFRelease(p);p=NULL;}return (CFDictionaryRef)p;}
static bool uuid(const char *s){if(strlen(s)!=36)return false;for(size_t i=0;i<36;i++){bool dash=i==8||i==13||i==18||i==23;if(dash?s[i]!='-':!isxdigit((unsigned char)s[i]))return false;}return true;}
static bool device(const char *s,bool container){if(strncmp(s,"disk",4))return false;const char *p=s+4;if(!isdigit((unsigned char)*p))return false;while(isdigit((unsigned char)*p))p++;if(container)return !*p;if(*p++!='s'||!isdigit((unsigned char)*p))return false;while(isdigit((unsigned char)*p))p++;return !*p;}
static bool strings_equal(CFTypeRef a,CFTypeRef b){return a&&b&&CFGetTypeID(a)==CFStringGetTypeID()&&CFGetTypeID(b)==CFStringGetTypeID()&&CFStringCompare(a,b,kCFCompareCaseInsensitive)==kCFCompareEqualTo;}
static bool safe_path(const char *s){if(!s||s[0]!='/'||!s[1]||strlen(s)>=PATH_MAX)return false;const char *p=s+1;while(*p){const char *end=strchr(p,'/');size_t n=end?(size_t)(end-p):strlen(p);if(!n||(n==1&&p[0]=='.')||(n==2&&p[0]=='.'&&p[1]=='.'))return false;if(!end)return true;p=end+1;if(!*p)return false;}return false;}
static bool role(CFTypeRef v,const char *wanted){CFTypeRef r=field((CFDictionaryRef)v,"Roles");return r&&CFGetTypeID(r)==CFArrayGetTypeID()&&CFArrayGetCount(r)==1&&equals(CFArrayGetValueAtIndex(r,0),wanted);}
static CFDictionaryRef container_for(CFDictionaryRef list,const char *ref){CFTypeRef array=field(list,"Containers");if(!array||CFGetTypeID(array)!=CFArrayGetTypeID())return NULL;CFIndex n=CFArrayGetCount(array);if(n<1||n>128)return NULL;CFDictionaryRef result=NULL;for(CFIndex i=0;i<n;i++){CFTypeRef v=CFArrayGetValueAtIndex(array,i);if(CFGetTypeID(v)!=CFDictionaryGetTypeID())return NULL;if(equals(field(v,"ContainerReference"),ref)){if(result)return NULL;result=v;}}return result;}
static CFArrayRef volumes(CFDictionaryRef c){CFTypeRef v=field(c,"Volumes");if(!v||CFGetTypeID(v)!=CFArrayGetTypeID()||CFArrayGetCount(v)<1||CFArrayGetCount(v)>256)return NULL;
    for(CFIndex i=0;i<CFArrayGetCount(v);i++){CFTypeRef a=CFArrayGetValueAtIndex(v,i);char id[64],u[64];if(CFGetTypeID(a)!=CFDictionaryGetTypeID()||!cstring(field(a,"DeviceIdentifier"),id,sizeof(id))||!device(id,false)||!cstring(field(a,"APFSVolumeUUID"),u,sizeof(u))||!uuid(u))return NULL;
        for(CFIndex j=0;j<i;j++){CFTypeRef other=CFArrayGetValueAtIndex(v,j);if(strings_equal(field(a,"DeviceIdentifier"),field(other,"DeviceIdentifier"))||strings_equal(field(a,"APFSVolumeUUID"),field(other,"APFSVolumeUUID")))return NULL;}}
    return v;
}
static CFDictionaryRef volume_for(CFArrayRef vols,const char *r,const char *name){if(!vols)return NULL;CFDictionaryRef found=NULL;for(CFIndex i=0;i<CFArrayGetCount(vols);i++){CFTypeRef v=CFArrayGetValueAtIndex(vols,i);if(role(v,r)&&(!name||equals(field(v,"Name"),name))){if(found)return NULL;found=v;}}return found;}
static bool info_matches(CFDictionaryRef info,CFDictionaryRef entry,const char *container_ref){return info&&entry&&equals(field(info,"APFSContainerReference"),container_ref)&&strings_equal(field(info,"VolumeUUID"),field(entry,"APFSVolumeUUID"))&&strings_equal(field(info,"DeviceIdentifier"),field(entry,"DeviceIdentifier"))&&strings_equal(field(info,"VolumeName"),field(entry,"Name"));}
static char *trim(char *s){while(isspace((unsigned char)*s))s++;char *end=s+strlen(s);while(end>s&&isspace((unsigned char)end[-1]))*--end=0;return s;}
static bool value_string(const char *value,bool integer,char out[24]){
    if(!strcasecmp(value,"absent")){strcpy(out,"ABSENT");return true;}
    if(!integer){if(!strcmp(value,"1")||!strcasecmp(value,"true")){strcpy(out,"true");return true;}if(!strcmp(value,"0")||!strcasecmp(value,"false")){strcpy(out,"false");return true;}return false;}
    const char *p=value;if(!strncmp(p,"0x",2))p+=2;size_t n=strlen(p);if(!n||n>16)return false;uint64_t result=0;for(size_t i=0;i<n;i++){int c=(unsigned char)p[i],digit;if(c>='0'&&c<='9')digit=c-'0';else if(c>='a'&&c<='f')digit=c-'a'+10;else if(c>='A'&&c<='F')digit=c-'A'+10;else return false;result=(result<<4)|(unsigned)digit;}snprintf(out,24,"0x%016llx",(unsigned long long)result);return true;
}
static bool object_reference(const char *s,char out[129]){if(!strcasecmp(s,"absent")){out[0]=0;return true;}size_t n=strlen(s);if(n<32||n>128||n%2)return false;for(size_t i=0;i<n;i++)if(!isxdigit((unsigned char)s[i]))return false;strcpy(out,s);return true;}
static bool private_hash(const char *s,char out[97]){if(!strcasecmp(s,"absent")){strcpy(out,"ABSENT");return true;}if(strlen(s)!=96)return false;for(size_t i=0;i<96;i++){if(!isxdigit((unsigned char)s[i]))return false;out[i]=(char)tolower((unsigned char)s[i]);}out[96]=0;return true;}
static bool private_counter(const char *s,char out[24]){if(!strcasecmp(s,"absent")){strcpy(out,"ABSENT");return true;}size_t n=strlen(s);if(!n||n>20)return false;uint64_t v=0;for(size_t i=0;i<n;i++){if(s[i]<'0'||s[i]>'9')return false;unsigned d=(unsigned)(s[i]-'0');if(v>(UINT64_MAX-d)/10)return false;v=v*10+d;}snprintf(out,24,"%llu",(unsigned long long)v);return true;}
static bool policy_commitment(const Policy *policy,const Profile *profile,const ComparisonKey *key,const char *role,char out[65]){
    if(!key||!key->loaded)return false;
    /* All components are fixed labels or canonical bounded scalars; NUL separators
       and explicit count distinguish vector order/absence without retaining values. */
    CCHmacContext ctx;CCHmacInit(&ctx,kCCHmacAlgSHA256,key->bytes,sizeof(key->bytes));
    const char *parts[]={"ilinux31aj-private-policy-v2",profile->sha,role,"rpnh","2",policy->rpnh[0],policy->rpnh[1],"ronh","1",policy->ronh,"spih","1",policy->spih,"stng","1",policy->stng};
    for(size_t i=0;i<sizeof(parts)/sizeof(parts[0]);i++)CCHmacUpdate(&ctx,parts[i],strlen(parts[i])+1);
    uint8_t digest[32];CCHmacFinal(&ctx,digest);static const char h[]="0123456789abcdef";for(size_t i=0;i<32;i++){out[i*2]=h[digest[i]>>4];out[i*2+1]=h[digest[i]&15];}out[64]=0;return true;
}
static bool tag_list(const char *s){unsigned count=0;for(;;){while(isspace((unsigned char)*s))s++;for(unsigned i=0;i<4;i++)if(!isalnum((unsigned char)*s++))return false;if(isalnum((unsigned char)*s))return false;while(isspace((unsigned char)*s))s++;if(++count>4)return false;if(!*s)return true;if(*s++!=',')return false;if(!*s)return false;}}
static bool policy(Bytes bytes,Policy *out){
    if(!bytes.n||bytes.n>POLICY_LIMIT||memchr(bytes.p,0,bytes.n))return false;char *copy=malloc(bytes.n+1);if(!copy)return false;memcpy(copy,bytes.p,bytes.n);copy[bytes.n]=0;memset(out,0,sizeof(*out));strcpy(out->ctrr,"unknown");
    unsigned seen[8]={0},coih=0,nsih=0,sip2_seen=0,mode_seen=0,current_seen=0,old_seen=0,ctrr_seen=0;char sip2[24]="",current[80]="",old[80]="",ctrr[16]="";bool paired=false,unpaired=false,ok=false;
    char *save=NULL;for(char *line=strtok_r(copy,"\n",&save);line;line=strtok_r(NULL,"\n",&save)){
        if(strlen(line)>2048)goto done;char *text=trim(line),*open=strchr(text,'('),*close=open?strchr(open,')'):NULL,*colon=strchr(text,':');
        if(colon){char label[128];size_t count=(size_t)(colon-text);if(count<sizeof(label)){memcpy(label,text,count);label[count]=0;char *name=trim(label);char val[256];snprintf(val,sizeof(val),"%s",trim(colon+1));char *paren=strchr(val,'(');if(paren)*paren=0;char *v=trim(val);
            if(!strcasecmp(name,"Security Mode")){if(mode_seen++)goto done;if(!strcasecmp(v,"Full")||!strcasecmp(v,"Full Security"))strcpy(out->mode,"Full");else if(!strcasecmp(v,"Permissive")||!strcasecmp(v,"Permissive Security"))strcpy(out->mode,"Permissive");else if(!strcasecmp(v,"Reduced")||!strcasecmp(v,"Reduced Security"))strcpy(out->mode,"Reduced");else goto done;}
            else if(!strcasecmp(name,"Current OS environment")){if(current_seen++||strlen(v)>=sizeof(current))goto done;strcpy(current,v);}
            else if(!strcasecmp(name,"OS Type")){if(old_seen++||strlen(v)>=sizeof(old))goto done;strcpy(old,v);}
            else if(!strcasecmp(name,"Kernel CTRR Status")){if(ctrr_seen++||strlen(v)>=sizeof(ctrr))goto done;strcpy(ctrr,v);}
            if(!strcmp(v,"Paired"))paired=true;if(!strcmp(v,"Unpaired")||!strcmp(v,"Not Paired"))unpaired=true;}}
        if(!open||!close)continue;char tags[128];size_t length=(size_t)(close-open-1);if(!length||length>=sizeof(tags))goto done;memcpy(tags,open+1,length);tags[length]=0;
        char *after=trim(close+1);if(*after!=':')continue;after=trim(after+1);if(!tag_list(tags))goto done;char *ts=NULL;unsigned count=0;
        for(char *tag=strtok_r(tags,",",&ts);tag;tag=strtok_r(NULL,",",&ts)){tag=trim(tag);if(strlen(tag)!=4)goto done;if(++count>4)goto done;
            bool handled=false;for(unsigned i=0;i<8;i++)if(!strcmp(tag,semantic_keys[i])){if(seen[i]++||!value_string(after,i==5,out->semantic[i]))goto done;handled=true;break;}if(handled)continue;
            if(!strcmp(tag,"sip2")){if(sip2_seen++||!value_string(after,false,sip2))goto done;continue;}
            if(!strcmp(tag,"coih")){if(coih++||!object_reference(after,out->coih))goto done;continue;}if(!strcmp(tag,"nsih")){if(nsih++||!object_reference(after,out->nsih))goto done;continue;}
            if(!strcmp(tag,"rpnh")){unsigned at=out->metadata_seen[0]++;if(at>=2||!private_hash(after,out->rpnh[at]))goto done;continue;}
            if(!strcmp(tag,"ronh")){if(out->metadata_seen[1]++||!private_hash(after,out->ronh))goto done;continue;}
            if(!strcmp(tag,"spih")){if(out->metadata_seen[2]++||!private_hash(after,out->spih))goto done;continue;}
            if(!strcmp(tag,"stng")){if(out->metadata_seen[3]++||!private_counter(after,out->stng))goto done;continue;}
            const char *auth[]={"auxp","auxi","auxr","prot","hrlp","losv"};bool authkey=false;for(size_t i=0;i<6;i++)if(!strcmp(tag,auth[i]))authkey=true;
            if(authkey){if(strcasecmp(after,"absent")){refusal_reason="unsupportedPolicyMetadata";goto done;}continue;}
            const char *identity[]={"lpnh","vuid","kuid","BORD","CHIP","ECID"};bool known=false;for(size_t i=0;i<6;i++)if(!strcmp(tag,identity[i]))known=true;
            if(!known){refusal_reason="unsupportedPolicyMetadata";goto done;}
        }
    }
    /* bputil's Full/Reduced rows print SMB0 only; SMB1 is implicit absent. */
    if(!seen[1]&&(!strcmp(out->mode,"Full")||!strcmp(out->mode,"Reduced"))){strcpy(out->semantic[1],"ABSENT");seen[1]=1;}
    for(unsigned i=0;i<8;i++)if(seen[i]!=1)goto done;
    if(out->metadata_seen[0]!=2||out->metadata_seen[1]!=1||out->metadata_seen[2]!=1||out->metadata_seen[3]!=1)goto done;
    if(mode_seen!=1||coih!=1||nsih!=1||(!out->nsih[0]&&out->coih[0])||(paired&&unpaired))goto done;
    const char *env=current_seen?current:old;
    out->one_true=!strcasecmp(env,"one true recoveryOS");out->paired=paired&&!unpaired;
    if(ctrr_seen){if(!strcasecmp(ctrr,"Enabled")){if(sip2_seen&&strcmp(sip2,"ABSENT")&&strcmp(sip2,"false"))goto done;strcpy(out->ctrr,"enabled");}
        else if(!strcasecmp(ctrr,"Disabled")){if(!sip2_seen||strcmp(sip2,"true"))goto done;strcpy(out->ctrr,"disabled");}else goto done;}
    if(!strcmp(out->mode,"Full")&&(!strcmp(out->semantic[0],"true")||!strcmp(out->semantic[1],"true")))goto done;
    if(!strcmp(out->mode,"Permissive")&&(strcmp(out->semantic[0],"true")||strcmp(out->semantic[1],"true")))goto done;
    ok=true;
done:free(copy);return ok;
}
static bool policy_for(Backend *backend,const char *key,const char *group,Policy *out){
    uint8_t *data=NULL;size_t n=0;bool ok=false;
    if(backend->fixture){CFTypeRef v=field(backend->fixture,key);if(!v&&!strcmp(key,"lab_policy_after"))v=field(backend->fixture,"lab_policy");if(!v&&!strcmp(key,"original_policy_after"))v=field(backend->fixture,"original_policy");if(!v||CFGetTypeID(v)!=CFStringGetTypeID())return false;CFIndex need=CFStringGetMaximumSizeForEncoding(CFStringGetLength(v),kCFStringEncodingUTF8)+1;if(need<=0||(size_t)need>POLICY_LIMIT)return false;data=malloc((size_t)need);if(!data||!CFStringGetCString(v,(char *)data,need,kCFStringEncodingUTF8))goto done;n=strlen((char *)data);}
    else {const char *argv[]={"/usr/bin/bputil","-d","-v",group,NULL};if(!capture(argv,POLICY_LIMIT,&data,&n))return false;}
    ok=policy((Bytes){data,n},out);
done:free(data);return ok;
}
bool recovery_admission(void){struct stat s;if(geteuid()!=0||lstat("/System/Installation/CDIS",&s)||!S_ISDIR(s.st_mode))return false;const char *argv[]={"/usr/sbin/sysctl","-n","hw.model",NULL};uint8_t *data;size_t n;if(!capture(argv,64,&data,&n))return false;bool ok=n==8&&!memcmp(data,"Mac17,6\n",8);free(data);return ok;}

bool collect_snapshot(const char *target_path,const char *original_path,const Profile *profile,const char *fixture,const ComparisonKey *key,Snapshot *out,char private_group[37]){
    memset(out,0,sizeof(*out));private_group[0]=0;Backend b={0};uint8_t *data=NULL;size_t n=0;CFDictionaryRef lab=NULL,original=NULL,list=NULL,pbinfo=NULL,dinfo=NULL;bool ok=false;
    if(strcmp(target_path,LAB_VOLUME)||strncmp(original_path,"/Volumes/",9)||!safe_path(original_path)||!strcmp(original_path,target_path))return false;
    if(fixture){if(!read_file(fixture,METADATA_LIMIT,true,&data,&n))goto done;CFPropertyListRef f=plist((Bytes){data,n});free(data);data=NULL;if(!f||CFGetTypeID(f)!=CFDictionaryGetTypeID()){if(f)CFRelease(f);goto done;}b.fixture=f;
        if(field(f,"recovery")!=kCFBooleanTrue||field(f,"root")!=kCFBooleanTrue||!equals(field(f,"model"),"Mac17,6"))goto done;
    }else if(!recovery_admission()||!safe_directory(target_path)||!safe_directory(original_path))goto done;
    lab=disk(&b,"lab_info",target_path);original=disk(&b,"original_info",original_path);list=apfs(&b);
    char group[64],ogroup[64],ref[64],oref[64],u[64],ou[64];
    if(!lab||!original||!list||field(lab,"Internal")!=kCFBooleanTrue||field(original,"Internal")!=kCFBooleanTrue||!equals(field(lab,"VolumeName"),"iLinux Boot Lab")||!equals(field(lab,"MountPoint"),target_path)||!equals(field(original,"VolumeName"),ORIGINAL_NAME)||!equals(field(original,"MountPoint"),original_path)||!cstring(field(lab,"APFSVolumeGroupID"),group,sizeof(group))||!uuid(group)||!cstring(field(original,"APFSVolumeGroupID"),ogroup,sizeof(ogroup))||!uuid(ogroup)||!strcasecmp(group,ogroup)||!cstring(field(lab,"VolumeUUID"),u,sizeof(u))||!uuid(u)||!cstring(field(original,"VolumeUUID"),ou,sizeof(ou))||!uuid(ou)||!strcasecmp(u,ou)||!cstring(field(lab,"APFSContainerReference"),ref,sizeof(ref))||!device(ref,true)||!cstring(field(original,"APFSContainerReference"),oref,sizeof(oref))||!device(oref,true))goto done;
    if(strcmp(ref,oref))goto done;
    CFArrayRef lv=volumes(container_for(list,ref)),ov=volumes(container_for(list,oref));
    CFDictionaryRef lsystem=volume_for(lv,"System","iLinux Boot Lab"),osystem=volume_for(ov,"System",ORIGINAL_NAME),preboot=volume_for(lv,"Preboot",NULL),lData=volume_for(lv,"Data",LAB_DATA_NAME);
    if(!info_matches(lab,lsystem,ref)||!info_matches(original,osystem,oref)||!preboot||!lData)goto done;
    char pbdev[64],datadev[64];if(!cstring(field(preboot,"DeviceIdentifier"),pbdev,sizeof(pbdev))||!cstring(field(lData,"DeviceIdentifier"),datadev,sizeof(datadev)))goto done;
    pbinfo=disk(&b,"preboot_info",pbdev);dinfo=disk(&b,"data_info",datadev);
    char mount[PATH_MAX],dgroup[64],dmount[PATH_MAX];
    if(!info_matches(pbinfo,preboot,ref)||!info_matches(dinfo,lData,ref)||field(pbinfo,"Internal")!=kCFBooleanTrue||field(dinfo,"Internal")!=kCFBooleanTrue||!cstring(field(dinfo,"APFSVolumeGroupID"),dgroup,sizeof(dgroup))||strcasecmp(dgroup,group)||!cstring(field(pbinfo,"MountPoint"),mount,sizeof(mount))||!cstring(field(dinfo,"MountPoint"),dmount,sizeof(dmount))||!safe_path(mount)||!safe_path(dmount)||strcmp(dmount,LAB_DATA_MOUNT)||!strcmp(mount,target_path)||!strcmp(mount,original_path)||!strcmp(mount,dmount))goto done;
    if(!b.fixture&&(!safe_directory(mount)||!safe_directory(dmount)))goto done;
    Policy lp,op;if(!policy_for(&b,"lab_policy",group,&lp)||!policy_for(&b,"original_policy",ogroup,&op)||!lp.one_true||!lp.paired||strcmp(lp.mode,"Permissive")||strcmp(op.mode,"Full")||strcmp(op.ctrr,"enabled"))goto done;
    strcpy(out->selected,"NONE");out->selected_exact=false;
    if(lp.coih[0]){char selected[PATH_MAX];int length=snprintf(selected,sizeof(selected),"%s/%s/boot/%s/System/Library/Caches/com.apple.kernelcaches/kernelcache.custom.%s",mount,group,lp.nsih,lp.coih);if(length<0||(size_t)length>=sizeof(selected))goto done;
        bool read_ok;if(b.fixture){char fixture_file[PATH_MAX];if(!cstring(field(b.fixture,"selected_file"),fixture_file,sizeof(fixture_file)))goto done;read_ok=read_file(fixture_file,FILE_LIMIT,true,&data,&n);}else read_ok=read_file(selected,FILE_LIMIT,false,&data,&n);
        Identity id;if(read_ok&&identify_object((Bytes){data,n},&id)&&strcmp(id.identity,"31AI")){strcpy(out->selected,id.identity);out->selected_exact=id.exact;}else strcpy(out->selected,"UNKNOWN");free(data);data=NULL;
    }
    Policy la,oa;if(!policy_for(&b,"lab_policy_after",group,&la)||!policy_for(&b,"original_policy_after",ogroup,&oa)||memcmp(&lp,&la,sizeof(lp))||memcmp(&op,&oa,sizeof(op)))goto done;
    out->synthetic=b.fixture!=NULL;out->guarded=true;out->paired=true;out->original_full=true;out->lab_permissive=true;out->policy_complete=true;strcpy(out->profile_sha,profile->sha);strcpy(out->lab_ctrr,lp.ctrr);memcpy(out->original_semantics,op.semantic,sizeof(op.semantic));memcpy(out->lab_semantics,lp.semantic,sizeof(lp.semantic));
    out->metadata_bound=key&&key->loaded;
    if(out->metadata_bound){strcpy(out->comparison_key_id,key->id);if(!policy_commitment(&lp,profile,key,"LAB",out->lab_metadata_hmac)||!policy_commitment(&op,profile,key,"ORIGINAL",out->original_metadata_hmac))goto done;}
    else{strcpy(out->comparison_key_id,"NONE");strcpy(out->lab_metadata_hmac,"NONE");strcpy(out->original_metadata_hmac,"NONE");}
    strcpy(private_group,group);ok=true;
done:free(data);if(lab)CFRelease(lab);if(original)CFRelease(original);if(list)CFRelease(list);if(pbinfo)CFRelease(pbinfo);if(dinfo)CFRelease(dinfo);if(b.fixture)CFRelease(b.fixture);return ok;
}

static void print_semantics(const char values[8][24]){putchar('{');for(unsigned i=0;i<8;i++){if(i)putchar(',');printf("\"%s\":",semantic_keys[i]);if(!strcmp(values[i],"true")||!strcmp(values[i],"false"))printf("%s",values[i]);else printf("\"%s\"",values[i]);}putchar('}');}
void print_snapshot(const Snapshot *s){
    printf("{\"schema\":\"ilinux31aj-native-snapshot-v2\",\"scope\":\"%s\",\"profile_sha256\":\"%s\",\"target_binding_verified\":true,\"lab_data_bound\":true,\"paired_1tr\":true,\"original_security\":\"Full\",\"original_ctrr\":\"enabled\",\"lab_security\":\"Permissive\",\"lab_ctrr\":\"%s\",\"selected_payload\":\"%s\",\"selected_payload_exact\":%s,\"policy_schema_complete\":true,\"original_semantics\":",s->synthetic?"SYNTHETIC_CONTROL":"RECOVERY_GUARDED_READ",s->profile_sha,s->lab_ctrr,s->selected,s->selected_exact?"true":"false");
    print_semantics(s->original_semantics);printf(",\"lab_semantics\":");print_semantics(s->lab_semantics);printf(",\"metadata_bound\":%s,\"comparison_key_id\":\"%s\",\"lab_metadata_hmac\":\"%s\",\"original_metadata_hmac\":\"%s\",\"wrapper_authentication_verified\":false,\"default_selection_verified\":false,\"restoration_verified\":false,\"writes_authorized\":false,\"read_only\":true}\n",s->metadata_bound?"true":"false",s->comparison_key_id,s->lab_metadata_hmac,s->original_metadata_hmac);
}
static bool node_bool(const Json *j,int object,const char *key,bool expected){int n=json_get(j,object,key);return n>=0&&j->nodes[n].type==(expected?J_TRUE:J_FALSE);}
static bool parse_semantics(const Json *j,int node,char values[8][24]){if(!json_keys(j,node,semantic_keys,8))return false;for(unsigned i=0;i<8;i++){int n=json_get(j,node,semantic_keys[i]);if(j->nodes[n].type==J_TRUE)strcpy(values[i],"true");else if(j->nodes[n].type==J_FALSE)strcpy(values[i],"false");else if(j->nodes[n].type==J_STRING){const char *s=j->nodes[n].value;if(!strcmp(s,"ABSENT"))strcpy(values[i],s);else if(i==5&&strlen(s)==18&&!strncmp(s,"0x",2)){char canonical[24];if(!value_string(s,true,canonical)||strcmp(s,canonical))return false;strcpy(values[i],canonical);}else return false;}else return false;if(i==5&&strcmp(values[i],"ABSENT")&&strncmp(values[i],"0x",2))return false;}return true;}
bool parse_snapshot(const char *path,Snapshot *out,bool workspace_only){
    uint8_t *data;size_t n;if(!read_file(path,65536,workspace_only,&data,&n))return false;Json j;bool ok=false;memset(out,0,sizeof(*out));if(!json_parse((Bytes){data,n},&j))goto done;
    const char *keys[]={"schema","scope","profile_sha256","target_binding_verified","lab_data_bound","paired_1tr","original_security","original_ctrr","lab_security","lab_ctrr","selected_payload","selected_payload_exact","policy_schema_complete","original_semantics","lab_semantics","metadata_bound","comparison_key_id","lab_metadata_hmac","original_metadata_hmac","wrapper_authentication_verified","default_selection_verified","restoration_verified","writes_authorized","read_only"};
    if(!json_keys(&j,0,keys,24)||!json_string(&j,json_get(&j,0,"schema"),"ilinux31aj-native-snapshot-v2")||!node_bool(&j,0,"target_binding_verified",true)||!node_bool(&j,0,"lab_data_bound",true)||!node_bool(&j,0,"paired_1tr",true)||!node_bool(&j,0,"policy_schema_complete",true)||!node_bool(&j,0,"read_only",true)||!node_bool(&j,0,"wrapper_authentication_verified",false)||!node_bool(&j,0,"default_selection_verified",false)||!node_bool(&j,0,"restoration_verified",false)||!node_bool(&j,0,"writes_authorized",false)||!json_string(&j,json_get(&j,0,"original_security"),"Full")||!json_string(&j,json_get(&j,0,"original_ctrr"),"enabled")||!json_string(&j,json_get(&j,0,"lab_security"),"Permissive"))goto done;
    out->metadata_bound=node_bool(&j,0,"metadata_bound",true);if(!out->metadata_bound&&!node_bool(&j,0,"metadata_bound",false))goto done;
    const char *boundkeys[]={"comparison_key_id","lab_metadata_hmac","original_metadata_hmac"};char *boundout[]={out->comparison_key_id,out->lab_metadata_hmac,out->original_metadata_hmac};
    for(unsigned i=0;i<3;i++){int node=json_get(&j,0,boundkeys[i]);if(j.nodes[node].type!=J_STRING||(out->metadata_bound?!valid_sha(j.nodes[node].value):strcmp(j.nodes[node].value,"NONE")))goto done;strcpy(boundout[i],j.nodes[node].value);}
    if(json_string(&j,json_get(&j,0,"scope"),"SYNTHETIC_CONTROL"))out->synthetic=true;else if(!json_string(&j,json_get(&j,0,"scope"),"RECOVERY_GUARDED_READ"))goto done;
    int hash=json_get(&j,0,"profile_sha256"),ctrr=json_get(&j,0,"lab_ctrr"),selected=json_get(&j,0,"selected_payload");if(j.nodes[hash].type!=J_STRING||!valid_sha(j.nodes[hash].value)||j.nodes[ctrr].type!=J_STRING||j.nodes[selected].type!=J_STRING)goto done;
    const char *c=j.nodes[ctrr].value,*s=j.nodes[selected].value;if(strcmp(c,"enabled")&&strcmp(c,"disabled")&&strcmp(c,"unknown"))goto done;if(strcmp(s,"31AF")&&strcmp(s,"CANDIDATE")&&strcmp(s,"BOOT021")&&strcmp(s,"NONE")&&strcmp(s,"UNKNOWN"))goto done;
    out->selected_exact=node_bool(&j,0,"selected_payload_exact",true);if(!out->selected_exact&&!node_bool(&j,0,"selected_payload_exact",false))goto done;if((!strcmp(s,"NONE")||!strcmp(s,"UNKNOWN"))==out->selected_exact)goto done;
    if(!parse_semantics(&j,json_get(&j,0,"original_semantics"),out->original_semantics)||!parse_semantics(&j,json_get(&j,0,"lab_semantics"),out->lab_semantics))goto done;
    if(!strcmp(out->original_semantics[0],"true")||!strcmp(out->original_semantics[1],"true")||strcmp(out->lab_semantics[0],"true")||strcmp(out->lab_semantics[1],"true"))goto done;
    strcpy(out->profile_sha,j.nodes[hash].value);strcpy(out->lab_ctrr,c);strcpy(out->selected,s);out->guarded=out->paired=out->original_full=out->lab_permissive=out->policy_complete=true;ok=true;
done:free(data);return ok;
}
bool validate_snapshot(const Snapshot *s,const Snapshot *base,const Profile *p,const ComparisonKey *key,const char *phase,bool synthetic){
    if(s->synthetic!=synthetic||!s->guarded||!s->paired||!s->original_full||!s->lab_permissive||!s->policy_complete||strcmp(s->profile_sha,p->sha))return false;
    if(!strcmp(phase,"initial-admission"))return !base&&!key&&!s->metadata_bound&&s->selected_exact&&!strcmp(s->selected,"31AF");
    if(!key||!key->loaded||!s->metadata_bound||strcmp(s->comparison_key_id,key->id))return false;
    if(!strcmp(phase,"initial"))return !base&&s->selected_exact&&!strcmp(s->selected,"31AF");
    if(!base||!validate_snapshot(base,NULL,p,key,"initial",synthetic)||memcmp(s->original_semantics,base->original_semantics,sizeof(s->original_semantics))||memcmp(s->lab_semantics,base->lab_semantics,sizeof(s->lab_semantics))||strcmp(s->lab_metadata_hmac,base->lab_metadata_hmac)||strcmp(s->original_metadata_hmac,base->original_metadata_hmac))return false;
    if(!strcmp(phase,"candidate"))return s->selected_exact&&!strcmp(s->selected,"CANDIDATE")&&!strcmp(s->lab_ctrr,"enabled");
    if(!strcmp(phase,"before-restore"))return true;
    if(!strcmp(phase,"raw-policy"))return !strcmp(s->lab_ctrr,"disabled");
    if(!strcmp(phase,"restored"))return s->selected_exact&&!strcmp(s->selected,"BOOT021")&&!strcmp(s->lab_ctrr,"disabled");
    return false;
}
