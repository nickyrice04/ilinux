/* SPDX-License-Identifier: MIT */
/* Pure fixture probe. No collector, filesystem, policy API or writer is linked.
 * Every value below is synthetic, including the public fixture comparison key.
 * KUID is tested as a typed KEK context; it is not a human owner identity. */
#include "policy_contract.h"
#include <stdio.h>
#include <string.h>
#include <ctype.h>

typedef struct { unsigned checks, failed; } Checks;
#define CHECK(c, expression) do { (c)->checks++; if (!(expression)) (c)->failed++; } while (0)
typedef struct {
 PolicyIdentity31AX lab, original;
 PolicyExtras lab_extra, original_extra;
 Profile profile; ComparisonKey key;
 char lab_group[97], original_group[97], lab_nsih[129], original_nsih[129], original_coih[129];
} Fixture;

static void synthetic_uuid(char out[97], unsigned value) {
 snprintf(out,97,"%08x-1111-4111-8111-%012llx",value,(unsigned long long)value);
}
static void synthetic_hash(char *out, size_t length, char value) {
 memset(out,value,length);out[length]=0;
}
static bool identity(PolicyIdentity31AX *out, const char *group, unsigned context) {
 memset(out,0,sizeof(*out));char kuid[97],hash[97];synthetic_uuid(kuid,context);
 const char *tags[]={"BORD","CHIP","ECID","vuid","kuid","lpnh","lpnh","auxp","auxi","auxr"};
 synthetic_hash(hash,96,'a');
 const char *values[]={"0x64","0x6050","0x1234",group,kuid,hash,hash,"absent","absent","absent"};
 for(unsigned i=0;i<10;i++)if(policy_identity_set31ax(out,tags[i],values[i])!=1)return false;
 return policy_identity_complete31ax(out);
}
static bool extras(PolicyExtras *out) {
 memset(out,0,sizeof(*out));
 const char *values[]={"0x1","0x2","true","true","false","1.2.3.4.5,6"};
 for(unsigned i=0;i<POLICY_EXTRA_COUNT;i++)if(policy_extra_set(out,policy_extra_tag(i),values[i])!=1)return false;
 return true;
}
static bool fixture(Fixture *f) {
 memset(f,0,sizeof(*f));synthetic_uuid(f->lab_group,0x11);synthetic_uuid(f->original_group,0x22);
 synthetic_hash(f->profile.sha,64,'b');synthetic_hash(f->key.id,64,'c');
 for(unsigned i=0;i<sizeof(f->key.bytes);i++)f->key.bytes[i]=(unsigned char)(i+0x31);
 f->key.loaded=true;synthetic_hash(f->lab_nsih,96,'d');
 synthetic_hash(f->original_nsih,96,'e');synthetic_hash(f->original_coih,96,'f');
 return identity(&f->lab,f->lab_group,0x33)&&identity(&f->original,f->original_group,0x44)&&
  extras(&f->lab_extra)&&extras(&f->original_extra);
}
static bool capture(Fixture *f) {
 return policy_view_capture31ax(&f->lab,&f->original,&f->lab_extra,&f->original_extra,
  f->lab_nsih,f->original_nsih,f->original_coih,f->lab_group,f->original_group,&f->profile,&f->key);
}
static bool capture_references(Fixture *f,const char *lab_nsih,const char *original_nsih,const char *original_coih) {
 return policy_view_capture31ax(&f->lab,&f->original,&f->lab_extra,&f->original_extra,
  lab_nsih,original_nsih,original_coih,f->lab_group,f->original_group,&f->profile,&f->key);
}
static bool change_extra(PolicyExtras *out, unsigned index, const char *value) {
 out->seen[index]=0;return policy_extra_set(out,policy_extra_tag(index),value)==1;
}
static void extra_digest(const PolicyExtras *out, const ComparisonKey *key, unsigned char digest[32]) {
 CCHmacContext context;CCHmacInit(&context,kCCHmacAlgSHA256,key->bytes,sizeof(key->bytes));
 policy_extra_commit(out,&context);CCHmacFinal(&context,digest);
}

