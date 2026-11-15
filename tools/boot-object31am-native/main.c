/* SPDX-License-Identifier: MIT */
#include "preboot.h"
#include <mach-o/dyld.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc,char **argv){
 PBResult result;pb_reset(&result,false);
 if(argc==1||(argc==2&&(!strcmp(argv[1],"--help")||!strcmp(argv[1],"-h")))){
  puts("ilinux31am conditional read-only Preboot companion\nDefault/help: inert; no host query.\n --preboot-diagnose --target-volume LAB --original-volume ORIGINAL --profile FILE --scratch DIR\n --diagnose-fixture WORKSPACE_PLIST --profile FILE --scratch WORKSPACE_DIR\n --validate-result FILE --profile FILE\nNo install, policy write, repair, remount, force or native boot mode.");return 0;
 }
 const char *mode=NULL,*input=NULL,*profile_path=NULL,*target=NULL,*original=NULL,*scratch=NULL;unsigned seen=0;
 for(int i=1;i<argc;i++){
  const char *a=argv[i];
  if(!strcmp(a,"--preboot-diagnose")||!strcmp(a,"--diagnose-fixture")||!strcmp(a,"--validate-result")){
   if(mode)goto done;mode=a;
   if(!strcmp(a,"--diagnose-fixture"))result.synthetic=true;
   if(strcmp(a,"--preboot-diagnose")){if(++i==argc)goto done;input=argv[i];}continue;
  }
  const char **slot=NULL;unsigned bit=0;
  if(!strcmp(a,"--profile")){slot=&profile_path;bit=1;}
  else if(!strcmp(a,"--target-volume")){slot=&target;bit=2;}
  else if(!strcmp(a,"--original-volume")){slot=&original;bit=4;}
  else if(!strcmp(a,"--scratch")){slot=&scratch;bit=8;}else goto done;
  if(seen&bit||++i==argc)goto done;seen|=bit;*slot=argv[i];
 }
 if(!mode||!profile_path)goto done;
 bool validation=!strcmp(mode,"--validate-result"),fixture=!strcmp(mode,"--diagnose-fixture");
 if(validation){if(seen!=1)goto done;}
 else if(fixture){if(seen!=9)goto done;target=LAB_VOLUME;original="/Volumes/Macintosh HD";}
 else if(seen!=15||strcmp(target,LAB_VOLUME)||strcmp(original,"/Volumes/Macintosh HD"))goto done;
 result.stage=PS_PROFILE;result.reason=PR_PROFILE_BINDING;
 char input_exe[PATH_MAX],exe[PATH_MAX];uint32_t cap=sizeof(input_exe);Profile profile;
 if(_NSGetExecutablePath(input_exe,&cap)||!realpath(input_exe,exe)||!load_profile(profile_path,exe,&profile))goto done;
 if(validation){
  result.stage=PS_VALIDATION;result.reason=PR_RESULT_FORMAT;
  if(!pb_load(input,&result))goto done;
  return pb_print(&result)?0:2;
 }
 pb_run(target,original,scratch,fixture?input:NULL,&profile,&result);
 done:return pb_print(&result)&&result.complete?0:2;
}
