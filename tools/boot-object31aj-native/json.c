/* SPDX-License-Identifier: MIT */
#include "reader.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <ctype.h>

typedef struct {const uint8_t *p;size_t n,at;Json *j;} Parser;
static void ws(Parser *p){while(p->at<p->n&&(p->p[p->at]==' '||p->p[p->at]=='\t'||p->p[p->at]=='\n'||p->p[p->at]=='\r'))p->at++;}
static int unhex(int c){if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;if(c>='A'&&c<='F')return c-'A'+10;return -1;}
static bool string(Parser *p,char *out,size_t cap){
    if(p->at==p->n||p->p[p->at++]!='"')return false;size_t n=0;
    while(p->at<p->n){int c=p->p[p->at++];if(c=='"'){out[n]=0;return true;}if(c<32||c>=128)return false;
        if(c=='\\'){if(p->at==p->n)return false;c=p->p[p->at++];if(c=='u'){int v=0;for(int i=0;i<4;i++){if(p->at==p->n)return false;int d=unhex(p->p[p->at++]);if(d<0)return false;v=v*16+d;}if(v==0||v>=128)return false;c=v;}
            else if(c=='n')c='\n';else if(c=='r')c='\r';else if(c=='t')c='\t';else if(c=='b')c='\b';else if(c=='f')c='\f';else if(c!='"'&&c!='\\'&&c!='/')return false;}
        if(n+1>=cap)return false;out[n++]=(char)c;}
    return false;
}
static int value(Parser *p,int depth){
    ws(p);if(depth>8||p->j->count>=512||p->at==p->n)return -1;
    int index=p->j->count++;JNode *node=&p->j->nodes[index];node->first=node->next=-1;
    if(p->p[p->at]=='{'){
        node->type=J_OBJECT;p->at++;ws(p);if(p->at<p->n&&p->p[p->at]=='}'){p->at++;return index;}int last=-1;
        while(p->at<p->n){char key[80];ws(p);if(!string(p,key,sizeof(key)))return -1;ws(p);if(p->at==p->n||p->p[p->at++]!=':')return -1;
            for(int n=node->first;n>=0;n=p->j->nodes[n].next)if(!strcmp(p->j->nodes[n].key,key))return -1;
            int child=value(p,depth+1);if(child<0)return -1;strcpy(p->j->nodes[child].key,key);if(last<0)node->first=child;else p->j->nodes[last].next=child;last=child;
            ws(p);if(p->at==p->n)return -1;uint8_t c=p->p[p->at++];if(c=='}')return index;if(c!=',')return -1;}
        return -1;
    }
    if(p->p[p->at]=='"'){node->type=J_STRING;return string(p,node->value,sizeof(node->value))?index:-1;}
    for(int k=0;k<3;k++){const char *s=k==0?"true":k==1?"false":"null";size_t n=strlen(s);if(n<=p->n-p->at&&!memcmp(p->p+p->at,s,n)){p->at+=n;node->type=k==0?J_TRUE:k==1?J_FALSE:J_NULL;return index;}}
    if(p->p[p->at]>='0'&&p->p[p->at]<='9'){size_t begin=p->at;while(p->at<p->n&&p->p[p->at]>='0'&&p->p[p->at]<='9')p->at++;size_t n=p->at-begin;if(n>20||(n>1&&p->p[begin]=='0'))return -1;memcpy(node->value,p->p+begin,n);node->value[n]=0;node->type=J_NUMBER;return index;}
    return -1;
}
bool json_parse(Bytes b,Json *j){if(!b.n||b.n>65536||memchr(b.p,0,b.n))return false;memset(j,0,sizeof(*j));Parser p={b.p,b.n,0,j};if(value(&p,0)!=0)return false;ws(&p);return p.at==p.n;}
int json_get(const Json *j,int object,const char *key){if(object<0||object>=j->count||j->nodes[object].type!=J_OBJECT)return -1;for(int n=j->nodes[object].first;n>=0;n=j->nodes[n].next)if(!strcmp(j->nodes[n].key,key))return n;return -1;}
bool json_keys(const Json *j,int object,const char *const *keys,size_t n){if(object<0||j->nodes[object].type!=J_OBJECT)return false;size_t count=0;for(int k=j->nodes[object].first;k>=0;k=j->nodes[k].next)count++;if(count!=n)return false;for(size_t i=0;i<n;i++)if(json_get(j,object,keys[i])<0)return false;return true;}
bool json_string(const Json *j,int node,const char *s){return node>=0&&j->nodes[node].type==J_STRING&&!strcmp(j->nodes[node].value,s);}
static bool jsize(const Json *j,int node,uint64_t *out){if(node<0||j->nodes[node].type!=J_NUMBER)return false;char *end;unsigned long long n=strtoull(j->nodes[node].value,&end,10);if(*end)return false;char canonical[32];snprintf(canonical,sizeof(canonical),"%llu",n);if(strcmp(canonical,j->nodes[node].value))return false;*out=n;return true;}
static bool file_record(const Json *j,int node,const char *name,uint64_t bytes,const char *sha){
    const char *keys[]={"name","bytes","sha256"};uint64_t n;
    return json_keys(j,node,keys,3)&&json_string(j,json_get(j,node,"name"),name)&&jsize(j,json_get(j,node,"bytes"),&n)&&n==bytes&&json_string(j,json_get(j,node,"sha256"),sha);
}
bool load_profile(const char *path,const char *exe,Profile *out){
    uint8_t *data=NULL,*binary=NULL;size_t n=0,bin=0;Json j;bool ok=false;char digest[65];
    if(!CANDIDATE_BYTES||!valid_sha(CANDIDATE_SHA256)||!read_file(path,65536,false,&data,&n)||!json_parse((Bytes){data,n},&j))goto done;
    const char *keys[]={"schema","target","files","native_deadline_ms","raw_policy_strategy","initial_payload","final_payload","publication_authorizes_writes"};
    const char *tk[]={"model","board","chip_id"};const char *fk[]={"candidate","rollback","helper"};uint64_t deadline;
    int target=json_get(&j,0,"target"),files=json_get(&j,0,"files"),helper=json_get(&j,files,"helper");
    if(!json_keys(&j,0,keys,8)||!json_string(&j,json_get(&j,0,"schema"),"ilinux31aj-recovery-profile-v1")||!json_keys(&j,target,tk,3)||!json_string(&j,json_get(&j,target,"model"),"Mac17,6")||!json_string(&j,json_get(&j,target,"board"),"j716c")||!json_string(&j,json_get(&j,target,"chip_id"),"0x6050")||!json_keys(&j,files,fk,3))goto done;
    if(!file_record(&j,json_get(&j,files,"candidate"),"candidate.macho",CANDIDATE_BYTES,CANDIDATE_SHA256)||!file_record(&j,json_get(&j,files,"rollback"),"m1n1-boot021.bin",ROLLBACK_BYTES,ROLLBACK_SHA))goto done;
    if(!jsize(&j,json_get(&j,0,"native_deadline_ms"),&deadline)||!deadline||deadline>90000||!json_string(&j,json_get(&j,0,"raw_policy_strategy"),"ctrr_only")||!json_string(&j,json_get(&j,0,"initial_payload"),"31AF")||!json_string(&j,json_get(&j,0,"final_payload"),"BOOT021")||j.nodes[json_get(&j,0,"publication_authorizes_writes")].type!=J_FALSE)goto done;
    const char *hk[]={"name","bytes","sha256"};uint64_t hb;int hs=json_get(&j,helper,"sha256");
    if(!json_keys(&j,helper,hk,3)||!json_string(&j,json_get(&j,helper,"name"),"ilinux31aj-reader")||!jsize(&j,json_get(&j,helper,"bytes"),&hb)||!hb||hb>16*1024*1024||hs<0||j.nodes[hs].type!=J_STRING||!valid_sha(j.nodes[hs].value))goto done;
    if(!read_file(exe,16*1024*1024,false,&binary,&bin)||bin!=hb||!sha_hex(binary,bin,digest)||strcmp(digest,j.nodes[hs].value))goto done;
    memset(out,0,sizeof(*out));sha_hex(data,n,out->sha);strcpy(out->helper_sha,digest);out->helper_bytes=hb;ok=true;
done:free(data);free(binary);return ok;
}
