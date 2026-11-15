/* SPDX-License-Identifier: MIT */
/* Reuse private original APFS/CF helpers without changing the collector. */
#include "state.c"
#include "preboot.h"
#include <ctype.h>
#include <signal.h>
#include <sys/mount.h>

typedef struct {
 char group[64],original_group[64],lab_uuid[64],original_uuid[64],data_uuid[64];
 char container[64],preboot_device[64],preboot_uuid[64],data_device[64];
} PBIdentity;
typedef struct {PBIdentity identity;char mount[PATH_MAX];bool mounted;} PBMetadata;
typedef struct {CFDictionaryRef fixture;bool synthetic,active;const char *phase;} PBContext;
typedef struct {int fd,child_fd;struct stat directory,child;char path[PATH_MAX],mount[PATH_MAX];bool child_created;} PBScratch;
static volatile sig_atomic_t interrupted;
static void interrupt_handler(int signo){(void)signo;interrupted=1;}
static bool fail(PBResult *r,int stage,int reason){r->stage=stage;r->reason=reason;return false;}
static bool same_inode(const struct stat *a,const struct stat *b){return a->st_dev==b->st_dev&&a->st_ino==b->st_ino;}
static int directory_fd(const char *path){
 if(!safe_path(path))return -1;
 char copy[PATH_MAX];strcpy(copy,path);int fd=open("/",O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW);if(fd<0)return -1;
 char *save=NULL,*part=strtok_r(copy+1,"/",&save);
 while(part){int child=openat(fd,part,O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK);close(fd);if(child<0)return -1;fd=child;part=strtok_r(NULL,"/",&save);}
 return fd;
}
static bool scratch_binding(const PBScratch *s){
 int named=directory_fd(s->path);if(named<0)return false;struct stat n,h;bool ok=!fstat(named,&n)&&!fstat(s->fd,&h)&&same_inode(&n,&h)&&same_inode(&n,&s->directory)&&n.st_uid==geteuid()&&(n.st_mode&07777)==0700;close(named);return ok;
}
static bool cwd_binding(const PBScratch *s){struct stat current,held;return !fstatat(AT_FDCWD,".",&current,AT_SYMLINK_NOFOLLOW)&&!fstat(s->fd,&held)&&same_inode(&current,&held)&&same_inode(&held,&s->directory);}
static bool scratch_open(PBScratch *s,const char *path,bool synthetic){
 memset(s,0,sizeof(*s));s->fd=s->child_fd=-1;
 if(!path||strlen(path)>=sizeof(s->path)||!safe_path(path))return false;
 const char *base=strrchr(path,'/');if(!base||strncmp(base+1,"ilinux31am.",11))return false;
 size_t suffix=strlen(base+12);if(suffix<6||suffix>32)return false;
 for(const char *p=base+12;*p;p++)if(!isalnum((unsigned char)*p))return false;
 if(synthetic){size_t length=strlen(WORKSPACE_ROOT);if(strncmp(path,WORKSPACE_ROOT,length)||path[length]!='/')return false;}
 char physical[PATH_MAX];if(!realpath(path,physical)||strcmp(physical,path))return false;
 strcpy(s->path,path);if(snprintf(s->mount,sizeof(s->mount),"%s/preboot",path)>=(int)sizeof(s->mount))return false;
 s->fd=directory_fd(path);if(s->fd<0||fstat(s->fd,&s->directory))return false;
 return s->directory.st_uid==geteuid()&&(s->directory.st_mode&07777)==0700&&scratch_binding(s);
}
static CFDictionaryRef fixture_phase(PBContext *c){
 if(!c->synthetic)return NULL;
 CFTypeRef value=field(c->fixture,c->phase);
 return value&&CFGetTypeID(value)==CFDictionaryGetTypeID()?(CFDictionaryRef)value:NULL;
}
static bool setting(PBContext *c,const char *name,bool fallback){
 if(!c->synthetic)return fallback;CFTypeRef v=field(c->fixture,name);return v?v==kCFBooleanTrue:fallback;
}
static int setting_exit(PBContext *c,const char *name){
 CFTypeRef v=field(c->fixture,name);int value=0;
 if(!v)return 0;if(CFGetTypeID(v)!=CFNumberGetTypeID()||!CFNumberGetValue(v,kCFNumberIntType,&value)||value<0||value>255)return 255;return value;
}
static bool source_device(const char *source,char output[80]){
 const char *p=strrchr(source,'@');p=p?p+1:source;
 if(!strncmp(p,"/dev/",5))p+=5;if(*p=='r')p++;
 if(strncmp(p,"disk",4)||strlen(p)>=80)return false;
 const char *q=p+4;if(!isdigit((unsigned char)*q))return false;
 while(isdigit((unsigned char)*q))q++;
 unsigned slices=0;while(*q){if(*q++!='s'||!isdigit((unsigned char)*q)||++slices>3)return false;while(isdigit((unsigned char)*q))q++;}
 strcpy(output,p);return true;
}
static bool source_matches(const char *source,const char *wanted){
 char name[80];if(!source_device(source,name))return false;size_t n=strlen(wanted);
 return !strncmp(name,wanted,n)&&(!name[n]||(name[n]=='s'&&isdigit((unsigned char)name[n+1])));
}
static int kernel_mount_state(PBContext *c,Backend *b,const char *wanted){
 if(c->synthetic){CFTypeRef v=field(b->fixture,"kernel_mounted");return v==kCFBooleanTrue?1:v==kCFBooleanFalse?0:-1;}
 int count=getfsstat(NULL,0,MNT_NOWAIT);if(count<1||count>1024)return -1;
 int capacity=count+8;struct statfs *table=calloc((size_t)capacity,sizeof(*table));if(!table)return -1;
 int n=getfsstat(table,(int)((size_t)capacity*sizeof(*table)),MNT_NOWAIT);bool found=false,unknown=false;
 if(n<1||n>=capacity){free(table);return -1;}
 for(int i=0;i<n;i++)if(!strcmp(table[i].f_fstypename,"apfs")){
  char normalized[80];if(!source_device(table[i].f_mntfromname,normalized)){unknown=true;continue;}
  if(source_matches(table[i].f_mntfromname,wanted))found=true;
 }
 free(table);return found?1:unknown?-1:0;
}
static bool metadata(PBContext *c,PBMetadata *out,PBResult *r){
 memset(out,0,sizeof(*out));Backend b={.fixture=fixture_phase(c)};
 if(c->synthetic&&!b.fixture)return fail(r,PS_IDENTITIES,PR_METADATA);
 CFDictionaryRef lab=disk(&b,"lab_info",LAB_VOLUME),original=disk(&b,"original_info","/Volumes/Macintosh HD"),list=apfs(&b),pb=NULL,data=NULL;bool ok=false;
 char ref[64],oref[64],group[64],ogroup[64],u[64],ou[64],dgroup[64],dmount[PATH_MAX];
 if(!lab||!original||!list||field(lab,"Internal")!=kCFBooleanTrue||field(original,"Internal")!=kCFBooleanTrue||!equals(field(lab,"VolumeName"),"iLinux Boot Lab")||!equals(field(lab,"MountPoint"),LAB_VOLUME)||!equals(field(original,"VolumeName"),ORIGINAL_NAME)||!equals(field(original,"MountPoint"),"/Volumes/Macintosh HD")||!cstring(field(lab,"APFSVolumeGroupID"),group,sizeof(group))||!uuid(group)||!cstring(field(original,"APFSVolumeGroupID"),ogroup,sizeof(ogroup))||!uuid(ogroup)||!strcasecmp(group,ogroup)||!cstring(field(lab,"VolumeUUID"),u,sizeof(u))||!uuid(u)||!cstring(field(original,"VolumeUUID"),ou,sizeof(ou))||!uuid(ou)||!strcasecmp(u,ou)||!cstring(field(lab,"APFSContainerReference"),ref,sizeof(ref))||!device(ref,true)||!cstring(field(original,"APFSContainerReference"),oref,sizeof(oref))||!device(oref,true)||strcmp(ref,oref))goto done;
 CFArrayRef volumes_here=volumes(container_for(list,ref));
 CFDictionaryRef ls=volume_for(volumes_here,"System","iLinux Boot Lab"),os=volume_for(volumes_here,"System",ORIGINAL_NAME),preboot=volume_for(volumes_here,"Preboot",NULL),ld=volume_for(volumes_here,"Data",LAB_DATA_NAME);
 if(!info_matches(lab,ls,ref)||!info_matches(original,os,ref)||!preboot||!ld||!cstring(field(preboot,"DeviceIdentifier"),out->identity.preboot_device,sizeof(out->identity.preboot_device))||!device(out->identity.preboot_device,false)||!cstring(field(ld,"DeviceIdentifier"),out->identity.data_device,sizeof(out->identity.data_device))||!device(out->identity.data_device,false))goto done;
 pb=disk(&b,"preboot_info",out->identity.preboot_device);data=disk(&b,"data_info",out->identity.data_device);
 if(!info_matches(pb,preboot,ref)||!info_matches(data,ld,ref)||field(pb,"Internal")!=kCFBooleanTrue||field(data,"Internal")!=kCFBooleanTrue||!cstring(field(data,"APFSVolumeGroupID"),dgroup,sizeof(dgroup))||strcasecmp(dgroup,group)||!cstring(field(data,"MountPoint"),dmount,sizeof(dmount))||strcmp(dmount,LAB_DATA_MOUNT)||!cstring(field(pb,"VolumeUUID"),out->identity.preboot_uuid,sizeof(out->identity.preboot_uuid))||!uuid(out->identity.preboot_uuid)||!cstring(field(data,"VolumeUUID"),out->identity.data_uuid,sizeof(out->identity.data_uuid))||!uuid(out->identity.data_uuid))goto done;
 if(!cstring(field(pb,"MountPoint"),out->mount,sizeof(out->mount))){fail(r,PS_STATE,PR_PATH_FORMAT);goto done;}
 int observed=kernel_mount_state(c,&b,out->identity.preboot_device);
 if(observed<0){fail(r,PS_STATE,PR_KERNEL_MOUNT_STATE);goto done;}
 out->mounted=observed==1;CFTypeRef mounted=field(pb,"Mounted");
 if(mounted&&mounted!=kCFBooleanTrue&&mounted!=kCFBooleanFalse){fail(r,PS_STATE,PR_MOUNTED_FIELD);goto done;}
 if(mounted&&((mounted==kCFBooleanTrue)!=out->mounted)){fail(r,PS_STATE,PR_STATE_CONTRADICTION);goto done;}
 if(!c->synthetic&&!safe_directory(dmount))goto done;
 strcpy(out->identity.group,group);strcpy(out->identity.original_group,ogroup);strcpy(out->identity.lab_uuid,u);strcpy(out->identity.original_uuid,ou);strcpy(out->identity.container,ref);ok=true;
 done:if(lab)CFRelease(lab);if(original)CFRelease(original);if(list)CFRelease(list);if(pb)CFRelease(pb);if(data)CFRelease(data);
 if(!ok&&r->stage!=PS_STATE)fail(r,PS_IDENTITIES,PR_METADATA);
 return ok;
}
static bool same_identity(const PBMetadata *a,const PBMetadata *b){return !memcmp(&a->identity,&b->identity,sizeof(a->identity));}
static bool mount_binding(PBContext *c,const PBScratch *s,const PBMetadata *m,bool own,bool *readonly){
 *readonly=false;if(!m->mounted||!safe_path(m->mount)||!strcmp(m->mount,LAB_VOLUME)||!strcmp(m->mount,"/Volumes/Macintosh HD")||!strcmp(m->mount,LAB_DATA_MOUNT))return false;
 if(own&&strcmp(m->mount,s->mount))return false;
 if(c->synthetic){if(own&&!c->active)return false;*readonly=setting(c,"read_only_after",true);return setting(c,"mount_binding_valid",true);}
 if(!safe_directory(m->mount)||(own&&!scratch_binding(s)))return false;
 int fd=own?openat(s->fd,"preboot",O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK):directory_fd(m->mount);if(fd<0)return false;
 struct statfs fs;struct stat named,held;char source[80];
 bool ok=!fstatfs(fd,&fs)&&!strcmp(fs.f_mntonname,m->mount)&&source_device(fs.f_mntfromname,source)&&!strcmp(source,m->identity.preboot_device)&&!strcmp(fs.f_fstypename,"apfs")&&!fstat(fd,&held);
 if(own)ok=ok&&!fstatat(s->fd,"preboot",&named,AT_SYMLINK_NOFOLLOW)&&same_inode(&named,&held)&&!same_inode(&held,&s->child);
 if(ok)*readonly=(fs.f_flags&MNT_RDONLY)!=0;close(fd);return ok;
}
static bool underlying_child(const PBScratch *s){
 struct stat current,held;if(!s->child_created||s->child_fd<0||!scratch_binding(s)||fstat(s->child_fd,&held)||fstatat(s->fd,"preboot",&current,AT_SYMLINK_NOFOLLOW))return false;
 return S_ISDIR(current.st_mode)&&same_inode(&current,&s->child)&&same_inode(&held,&s->child);
}
static bool command(PBContext *c,bool mount,const PBMetadata *m,const PBScratch *s,int *exit){
 if(!cwd_binding(s)||!scratch_binding(s)){*exit=-1;return false;}
 if(c->synthetic){*exit=setting_exit(c,mount?"mount_exit":"unmount_exit");if(mount)c->active=*exit==0||setting(c,"partial_mount",false);else if(*exit==0||setting(c,"partial_unmount",false))c->active=false;return *exit==0;}
 char source[80];snprintf(source,sizeof(source),"/dev/%s",m->identity.preboot_device);
 const char *const mount_args[]={"/sbin/mount_apfs","-o","rdonly,nobrowse,nofollow",source,"./preboot",NULL};
 const char *const unmount_args[]={"/sbin/umount","./preboot",NULL};
 uint8_t *data=NULL;size_t n=0;diagnostic_reset(false);bool ok=capture(mount?mount_args:unmount_args,4096,&data,&n);free(data);*exit=diagnostic.command_exit;return ok;
}
bool pb_run(const char *target,const char *original,const char *scratch,const char *fixture,const Profile *profile,PBResult *r){
 PBContext c={.synthetic=fixture!=NULL,.phase="preflight_before"};PBScratch s={.fd=-1,.child_fd=-1};PBMetadata before,again,after;uint8_t *data=NULL;size_t n=0;bool prepared=false;
 interrupted=0;signal(SIGINT,interrupt_handler);signal(SIGTERM,interrupt_handler);signal(SIGHUP,interrupt_handler);
 fail(r,PS_ENVIRONMENT,PR_ENVIRONMENT);
 if(strcmp(target,LAB_VOLUME)||strcmp(original,"/Volumes/Macintosh HD"))goto done;
 if(c.synthetic){
  if(!read_file(fixture,METADATA_LIMIT,true,&data,&n))goto done;
  CFPropertyListRef f=plist((Bytes){data,n});free(data);data=NULL;
  if(!f||CFGetTypeID(f)!=CFDictionaryGetTypeID()){if(f)CFRelease(f);goto done;}c.fixture=f;
  if(field(f,"recovery")!=kCFBooleanTrue||field(f,"root")!=kCFBooleanTrue||!equals(field(f,"model"),"Mac17,6"))goto done;
 }else if(!recovery_admission()||!safe_directory(target)||!safe_directory(original))goto done;
 if(!scratch_open(&s,scratch,c.synthetic)||fchdir(s.fd)||!cwd_binding(&s)){fail(r,PS_SCRATCH,PR_SCRATCH_BINDING);goto done;}
 if(!metadata(&c,&before,r))goto done;
 if(before.mounted){
  r->initial=PI_INVALID;bool ro=false;
  if(!safe_path(before.mount)){fail(r,PS_STATE,PR_PATH_UNSAFE);goto done;}
  if(!mount_binding(&c,&s,&before,false,&ro)){fail(r,PS_STATE,PR_MOUNT_BINDING);goto done;}
  r->initial=PI_MOUNTED_VALID;prepared=true;
 }else{
  r->initial=PI_INVALID;
  if(before.mount[0]){fail(r,PS_STATE,PR_STATE_CONTRADICTION);goto done;}
  r->initial=PI_UNMOUNTED_EMPTY;c.phase="preflight_before_again";
  if(!metadata(&c,&again,r))goto done;
  if(!same_identity(&before,&again)||again.mounted||again.mount[0]){fail(r,PS_REOBSERVATION,PR_IDENTITY_CHANGED);goto done;}
  if(interrupted){fail(r,PS_MOUNT,PR_INTERRUPTED);goto done;}
  if(!c.synthetic&&(access("/sbin/mount_apfs",X_OK)||access("/sbin/umount",X_OK))){fail(r,PS_MOUNT,PR_TOOL_UNAVAILABLE);goto done;}
  if(!scratch_binding(&s)||mkdirat(s.fd,"preboot",0700)){fail(r,PS_SCRATCH,PR_CHILD_EXISTS);goto done;}
  s.child_created=true;s.child_fd=openat(s.fd,"preboot",O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK);
  if(s.child_fd<0||fstat(s.child_fd,&s.child)||s.child.st_uid!=geteuid()||(s.child.st_mode&07777)!=0700||!underlying_child(&s)){fail(r,PS_SCRATCH,PR_SCRATCH_BINDING);goto done;}
  if(interrupted){fail(r,PS_MOUNT,PR_INTERRUPTED);goto done;}
  r->attempted=true;bool mounted_ok=command(&c,true,&before,&s,&r->mount_exit);r->uncertain=true;r->cleanup=PC_REFUSED;
  c.phase="preflight_after";
  if(!metadata(&c,&after,r))goto done;
  if(!same_identity(&before,&after)){fail(r,PS_MOUNT_VERIFICATION,PR_IDENTITY_CHANGED);goto done;}
  if(!after.mounted&&!after.mount[0]&&underlying_child(&s)&&(!c.synthetic||!c.active)){
   r->uncertain=false;r->cleanup=PC_NOT_NEEDED;fail(r,PS_MOUNT,mounted_ok?PR_MOUNT_NOT_OBSERVED:PR_MOUNT_COMMAND);goto done;
  }
  bool ro=false;
  if(!mount_binding(&c,&s,&after,true,&ro)){fail(r,PS_MOUNT_VERIFICATION,PR_MOUNT_BINDING);goto done;}
  r->created=true;r->readonly=ro;r->uncertain=false;
  if(!mounted_ok){fail(r,PS_MOUNT,PR_MOUNT_COMMAND);goto done;}
  if(!ro){fail(r,PS_MOUNT_VERIFICATION,PR_NOT_READ_ONLY);goto done;}
  prepared=true;
 }
 if(prepared&&!interrupted){
  Snapshot snapshot;char group[37];diagnostic_reset(c.synthetic);
  bool ok=collect_snapshot(target,original,profile,fixture,NULL,&snapshot,group);
  if(ok){diagnostic.collected=true;diagnostic_note(DS_INITIAL_ADMISSION,DK_GUARD,DR_INITIAL_ADMISSION_GUARD);ok=validate_snapshot(&snapshot,NULL,profile,NULL,"initial-admission",c.synthetic);if(ok){diagnostic.valid=true;diagnostic_note(DS_INITIAL_ADMISSION,DK_NONE,DR_NONE);}}
  if(!ok)diagnostic_seal();r->diagnostic=diagnostic;r->has_diagnostic=true;fail(r,PS_DIAGNOSTIC,PR_DIAGNOSTIC_REFUSED);
 }else if(interrupted)fail(r,PS_DIAGNOSTIC,PR_INTERRUPTED);
 done:
 if(r->created){
  c.phase="preflight_cleanup";PBMetadata current;bool ro=false;
  if(!metadata(&c,&current,r)||!same_identity(&before,&current)||!mount_binding(&c,&s,&current,true,&ro)){
   r->uncertain=true;r->cleanup=PC_REFUSED;fail(r,PS_CLEANUP,PR_CLEANUP_BINDING);
  }else if(!ro){
   r->uncertain=true;r->cleanup=PC_REFUSED;fail(r,PS_CLEANUP,PR_NOT_READ_ONLY);
  }else{
   bool unmounted_ok=command(&c,false,&current,&s,&r->unmount_exit);
   c.phase="preflight_final";PBMetadata final;
   if(!metadata(&c,&final,r)||!same_identity(&before,&final)){
    r->uncertain=true;r->cleanup=PC_REFUSED;fail(r,PS_CLEANUP,PR_UNMOUNT_NOT_OBSERVED);
   }else if(!final.mounted&&!final.mount[0]&&underlying_child(&s)&&(!c.synthetic||!c.active)){
    r->cleanup=PC_UNMOUNTED;
    if(!unmounted_ok)fail(r,PS_CLEANUP,PR_UNMOUNT_COMMAND);
   }else if(!unmounted_ok&&mount_binding(&c,&s,&final,true,&ro)&&ro){
    r->cleanup=PC_FAILED;fail(r,PS_CLEANUP,PR_UNMOUNT_COMMAND);
   }else{
    r->uncertain=true;r->cleanup=PC_REFUSED;fail(r,PS_CLEANUP,PR_UNMOUNT_NOT_OBSERVED);
   }
  }
 }
 if(s.child_created&&!r->uncertain&&(!r->attempted||r->cleanup==PC_NOT_NEEDED||r->cleanup==PC_UNMOUNTED)){
  if(!underlying_child(&s)){fail(r,PS_CLEANUP,PR_CLEANUP_BINDING);if(r->attempted){r->uncertain=true;r->cleanup=PC_REFUSED;}}
  else if(unlinkat(s.fd,"preboot",AT_REMOVEDIR)){fail(r,PS_CLEANUP,PR_CLEANUP_BINDING);r->cleanup=r->created?PC_FAILED:PC_NOT_NEEDED;}
 }
 if(interrupted&&r->stage!=PS_CLEANUP)fail(r,PS_DIAGNOSTIC,PR_INTERRUPTED);
 if(r->has_diagnostic&&r->diagnostic.valid&&!r->uncertain&&(!r->attempted||r->cleanup==PC_UNMOUNTED)&&r->stage!=PS_CLEANUP&&!interrupted){r->complete=true;r->stage=PS_COMPLETE;r->reason=PR_NONE;}
 if(s.child_fd>=0)close(s.child_fd);if(s.fd>=0)close(s.fd);if(c.fixture)CFRelease(c.fixture);free(data);
 signal(SIGINT,SIG_DFL);signal(SIGTERM,SIG_DFL);signal(SIGHUP,SIG_DFL);return r->complete;
}