static void required_counts(Checks *c) {
 Fixture f;CHECK(c,fixture(&f));CHECK(c,policy_identity_complete31ax(&f.lab));
 for(unsigned i=0;i<9;i++){PolicyIdentity31AX p=f.lab;p.seen[i]--;CHECK(c,!policy_identity_complete31ax(&p));}
 PolicyIdentity31AX p=f.lab;p.seen[5]=3;CHECK(c,!policy_identity_complete31ax(&p));
 for(unsigned i=9;i<12;i++){
  p=f.lab;p.seen[i]=2;CHECK(c,!policy_identity_complete31ax(&p));
  p=f.lab;CHECK(c,policy_identity_set31ax(&p,(const char*[]){"prot","hrlp","losv"}[i-9],"absent")==1);
  CHECK(c,policy_identity_complete31ax(&p));
 }
}
static void duplicate_tags(Checks *c) {
 Fixture f;CHECK(c,fixture(&f));
 const char *tags[]={"BORD","CHIP","ECID","vuid","kuid","lpnh","auxp","auxi","auxr"};
 const char *values[]={"0x64","0x6050","0x1234",f.lab_group,f.lab_group,f.lab.lpnh[0],"absent","absent","absent"};
 for(unsigned i=0;i<9;i++){PolicyIdentity31AX p=f.lab;CHECK(c,policy_identity_set31ax(&p,tags[i],values[i])==-1);}
 for(unsigned i=0;i<3;i++){
  PolicyIdentity31AX p=f.lab;const char *tag=(const char*[]){"prot","hrlp","losv"}[i];
  CHECK(c,policy_identity_set31ax(&p,tag,"absent")==1);CHECK(c,policy_identity_set31ax(&p,tag,"absent")==-1);
 }
 PolicyIdentity31AX p=f.lab;CHECK(c,policy_identity_set31ax(&p,"ZZZZ","absent")==0);
 CHECK(c,!memcmp(&p,&f.lab,sizeof(p)));
}
static void uuid_grammar(Checks *c) {
 char value[97];synthetic_uuid(value,0xabcd);PolicyIdentity31AX p={0};
 for(size_t i=0;value[i];i++)value[i]=(char)toupper((unsigned char)value[i]);
 CHECK(c,policy_identity_set31ax(&p,"vuid",value)==1);
 for(size_t i=0;value[i];i++)CHECK(c,p.identity[3][i]==(char)tolower((unsigned char)value[i]));
 const char *bad[]={"","absent","1234","00000000-0000-0000-0000-00000000000g",
  "000000000000-0000-0000-000000000000","00000000-0000-0000-0000-0000000000000"};
 for(unsigned j=0;j<2;j++)for(unsigned i=0;i<sizeof(bad)/sizeof(bad[0]);i++){
  memset(&p,0,sizeof(p));CHECK(c,policy_identity_set31ax(&p,j?"kuid":"vuid",bad[i])==-1);
  CHECK(c,p.seen[j?4:3]==0);
 }
}
static void lpnh_grammar(Checks *c) {
 char hash[98];synthetic_hash(hash,96,'A');PolicyIdentity31AX p={0};
 CHECK(c,policy_identity_set31ax(&p,"lpnh",hash)==1);
 for(unsigned i=0;i<96;i++)CHECK(c,p.lpnh[0][i]=='a');
 CHECK(c,policy_identity_set31ax(&p,"lpnh",hash)==1);CHECK(c,policy_identity_set31ax(&p,"lpnh",hash)==-1);
 const char *bad[]={"","absent","0x1234"};
 for(unsigned i=0;i<3;i++){memset(&p,0,sizeof(p));CHECK(c,policy_identity_set31ax(&p,"lpnh",bad[i])==-1);}
 for(unsigned length=95;length<=97;length+=2){synthetic_hash(hash,length,'a');memset(&p,0,sizeof(p));CHECK(c,policy_identity_set31ax(&p,"lpnh",hash)==-1);}
 synthetic_hash(hash,96,'a');hash[50]='g';memset(&p,0,sizeof(p));CHECK(c,policy_identity_set31ax(&p,"lpnh",hash)==-1);
}
static void bounded_numbers(Checks *c) {
 const char *tags[]={"BORD","CHIP","ECID"};
 const char *bad[]={"","0x","0X1","-1","+1","1","0x-1","0x1 ","0x10000000000000000","0xg"};
 for(unsigned j=0;j<3;j++){
  for(unsigned i=0;i<sizeof(bad)/sizeof(bad[0]);i++){
   PolicyIdentity31AX p={0};CHECK(c,policy_identity_set31ax(&p,tags[j],bad[i])==-1);CHECK(c,p.seen[j]==0);
  }
  PolicyIdentity31AX p={0};CHECK(c,policy_identity_set31ax(&p,tags[j],j==2?"0xffffffffffffffff":"0xffffffff")==1);
  memset(&p,0,sizeof(p));CHECK(c,policy_identity_set31ax(&p,tags[j],"0x0000000000000001")==1);
  CHECK(c,!strcmp(p.identity[j],"0x0000000000000001"));
 }
 for(unsigned j=0;j<2;j++){PolicyIdentity31AX p={0};CHECK(c,policy_identity_set31ax(&p,tags[j],"0x100000000")==-1);}
 PolicyIdentity31AX p={0};CHECK(c,policy_identity_set31ax(&p,"ECID","0x100000000")==1);
}
static void auxiliary_absence(Checks *c) {
 const char *tags[]={"auxp","auxi","auxr","prot","hrlp","losv"};
 const char *bad[]={"true","false","0","1","0x0","present","abcd"};
 for(unsigned j=0;j<6;j++){
  PolicyIdentity31AX p={0};CHECK(c,policy_identity_set31ax(&p,tags[j],"AbSeNt")==1);
  for(unsigned i=0;i<7;i++){memset(&p,0,sizeof(p));CHECK(c,policy_identity_set31ax(&p,tags[j],bad[i])==-1);}
 }
}
static void target_binding(Checks *c) {
 Fixture f;CHECK(c,fixture(&f));CHECK(c,capture(&f));CHECK(c,ax_policy_view.bound);
 synthetic_uuid(f.lab_group,0x99);CHECK(c,!capture(&f));CHECK(c,!ax_policy_view.observed&&!ax_policy_view.bound);
 CHECK(c,fixture(&f));synthetic_uuid(f.original_group,0x99);CHECK(c,!capture(&f));
 CHECK(c,fixture(&f));strcpy(f.lab.identity[1],"0x0000000000006040");strcpy(f.original.identity[1],f.lab.identity[1]);CHECK(c,!capture(&f));
 CHECK(c,fixture(&f));strcpy(f.original.identity[0],"0x0000000000000065");CHECK(c,!capture(&f));
 CHECK(c,fixture(&f));strcpy(f.original.identity[2],"0x0000000000001235");CHECK(c,!capture(&f));
}
static void complete_extras(Checks *c) {
 Fixture f;CHECK(c,fixture(&f));
 for(unsigned role=0;role<2;role++)for(unsigned i=0;i<POLICY_EXTRA_COUNT;i++){
  CHECK(c,fixture(&f));PolicyExtras *e=role?&f.original_extra:&f.lab_extra;e->seen[i]=0;CHECK(c,!capture(&f));
  e->seen[i]=2;CHECK(c,!capture(&f));
 }
 PolicyExtras p={0};CHECK(c,policy_extra_set(&p,"CPRO","absent")==-1);
 CHECK(c,policy_extra_set(&p,"love","1.2.3.4.5.6")==-1);
 CHECK(c,policy_extra_set(&p,"love","1.2.3.4.5,4294967296")==-1);
 CHECK(c,policy_extra_set(&p,"ZZZZ","true")==0);
}
static void original_reference_anchors(Checks *c) {
 Fixture f;CHECK(c,fixture(&f));CHECK(c,capture(&f));PolicyView31AX base=ax_policy_view;
 synthetic_hash(f.original_nsih,96,'a');CHECK(c,capture(&f));
 CHECK(c,strcmp(base.original_identity,ax_policy_view.original_identity)!=0);CHECK(c,!strcmp(base.lab_identity,ax_policy_view.lab_identity));
 CHECK(c,fixture(&f));synthetic_hash(f.original_coih,96,'a');CHECK(c,capture(&f));
 CHECK(c,strcmp(base.original_identity,ax_policy_view.original_identity)!=0);CHECK(c,!strcmp(base.lab_identity,ax_policy_view.lab_identity));
 CHECK(c,fixture(&f));f.original_coih[0]=0;CHECK(c,capture(&f));CHECK(c,strcmp(base.original_identity,ax_policy_view.original_identity)!=0);
 CHECK(c,fixture(&f));for(size_t i=0;f.original_nsih[i];i++)f.original_nsih[i]=(char)toupper((unsigned char)f.original_nsih[i]);
 for(size_t i=0;f.original_coih[i];i++)f.original_coih[i]=(char)toupper((unsigned char)f.original_coih[i]);
 CHECK(c,capture(&f));CHECK(c,!strcmp(base.original_identity,ax_policy_view.original_identity));
}
static void authority_anchors(Checks *c) {
 Fixture f;CHECK(c,fixture(&f));CHECK(c,capture(&f));PolicyView31AX base=ax_policy_view;
 synthetic_uuid(f.original.identity[4],0x66);CHECK(c,capture(&f));CHECK(c,strcmp(base.original_identity,ax_policy_view.original_identity)!=0);
 CHECK(c,!strcmp(base.lab_identity,ax_policy_view.lab_identity));
 CHECK(c,fixture(&f));synthetic_uuid(f.lab.identity[4],0x66);CHECK(c,capture(&f));CHECK(c,strcmp(base.lab_identity,ax_policy_view.lab_identity)!=0);
 CHECK(c,!strcmp(base.original_identity,ax_policy_view.original_identity));
 for(unsigned i=0;i<3;i+=2){CHECK(c,fixture(&f));strcpy(f.lab.identity[i],i?"0x0000000000001235":"0x0000000000000065");
  strcpy(f.original.identity[i],f.lab.identity[i]);CHECK(c,capture(&f));CHECK(c,strcmp(base.lab_identity,ax_policy_view.lab_identity)!=0);
  CHECK(c,strcmp(base.original_identity,ax_policy_view.original_identity)!=0);}
}
static void nonce_rotation(Checks *c) {
 Fixture f;CHECK(c,fixture(&f));CHECK(c,capture(&f));PolicyView31AX base=ax_policy_view;
 synthetic_hash(f.lab.lpnh[0],96,'1');synthetic_hash(f.lab.lpnh[1],96,'2');
 synthetic_hash(f.original.lpnh[0],96,'3');synthetic_hash(f.original.lpnh[1],96,'4');
 CHECK(c,capture(&f));CHECK(c,!memcmp(&base,&ax_policy_view,sizeof(base)));
}
static void lab_manifest_anchor(Checks *c) {
 Fixture f;CHECK(c,fixture(&f));CHECK(c,capture(&f));PolicyView31AX base=ax_policy_view;
 synthetic_hash(f.lab_nsih,96,'a');CHECK(c,capture(&f));CHECK(c,strcmp(base.lab_manifest,ax_policy_view.lab_manifest)!=0);
 CHECK(c,!strcmp(base.lab_identity,ax_policy_view.lab_identity));CHECK(c,!strcmp(base.original_identity,ax_policy_view.original_identity));
 f.lab_nsih[0]=0;CHECK(c,capture(&f));CHECK(c,!ax_policy_view.lab_manifest_present);CHECK(c,strcmp(base.lab_manifest,ax_policy_view.lab_manifest)!=0);
 /* The pure view records absence. Candidate admission is a separate controller contract. */
}
static void reference_grammar(Checks *c) {
 Fixture f;CHECK(c,fixture(&f));char too_short[32],odd[34],too_long[130],edge[129],nonhex[97];
 synthetic_hash(too_short,31,'a');synthetic_hash(odd,33,'a');synthetic_hash(too_long,129,'a');
 synthetic_hash(nonhex,96,'a');nonhex[3]='g';
 const char *bad[]={NULL,"absent","0x1234",too_short,odd,too_long,nonhex};
 for(unsigned i=0;i<sizeof(bad)/sizeof(bad[0]);i++){
  CHECK(c,!capture_references(&f,bad[i],f.original_nsih,f.original_coih));
  CHECK(c,!capture_references(&f,f.lab_nsih,bad[i],f.original_coih));
  CHECK(c,!capture_references(&f,f.lab_nsih,f.original_nsih,bad[i]));
  CHECK(c,!ax_policy_view.observed&&!ax_policy_view.bound);
 }
 CHECK(c,!capture_references(&f,f.lab_nsih,"",f.original_coih));
 CHECK(c,capture_references(&f,"",f.original_nsih,""));CHECK(c,!ax_policy_view.lab_manifest_present);
 for(unsigned length=32;length<=128;length+=96){
  synthetic_hash(edge,length,'a');CHECK(c,capture_references(&f,edge,edge,edge));CHECK(c,ax_policy_view.bound);
 }
}
static void extra_anchor_separation(Checks *c) {
 Fixture f;CHECK(c,fixture(&f));CHECK(c,capture(&f));PolicyView31AX base=ax_policy_view;unsigned char before[32],after[32];
 extra_digest(&f.lab_extra,&f.key,before);CHECK(c,change_extra(&f.lab_extra,5,"9.2.3.4.5,6"));CHECK(c,capture(&f));
 CHECK(c,!strcmp(base.lab_identity,ax_policy_view.lab_identity));extra_digest(&f.lab_extra,&f.key,after);CHECK(c,memcmp(before,after,sizeof(before))!=0);
 const char *changed[]={"0x2","0x3","false","false","true"};
 for(unsigned i=0;i<5;i++){CHECK(c,fixture(&f));CHECK(c,change_extra(&f.lab_extra,i,changed[i]));CHECK(c,capture(&f));
  CHECK(c,strcmp(base.lab_identity,ax_policy_view.lab_identity)!=0);CHECK(c,!strcmp(base.original_identity,ax_policy_view.original_identity));}
}
static void domain_and_key_binding(Checks *c) {
 Fixture f;CHECK(c,fixture(&f));CHECK(c,capture(&f));PolicyView31AX base=ax_policy_view;
 synthetic_hash(f.profile.sha,64,'a');CHECK(c,capture(&f));CHECK(c,strcmp(base.original_identity,ax_policy_view.original_identity)!=0);
 CHECK(c,strcmp(base.lab_identity,ax_policy_view.lab_identity)!=0);CHECK(c,strcmp(base.lab_manifest,ax_policy_view.lab_manifest)!=0);
 CHECK(c,fixture(&f));f.key.bytes[0]^=1;CHECK(c,capture(&f));CHECK(c,strcmp(base.original_identity,ax_policy_view.original_identity)!=0);
 CHECK(c,strcmp(base.lab_identity,ax_policy_view.lab_identity)!=0);CHECK(c,strcmp(base.lab_manifest,ax_policy_view.lab_manifest)!=0);
 CHECK(c,fixture(&f));for(unsigned i=0;i<8;i++){CHECK(c,capture(&f));CHECK(c,!memcmp(&base,&ax_policy_view,sizeof(base)));}
}
static void unbound_and_reset_views(Checks *c) {
 Fixture f;CHECK(c,fixture(&f));CHECK(c,capture(&f));CHECK(c,ax_policy_view.bound);
 f.key.loaded=false;CHECK(c,capture(&f));CHECK(c,ax_policy_view.observed&&!ax_policy_view.bound);
 CHECK(c,!ax_policy_view.original_identity[0]&&!ax_policy_view.lab_identity[0]&&!ax_policy_view.lab_manifest[0]);
 f.key.loaded=true;CHECK(c,capture(&f));f.lab.seen[0]=0;CHECK(c,!capture(&f));CHECK(c,!ax_policy_view.observed&&!ax_policy_view.bound);
 policy_view_reset31ax();PolicyView31AX zero={0};CHECK(c,!memcmp(&zero,&ax_policy_view,sizeof(zero)));
}

