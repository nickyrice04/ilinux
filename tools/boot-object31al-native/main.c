/* SPDX-License-Identifier: MIT */
#include "diagnostic.h"
#include <mach-o/dyld.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void help(void){puts("ilinux31al diagnostic-only read-only companion\nDefault: help; no host query. Modes:\n --diagnose-snapshot --target-volume LAB --original-volume ORIGINAL --profile FILE\n --diagnose-fixture WORKSPACE_PLIST --profile FILE\n --validate-diagnostic FILE --profile FILE\nNo installation, RNG, private-identifier, full-snapshot or phase/write modes.");}
int main(int argc,char **argv){
 const char *mode=NULL,*input=NULL,*profile_path=NULL,*target=NULL,*original=NULL;unsigned seen=0;
 diagnostic_reset(false);
 if(argc==1){help();return 0;}
 for(int i=1;i<argc;i++){
  const char *a=argv[i];if((!strcmp(a,"--help")||!strcmp(a,"-h"))&&argc==2){help();return 0;}
  if(!strcmp(a,"--diagnose-snapshot")||!strcmp(a,"--diagnose-fixture")||!strcmp(a,"--validate-diagnostic")){
   if(mode)goto fail;mode=a;if(!strcmp(a,"--diagnose-fixture"))diagnostic.synthetic=true;
   if(strcmp(a,"--diagnose-snapshot")){if(++i==argc)goto fail;input=argv[i];}continue;
  }
  const char **slot=NULL;unsigned bit=0;
  if(!strcmp(a,"--profile")){slot=&profile_path;bit=1;}else if(!strcmp(a,"--target-volume")){slot=&target;bit=2;}else if(!strcmp(a,"--original-volume")){slot=&original;bit=4;}else goto fail;
  if(seen&bit||++i==argc)goto fail;seen|=bit;*slot=argv[i];
 }
 if(!mode||!profile_path)goto fail;
 bool fixture=!strcmp(mode,"--diagnose-fixture"),validation=!strcmp(mode,"--validate-diagnostic");
 if(fixture||validation){if(seen!=1)goto fail;}else if(seen!=7||strcmp(target,LAB_VOLUME)||strcmp(original,"/Volumes/Macintosh HD"))goto fail;
 diagnostic_note(DS_PROFILE,DK_FORMAT,DR_PROFILE_BINDING);
 char exe_input[PATH_MAX],exe[PATH_MAX];uint32_t capacity=sizeof(exe_input);Profile profile;
 if(_NSGetExecutablePath(exe_input,&capacity)||!realpath(exe_input,exe)||!load_profile(profile_path,exe,&profile))goto fail;
 if(validation){Diagnostic value;diagnostic_note(DS_DIAGNOSTIC_VALIDATION,DK_FORMAT,DR_DIAGNOSTIC_FORMAT);if(!diagnostic_load(input,&value))goto fail;diagnostic_print(&value);return 0;}
 Snapshot snapshot;char private_group[37];
 if(!collect_snapshot(fixture?LAB_VOLUME:target,fixture?"/Volumes/Macintosh HD":original,&profile,fixture?input:NULL,NULL,&snapshot,private_group))goto fail;
 diagnostic.collected=true;diagnostic_note(DS_INITIAL_ADMISSION,DK_GUARD,DR_INITIAL_ADMISSION_GUARD);
 if(!validate_snapshot(&snapshot,NULL,&profile,NULL,"initial-admission",fixture))goto fail;
 diagnostic.valid=true;diagnostic_note(DS_INITIAL_ADMISSION,DK_NONE,DR_NONE);diagnostic_print(&diagnostic);return 0;
 fail:diagnostic_seal();diagnostic_print(&diagnostic);return 2;
}
