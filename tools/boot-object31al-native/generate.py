#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Add observation-only marks to pinned original project C; verify exact stripping."""
import hashlib
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FROZEN={
 'core.c':'2e9882eae113e24ba2023fa2843fe8447f3da4ec7e022591d5ca46d987bfcdd8',
 'json.c':'a06a21280546f02c3ec330b346b95c9a55872e3712198f18bdee7e8e9bdb240f',
 'reader.h':'bfa3bfe2af667e4b54db1913c80a35d9da4e343cddbc182464d08be674fcbf99',
 'state.c':'31e97a75f1fe5dbd1dfe3585a15822c56ee86156d2a3cc52c39e304f1dd4d08a',
}

def mark(code):return '/*31AL+*/'+code+'/*31AL-*/'
def once(text,old,new):
 if text.count(old)!=1:raise ValueError('observation anchor mismatch: '+old[:64])
 return text.replace(old,new,1)
def test(text,condition,stage='DS_KEEP',kind='DK_FORMAT',reason='DR_MALFORMED_FIELD'):
 return once(text,condition,'D_TEST(('+condition+'),'+stage+','+kind+','+reason+')')
def region(text,begin,end,change):
 a=text.index(begin);b=text.index(end,a)
 return text[:a]+change(text[a:b])+text[b:]

