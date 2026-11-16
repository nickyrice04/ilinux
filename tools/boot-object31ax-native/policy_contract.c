/* SPDX-License-Identifier: MIT */
#include "policy_contract.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <ctype.h>
PolicyView31AX ax_policy_view;
static const char *tags31ax[]={"BORD","CHIP","ECID","vuid","kuid","lpnh","auxp","auxi","auxr","prot","hrlp","losv"};

static bool fixed_hex31ax(const char *input,char out[97],size_t length){
 if(strlen(input)!=length)return false;
 for(size_t i=0;i<length;i++){if(!isxdigit((unsigned char)input[i]))return false;out[i]=(char)tolower((unsigned char)input[i]);}
 out[length]=0;return true;
}
static bool uuid31ax(const char *input,char out[97]){
 if(strlen(input)!=36)return false;
 for(size_t i=0;i<36;i++){bool dash=i==8||i==13||i==18||i==23;
  if(dash?input[i]!='-':!isxdigit((unsigned char)input[i]))return false;
  out[i]=(char)tolower((unsigned char)input[i]);}
 out[36]=0;return true;
}
static bool number31ax(const char *input,char out[97],bool word32){
 if(strncmp(input,"0x",2))return false;input+=2;size_t n=strlen(input);if(!n||n>16)return false;
 uint64_t value=0;for(size_t i=0;i<n;i++){unsigned char c=(unsigned char)input[i];unsigned d;
  if(c>='0'&&c<='9')d=c-'0';else if(c>='a'&&c<='f')d=c-'a'+10;else if(c>='A'&&c<='F')d=c-'A'+10;else return false;
  value=(value<<4)|d;}
 if(word32&&value>UINT32_MAX)return false;
 snprintf(out,97,"0x%016llx",(unsigned long long)value);return true;
}
int policy_identity_set31ax(PolicyIdentity31AX *out,const char *tag,const char *value){
 for(unsigned i=0;i<12;i++)if(!strcmp(tags31ax[i],tag)){
  unsigned at=out->seen[i];if(at>=(i==5?2u:1u))return -1;
  bool ok=i<3?number31ax(value,out->identity[i],i<2):i<5?uuid31ax(value,out->identity[i]):
   i==5?fixed_hex31ax(value,out->lpnh[at],96):!strcasecmp(value,"absent");
  if(!ok)return -1;out->seen[i]++;return 1;
 }
 return 0;
}
bool policy_identity_complete31ax(const PolicyIdentity31AX *p){
 for(unsigned i=0;i<9;i++)if(p->seen[i]!=(i==5?2u:1u))return false;
 for(unsigned i=9;i<12;i++)if(p->seen[i]>1)return false;
 return true;
}
void policy_view_reset31ax(void){memset(&ax_policy_view,0,sizeof(ax_policy_view));}
static void add31ax(CCHmacContext *context,const char *part){CCHmacUpdate(context,part,strlen(part)+1);}
static void finish31ax(CCHmacContext *context,char out[65]){
 unsigned char digest[32];static const char digits[]="0123456789abcdef";CCHmacFinal(context,digest);
 for(unsigned i=0;i<32;i++){out[i*2]=digits[digest[i]>>4];out[i*2+1]=digits[digest[i]&15];}out[64]=0;memset(digest,0,sizeof(digest));
}
static void reference31ax(CCHmacContext *context,const char *value){
 char lower[129];size_t n=strlen(value);
 for(size_t i=0;i<n;i++)lower[i]=(char)tolower((unsigned char)value[i]);lower[n]=0;add31ax(context,lower);
}
static bool reference_valid31ax(const char *value){
 if(!value)return false;size_t n=strlen(value);if(!n)return true;
 if(n<32||n>128||n%2)return false;
 for(size_t i=0;i<n;i++)if(!isxdigit((unsigned char)value[i]))return false;
 return true;
}
static void identity_commit31ax(const PolicyIdentity31AX *p,const PolicyExtras *extra,
 const char *role,const char *nsih,const char *coih,const Profile *profile,const ComparisonKey *key,char out[65]){
 CCHmacContext c;CCHmacInit(&c,kCCHmacAlgSHA256,key->bytes,sizeof(key->bytes));
 add31ax(&c,"ilinux31ax-immutable-identity-v1");add31ax(&c,profile->sha);add31ax(&c,role);
 for(unsigned i=0;i<5;i++){add31ax(&c,tags31ax[i]);add31ax(&c,p->identity[i]);}
 /* LOVE is separately issuance-protected. Production/epoch/domain/lobo stay
  * invariant even on the narrowly exceptional functional-rescue path. */
 for(unsigned i=0;i<5;i++){add31ax(&c,policy_extra_tag(i));add31ax(&c,extra->value[i]);}
 if(!strcmp(role,"ORIGINAL")){reference31ax(&c,nsih);reference31ax(&c,coih);}
 finish31ax(&c,out);
}
bool policy_view_capture31ax(const PolicyIdentity31AX *lab,const PolicyIdentity31AX *original,
 const PolicyExtras *le,const PolicyExtras *oe,const char *ln,const char *on,const char *oc,
 const char *lg,const char *og,const Profile *profile,const ComparisonKey *key){
 policy_view_reset31ax();
 if(!reference_valid31ax(ln)||!reference_valid31ax(on)||!reference_valid31ax(oc)||!on[0])return false;
 if(!policy_identity_complete31ax(lab)||!policy_identity_complete31ax(original)||
    strcasecmp(lab->identity[3],lg)||strcasecmp(original->identity[3],og))return false;
 for(unsigned i=0;i<3;i++)if(strcmp(lab->identity[i],original->identity[i]))return false;
 if(strcmp(lab->identity[1],"0x0000000000006050"))return false;
 for(unsigned i=0;i<POLICY_EXTRA_COUNT;i++)if(le->seen[i]!=1||oe->seen[i]!=1)return false;
 ax_policy_view.observed=true;ax_policy_view.lab_manifest_present=ln[0]!=0;
 if(!key||!key->loaded)return true;
 identity_commit31ax(lab,le,"LAB",NULL,NULL,profile,key,ax_policy_view.lab_identity);
 identity_commit31ax(original,oe,"ORIGINAL",on,oc,profile,key,ax_policy_view.original_identity);
 CCHmacContext c;CCHmacInit(&c,kCCHmacAlgSHA256,key->bytes,sizeof(key->bytes));
 add31ax(&c,"ilinux31ax-lab-manifest-v1");add31ax(&c,profile->sha);reference31ax(&c,ln);
 finish31ax(&c,ax_policy_view.lab_manifest);ax_policy_view.bound=true;return true;
}