typedef void (*Probe)(Checks *);
int main(int argc,char **argv) {
 const struct {const char *name;Probe run;} cases[]={
  {"required_counts",required_counts},{"duplicate_tags",duplicate_tags},{"uuid_grammar",uuid_grammar},
  {"lpnh_grammar",lpnh_grammar},{"bounded_numbers",bounded_numbers},{"auxiliary_absence",auxiliary_absence},
  {"target_binding",target_binding},{"complete_extras",complete_extras},
  {"original_reference_anchors",original_reference_anchors},{"authority_anchors",authority_anchors},
  {"nonce_rotation",nonce_rotation},{"lab_manifest_anchor",lab_manifest_anchor},
  {"reference_grammar",reference_grammar},
  {"extra_anchor_separation",extra_anchor_separation},{"domain_and_key_binding",domain_and_key_binding},
  {"unbound_and_reset_views",unbound_and_reset_views}};
 for(unsigned i=0;argc==2&&i<sizeof(cases)/sizeof(cases[0]);i++)if(!strcmp(argv[1],cases[i].name)){
  Checks c={0};cases[i].run(&c);
  printf("{\"case\":\"%s\",\"passed\":%s,\"checks\":%u,\"failed\":%u,\"private_values_returned\":false,\"target_or_writer_linked\":false}\n",
   cases[i].name,c.failed?"false":"true",c.checks,c.failed);
  return c.failed?1:0;
 }
 puts("{\"case\":\"UNRECOGNIZED\",\"passed\":false,\"checks\":0,\"failed\":0,\"private_values_returned\":false,\"target_or_writer_linked\":false}");return 64;
}