def instrument(source):
 text=once(source,'#include "reader.h"\n','#include "reader.h"\n'+mark('#include "diagnostic.h"\n'))
 def capture(s):
  s=once(s,'    int pipefd[2];',mark('diagnostic_capture_begin(argv);')+'    int pipefd[2];')
  s=s.replace('return false;','return D_FALSE(DS_KEEP,DK_CAPTURE,DR_CAPTURE_SETUP);')
  s=once(s,'if(r==child){child=-1;','if(r==child){'+mark('diagnostic_capture_status(status);')+'child=-1;')
  s=test(s,'n>cap',kind='DK_CAPTURE',reason='DR_CAPTURE_BOUND')
  s=once(s,'if(!eof)goto done;','if(D_TEST((!eof),DS_KEEP,DK_CAPTURE,DR_CAPTURE_TIMEOUT))goto done;')
  s=once(s,'    close(pipefd[0]);if(ok)',mark('diagnostic_capture_end(n,ok);')+'    close(pipefd[0]);if(ok)')
  return s
 text=region(text,'static bool capture(','\nstatic CFTypeRef field',capture)
 def disk(s):
  s=once(s,'    if(b->fixture)',mark('diagnostic_source(which);')+'    if(b->fixture)')
  s=once(s,'return v&&CFGetTypeID(v)==CFDictionaryGetTypeID()?CFRetain(v):NULL;',
      'return v&&CFGetTypeID(v)==CFDictionaryGetTypeID()?CFRetain(v):'+mark('diagnostic_null(DK_FORMAT,DR_PLIST_DICTIONARY)')+'NULL;')
  # Comma expression observes a NULL result without modifying the ternary predicate.
  s=s.replace(mark('diagnostic_null(DK_FORMAT,DR_PLIST_DICTIONARY)')+'NULL','('+mark('diagnostic_fail(DS_KEEP,DK_FORMAT,DR_PLIST_DICTIONARY),')+'NULL)')
  s=once(s,'if(p&&CFGetTypeID(p)!=CFDictionaryGetTypeID())', 'if(p&&CFGetTypeID(p)!=CFDictionaryGetTypeID())')
  s=once(s,'CFRelease(p);p=NULL;',mark('diagnostic_fail(DS_KEEP,DK_FORMAT,DR_PLIST_DICTIONARY);')+'CFRelease(p);p=NULL;')
  s=once(s,'return (CFDictionaryRef)p;',mark('if(!p)diagnostic_fail(DS_KEEP,DK_FORMAT,DR_PLIST_DICTIONARY);')+'return (CFDictionaryRef)p;')
  return s
 text=region(text,'static CFDictionaryRef disk(','\nstatic CFDictionaryRef apfs',disk)
 def apfs(s):
  s=once(s,'{if(b->fixture)','{'+mark('diagnostic_note(DS_APFS_LIST,DK_FORMAT,DR_PLIST_DICTIONARY);')+'if(b->fixture)')
  s=once(s,'return v&&CFGetTypeID(v)==CFDictionaryGetTypeID()?CFRetain(v):NULL;',
      'return v&&CFGetTypeID(v)==CFDictionaryGetTypeID()?CFRetain(v):('+mark('diagnostic_fail(DS_KEEP,DK_FORMAT,DR_PLIST_DICTIONARY),')+'NULL);')
  s=once(s,'CFRelease(p);p=NULL;',mark('diagnostic_fail(DS_KEEP,DK_FORMAT,DR_PLIST_DICTIONARY);')+'CFRelease(p);p=NULL;')
  s=once(s,'return (CFDictionaryRef)p;',mark('if(!p)diagnostic_fail(DS_KEEP,DK_FORMAT,DR_PLIST_DICTIONARY);')+'return (CFDictionaryRef)p;')
  return s
 text=region(text,'static CFDictionaryRef apfs(','\nstatic bool uuid',apfs)
 def policy(s):
  s=once(s,'    if(!bytes.n',mark('diagnostic_note(DS_KEEP,DK_FORMAT,DR_POLICY_INPUT);')+'    if(!bytes.n')
  s=s.replace('return false;','return D_FALSE(DS_KEEP,DK_FORMAT,DR_POLICY_INPUT);')
  specs=[
   ('strlen(line)>2048','DK_FORMAT','DR_POLICY_BOUND'),
   ('mode_seen++','DK_FORMAT','DR_DUPLICATE_FIELD'),
   ('current_seen++||strlen(v)>=sizeof(current)','DK_FORMAT','DR_DUPLICATE_OR_MALFORMED'),
   ('old_seen++||strlen(v)>=sizeof(old)','DK_FORMAT','DR_DUPLICATE_OR_MALFORMED'),
   ('ctrr_seen++||strlen(v)>=sizeof(ctrr)','DK_FORMAT','DR_DUPLICATE_OR_MALFORMED'),
   ('!length||length>=sizeof(tags)','DK_FORMAT','DR_MALFORMED_TAGS'),
   ('!tag_list(tags)','DK_FORMAT','DR_MALFORMED_TAGS'),
   ('strlen(tag)!=4','DK_FORMAT','DR_MALFORMED_TAGS'),
   ('++count>4','DK_FORMAT','DR_CARDINALITY'),
   ('seen[i]++','DK_FORMAT','DR_SEMANTIC_DUPLICATE_BASE+i'),
   ('!value_string(after,i==5,out->semantic[i])','DK_FORMAT','DR_SEMANTIC_MALFORMED_BASE+i'),
   ('sip2_seen++','DK_FORMAT','DR_DUPLICATE_FIELD'),
   ('!value_string(after,false,sip2)','DK_FORMAT','DR_MALFORMED_FIELD'),
   ('coih++','DK_FORMAT','DR_DUPLICATE_FIELD'),
   ('!object_reference(after,out->coih)','DK_FORMAT','DR_MALFORMED_FIELD'),
   ('nsih++','DK_FORMAT','DR_DUPLICATE_FIELD'),
   ('!object_reference(after,out->nsih)','DK_FORMAT','DR_MALFORMED_FIELD'),
   ('at>=2','DK_FORMAT','DR_RPNH_CARDINALITY'),
   ('!private_hash(after,out->rpnh[at])','DK_FORMAT','DR_RPNH_MALFORMED'),
   ('out->metadata_seen[1]++','DK_FORMAT','DR_RONH_DUPLICATE'),
   ('!private_hash(after,out->ronh)','DK_FORMAT','DR_RONH_MALFORMED'),
   ('out->metadata_seen[2]++','DK_FORMAT','DR_SPIH_DUPLICATE'),
   ('!private_hash(after,out->spih)','DK_FORMAT','DR_SPIH_MALFORMED'),
   ('out->metadata_seen[3]++','DK_FORMAT','DR_STNG_DUPLICATE'),
   ('!private_counter(after,out->stng)','DK_FORMAT','DR_STNG_MALFORMED'),
   ('seen[i]!=1','DK_FORMAT','DR_SEMANTIC_MISSING_BASE+i'),
      ('out->metadata_seen[0]!=2','DK_FORMAT','DR_RPNH_CARDINALITY'),
   ('out->metadata_seen[1]!=1','DK_FORMAT','DR_RONH_CARDINALITY'),
   ('out->metadata_seen[2]!=1','DK_FORMAT','DR_SPIH_CARDINALITY'),
   ('out->metadata_seen[3]!=1','DK_FORMAT','DR_STNG_CARDINALITY'),
   ('mode_seen!=1||coih!=1||nsih!=1','DK_FORMAT','DR_MISSING_FIELD'),
   ('(!out->nsih[0]&&out->coih[0])||(paired&&unpaired)','DK_CONSISTENCY','DR_POLICY_CONTRADICTION'),
   ('sip2_seen&&strcmp(sip2,"ABSENT")&&strcmp(sip2,"false")','DK_CONSISTENCY','DR_POLICY_CONTRADICTION'),
   ('!sip2_seen||strcmp(sip2,"true")','DK_CONSISTENCY','DR_POLICY_CONTRADICTION'),
   ('!strcmp(out->mode,"Full")&&(!strcmp(out->semantic[0],"true")||!strcmp(out->semantic[1],"true"))','DK_CONSISTENCY','DR_POLICY_CONTRADICTION'),
   ('!strcmp(out->mode,"Permissive")&&(strcmp(out->semantic[0],"true")||strcmp(out->semantic[1],"true"))','DK_CONSISTENCY','DR_POLICY_CONTRADICTION'),
  ]
  for condition,kind,reason in specs:s=test(s,condition,kind=kind,reason=reason)
  s=s.replace('refusal_reason="unsupportedPolicyMetadata";', 'refusal_reason="unsupportedPolicyMetadata";'+mark('diagnostic_fail(DS_KEEP,DK_FORMAT,DR_UNSUPPORTED_METADATA);'))
  s=once(s,'done:free(copy);return ok;', 'done:'+mark('if(!ok)diagnostic_fail(DS_KEEP,DK_FORMAT,DR_MALFORMED_FIELD);')+'free(copy);return ok;')
  return s
 text=region(text,'static bool policy(Bytes','\nstatic bool policy_for',policy)
 def policy_for(s):
  s=once(s,'    uint8_t *data=NULL;',mark('diagnostic_source(key);')+'    uint8_t *data=NULL;')
  s=s.replace('return false;','return D_FALSE(DS_KEEP,DK_FORMAT,DR_POLICY_INPUT);')
  # capture failures already lock CAPTURE; this final fallback cannot overwrite them.
  s=once(s,'done:free(data);return ok;', 'done:'+mark('if(!ok)diagnostic_fail(DS_KEEP,DK_FORMAT,DR_POLICY_INPUT);')+'free(data);return ok;')
  return s
 text=region(text,'static bool policy_for(','\nbool recovery_admission',policy_for)
 def admission(s):
  s=once(s,'{struct stat s;', '{'+mark('diagnostic_note(DS_RECOVERY_ENVIRONMENT,DK_GUARD,DR_RECOVERY_ENVIRONMENT);')+'struct stat s;')
  s=s.replace('return false;','return D_FALSE(DS_KEEP,DK_GUARD,DR_RECOVERY_ENVIRONMENT);')
  s=once(s,'free(data);return ok;',mark('if(!ok)diagnostic_fail(DS_RECOVERY_ENVIRONMENT,DK_GUARD,DR_MACHINE_MODEL);')+'free(data);return ok;')
  return s
 text=region(text,'bool recovery_admission(','\n\nbool collect_snapshot',admission)
 def collect(s):
  s=once(s,'    memset(out,0,sizeof(*out));',mark('diagnostic_note(DS_TARGET_PATHS,DK_GUARD,DR_TARGET_PATHS);')+'    memset(out,0,sizeof(*out));')
  s=s.replace('return false;','return D_FALSE(DS_KEEP,DK_GUARD,DR_TARGET_PATHS);')
  s=test(s,'!read_file(fixture,METADATA_LIMIT,true,&data,&n)','DS_FIXTURE_READ','DK_FORMAT','DR_FIXTURE_INPUT')
  s=once(s,'CFPropertyListRef f=plist((Bytes){data,n});',mark('diagnostic_note(DS_FIXTURE_FORMAT,DK_FORMAT,DR_PLIST_DICTIONARY);')+'CFPropertyListRef f=plist((Bytes){data,n});')
  s=test(s,'field(f,"recovery")!=kCFBooleanTrue||field(f,"root")!=kCFBooleanTrue||!equals(field(f,"model"),"Mac17,6")','DS_RECOVERY_ENVIRONMENT','DK_GUARD','DR_RECOVERY_ENVIRONMENT')
  s=test(s,'!recovery_admission()||!safe_directory(target_path)||!safe_directory(original_path)','DS_TARGET_MOUNTS','DK_GUARD','DR_MOUNT_PATHS')
  s=once(s,'    char group[64]',mark('diagnostic_note(DS_SYSTEM_IDENTITIES,DK_GUARD,DR_SYSTEM_IDENTITIES);')+'    char group[64]')
  s=test(s,'strcmp(ref,oref)','DS_SYSTEM_IDENTITIES','DK_GUARD','DR_CONTAINER_MISMATCH')
  s=once(s,'    CFArrayRef lv=',mark('diagnostic_note(DS_VOLUME_ROLES,DK_GUARD,DR_VOLUME_ROLES);')+'    CFArrayRef lv=')
  s=once(s,'    char pbdev[64]',mark('diagnostic_note(DS_AUX_IDENTITIES,DK_GUARD,DR_AUX_IDENTITIES);')+'    char pbdev[64]')
  s=once(s,'    char mount[PATH_MAX]',mark('diagnostic_note(DS_AUX_IDENTITIES,DK_GUARD,DR_AUX_IDENTITIES);')+'    char mount[PATH_MAX]')
  s=test(s,'!b.fixture&&(!safe_directory(mount)||!safe_directory(dmount))','DS_AUX_MOUNTS','DK_GUARD','DR_MOUNT_PATHS')
  for condition,stage,reason in [
   ('!lp.one_true','DS_RECOVERY_PAIRING','DR_NOT_ONE_TRUE_RECOVERY'),
   ('!lp.paired','DS_RECOVERY_PAIRING','DR_NOT_PAIRED'),
   ('strcmp(lp.mode,"Permissive")','DS_SECURITY_GUARDS','DR_LAB_SECURITY_GUARD'),
   ('strcmp(op.mode,"Full")','DS_SECURITY_GUARDS','DR_ORIGINAL_SECURITY_GUARD'),
   ('strcmp(op.ctrr,"enabled")','DS_SECURITY_GUARDS','DR_ORIGINAL_CTRR_GUARD')]:
   s=test(s,condition,stage,'DK_GUARD',reason)
  for condition,stage,kind,reason in [
   ('!lab||!original||!list','DS_SYSTEM_IDENTITIES','DK_FORMAT','DR_LAB_INFO_PRESENT'),
   ('field(lab,"Internal")!=kCFBooleanTrue','DS_SYSTEM_IDENTITIES','DK_GUARD','DR_LAB_INTERNAL_TRUE'),
   ('field(original,"Internal")!=kCFBooleanTrue','DS_SYSTEM_IDENTITIES','DK_GUARD','DR_ORIGINAL_INTERNAL_TRUE'),
   ('!equals(field(lab,"VolumeName"),"iLinux Boot Lab")','DS_SYSTEM_IDENTITIES','DK_GUARD','DR_LAB_NAME'),
   ('!equals(field(lab,"MountPoint"),target_path)','DS_SYSTEM_IDENTITIES','DK_GUARD','DR_LAB_MOUNT'),
   ('!equals(field(original,"VolumeName"),ORIGINAL_NAME)','DS_SYSTEM_IDENTITIES','DK_GUARD','DR_ORIGINAL_NAME'),
   ('!equals(field(original,"MountPoint"),original_path)','DS_SYSTEM_IDENTITIES','DK_GUARD','DR_ORIGINAL_MOUNT'),
   ('!cstring(field(lab,"APFSVolumeGroupID"),group,sizeof(group))','DS_SYSTEM_IDENTITIES','DK_FORMAT','DR_LAB_GROUP_FORMAT'),
   ('!uuid(group)','DS_SYSTEM_IDENTITIES','DK_FORMAT','DR_LAB_GROUP_FORMAT'),
   ('!cstring(field(original,"APFSVolumeGroupID"),ogroup,sizeof(ogroup))','DS_SYSTEM_IDENTITIES','DK_FORMAT','DR_ORIGINAL_GROUP_FORMAT'),
   ('!uuid(ogroup)','DS_SYSTEM_IDENTITIES','DK_FORMAT','DR_ORIGINAL_GROUP_FORMAT'),
   ('!strcasecmp(group,ogroup)','DS_SYSTEM_IDENTITIES','DK_GUARD','DR_DISTINCT_GROUPS'),
   ('!cstring(field(lab,"VolumeUUID"),u,sizeof(u))','DS_SYSTEM_IDENTITIES','DK_FORMAT','DR_LAB_UUID_FORMAT'),
   ('!uuid(u)','DS_SYSTEM_IDENTITIES','DK_FORMAT','DR_LAB_UUID_FORMAT'),
   ('!cstring(field(original,"VolumeUUID"),ou,sizeof(ou))','DS_SYSTEM_IDENTITIES','DK_FORMAT','DR_ORIGINAL_UUID_FORMAT'),
   ('!uuid(ou)','DS_SYSTEM_IDENTITIES','DK_FORMAT','DR_ORIGINAL_UUID_FORMAT'),
   ('!strcasecmp(u,ou)','DS_SYSTEM_IDENTITIES','DK_GUARD','DR_DISTINCT_UUIDS'),
   ('!cstring(field(lab,"APFSContainerReference"),ref,sizeof(ref))','DS_SYSTEM_IDENTITIES','DK_FORMAT','DR_LAB_CONTAINER_FORMAT'),
   ('!device(ref,true)','DS_SYSTEM_IDENTITIES','DK_FORMAT','DR_LAB_CONTAINER_FORMAT'),
   ('!cstring(field(original,"APFSContainerReference"),oref,sizeof(oref))','DS_SYSTEM_IDENTITIES','DK_FORMAT','DR_ORIGINAL_CONTAINER_FORMAT'),
   ('!device(oref,true)','DS_SYSTEM_IDENTITIES','DK_FORMAT','DR_ORIGINAL_CONTAINER_FORMAT'),
   ('!info_matches(lab,lsystem,ref)','DS_VOLUME_ROLES','DK_GUARD','DR_LAB_SYSTEM_MATCH'),
   ('!info_matches(original,osystem,oref)','DS_VOLUME_ROLES','DK_GUARD','DR_ORIGINAL_SYSTEM_MATCH'),
   ('!preboot','DS_VOLUME_ROLES','DK_GUARD','DR_PREBOOT_ROLE_PRESENT'),
   ('!lData','DS_VOLUME_ROLES','DK_GUARD','DR_DATA_ROLE_PRESENT'),
   ('!cstring(field(preboot,"DeviceIdentifier"),pbdev,sizeof(pbdev))','DS_AUX_IDENTITIES','DK_FORMAT','DR_PREBOOT_DEVICE_FORMAT'),
   ('!cstring(field(lData,"DeviceIdentifier"),datadev,sizeof(datadev))','DS_AUX_IDENTITIES','DK_FORMAT','DR_DATA_DEVICE_FORMAT'),
   ('!info_matches(pbinfo,preboot,ref)','DS_AUX_IDENTITIES','DK_GUARD','DR_PREBOOT_INFO_MATCH'),
   ('!info_matches(dinfo,lData,ref)','DS_AUX_IDENTITIES','DK_GUARD','DR_DATA_INFO_MATCH'),
   ('field(pbinfo,"Internal")!=kCFBooleanTrue','DS_AUX_IDENTITIES','DK_GUARD','DR_PREBOOT_INTERNAL_TRUE'),
   ('field(dinfo,"Internal")!=kCFBooleanTrue','DS_AUX_IDENTITIES','DK_GUARD','DR_DATA_INTERNAL_TRUE'),
   ('!cstring(field(dinfo,"APFSVolumeGroupID"),dgroup,sizeof(dgroup))','DS_AUX_IDENTITIES','DK_FORMAT','DR_DATA_GROUP_FORMAT'),
   ('strcasecmp(dgroup,group)','DS_AUX_IDENTITIES','DK_GUARD','DR_DATA_GROUP_MATCH'),
   ('!cstring(field(pbinfo,"MountPoint"),mount,sizeof(mount))','DS_AUX_IDENTITIES','DK_FORMAT','DR_PREBOOT_MOUNT_FORMAT'),
   ('!cstring(field(dinfo,"MountPoint"),dmount,sizeof(dmount))','DS_AUX_IDENTITIES','DK_FORMAT','DR_DATA_MOUNT_FORMAT'),
   ('!safe_path(mount)','DS_AUX_IDENTITIES','DK_GUARD','DR_PREBOOT_MOUNT_PATH'),
   ('!safe_path(dmount)','DS_AUX_IDENTITIES','DK_GUARD','DR_DATA_MOUNT_PATH'),
   ('strcmp(dmount,LAB_DATA_MOUNT)','DS_AUX_IDENTITIES','DK_GUARD','DR_DATA_MOUNT_MATCH'),
   ('!strcmp(mount,target_path)||!strcmp(mount,original_path)||!strcmp(mount,dmount)','DS_AUX_IDENTITIES','DK_GUARD','DR_PREBOOT_DISTINCT_MOUNTS')]:
   s=test(s,condition,stage,kind,reason)
  s=once(s,'    strcpy(out->selected,"NONE");',mark('diagnostic_note(DS_SELECTED_OBJECT,DK_GUARD,DR_SELECTED_OBJECT);')+'    strcpy(out->selected,"NONE");')
  s=test(s,'length<0||(size_t)length>=sizeof(selected)','DS_SELECTED_OBJECT','DK_FORMAT','DR_OBJECT_PATH_BOUND')
  s=test(s,'!cstring(field(b.fixture,"selected_file"),fixture_file,sizeof(fixture_file))','DS_SELECTED_OBJECT','DK_FORMAT','DR_FIXTURE_INPUT')
  s=test(s,'memcmp(&lp,&la,sizeof(lp))||memcmp(&op,&oa,sizeof(op))','DS_POLICY_COMPARISON','DK_CONSISTENCY','DR_POLICY_CHANGED')
  s=once(s,'    strcpy(private_group,group);ok=true;',mark('diagnostic_note(DS_COLLECTION_COMPLETE,DK_NONE,DR_NONE);')+'    strcpy(private_group,group);ok=true;')
  s=once(s,'done:free(data);', 'done:'+mark('if(!ok)diagnostic_seal();')+'free(data);')
  return s
 text=region(text,'bool collect_snapshot(','\nstatic void print_semantics',collect)
 return text

