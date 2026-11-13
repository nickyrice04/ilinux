/* SPDX-License-Identifier: MIT */
#include "reader.h"
#include <CommonCrypto/CommonDigest.h>
#include <compression.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>

static int secure_open(const char *path,bool directory) {
    if(!path || path[0]!='/' || strlen(path)>=PATH_MAX)return -1;
    char copy[PATH_MAX];strcpy(copy,path);
    int fd=open("/",O_RDONLY|O_DIRECTORY|O_CLOEXEC);
    if(fd<0)return -1;
    char *part=copy+1;
    while(*part) {
        char *slash=strchr(part,'/');if(slash)*slash=0;
        if(!*part || !strcmp(part,".") || !strcmp(part,"..")){close(fd);return -1;}
        int flags=O_RDONLY|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK;
        if(slash || directory)flags|=O_DIRECTORY;
        int next=openat(fd,part,flags);close(fd);if(next<0)return -1;fd=next;
        if(!slash)break;part=slash+1;if(!*part){close(fd);return -1;}
    }
    return fd;
}
bool safe_directory(const char *path){int fd=secure_open(path,true);if(fd<0)return false;close(fd);return true;}
bool read_file(const char *path,size_t cap,bool workspace_only,uint8_t **data,size_t *size) {
    *data=NULL;*size=0;
    size_t root=strlen(WORKSPACE_ROOT);
    if(workspace_only && (strncmp(path,WORKSPACE_ROOT,root) || path[root]!='/'))return false;
    int fd=secure_open(path,false);if(fd<0)return false;
    struct stat a,b;bool ok=false;uint8_t *p=NULL;
    if(fstat(fd,&a) || !S_ISREG(a.st_mode) || a.st_size<=0 || (uint64_t)a.st_size>cap)goto done;
    p=malloc((size_t)a.st_size+1);if(!p)goto done;
    size_t n=0;while(n<(size_t)a.st_size){ssize_t got=read(fd,p+n,(size_t)a.st_size-n);if(got<0&&errno==EINTR)continue;if(got<=0)goto done;n+=(size_t)got;}
    uint8_t extra;if(read(fd,&extra,1)!=0 || fstat(fd,&b))goto done;
    if(a.st_dev!=b.st_dev || a.st_ino!=b.st_ino || a.st_size!=b.st_size ||
       a.st_mtimespec.tv_sec!=b.st_mtimespec.tv_sec || a.st_mtimespec.tv_nsec!=b.st_mtimespec.tv_nsec ||
       a.st_ctimespec.tv_sec!=b.st_ctimespec.tv_sec || a.st_ctimespec.tv_nsec!=b.st_ctimespec.tv_nsec)goto done;
    p[n]=0;*data=p;*size=n;p=NULL;ok=true;
done:free(p);close(fd);return ok;
}
static void hex(const uint8_t *p,size_t n,char *out){static const char digits[]="0123456789abcdef";for(size_t i=0;i<n;i++){out[i*2]=digits[p[i]>>4];out[i*2+1]=digits[p[i]&15];}out[n*2]=0;}
bool valid_sha(const char *s){if(!s || strlen(s)!=64)return false;for(size_t i=0;i<64;i++)if(!((s[i]>='0'&&s[i]<='9')||(s[i]>='a'&&s[i]<='f')))return false;return true;}
bool sha_hex(const uint8_t *data,size_t size,char out[65]){CC_SHA256_CTX c;uint8_t digest[32];CC_SHA256_Init(&c);while(size){size_t n=size>1024*1024?1024*1024:size;CC_SHA256_Update(&c,data,(CC_LONG)n);data+=n;size-=n;}CC_SHA256_Final(digest,&c);hex(digest,32,out);return true;}
bool load_comparison_key(const char *path,bool fixture,ComparisonKey *out){
    memset(out,0,sizeof(*out));size_t root=strlen(WORKSPACE_ROOT);if(fixture&&(!path||strncmp(path,WORKSPACE_ROOT,root)||path[root]!='/'))return false;
    int fd=secure_open(path,false);if(fd<0)return false;
    struct stat a,b;bool ok=false;uint8_t extra;
    if(fstat(fd,&a)||!S_ISREG(a.st_mode)||a.st_size!=32||(a.st_mode&07777)!=0600||a.st_nlink!=1||a.st_uid!=(fixture?geteuid():0))goto done;
    size_t n=0;while(n<32){ssize_t got=read(fd,out->bytes+n,32-n);if(got<0&&errno==EINTR)continue;if(got<=0)goto done;n+=(size_t)got;}
    if(read(fd,&extra,1)!=0||fstat(fd,&b)||a.st_dev!=b.st_dev||a.st_ino!=b.st_ino||a.st_size!=b.st_size||a.st_uid!=b.st_uid||a.st_mode!=b.st_mode||a.st_nlink!=b.st_nlink||a.st_mtimespec.tv_sec!=b.st_mtimespec.tv_sec||a.st_mtimespec.tv_nsec!=b.st_mtimespec.tv_nsec||a.st_ctimespec.tv_sec!=b.st_ctimespec.tv_sec||a.st_ctimespec.tv_nsec!=b.st_ctimespec.tv_nsec)goto done;
    sha_hex(out->bytes,32,out->id);out->loaded=ok=true;
done:close(fd);if(!ok)memset(out,0,sizeof(*out));return ok;
}

