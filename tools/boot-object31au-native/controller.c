/* SPDX-License-Identifier: MIT */
/* Original fixed-operation controller. The qualified collector is included so
 * its private APFS/CF primitives are reused, not duplicated or weakened. */
#include "reader.h"
#include "read_diagnostics.h"
#include <unistd.h>
#include <errno.h>
static bool ar_fixture_execution_disabled;
static int ar_observer_execve(const char *path,char *const argv[],char *const env[]){
 if(ar_fixture_execution_disabled){errno=EPERM;return -1;}return execve(path,argv,env);
}
/* A second, independent fixture boundary: even a future mistaken NULL backend
 * cannot execute any observer command in a synthetic transaction. */
#define execve ar_observer_execve
#include "state.c"
#undef execve
#include <mach-o/dyld.h>
#include <sys/mount.h>
#include <sys/file.h>
#include <sys/acl.h>
#include <termios.h>

#define STATE_PARENT LAB_DATA_MOUNT "/private/var/db"
#define STATE_NAME "ilinux31au-state"
#define ORIGINAL_VOLUME "/Volumes/Macintosh HD"

typedef struct {
 char group[37],original_group[37],lab[37],original[37],data[37],preboot[37],container[37];
 char reference[64],pbdev[64],datadev[64],mount[PATH_MAX];bool mounted,readonly;
} Target;
typedef struct {
 bool available,preservation,selected,ctrr,passed,ctrr_enabled,ctrr_disabled,ctrr_unknown,comparison_available,selection_changed;
 const char *phase;ObjectRead31AU read;
} Diagnostic31AU;
typedef struct {
 bool synthetic,install,owned,mount_uncertain,child_created,cleanup_verified;
 bool attempted,candidate_verified,rollback_verified,state_preserved;
 int work_fd,child_fd,parent_fd,state_fd,lock_fd,mount_mode,writer_exit;
 struct stat work_stat,child_stat,state_stat,parent_stat;
 char scratch[PATH_MAX],mount[PATH_MAX],state_path[PATH_MAX],parent_path[PATH_MAX];
 char fixture_path[PATH_MAX];CFDictionaryRef fixture,phase_fixture;
 const char *phase,*stage,*reason;Profile profile;ComparisonKey key;
 Target target;Snapshot baseline;unsigned writes;bool enrolled;Diagnostic31AU diagnostic;
 bool selection_before_available;char selection_before[65];
} Transaction;
static volatile sig_atomic_t stop_requested;
static void stop_handler(int sig){(void)sig;stop_requested=1;}
static bool refused_at(Transaction *t,const char *stage,const char *reason){t->stage=stage;t->reason=reason;return false;}
static bool same_inode_ar(const struct stat *a,const struct stat *b){return a->st_dev==b->st_dev&&a->st_ino==b->st_ino;}
static bool no_acl(int fd){
 acl_t acl=acl_get_fd_np(fd,ACL_TYPE_EXTENDED);if(!acl)return errno==ENOENT;
 if(acl_valid(acl)){acl_free(acl);return false;}
 acl_entry_t entry=NULL;errno=0;int count=acl_get_entry(acl,ACL_FIRST_ENTRY,&entry),error=errno;
 bool ok=count==-1&&error==EINVAL&&!entry;return !acl_free(acl)&&ok;
}
static int ar_secure_open(const char *path,bool directory){
 if(!safe_path(path))return -1;char copy[PATH_MAX];strcpy(copy,path);
 int fd=open("/",O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW);if(fd<0)return -1;
 char *save=NULL,*part=strtok_r(copy+1,"/",&save);
 while(part){char *next=strtok_r(NULL,"/",&save);int flags=O_RDONLY|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK;
  if(next||directory)flags|=O_DIRECTORY;int child=openat(fd,part,flags);close(fd);if(child<0)return -1;fd=child;part=next;}
 return fd;
}
static bool private_fd(int fd,bool directory){
 struct stat s;if(fstat(fd,&s)||s.st_uid!=geteuid()||(s.st_mode&07777)!=(directory?0700:0600)||
    (directory?!S_ISDIR(s.st_mode):!S_ISREG(s.st_mode)||s.st_nlink!=1))return false;
 return no_acl(fd);
}
static bool path_join(char out[PATH_MAX],const char *base,const char *name){return snprintf(out,PATH_MAX,"%s/%s",base,name)<PATH_MAX;}
static bool workspace(const char *p){size_t n=strlen(WORKSPACE_ROOT);return safe_path(p)&&!strncmp(p,WORKSPACE_ROOT,n)&&p[n]=='/';}
static bool option_bool(Transaction *t,const char *key,bool fallback){
 if(!t->synthetic)return fallback;CFTypeRef v=field(t->fixture,key);if(!v)return fallback;return v==kCFBooleanTrue;
}
static bool failpoint(Transaction *t,const char *name){return t->synthetic&&equals(field(t->fixture,"failpoint"),name);}
static int option_exit(Transaction *t,const char *key){
 if(!t->synthetic)return -1;CFTypeRef v=field(t->fixture,key);int n=0;
 if(v&&(CFGetTypeID(v)!=CFNumberGetTypeID()||!CFNumberGetValue(v,kCFNumberIntType,&n)||n<0||n>255))return 255;return n;
}
static bool stable_directory(const char *path,int held,const struct stat *original,bool private){
 int fd=ar_secure_open(path,true);if(fd<0)return false;struct stat a,b;
 bool ok=!fstat(fd,&a)&&!fstat(held,&b)&&same_inode_ar(&a,&b)&&same_inode_ar(&a,original)&&(!private||private_fd(fd,true));close(fd);return ok;
}
static bool work_binding(Transaction *t){
 struct stat cwd;return stable_directory(t->scratch,t->work_fd,&t->work_stat,true)&&
 !fstatat(AT_FDCWD,".",&cwd,AT_SYMLINK_NOFOLLOW)&&same_inode_ar(&cwd,&t->work_stat);
}
static bool state_binding(Transaction *t){
 return t->state_fd>=0&&stable_directory(t->parent_path,t->parent_fd,&t->parent_stat,false)&&
 stable_directory(t->state_path,t->state_fd,&t->state_stat,true);
}
static bool trusted_parent(int fd){struct stat s;return !fstat(fd,&s)&&S_ISDIR(s.st_mode)&&s.st_uid==geteuid()&&!(s.st_mode&0022)&&no_acl(fd);}
static bool sync_file(Transaction *t,int fd,const char *point){
 if(failpoint(t,point)||fsync(fd))return false;
 return !fcntl(fd,F_FULLFSYNC);
}
static bool sync_dir(Transaction *t,int fd,const char *point){return !failpoint(t,point)&&fsync(fd)==0;}
static bool write_all(int fd,const uint8_t *data,size_t n){while(n){ssize_t got=write(fd,data,n);if(got<0&&errno==EINTR)continue;if(got<=0)return false;data+=got;n-=(size_t)got;}return true;}
/* Never overwrite: an incomplete file remains present and spends its name. */
static bool persist(Transaction *t,const char *name,const void *data,size_t n,const char *point){
 if(!state_binding(t)||!work_binding(t))return false;
 int fd=openat(t->state_fd,name,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);if(fd<0)return false;
 bool ok=private_fd(fd,false)&&write_all(fd,data,n)&&sync_file(t,fd,point);close(fd);
 return ok&&sync_dir(t,t->state_fd,point)&&state_binding(t);
}
static bool read_state(Transaction *t,const char *name,size_t limit,uint8_t **bytes,size_t *n){
 *bytes=NULL;*n=0;if(!state_binding(t))return false;
 int fd=openat(t->state_fd,name,O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);if(fd<0)return false;
 struct stat before,after;bool ok=false;uint8_t *data=NULL;
 if(!private_fd(fd,false)||fstat(fd,&before)||before.st_size<=0||(uint64_t)before.st_size>limit)goto done;
 data=malloc((size_t)before.st_size+1);if(!data)goto done;size_t used=0;
 while(used<(size_t)before.st_size){ssize_t got=read(fd,data+used,(size_t)before.st_size-used);if(got<0&&errno==EINTR)continue;if(got<=0)goto done;used+=(size_t)got;}
 uint8_t extra;if(read(fd,&extra,1)!=0||fstat(fd,&after)||memcmp(&before.st_mtimespec,&after.st_mtimespec,sizeof(before.st_mtimespec))||
 memcmp(&before.st_ctimespec,&after.st_ctimespec,sizeof(before.st_ctimespec))||!same_inode_ar(&before,&after)||before.st_size!=after.st_size||!private_fd(fd,false)||!state_binding(t))goto done;
 data[used]=0;*bytes=data;*n=used;data=NULL;ok=true;
done:free(data);close(fd);return ok;
}
static bool file_matches(const char *path,size_t bytes,const char *wanted){
 uint8_t *p=NULL;size_t n=0;char got[65];if(!read_file(path,FILE_LIMIT,false,&p,&n))return false;
 bool ok=n==bytes&&sha_hex(p,n,got)&&!strcmp(got,wanted);free(p);return ok;
}
static bool phase(Transaction *t,const char *name){
 t->phase=name;if(t->phase_fixture){CFRelease(t->phase_fixture);t->phase_fixture=NULL;}
 if(!t->synthetic)return true;
 CFDictionaryRef phases=(CFDictionaryRef)field(t->fixture,"phases");char path[PATH_MAX];
 if(!phases||CFGetTypeID(phases)!=CFDictionaryGetTypeID()||!cstring(field(phases,name),path,sizeof(path))||!workspace(path))return false;
 uint8_t *bytes=NULL;size_t n;if(!read_file(path,METADATA_LIMIT,true,&bytes,&n))return false;
 CFPropertyListRef p=plist((Bytes){bytes,n});free(bytes);
 if(!p||CFGetTypeID(p)!=CFDictionaryGetTypeID()){if(p)CFRelease(p);return false;}
 t->phase_fixture=p;strcpy(t->fixture_path,path);return true;
}
static bool source_device_ar(const char *source,char out[80]){
 const char *p=strrchr(source,'@');p=p?p+1:source;if(!strncmp(p,"/dev/",5))p+=5;
 if(*p=='r')p++;if(strncmp(p,"disk",4)||strlen(p)>=80)return false;const char *q=p+4;
 if(!isdigit((unsigned char)*q))return false;while(isdigit((unsigned char)*q))q++;
 unsigned slices=0;while(*q){if(*q++!='s'||!isdigit((unsigned char)*q)||++slices>3)return false;while(isdigit((unsigned char)*q))q++;}
 if(!slices)return false;strcpy(out,p);return true;
}
static int mounted_source(Transaction *t,const char *wanted,char out[PATH_MAX],bool *ro){
 if(t->synthetic){
  if(failpoint(t,"kernel_mount_state"))return -1;
  if(t->mount_mode){strcpy(out,t->mount);*ro=t->mount_mode==1;return 1;}
  if(option_bool(t,"foreign_mount",false)){strcpy(out,"/Volumes/ForeignPreboot");*ro=option_bool(t,"foreign_read_only",false);return 1;}
  out[0]=0;*ro=false;return 0;
 }
 int count=getfsstat(NULL,0,MNT_NOWAIT);if(count<1||count>1024)return -1;
 int cap=count+8;struct statfs *table=calloc((size_t)cap,sizeof(*table));if(!table)return -1;
 int n=getfsstat(table,(int)((size_t)cap*sizeof(*table)),MNT_NOWAIT),found=0;bool unknown=false;
 if(n<1||n>=cap){free(table);return -1;}
 for(int i=0;i<n;i++)if(!strcmp(table[i].f_fstypename,"apfs")){
  char source[80];if(!source_device_ar(table[i].f_mntfromname,source)){unknown=true;continue;}
  if(!strcmp(source,wanted)){if(++found>1){free(table);return -1;}if(strlen(table[i].f_mntonname)>=PATH_MAX){free(table);return -1;}
   strcpy(out,table[i].f_mntonname);*ro=(table[i].f_flags&MNT_RDONLY)!=0;}
 }
 free(table);return unknown?-1:found;
}
static bool target_metadata(Transaction *t,Target *out){
 if(t->synthetic&&!t->phase_fixture)return false;
 memset(out,0,sizeof(*out));Backend b={.fixture=t->phase_fixture};
 CFDictionaryRef lab=disk(&b,"lab_info",LAB_VOLUME),original=disk(&b,"original_info",ORIGINAL_VOLUME),list=apfs(&b),pb=NULL,data=NULL;bool ok=false;
 char reference[64],oref[64],data_group[37],dmount[PATH_MAX];
 if(!lab||!original||!list||field(lab,"Internal")!=kCFBooleanTrue||field(original,"Internal")!=kCFBooleanTrue||
    !equals(field(lab,"VolumeName"),"iLinux Boot Lab")||!equals(field(original,"VolumeName"),ORIGINAL_NAME)||
    !equals(field(lab,"MountPoint"),LAB_VOLUME)||!equals(field(original,"MountPoint"),ORIGINAL_VOLUME)||
    !cstring(field(lab,"APFSVolumeGroupID"),out->group,sizeof(out->group))||!uuid(out->group)||
    !cstring(field(original,"APFSVolumeGroupID"),out->original_group,sizeof(out->original_group))||!uuid(out->original_group)||
    !strcasecmp(out->group,out->original_group)||!cstring(field(lab,"APFSContainerReference"),reference,sizeof(reference))||!device(reference,true)||
    !cstring(field(original,"APFSContainerReference"),oref,sizeof(oref))||strcmp(reference,oref))goto done;
 CFDictionaryRef container=container_for(list,reference);CFArrayRef vols=volumes(container);
 CFDictionaryRef ls=volume_for(vols,"System","iLinux Boot Lab"),os=volume_for(vols,"System",ORIGINAL_NAME),p=volume_for(vols,"Preboot",NULL),d=volume_for(vols,"Data",LAB_DATA_NAME);
 if(!info_matches(lab,ls,reference)||!info_matches(original,os,reference)||!p||!d||
    !cstring(field(container,"APFSContainerUUID"),out->container,sizeof(out->container))||!uuid(out->container)||
    !cstring(field(p,"DeviceIdentifier"),out->pbdev,sizeof(out->pbdev))||!device(out->pbdev,false)||
    !cstring(field(d,"DeviceIdentifier"),out->datadev,sizeof(out->datadev))||!device(out->datadev,false))goto done;
 pb=disk(&b,"preboot_info",out->pbdev);data=disk(&b,"data_info",out->datadev);
 if(!info_matches(pb,p,reference)||!info_matches(data,d,reference)||field(pb,"Internal")!=kCFBooleanTrue||field(data,"Internal")!=kCFBooleanTrue||
    !cstring(field(lab,"VolumeUUID"),out->lab,sizeof(out->lab))||!uuid(out->lab)||
    !cstring(field(original,"VolumeUUID"),out->original,sizeof(out->original))||!uuid(out->original)||!strcasecmp(out->lab,out->original)||
    !cstring(field(pb,"VolumeUUID"),out->preboot,sizeof(out->preboot))||!uuid(out->preboot)||
    !cstring(field(data,"VolumeUUID"),out->data,sizeof(out->data))||!uuid(out->data)||
    !cstring(field(data,"APFSVolumeGroupID"),data_group,sizeof(data_group))||strcasecmp(data_group,out->group)||
    !cstring(field(data,"MountPoint"),dmount,sizeof(dmount))||strcmp(dmount,LAB_DATA_MOUNT))goto done;
 strcpy(out->reference,reference);int mounted=mounted_source(t,out->pbdev,out->mount,&out->readonly);if(mounted<0)goto done;
 out->mounted=mounted==1;
 if(!t->synthetic){char reported[PATH_MAX];if(!cstring(field(pb,"MountPoint"),reported,sizeof(reported))||strcmp(reported,out->mount))goto done;
  CFTypeRef bit=field(pb,"Mounted");if(bit&&bit!=(out->mounted?kCFBooleanTrue:kCFBooleanFalse))goto done;
  if(!safe_directory(dmount))goto done;
 }
 ok=true;
done:if(lab)CFRelease(lab);if(original)CFRelease(original);if(list)CFRelease(list);if(pb)CFRelease(pb);if(data)CFRelease(data);return ok;
}
static bool same_target(const Target *a,const Target *b){
 Target x=*a,y=*b;memset(x.mount,0,sizeof(x.mount));memset(y.mount,0,sizeof(y.mount));x.mounted=x.readonly=y.mounted=y.readonly=false;
 return !memcmp(&x,&y,sizeof(x));
}
static bool identity_commitment(Transaction *t,const Target *target,char out[65]){
 if(!t->key.loaded)return false;CCHmacContext ctx;CCHmacInit(&ctx,kCCHmacAlgSHA256,t->key.bytes,32);
 const char *parts[]={"ilinux31au-target-identity-v1",t->profile.sha,"LAB_GROUP",target->group,"ORIGINAL_GROUP",target->original_group,
  "LAB_SYSTEM",target->lab,"ORIGINAL_SYSTEM",target->original,"LAB_DATA",target->data,"PREBOOT",target->preboot,"CONTAINER",target->container};
 for(size_t i=0;i<sizeof(parts)/sizeof(parts[0]);i++){char normalized[128];if(strlen(parts[i])>=sizeof(normalized))return false;
  strcpy(normalized,parts[i]);if(i>=3&&i%2==1)for(char *p=normalized;*p;p++)*p=(char)tolower((unsigned char)*p);
  CCHmacUpdate(&ctx,normalized,strlen(normalized)+1);}
 uint8_t digest[32];CCHmacFinal(&ctx,digest);static const char h[]="0123456789abcdef";
 for(unsigned i=0;i<32;i++){out[i*2]=h[digest[i]>>4];out[i*2+1]=h[digest[i]&15];}out[64]=0;return true;
}
static bool underlying_child_ar(Transaction *t){
 struct stat named,held;return t->child_created&&t->child_fd>=0&&work_binding(t)&&!fstat(t->child_fd,&held)&&
 !fstatat(t->work_fd,"preboot",&named,AT_SYMLINK_NOFOLLOW)&&same_inode_ar(&named,&t->child_stat)&&same_inode_ar(&held,&t->child_stat);
}
static bool mount_binding_ar(Transaction *t,const Target *current,bool ro){
 if(!work_binding(t)||!current->mounted||strcmp(current->mount,t->mount)||current->readonly!=ro)return false;
 if(t->synthetic)return !failpoint(t,"mount_binding")&&!failpoint(t,ro?"ro_mount_binding":"rw_mount_binding");
 int fd=openat(t->work_fd,"preboot",O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW);if(fd<0)return false;
 struct statfs fs;struct stat held,named;char source[80];
 bool ok=!fstatfs(fd,&fs)&&!strcmp(fs.f_fstypename,"apfs")&&!strcmp(fs.f_mntonname,t->mount)&&
 source_device_ar(fs.f_mntfromname,source)&&!strcmp(source,current->pbdev)&&((fs.f_flags&MNT_RDONLY)!=0)==ro&&
 !fstat(fd,&held)&&!fstatat(t->work_fd,"preboot",&named,AT_SYMLINK_NOFOLLOW)&&same_inode_ar(&held,&named)&&!same_inode_ar(&held,&t->child_stat);
 close(fd);return ok;
}
static bool mount_command(Transaction *t,bool mount,bool ro){
 if(!work_binding(t))return false;
 if(t->synthetic){const char *name=mount?(ro?"mount_ro_exit":"mount_rw_exit"):"unmount_exit";int rc=option_exit(t,name);
  if(mount){if(!rc||option_bool(t,"partial_mount",false))t->mount_mode=ro?1:2;if(!ro&&option_bool(t,"rw_stays_readonly",false))t->mount_mode=1;}
  else if(!rc||option_bool(t,"partial_unmount",false))t->mount_mode=0;return !rc;
 }
 char source[80];snprintf(source,sizeof(source),"/dev/%s",t->target.pbdev);
 const char *const m[]={"/sbin/mount_apfs","-o",ro?"rdonly,nobrowse,nofollow":"rw,nobrowse,nofollow",source,"./preboot",NULL};
 const char *const u[]={"/sbin/umount","./preboot",NULL};uint8_t *bytes=NULL;size_t n;bool ok=capture(mount?m:u,4096,&bytes,&n);free(bytes);return ok;
}
static bool release_mount(Transaction *t){
 if(!t->owned)return !t->mount_uncertain;
 Target current,final;if(!target_metadata(t,&current)||!same_target(&current,&t->target)||!mount_binding_ar(t,&current,t->mount_mode==1)){
  t->mount_uncertain=true;return false;}
 bool command_ok=mount_command(t,false,false);
 if(!target_metadata(t,&final)||!same_target(&final,&t->target)||final.mounted||final.mount[0]||!underlying_child_ar(t)){
  t->mount_uncertain=true;return false;}
 t->owned=false;t->mount_uncertain=false;return command_ok;
}
static bool acquire_mount(Transaction *t,bool ro){
 Target current;if(stop_requested||!target_metadata(t,&current)||!same_target(&current,&t->target)||current.mounted||current.mount[0]||!underlying_child_ar(t))return false;
 t->mount_uncertain=true;bool command_ok=mount_command(t,true,ro);Target after;
 if(!target_metadata(t,&after)||!same_target(&after,&t->target))return false;
 if(!after.mounted&&!after.mount[0]&&underlying_child_ar(t)){t->mount_uncertain=false;return false;}
 if(!mount_binding_ar(t,&after,after.readonly))return false;
 t->owned=true;t->mount_mode=after.readonly?1:2;t->mount_uncertain=false;
 return command_ok&&after.readonly==ro;
}
static bool observe(Transaction *t,Snapshot *snapshot,const ComparisonKey *key){
 Target before,after;char group[37];if(!work_binding(t)||!target_metadata(t,&before)||!same_target(&before,&t->target)||
    !mount_binding_ar(t,&before,t->mount_mode==1))return false;
 bool ok=collect_snapshot(LAB_VOLUME,ORIGINAL_VOLUME,&t->profile,t->synthetic?t->fixture_path:NULL,key,snapshot,group);
 if(!ok||strcasecmp(group,t->target.group)||!target_metadata(t,&after)||!same_target(&after,&t->target)||
    !mount_binding_ar(t,&after,t->mount_mode==1))return false;
 return true;
}
static bool save_snapshot(Transaction *t,const char *name,const Snapshot *snapshot){
 /* Reuse the exact serializer without exposing its private HMACs to the page.
  * stdout is held only for this bounded, single-threaded serialization. */
 if(!state_binding(t)||!work_binding(t))return false;
 int fd=openat(t->state_fd,name,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);if(fd<0)return false;
 int saved=dup(STDOUT_FILENO);if(saved<0){close(fd);return false;}bool ok=false;
 if(fflush(stdout)||dup2(fd,STDOUT_FILENO)<0)goto done;
 print_snapshot(snapshot);ok=!fflush(stdout)&&!ferror(stdout);
 if(dup2(saved,STDOUT_FILENO)<0)ok=false;
 if(ok)ok=private_fd(fd,false)&&sync_file(t,fd,"snapshot_sync")&&sync_dir(t,t->state_fd,"snapshot_sync");
done:close(saved);close(fd);return ok&&state_binding(t);
}
static bool prepare_state(Transaction *t,const char *profile_path){
 t->parent_fd=ar_secure_open(t->parent_path,true);if(t->parent_fd<0||!trusted_parent(t->parent_fd)||fstat(t->parent_fd,&t->parent_stat))return false;
 if(t->install){if(mkdirat(t->parent_fd,STATE_NAME,0700))return false;t->state_preserved=true;
  if(!sync_dir(t,t->parent_fd,"state_parent_sync"))return false;}
 t->state_fd=openat(t->parent_fd,STATE_NAME,O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW);
 if(t->state_fd<0||!private_fd(t->state_fd,true)||fstat(t->state_fd,&t->state_stat)||!state_binding(t))return false;
 t->state_preserved=true;
 t->lock_fd=openat(t->state_fd,"session.lock",O_RDWR|O_CLOEXEC|O_NOFOLLOW|(t->install?O_CREAT|O_EXCL:0),0600);
 if(t->lock_fd<0||!private_fd(t->lock_fd,false)||flock(t->lock_fd,LOCK_EX|LOCK_NB))return false;
 if(t->install){
  uint8_t random[32];arc4random_buf(random,sizeof(random));
  bool ok=persist(t,"comparison.key",random,sizeof(random),"key_sync");memset(random,0,sizeof(random));if(!ok)return false;
  uint8_t *bytes=NULL;size_t n;char hash[65];if(!read_file(profile_path,65536,false,&bytes,&n))return false;
  bool bound=sha_hex(bytes,n,hash)&&!strcmp(hash,t->profile.sha)&&persist(t,"profile.json",bytes,n,"profile_sync");free(bytes);if(!bound)return false;
 }
 char key_path[PATH_MAX];if(!path_join(key_path,t->state_path,"comparison.key")||!load_comparison_key(key_path,t->synthetic,&t->key))return false;
 if(!t->install){uint8_t *bytes=NULL;size_t n;char hash[65];if(!read_state(t,"profile.json",65536,&bytes,&n))return false;
  bool bound=sha_hex(bytes,n,hash)&&!strcmp(hash,t->profile.sha);free(bytes);if(!bound)return false;}
 return true;
}
static bool enroll(Transaction *t){
 if(!observe(t,&t->baseline,&t->key)||!validate_snapshot(&t->baseline,NULL,&t->profile,&t->key,"initial",t->synthetic))return false;
 char commitment[65];if(!identity_commitment(t,&t->target,commitment)||!persist(t,"target.hmac",commitment,64,"target_sync")||
    !save_snapshot(t,"baseline.json",&t->baseline)||!persist(t,"enrolled","ENROLLED\n",9,"enrolled_sync"))return false;
 t->enrolled=true;return true;
}
static bool load_enrollment(Transaction *t){
 uint8_t *bytes=NULL;size_t n;char commitment[65];
 if(!read_state(t,"enrolled",32,&bytes,&n))return false;bool ok=n==9&&!memcmp(bytes,"ENROLLED\n",9);free(bytes);if(!ok)return false;
 if(!read_state(t,"target.hmac",64,&bytes,&n))return false;
 ok=n==64&&identity_commitment(t,&t->target,commitment)&&!memcmp(bytes,commitment,64);free(bytes);if(!ok)return false;
 char path[PATH_MAX];if(!path_join(path,t->state_path,"baseline.json"))return false;
 int fd=openat(t->state_fd,"baseline.json",O_RDONLY|O_NOFOLLOW|O_CLOEXEC);if(fd<0)return false;ok=private_fd(fd,false);close(fd);
 if(!ok||!parse_snapshot(path,&t->baseline,t->synthetic)||!validate_snapshot(&t->baseline,NULL,&t->profile,&t->key,"initial",t->synthetic))return false;
 t->enrolled=true;return true;
}
static bool prewrite(Transaction *t,const char *phase_name){
 if(stop_requested||!state_binding(t)||!work_binding(t))return false;Snapshot current;
 if(!observe(t,&current,&t->key))return false;
 bool admitted=!strcmp(phase_name,"initial")?
  validate_snapshot(&current,NULL,&t->profile,&t->key,"initial",t->synthetic)&&!memcmp(&current,&t->baseline,sizeof(current)):
  validate_snapshot(&current,&t->baseline,&t->profile,&t->key,phase_name,t->synthetic);
 t->selection_before_available=admitted&&au_object_read.reference_commitment_bound;
 if(t->selection_before_available)memcpy(t->selection_before,au_object_read.reference_commitment,sizeof(t->selection_before));
 else memset(t->selection_before,0,sizeof(t->selection_before));
 return admitted;
}
static void diagnostic_au(Transaction *t,const Snapshot *s,const char *phase){
 Diagnostic31AU *d=&t->diagnostic;
 *d=(Diagnostic31AU){.available=true,.phase=phase,.read=au_object_read};
 d->comparison_available=t->selection_before_available&&au_object_read.reference_commitment_bound;
 d->selection_changed=d->comparison_available&&memcmp(t->selection_before,au_object_read.reference_commitment,64)!=0;
 memset(d->read.reference_commitment,0,sizeof(d->read.reference_commitment));d->read.reference_commitment_bound=false;
 d->preservation=validate_snapshot(s,&t->baseline,&t->profile,&t->key,"before-restore",t->synthetic);
 d->selected=!strcmp(phase,"raw-policy")||(s->selected_exact&&!strcmp(s->selected,!strcmp(phase,"candidate")?"CANDIDATE":"BOOT021"));
 d->ctrr_enabled=!strcmp(s->lab_ctrr,"enabled");d->ctrr_disabled=!strcmp(s->lab_ctrr,"disabled");d->ctrr_unknown=!strcmp(s->lab_ctrr,"unknown");
 d->ctrr=!strcmp(phase,"candidate")?d->ctrr_enabled:d->ctrr_disabled;
 d->passed=validate_snapshot(s,&t->baseline,&t->profile,&t->key,phase,t->synthetic);
}
static int format_diagnostic_au(const Diagnostic31AU *d,char *out,size_t cap){
 const ObjectDiagnostics31AT *o=&d->read.object;
 const char *stage=!d->available?"NOT_OBSERVED":!d->read.reference_present?"NO_REFERENCE":!d->read.read_succeeded?"READ_REFUSED":o->stage;
 int n=snprintf(out,cap,"{\"available\":%s,\"phase\":\"%s\",\"reference_present\":%s,\"read_attempted\":%s,\"read_succeeded\":%s,\"object_stage\":\"%s\",\"object_identity\":\"%s\",\"object_container\":\"%s\",\"object_codec\":\"%s\",\"recognizer_completed\":%s,\"known_exact\":%s,\"candidate_exact\":%s,\"lab_ctrr_enabled\":%s,\"lab_ctrr_disabled\":%s,\"lab_ctrr_unknown\":%s,\"preservation_contract\":%s,\"selected_payload_matches_phase\":%s,\"lab_ctrr_matches_phase\":%s,\"phase_contract\":%s,\"selection_comparison_available\":%s,\"selected_reference_changed\":%s}",
  d->available?"true":"false",d->available?d->phase:"NOT_OBSERVED",d->read.reference_present?"true":"false",d->read.read_attempted?"true":"false",d->read.read_succeeded?"true":"false",stage,
  d->available&&d->read.read_succeeded?o->identity:"UNKNOWN",d->available&&d->read.read_succeeded?o->container:"UNCLASSIFIED",d->available&&d->read.read_succeeded?o->codec:"NONE",
  o->recognizer_completed?"true":"false",o->known_exact?"true":"false",o->candidate_exact?"true":"false",d->ctrr_enabled?"true":"false",d->ctrr_disabled?"true":"false",d->ctrr_unknown?"true":"false",d->preservation?"true":"false",d->selected?"true":"false",d->ctrr?"true":"false",d->passed?"true":"false",d->comparison_available?"true":"false",d->selection_changed?"true":"false");
 return n>0&&(size_t)n<cap?n:-1;
}
static bool save_diagnostic_au(Transaction *t,const char *which){
 char name[64],bytes[2048];int n=format_diagnostic_au(&t->diagnostic,bytes,sizeof(bytes));
 if(n<0||snprintf(name,sizeof(name),"%s-diagnostic.json",which)>=(int)sizeof(name))return false;
 return persist(t,name,bytes,(size_t)n,"diagnostic_sync");
}
/* The child waits behind a gate until it owns the terminal foreground group.
 * This avoids a SIGTTIN stop on its first authentication read. The original
 * foreground group is restored on success, failure, interruption and timeout. */