def arguments(text,start):
 # Split one macro invocation while respecting parentheses and C string literals.
 depth=1;at=start;begin=start;parts=[];quote=None;escape=False
 while at<len(text):
  c=text[at]
  if quote:
   if escape:escape=False
   elif c=='\\':escape=True
   elif c==quote:quote=None
  elif c in ('"',"'"):quote=c
  elif c=='(':depth+=1
  elif c==')':
   depth-=1
   if depth==0:parts.append(text[begin:at]);return parts,at+1
  elif c==',' and depth==1:parts.append(text[begin:at]);begin=at+1
  at+=1
 raise ValueError('unbalanced observation macro')

def strip(text):
 text=re.sub(r'/\*31AL\+\*/.*?/\*31AL-\*/','',text,flags=re.S)
 # Remove only the extra parentheses around observed predicates/false constants.
 while True:
  match=re.search(r'\b(D_TEST|D_FALSE)\(',text)
  if not match:break
  args,end=arguments(text,match.end())
  if match.group(1)=='D_FALSE':
   if len(args)!=3:raise ValueError('false marker shape')
   replacement='false'
  else:
   if len(args)!=4 or not args[0].startswith('(') or not args[0].endswith(')'):raise ValueError('test marker shape')
   replacement=args[0][1:-1]
  text=text[:match.start()]+replacement+text[end:]
 # A NULL observation needs its comma-expression parentheses removed as well.
 text=text.replace(':('+'NULL)',':NULL')
 return text

def generate(output):
 output=Path(output)
 if output.exists():raise ValueError('new generated source directory required')
 data={}
 for name,expected in FROZEN.items():
  blob=(ROOT/'tools/boot-object31aj-native'/name).read_bytes()
  if hashlib.sha256(blob).hexdigest()!=expected:raise ValueError('frozen source changed')
  data[name]=blob
 marked=instrument(data['state.c'].decode())
 if strip(marked).encode()!=data['state.c']:raise ValueError('observation stripping not exact')
 output.mkdir(parents=True,mode=0o700)
 for name,blob in data.items():(output/name).write_bytes(marked.encode() if name=='state.c' else blob)
 return {'frozen_sources':FROZEN,'core_json_reader_byte_identical':True,'state_marks_strip_exact':True}