typedef struct {uint8_t tag;size_t start,end,next;} TLV;
static bool tlv(Bytes data,size_t at,size_t limit,TLV *out){
    if(limit>data.n || at>limit || limit-at<2)return false;
    uint8_t tag=data.p[at++];if(!tag || (tag&31)==31)return false;
    uint8_t first=data.p[at++];size_t length=first;
    if(first&128){size_t count=first&127;if(!count||count>4||count>limit-at||data.p[at]==0)return false;length=0;while(count--)length=(length<<8)|data.p[at++];if(length<128)return false;}
    if(length>limit-at)return false;
    *out=(TLV){tag,at,at+length,at+length};return true;
}
static bool text_is(Bytes data,TLV field,const char *s){return field.tag==0x16 && field.end-field.start==strlen(s) && !memcmp(data.p+field.start,s,strlen(s));}
static bool positive_integer(Bytes data,TLV field,uint64_t *value){
    size_t n=field.end-field.start;if(field.tag!=2 || !n || n>9 || data.p[field.start]&128)return false;
    if(n>1 && data.p[field.start]==0 && !(data.p[field.start+1]&128))return false;
    if(n==9 && data.p[field.start]!=0)return false;
    uint64_t v=0;for(size_t i=field.start;i<field.end;i++)v=(v<<8)|data.p[i];*value=v;return true;
}
static bool payload(Bytes data,Bytes *body,uint64_t *declared,bool *keybag,const char **framing){
    TLV root,fields[8];size_t n=0;
    if(!tlv(data,0,data.n,&root)||root.tag!=0x30||root.next!=data.n)return false;
    for(size_t at=root.start;at<root.end;){if(n==8||!tlv(data,at,root.end,&fields[n]))return false;at=fields[n++].next;}
    if(n>=2 && text_is(data,fields[0],"IMG4")){
        bool a0=false,a1=false;
        for(size_t i=2;i<n;i++){if(fields[i].tag==0xa0&&!a0&&!a1)a0=true;else if(fields[i].tag==0xa1&&!a1)a1=true;else return false;}
        TLV nested=fields[1];if(nested.tag!=0x30)return false;n=0;
        for(size_t at=nested.start;at<nested.end;){if(n==8||!tlv(data,at,nested.end,&fields[n]))return false;at=fields[n++].next;}
        *framing="IMG4";
    }else *framing="IM4P";
    if(n<4||n>7||!text_is(data,fields[0],"IM4P")||fields[1].tag!=0x16||fields[1].end-fields[1].start!=4||fields[2].tag!=0x16||fields[2].end-fields[2].start>4096||fields[3].tag!=4)return false;
    for(size_t k=fields[1].start;k<fields[1].end;k++)if(data.p[k]<32||data.p[k]>=127)return false;
    size_t i=4;*keybag=false;*declared=0;
    if(i<n&&fields[i].tag==4){*keybag=true;i++;}
    if(i<n&&fields[i].tag==0x30){TLV first,second;uint64_t version;
        if(!tlv(data,fields[i].start,fields[i].end,&first)||!tlv(data,first.next,fields[i].end,&second)||second.next!=fields[i].end||!positive_integer(data,first,&version)||version!=1||!positive_integer(data,second,declared)||!*declared||*declared>RAW_LIMIT)return false;i++;}
    if(i<n&&fields[i].tag==0xa0){if(fields[i].end-fields[i].start>65536)return false;i++;}
    if(i!=n)return false;
    *body=(Bytes){data.p+fields[3].start,fields[3].end-fields[3].start};return true;
}
static bool lzfse_magic(Bytes b){return b.n>=4 && (!memcmp(b.p,"bvx2",4)||!memcmp(b.p,"bvx1",4)||!memcmp(b.p,"bvx-",4)||!memcmp(b.p,"bvxn",4)||!memcmp(b.p,"bvx$",4));}
static uint32_t le32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint64_t le64(const uint8_t *p){return le32(p)|(uint64_t)le32(p+4)<<32;}
static bool lzfse_frame(Bytes in,size_t maximum,size_t *raw_size){
    size_t at=0,total=0;
    for(unsigned block=0;block<65536;block++){
        if(in.n-at<4)return false;const uint8_t *p=in.p+at;
        if(!memcmp(p,"bvx$",4)){if(at+4!=in.n)return false;*raw_size=total;return true;}
        if(in.n-at<8)return false;size_t raw=le32(p+4),header=0,encoded=0;
        if(!raw||raw>maximum-total)return false;
        if(!memcmp(p,"bvx-",4)){header=8;encoded=raw;}
        else if(!memcmp(p,"bvxn",4)){if(in.n-at<12)return false;header=12;encoded=le32(p+8);}
        else if(!memcmp(p,"bvx1",4)){if(in.n-at<772)return false;header=772;encoded=le32(p+8);if((uint64_t)le32(p+20)+le32(p+24)!=encoded)return false;}
        else if(!memcmp(p,"bvx2",4)){if(in.n-at<32)return false;header=le32(p+24);if(header<32||header>752)return false;encoded=(size_t)((le64(p+8)>>20)&0xfffff)+(size_t)((le64(p+16)>>40)&0xfffff);}
        else return false;
        if(header>in.n-at||encoded>in.n-at-header)return false;
        at+=header+encoded;total+=raw;
    }
    return false;
}
static bool decoded_hash(Bytes in,size_t maximum,uint64_t declared,char digest[65],size_t *output){
    if(!in.n||in.n>COMPRESSED_LIMIT||!maximum||maximum>RAW_LIMIT)return false;
    size_t framed=0;if(!lzfse_frame(in,maximum,&framed)||(declared&&framed!=declared))return false;
    compression_stream stream;memset(&stream,0,sizeof(stream));
    if(compression_stream_init(&stream,COMPRESSION_STREAM_DECODE,COMPRESSION_LZFSE)!=COMPRESSION_STATUS_OK)return false;
    stream.src_ptr=in.p;stream.src_size=in.n;uint8_t buffer[65536],hash[32];CC_SHA256_CTX sha;CC_SHA256_Init(&sha);size_t total=0;bool ok=false;
    for(size_t iteration=0;iteration<RAW_LIMIT/sizeof(buffer)+COMPRESSED_LIMIT+16;iteration++){
        size_t before=stream.src_size;stream.dst_ptr=buffer;stream.dst_size=sizeof(buffer);
        compression_status status=compression_stream_process(&stream,COMPRESSION_STREAM_FINALIZE);
        size_t wrote=sizeof(buffer)-stream.dst_size;
        if(wrote>maximum-total||status==COMPRESSION_STATUS_ERROR)break;
        total+=wrote;CC_SHA256_Update(&sha,buffer,(CC_LONG)wrote);
        if(status==COMPRESSION_STATUS_END){ok=stream.src_size==0&&total==framed&&(!declared||total==declared);break;}
        if(status!=COMPRESSION_STATUS_OK||(!wrote&&before==stream.src_size))break;
    }
    compression_stream_destroy(&stream);if(!ok)return false;CC_SHA256_Final(hash,&sha);hex(hash,32,digest);*output=total;return true;
}
static const char *known(size_t n,const char *sha){
    if(n==ROLLBACK_BYTES&&!strcmp(sha,ROLLBACK_SHA))return "BOOT021";
    if(n==442368&&!strcmp(sha,"166bea74bf515473057dfd29dc89127d04768945a451e497cc80a9fc53d4951b"))return "31AF";
    if(CANDIDATE_BYTES && n==(size_t)CANDIDATE_BYTES&&!strcmp(sha,CANDIDATE_SHA256))return "CANDIDATE";
    if(n==153190400&&!strcmp(sha,"0d43feada6d758fcfea2ce78b4fd9f21ae4b7a7450ab06ba9e8c6c06b834dc4d"))return "31AI";
    return "UNKNOWN";
}
bool identify_object(Bytes data,Identity *out){
    memset(out,0,sizeof(*out));strcpy(out->identity,"UNKNOWN");strcpy(out->framing,"RAW");strcpy(out->codec,"NONE");
    if(!data.n||data.n>FILE_LIMIT)return false;
    if(data.n==ROLLBACK_BYTES||data.n==442368||data.n==153190400||data.n==(size_t)CANDIDATE_BYTES){char direct[65];sha_hex(data.p,data.n,direct);const char *label=known(data.n,direct);if(strcmp(label,"UNKNOWN")){strcpy(out->identity,label);out->raw_bytes=data.n;out->exact=true;return true;}}
    Bytes body=data;uint64_t declared=0;bool keybag=false;
    if(data.p[0]==0x30){const char *framing=NULL;if(!payload(data,&body,&declared,&keybag,&framing))return false;strcpy(out->framing,framing);}
    if(keybag){strcpy(out->codec,"KEYBAG_BLOCKED");return true;}
    char digest[65];size_t n=body.n;
    if(lzfse_magic(body)){strcpy(out->codec,"LZFSE");if(!decoded_hash(body,RAW_LIMIT,declared,digest,&n))return false;}
    else {if(declared||(body.n>=3&&!memcmp(body.p,"\x1f\x8b\x08",3)))return false;if(body.n>RAW_LIMIT)return false;sha_hex(body.p,body.n,digest);}
    const char *label=known(n,digest);strcpy(out->identity,label);out->raw_bytes=n;out->exact=strcmp(label,"UNKNOWN")!=0;return true;
}
bool codec_selftest(void){
    enum{N=65536};uint8_t *plain=malloc(N),*encoded=malloc(N*2+1);if(!plain||!encoded){free(plain);free(encoded);return false;}
    for(size_t i=0;i<N;i++)plain[i]=(uint8_t)((i*17)^(i>>4));
    size_t n=compression_encode_buffer(encoded,N*2,plain,N,NULL,COMPRESSION_LZFSE);char expected[65],actual[65];size_t got=0;sha_hex(plain,N,expected);
    bool ok=n>0&&decoded_hash((Bytes){encoded,n},N,N,actual,&got)&&got==N&&!strcmp(actual,expected);
    if(ok){encoded[n]=0;ok=!decoded_hash((Bytes){encoded,n+1},N,N,actual,&got)&&!decoded_hash((Bytes){encoded,n-1},N,N,actual,&got)&&!decoded_hash((Bytes){encoded,n},N-1,N,actual,&got);}
    free(plain);free(encoded);return ok;
}