static int interactive_child(const char *const *args,uint64_t timeout_ms){
 int tty=open("/dev/tty",O_RDWR|O_NOCTTY|O_CLOEXEC);if(tty<0||!isatty(tty)){if(tty>=0)close(tty);return 126;}
 pid_t foreground=tcgetpgrp(tty);if(foreground<0||foreground!=getpgrp()){close(tty);return 126;}
 struct termios original_termios;if(tcgetattr(tty,&original_termios)){close(tty);return 126;}
 int gate[2];if(pipe(gate)){close(tty);return 126;}fcntl(gate[0],F_SETFD,FD_CLOEXEC);fcntl(gate[1],F_SETFD,FD_CLOEXEC);
 struct sigaction ignore={0},old_ttou,old_pipe;ignore.sa_handler=SIG_IGN;sigemptyset(&ignore.sa_mask);
 if(sigaction(SIGTTOU,&ignore,&old_ttou)){close(gate[0]);close(gate[1]);close(tty);return 126;}
 if(sigaction(SIGPIPE,&ignore,&old_pipe)){sigaction(SIGTTOU,&old_ttou,NULL);close(gate[0]);close(gate[1]);close(tty);return 126;}
 pid_t child=fork();if(child<0){sigaction(SIGTTOU,&old_ttou,NULL);sigaction(SIGPIPE,&old_pipe,NULL);close(gate[0]);close(gate[1]);close(tty);return 126;}
 if(!child){close(gate[1]);if(setpgid(0,0))_exit(126);
#ifdef AR_TEST_EARLY_EXIT
  if(AR_TEST_EARLY_EXIT)_exit(19);
#endif
  char go;if(read(gate[0],&go,1)!=1)_exit(126);close(gate[0]);
  signal(SIGTTOU,SIG_DFL);signal(SIGPIPE,SIG_DFL);dup2(tty,0);dup2(tty,1);dup2(tty,2);if(tty>2)close(tty);
  char *const env[]={"PATH=/usr/bin:/usr/sbin:/bin:/sbin","LANG=C","LC_ALL=C",NULL};execve(args[0],(char *const *)args,env);_exit(127);}
 close(gate[0]);int result=126,status=0;bool reaped=false;setpgid(child,child);
 if(tcsetpgrp(tty,child)||write(gate[1],"G",1)!=1){close(gate[1]);goto terminate;}close(gate[1]);
 uint64_t deadline=ms()+timeout_ms;
 while(!stop_requested&&ms()<deadline){pid_t got=waitpid(child,&status,WNOHANG);
  if(got==child){reaped=true;result=WIFEXITED(status)?WEXITSTATUS(status):128+(WIFSIGNALED(status)?WTERMSIG(status):0);goto restore;}
  if(got<0&&errno!=EINTR)break;struct timespec nap={0,50000000};nanosleep(&nap,NULL);}
 result=stop_requested?130:124;
terminate:
 kill(-child,SIGKILL);kill(child,SIGKILL);while(waitpid(child,&status,0)<0&&errno==EINTR){}reaped=true;
restore:
 if(!reaped){kill(-child,SIGKILL);while(waitpid(child,&status,0)<0&&errno==EINTR){}}
 /* A killed authenticator may leave a partial line queued while ECHO is off.
  * Discard only pending terminal input on unsuccessful outcomes, before the
  * shell regains the terminal. Never collect or inspect those bytes. */
 bool terminal_ok=true;if(result&&tcflush(tty,TCIFLUSH))terminal_ok=false;
 if(tcsetpgrp(tty,foreground))terminal_ok=false;
 if(tcsetattr(tty,TCSANOW,&original_termios))terminal_ok=false;
 if(!terminal_ok)result=125;
 sigaction(SIGTTOU,&old_ttou,NULL);sigaction(SIGPIPE,&old_pipe,NULL);close(tty);return result;
}
static int run_writer(Transaction *t,const char *which){
 if(t->synthetic){t->writes++;char name[40];snprintf(name,sizeof(name),"%s_exit",which);
  if(failpoint(t,"writer_interrupt")){stop_requested=1;return 130;}
  if(failpoint(t,"writer_timeout"))return 124;return option_exit(t,name);}
 const char *const candidate[]={"/usr/bin/kmutil","configure-boot","--custom-boot-object","./candidate.macho","--volume",LAB_VOLUME,"--compress",NULL};
 const char *const raw[]={"/usr/bin/kmutil","configure-boot","--custom-boot-object","./m1n1-boot021.bin","--raw","--entry-point","2048","--lowest-virtual-address","0","--volume",LAB_VOLUME,NULL};
 const char *const ctrr[]={"/usr/bin/bputil","-c","-v",t->target.group,NULL};
 const char *const *args=!strcmp(which,"candidate")?candidate:!strcmp(which,"ctrr")?ctrr:raw;
 return interactive_child(args,180000);
}
static bool mutate(Transaction *t,const char *which,const char *post_phase,const char *post_name){
 char marker[48],exit_name[48];snprintf(marker,sizeof(marker),"%s-attempt",which);snprintf(exit_name,sizeof(exit_name),"%s-exit",which);
 if(!state_binding(t)||!work_binding(t)||stop_requested||!persist(t,marker,"SPENT\n",6,"marker_sync"))return refused_at(t,"MARKER","SPENT_OR_DURABILITY");
 /* Recheck after durability, immediately before delegating the exact operation.
  * A refusal here still leaves the one-shot marker spent. */
 Target fresh;char artifact[PATH_MAX];bool candidate=!strcmp(which,"candidate"),raw=!strcmp(which,"boot021");
 if(!work_binding(t)||!state_binding(t)||!trusted_parent(t->parent_fd)||stop_requested||
    !target_metadata(t,&fresh)||!same_target(&fresh,&t->target)||!mount_binding_ar(t,&fresh,false)||
    ((candidate||raw)&&(!path_join(artifact,t->scratch,candidate?"candidate.macho":"m1n1-boot021.bin")||
     !file_matches(artifact,candidate?CANDIDATE_BYTES:ROLLBACK_BYTES,candidate?CANDIDATE_SHA256:ROLLBACK_SHA))))
  return refused_at(t,"PREWRITE","POLICY_OR_IDENTITY_CHANGED");
 /* The fixed name is spent even if opening the TTY/exec fails. */
 t->attempted=true;t->writer_exit=run_writer(t,which);
 char exit_text[16];int n=snprintf(exit_text,sizeof(exit_text),"%d\n",t->writer_exit);
 bool exit_saved=n>0&&persist(t,exit_name,exit_text,(size_t)n,"exit_sync");
 memset(&t->diagnostic,0,sizeof(t->diagnostic));
 bool phase_ok=phase(t,post_phase);Snapshot after;
 bool observed=phase_ok&&observe(t,&after,&t->key);
 if(observed)diagnostic_au(t,&after,post_phase);
 bool readback_saved=observed&&save_snapshot(t,post_name,&after);
 bool diagnostic_saved=observed&&save_diagnostic_au(t,which);
 bool valid=observed&&validate_snapshot(&after,&t->baseline,&t->profile,&t->key,post_phase,t->synthetic);
 if(!exit_saved||!readback_saved||!diagnostic_saved)return refused_at(t,"READBACK","READBACK_OR_DURABILITY");
 if(t->writer_exit||stop_requested)return refused_at(t,"WRITER","NONZERO_OR_INTERRUPTED");
 if(!valid)return refused_at(t,"POSTCONDITION","POLICY_OR_OBJECT");return true;
}
static bool cleanup(Transaction *t){
 bool ok=true;
 if(t->owned&&!release_mount(t))ok=false;
 if(t->mount_uncertain)ok=false;
 if(t->child_created&&ok){if(!underlying_child_ar(t)||unlinkat(t->work_fd,"preboot",AT_REMOVEDIR))ok=false;else t->child_created=false;}
 t->cleanup_verified=ok&&!t->owned&&!t->mount_uncertain&&!t->child_created;
 return t->cleanup_verified;
}
static bool run_transaction(Transaction *t,const char *profile_path){
 Snapshot admission,current;char path[PATH_MAX];
 if(t->synthetic){if(!option_bool(t,"recovery",false)||!option_bool(t,"root",false)||!equals(field(t->fixture,"model"),"Mac17,6"))return refused_at(t,"ENVIRONMENT","RECOVERY_REQUIRED");}
 else if(!recovery_admission())return refused_at(t,"ENVIRONMENT","RECOVERY_REQUIRED");
 if(!work_binding(t)||!phase(t,t->install?"initial":"before-restore")||!target_metadata(t,&t->target))return refused_at(t,"IDENTITIES","TARGET_BINDING");
 /* First version deliberately refuses all foreign mounts, without touching them. */
 if(t->target.mounted||t->target.mount[0])return refused_at(t,"MOUNT","FOREIGN_MOUNT");
 if(!path_join(path,t->scratch,"m1n1-boot021.bin")||!file_matches(path,ROLLBACK_BYTES,ROLLBACK_SHA))return refused_at(t,"ARTIFACTS","ROLLBACK_PIN");
 if(t->install&&(!path_join(path,t->scratch,"candidate.macho")||!file_matches(path,CANDIDATE_BYTES,CANDIDATE_SHA256)))return refused_at(t,"ARTIFACTS","CANDIDATE_PIN");
 if(mkdirat(t->work_fd,"preboot",0700))return refused_at(t,"SCRATCH","CHILD_EXISTS");
 t->child_created=true;t->child_fd=openat(t->work_fd,"preboot",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
 if(t->child_fd<0||!private_fd(t->child_fd,true)||fstat(t->child_fd,&t->child_stat)||!underlying_child_ar(t))return refused_at(t,"SCRATCH","CHILD_BINDING");
 if(!acquire_mount(t,true))return refused_at(t,"MOUNT_RO","MOUNT_OR_BINDING");
 if(t->install){
  if(!observe(t,&admission,NULL)||!validate_snapshot(&admission,NULL,&t->profile,NULL,"initial-admission",t->synthetic))return refused_at(t,"ADMISSION","POLICY_OR_OBJECT");
  if(!prepare_state(t,profile_path)||!enroll(t))return refused_at(t,"ENROLLMENT","STATE_OR_DURABILITY");
 }else{
  if(!prepare_state(t,profile_path)||!load_enrollment(t))return refused_at(t,"ENROLLMENT","STATE_OR_TARGET_COMMITMENT");
  if(!observe(t,&current,&t->key)||!validate_snapshot(&current,&t->baseline,&t->profile,&t->key,"before-restore",t->synthetic))return refused_at(t,"RESTORE_ADMISSION","POLICY_OR_OBJECT");
  if(validate_snapshot(&current,&t->baseline,&t->profile,&t->key,"restored",t->synthetic)){diagnostic_au(t,&current,"restored");t->rollback_verified=true;return true;}
 }
 if(!release_mount(t))return refused_at(t,"RELEASE_RO","CLEANUP_UNCERTAIN");
 if(!phase(t,t->install?"prewrite":"before-restore")||!acquire_mount(t,false))return refused_at(t,"MOUNT_RW","MOUNT_OR_BINDING");
 if(!prewrite(t,t->install?"initial":"before-restore"))return refused_at(t,"PREWRITE","POLICY_OR_IDENTITY_CHANGED");
 if(t->install){
  if(!mutate(t,"candidate","candidate","candidate.json"))return false;t->candidate_verified=true;
 }else{
  if(!observe(t,&current,&t->key))return refused_at(t,"RESTORE_ADMISSION","READBACK_UNAVAILABLE");
  if(!strcmp(current.lab_ctrr,"enabled")){
   if(!mutate(t,"ctrr","raw-policy","raw-policy.json"))return false;
  }else if(!strcmp(current.lab_ctrr,"disabled")){
   if(!validate_snapshot(&current,&t->baseline,&t->profile,&t->key,"raw-policy",t->synthetic))return refused_at(t,"RAW_POLICY","POLICY_CHANGED");
  }else return refused_at(t,"RAW_POLICY","UNKNOWN_CTRR");
  if(!prewrite(t,"raw-policy"))return refused_at(t,"RAW_POLICY","PREWRITE_CHANGED");
  if(!mutate(t,"boot021","restored","restored.json"))return false;t->rollback_verified=true;
 }
 return true;
}
static void print_result(const Transaction *t,bool ok){
 char diagnostic[2048];int dn=format_diagnostic_au(&t->diagnostic,diagnostic,sizeof(diagnostic));
 if(dn<0){puts("{\"schema\":\"ilinux31au-cli-refusal-v1\",\"status\":\"REFUSED\",\"native_ready\":false}");return;}
 printf("{\"schema\":\"ilinux31au-transaction-result-v1\",\"status\":\"%s\",\"operation\":\"%s\",\"stage\":\"%s\",\"reason\":\"%s\",\"synthetic\":%s,\"cleanup_verified\":%s,\"candidate_verified\":%s,\"rollback_verified\":%s,\"mutation_attempted\":%s,\"writer_exit\":%d,\"state_preserved\":%s,\"restart_performed\":false,\"default_changed\":false,\"native_ready\":false,\"identifiers_returned\":false,\"policy_values_returned\":false,\"diagnostics\":%s}\n",
  ok?(t->install?"INSTALL_COMPLETE":"RESTORE_COMPLETE"):"REFUSED",t->install?"install":"restore",ok?"COMPLETE":t->stage,ok?"NONE":t->reason,
  t->synthetic?"true":"false",t->cleanup_verified?"true":"false",t->candidate_verified?"true":"false",t->rollback_verified?"true":"false",
  t->attempted?"true":"false",t->writer_exit,t->state_preserved?"true":"false",diagnostic);
}
static bool enum_au(const Json *j,int object,const char *key,const char *const *values,size_t count){
 int node=json_get(j,object,key);for(size_t i=0;i<count;i++)if(json_string(j,node,values[i]))return true;return false;
}
static bool object_result_category_au(const Json *j,int node,bool completed,bool known){
 /* These are relations of the unchanged original recognizer/AT explanatory
  * adapter, not a second object parser or an acceptance decision. Bits name
  * only finite result labels: containers U/R/I/G and codecs N/L/K/Z. */
 enum {U=1,R=2,I=4,G=8,N=1,L=2,K=4,Z=8};
 const char *containers[]={"UNCLASSIFIED","RAW","IM4P","IMG4"};
 const char *codecs[]={"NONE","LZFSE","KEYBAG_BLOCKED","GZIP_UNSUPPORTED"};
 unsigned container=0,codec=0;
 for(unsigned i=0;i<4;i++){
  if(json_string(j,json_get(j,node,"object_container"),containers[i]))container=1u<<i;
  if(json_string(j,json_get(j,node,"object_codec"),codecs[i]))codec=1u<<i;
 }
 const struct {const char *stage;unsigned containers,codecs;bool completed,known;} rules[]={
  {"NOT_OBSERVED",U,N,false,false},{"NO_REFERENCE",U,N,false,false},{"READ_REFUSED",U,N,false,false},
  {"INPUT_BOUND_REJECTED",U,N,false,false},{"DER_FRAMING_REJECTED",U,N,false,false},
  {"KEYBAG_BLOCKED",I|G,K,true,false},{"COMPRESSED_BOUND_REJECTED",R|I|G,L,false,false},
  {"LZFSE_FRAME_REJECTED",R|I|G,L,false,false},{"DECLARED_SIZE_MISMATCH",I|G,L,false,false},
  {"DECODE_REJECTED",R|I|G,L,false,false},{"DECODED_UNMATCHED",R|I|G,L,true,false},
  {"UNCOMPRESSED_DECLARATION_REJECTED",I|G,N,false,false},{"GZIP_UNSUPPORTED",R|I|G,Z,false,false},
  {"UNCOMPRESSED_BOUND_REJECTED",R|I|G,N,false,false},{"UNCOMPRESSED_UNMATCHED",R|I|G,N,true,false},
  {"KNOWN_MATCHED",R|I|G,N|L,true,true}
 };
 for(size_t i=0;i<sizeof(rules)/sizeof(rules[0]);i++)if(json_string(j,json_get(j,node,"object_stage"),rules[i].stage))
  return container&&(container&rules[i].containers)&&codec&&(codec&rules[i].codecs)&&completed==rules[i].completed&&known==rules[i].known;
 return false;
}
static bool diagnostic_result_au(const Json *j,int node){
 const char *keys[]={"available","phase","reference_present","read_attempted","read_succeeded","object_stage","object_identity","object_container","object_codec","recognizer_completed","known_exact","candidate_exact","lab_ctrr_enabled","lab_ctrr_disabled","lab_ctrr_unknown","preservation_contract","selected_payload_matches_phase","lab_ctrr_matches_phase","phase_contract","selection_comparison_available","selected_reference_changed"};
 const char *bools[]={"available","reference_present","read_attempted","read_succeeded","recognizer_completed","known_exact","candidate_exact","lab_ctrr_enabled","lab_ctrr_disabled","lab_ctrr_unknown","preservation_contract","selected_payload_matches_phase","lab_ctrr_matches_phase","phase_contract","selection_comparison_available","selected_reference_changed"};
 const char *phases[]={"NOT_OBSERVED","candidate","raw-policy","restored"};
 const char *stages[]={"NOT_OBSERVED","NO_REFERENCE","READ_REFUSED","INPUT_BOUND_REJECTED","DER_FRAMING_REJECTED","KEYBAG_BLOCKED","COMPRESSED_BOUND_REJECTED","LZFSE_FRAME_REJECTED","DECLARED_SIZE_MISMATCH","DECODE_REJECTED","DECODED_UNMATCHED","UNCOMPRESSED_DECLARATION_REJECTED","GZIP_UNSUPPORTED","UNCOMPRESSED_BOUND_REJECTED","UNCOMPRESSED_UNMATCHED","KNOWN_MATCHED"};
 const char *identities[]={"UNKNOWN","CANDIDATE","BOOT021","31AF","31AI"};
 const char *containers[]={"UNCLASSIFIED","RAW","IM4P","IMG4"};
 const char *codecs[]={"NONE","LZFSE","KEYBAG_BLOCKED","GZIP_UNSUPPORTED"};
 if(!json_keys(j,node,keys,21)||!enum_au(j,node,"phase",phases,4)||!enum_au(j,node,"object_stage",stages,16)||!enum_au(j,node,"object_identity",identities,5)||!enum_au(j,node,"object_container",containers,4)||!enum_au(j,node,"object_codec",codecs,4))return false;
 for(size_t i=0;i<16;i++)if(!node_bool(j,node,bools[i],true)&&!node_bool(j,node,bools[i],false))return false;
 bool available=node_bool(j,node,"available",true),reference=node_bool(j,node,"reference_present",true),attempted=node_bool(j,node,"read_attempted",true),read=node_bool(j,node,"read_succeeded",true);
 bool completed=node_bool(j,node,"recognizer_completed",true),known=node_bool(j,node,"known_exact",true),candidate=node_bool(j,node,"candidate_exact",true);
 bool enabled=node_bool(j,node,"lab_ctrr_enabled",true),disabled=node_bool(j,node,"lab_ctrr_disabled",true),unknown=node_bool(j,node,"lab_ctrr_unknown",true);
 bool preservation=node_bool(j,node,"preservation_contract",true),selected=node_bool(j,node,"selected_payload_matches_phase",true),ctrr=node_bool(j,node,"lab_ctrr_matches_phase",true),passed=node_bool(j,node,"phase_contract",true);
 if(!object_result_category_au(j,node,completed,known))return false;
 if(node_bool(j,node,"selected_reference_changed",true)&&!node_bool(j,node,"selection_comparison_available",true))return false;
 if(!available){
  for(size_t i=1;i<16;i++)if(node_bool(j,node,bools[i],true))return false;
  return json_string(j,json_get(j,node,"phase"),"NOT_OBSERVED")&&json_string(j,json_get(j,node,"object_stage"),"NOT_OBSERVED")&&json_string(j,json_get(j,node,"object_identity"),"UNKNOWN")&&json_string(j,json_get(j,node,"object_container"),"UNCLASSIFIED")&&json_string(j,json_get(j,node,"object_codec"),"NONE");
 }
 if(json_string(j,json_get(j,node,"phase"),"NOT_OBSERVED")||enabled+disabled+unknown!=1||attempted!=reference||(read&&!attempted))return false;
 if(!reference&&!json_string(j,json_get(j,node,"object_stage"),"NO_REFERENCE"))return false;
 if(reference&&!read&&!json_string(j,json_get(j,node,"object_stage"),"READ_REFUSED"))return false;
 if(read&&(json_string(j,json_get(j,node,"object_stage"),"NOT_OBSERVED")||json_string(j,json_get(j,node,"object_stage"),"NO_REFERENCE")||json_string(j,json_get(j,node,"object_stage"),"READ_REFUSED")))return false;
 if(!read&&(completed||known||candidate||!json_string(j,json_get(j,node,"object_identity"),"UNKNOWN")||!json_string(j,json_get(j,node,"object_container"),"UNCLASSIFIED")||!json_string(j,json_get(j,node,"object_codec"),"NONE")))return false;
 if(known!=!json_string(j,json_get(j,node,"object_identity"),"UNKNOWN")||(known&&!completed)||known!=json_string(j,json_get(j,node,"object_stage"),"KNOWN_MATCHED")||candidate!=(known&&json_string(j,json_get(j,node,"object_identity"),"CANDIDATE")))return false;
 bool candidate_phase=json_string(j,json_get(j,node,"phase"),"candidate"),raw=json_string(j,json_get(j,node,"phase"),"raw-policy");
 if(ctrr!=(candidate_phase?enabled:disabled)||selected!=(raw|| (candidate_phase?candidate:(known&&json_string(j,json_get(j,node,"object_identity"),"BOOT021")))))return false;
 return passed==(preservation&&selected&&ctrr);
}
static bool validate_result(const char *path,const char *operation){
 uint8_t *bytes=NULL;size_t n;if(!read_file(path,4096,false,&bytes,&n))return false;Json json;bool ok=false;
 const char *keys[]={"schema","status","operation","stage","reason","synthetic","cleanup_verified","candidate_verified","rollback_verified","mutation_attempted","writer_exit","state_preserved","restart_performed","default_changed","native_ready","identifiers_returned","policy_values_returned","diagnostics"};
 if(!json_parse((Bytes){bytes,n},&json)||!json_keys(&json,0,keys,18)||!diagnostic_result_au(&json,json_get(&json,0,"diagnostics"))||!json_string(&json,json_get(&json,0,"schema"),"ilinux31au-transaction-result-v1")||
    !json_string(&json,json_get(&json,0,"operation"),operation)||!node_bool(&json,0,"synthetic",false))goto done;
 const char *false_keys[]={"restart_performed","default_changed","native_ready","identifiers_returned","policy_values_returned"};
 for(unsigned i=0;i<5;i++)if(!node_bool(&json,0,false_keys[i],false))goto done;
 bool install=!strcmp(operation,"install"),refused=json_string(&json,json_get(&json,0,"status"),"REFUSED");
 const char *boolean_keys[]={"cleanup_verified","state_preserved","candidate_verified","rollback_verified","mutation_attempted"};
 for(unsigned i=0;i<5;i++)if(!node_bool(&json,0,boolean_keys[i],true)&&!node_bool(&json,0,boolean_keys[i],false))goto done;
 if(refused){
  const char *stages[]={"PREFLIGHT","ENVIRONMENT","IDENTITIES","MOUNT","ARTIFACTS","SCRATCH","MOUNT_RO","ADMISSION","ENROLLMENT","RESTORE_ADMISSION","RELEASE_RO","MOUNT_RW","PREWRITE","RAW_POLICY","MARKER","READBACK","WRITER","POSTCONDITION","CLEANUP","INTERRUPTED"};
  const char *reasons[]={"INPUT_OR_BINDING","RECOVERY_REQUIRED","TARGET_BINDING","FOREIGN_MOUNT","ROLLBACK_PIN","CANDIDATE_PIN","CHILD_EXISTS","CHILD_BINDING","MOUNT_OR_BINDING","POLICY_OR_OBJECT","STATE_OR_DURABILITY","STATE_OR_TARGET_COMMITMENT","READBACK_UNAVAILABLE","CLEANUP_UNCERTAIN","POLICY_OR_IDENTITY_CHANGED","POLICY_CHANGED","UNKNOWN_CTRR","PREWRITE_CHANGED","SPENT_OR_DURABILITY","READBACK_OR_DURABILITY","NONZERO_OR_INTERRUPTED","MOUNT_OR_CHILD_UNCERTAIN","INTERRUPTED"};
  bool stage_ok=false,reason_ok=false;
  for(unsigned i=0;i<sizeof(stages)/sizeof(stages[0]);i++)if(json_string(&json,json_get(&json,0,"stage"),stages[i]))stage_ok=true;
  for(unsigned i=0;i<sizeof(reasons)/sizeof(reasons[0]);i++)if(json_string(&json,json_get(&json,0,"reason"),reasons[i]))reason_ok=true;
  if(!stage_ok||!reason_ok)goto done;
  if((install&&node_bool(&json,0,"rollback_verified",true))||(!install&&node_bool(&json,0,"candidate_verified",true)))goto done;
 }else if(!json_string(&json,json_get(&json,0,"status"),install?"INSTALL_COMPLETE":"RESTORE_COMPLETE")||
  !json_string(&json,json_get(&json,0,"stage"),"COMPLETE")||!json_string(&json,json_get(&json,0,"reason"),"NONE")||
  !node_bool(&json,0,"cleanup_verified",true)||!node_bool(&json,0,"state_preserved",true)||
  !node_bool(&json,0,"candidate_verified",install)||!node_bool(&json,0,"rollback_verified",!install))goto done;
 int exit=json_get(&json,0,"writer_exit");if(exit<0||json.nodes[exit].type!=J_NUMBER)goto done;
 bool mutated=node_bool(&json,0,"mutation_attempted",true);
 if(!mutated&&!node_bool(&json,0,"mutation_attempted",false))goto done;
 if(refused){char *end=NULL;long value=strtol(json.nodes[exit].value,&end,10);char canonical[16];snprintf(canonical,sizeof(canonical),"%ld",value);
  if(*end||strcmp(canonical,json.nodes[exit].value)||value< -1||value>255||(!mutated&&value!= -1)||(mutated&&value<0))goto done;
 }else if((install&&!mutated)||(mutated?strcmp(json.nodes[exit].value,"0"):strcmp(json.nodes[exit].value,"-1")))goto done;
 int diagnostic=json_get(&json,0,"diagnostics");
 if(node_bool(&json,diagnostic,"available",true)&&
    (install?!json_string(&json,json_get(&json,diagnostic,"phase"),"candidate"):
     (!json_string(&json,json_get(&json,diagnostic,"phase"),"raw-policy")&&!json_string(&json,json_get(&json,diagnostic,"phase"),"restored"))))goto done;
 if(mutated&&node_bool(&json,diagnostic,"available",true)&&!node_bool(&json,diagnostic,"selection_comparison_available",true))goto done;
 if((node_bool(&json,0,"candidate_verified",true)||node_bool(&json,0,"rollback_verified",true))&&(!node_bool(&json,diagnostic,"available",true)||!node_bool(&json,diagnostic,"phase_contract",true)||!json_string(&json,json_get(&json,diagnostic,"phase"),install?"candidate":"restored")))goto done;
 if(fwrite(bytes,1,n,stdout)!=n)goto done;ok=true;
done:free(bytes);return ok;
}
static void help_ar(void){puts("ilinux31au-reader: 31AU fixed lab transaction controller\nDefault/help is inert.\n --transaction install|restore --profile ABS/profile.json --scratch ABS\n --transaction-fixture PLIST (workspace synthetic backend; no live commands)\n --validate-transaction-result FILE --operation install|restore\nNo restart/default selection is performed. Do not execute live without separate reviewed authorization.");}
int main(int argc,char **argv){
 if(argc==1||(argc==2&&!strcmp(argv[1],"--help"))){help_ar();return 0;}
 const char *operation=NULL,*profile_path=NULL,*scratch=NULL,*fixture_path=NULL,*result_path=NULL,*result_operation=NULL;unsigned seen=0;
 for(int i=1;i<argc;i++){
  const char **slot=NULL;unsigned bit=0;
  if(!strcmp(argv[i],"--transaction")){slot=&operation;bit=1;}
  else if(!strcmp(argv[i],"--profile")){slot=&profile_path;bit=2;}
  else if(!strcmp(argv[i],"--scratch")){slot=&scratch;bit=4;}
  else if(!strcmp(argv[i],"--transaction-fixture")){slot=&fixture_path;bit=8;}
  else if(!strcmp(argv[i],"--validate-transaction-result")){slot=&result_path;bit=16;}
  else if(!strcmp(argv[i],"--operation")){slot=&result_operation;bit=32;}
  else goto arguments;if(seen&bit||++i==argc)goto arguments;seen|=bit;*slot=argv[i];
 }
 if(result_path){if(seen!=48||(!result_operation||(strcmp(result_operation,"install")&&strcmp(result_operation,"restore")))||!validate_result(result_path,result_operation))goto arguments;return 0;}
 if((seen!=7&&seen!=15)||!operation||(strcmp(operation,"install")&&strcmp(operation,"restore")))goto arguments;
 Transaction t={.install=!strcmp(operation,"install"),.synthetic=fixture_path!=NULL,.work_fd=-1,.child_fd=-1,.parent_fd=-1,.state_fd=-1,.lock_fd=-1,.writer_exit=-1,.stage="PREFLIGHT",.reason="INPUT_OR_BINDING"};
 ar_fixture_execution_disabled=t.synthetic;
 uint8_t *bytes=NULL;size_t n;bool ok=false;stop_requested=0;
 if(!safe_path(scratch)||strlen(scratch)>=sizeof(t.scratch))goto finish;strcpy(t.scratch,scratch);
 const char *base=strrchr(scratch,'/');if(!base||strncmp(base+1,"ilinux31au.",11)||strlen(base+12)<6||strlen(base+12)>32)goto finish;
 for(const char *p=base+12;*p;p++)if(!isalnum((unsigned char)*p))goto finish;
 char physical[PATH_MAX];if(!realpath(scratch,physical)||strcmp(scratch,physical)||!path_join(t.mount,scratch,"preboot"))goto finish;
 t.work_fd=ar_secure_open(scratch,true);if(t.work_fd<0||!private_fd(t.work_fd,true)||fstat(t.work_fd,&t.work_stat)||!work_binding(&t))goto finish;
 if(t.synthetic){
  if(!workspace(scratch)||!read_file(fixture_path,METADATA_LIMIT,true,&bytes,&n))goto finish;
  CFPropertyListRef f=plist((Bytes){bytes,n});free(bytes);bytes=NULL;if(!f||CFGetTypeID(f)!=CFDictionaryGetTypeID()){if(f)CFRelease(f);goto finish;}t.fixture=f;
  if(!cstring(field(f,"state_parent"),t.parent_path,sizeof(t.parent_path))||!workspace(t.parent_path))goto finish;
 }else strcpy(t.parent_path,STATE_PARENT);
 if(!path_join(t.state_path,t.parent_path,STATE_NAME))goto finish;
 char exe_raw[PATH_MAX],exe[PATH_MAX];uint32_t length=sizeof(exe_raw);
 if(_NSGetExecutablePath(exe_raw,&length)||!realpath(exe_raw,exe)||!load_profile(profile_path,exe,&t.profile))goto finish;
 char expected_profile[PATH_MAX];if(!path_join(expected_profile,t.scratch,"profile.json")||strcmp(profile_path,expected_profile))goto finish;
 umask(077);signal(SIGINT,stop_handler);signal(SIGTERM,stop_handler);signal(SIGHUP,stop_handler);
 ok=run_transaction(&t,profile_path);
 if(!cleanup(&t)){ok=false;refused_at(&t,"CLEANUP","MOUNT_OR_CHILD_UNCERTAIN");}
 if(stop_requested){ok=false;if(strcmp(t.stage,"CLEANUP"))refused_at(&t,"INTERRUPTED","INTERRUPTED");}
finish:
 free(bytes);if(t.phase_fixture)CFRelease(t.phase_fixture);if(t.fixture)CFRelease(t.fixture);
 if(t.child_fd>=0)close(t.child_fd);if(t.lock_fd>=0)close(t.lock_fd);if(t.state_fd>=0)close(t.state_fd);if(t.parent_fd>=0)close(t.parent_fd);if(t.work_fd>=0)close(t.work_fd);
 memset(&t.key,0,sizeof(t.key));memset(t.selection_before,0,sizeof(t.selection_before));memset(au_object_read.reference_commitment,0,sizeof(au_object_read.reference_commitment));print_result(&t,ok);return ok?0:2;
arguments:puts("{\"schema\":\"ilinux31au-cli-refusal-v1\",\"status\":\"REFUSED\",\"native_ready\":false}");return 2;
}
