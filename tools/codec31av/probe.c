/* SPDX-License-Identifier: MIT */
/* Original, own-fixture-only decoder differential. Frozen implementation is
 * copied by build.py and included unchanged; no target collector is linked. */
#include "core.c"
#include "buffer_proposal.c"

typedef struct {
    const char *reason;
    size_t output, remaining, calls;
    bool exact;
} Trace;

static Trace trace_stream(Bytes encoded, size_t expected, const char *expected_sha,
                          size_t chunk, size_t input_chunk, bool finalize) {
    Trace r = {.reason="INIT_ERROR", .remaining=encoded.n};
    compression_stream stream = {0};
    if (compression_stream_init(&stream, COMPRESSION_STREAM_DECODE,
                                COMPRESSION_LZFSE) != COMPRESSION_STATUS_OK) return r;
    uint8_t *buffer = malloc(chunk);
    if (!buffer) { compression_stream_destroy(&stream); r.reason="ALLOCATION_ERROR"; return r; }
    size_t supplied=0;
    CC_SHA256_CTX sha; CC_SHA256_Init(&sha);
    r.reason="ITERATION_BOUND";
    for (size_t i=0; i<RAW_LIMIT/chunk+COMPRESSED_LIMIT+16; i++) {
        if (!stream.src_size && supplied<encoded.n) {
            size_t amount=encoded.n-supplied;
            if(amount>input_chunk)amount=input_chunk;
            stream.src_ptr=encoded.p+supplied;stream.src_size=amount;supplied+=amount;
        }
        size_t before=stream.src_size;
        stream.dst_ptr=buffer; stream.dst_size=chunk;
        compression_status status=compression_stream_process(&stream,
            finalize&&supplied==encoded.n?COMPRESSION_STREAM_FINALIZE:0);
        r.calls++; r.remaining=stream.src_size+encoded.n-supplied;
        size_t wrote=chunk-stream.dst_size;
        if (wrote>RAW_LIMIT-r.output) { r.reason="OUTPUT_BOUND"; break; }
        if (status==COMPRESSION_STATUS_ERROR) { r.reason="PROCESS_ERROR"; break; }
        r.output+=wrote; CC_SHA256_Update(&sha,buffer,(CC_LONG)wrote);
        if (status==COMPRESSION_STATUS_END) {
            if (r.remaining) r.reason="END_WITH_INPUT";
            else if (r.output!=expected) r.reason="OUTPUT_SIZE_MISMATCH";
            else {
                uint8_t sum[32]; char digest[65];
                CC_SHA256_Final(sum,&sha); hex(sum,32,digest);
                r.exact=!strcmp(digest,expected_sha);
                r.reason=r.exact?"EXACT":"OUTPUT_HASH_MISMATCH";
            }
            break;
        }
        if (status!=COMPRESSION_STATUS_OK) { r.reason="UNEXPECTED_STATUS"; break; }
        if (!wrote && before==stream.src_size) { r.reason="NO_PROGRESS"; break; }
    }
    compression_stream_destroy(&stream); free(buffer); return r;
}

static bool buffer_exact(Bytes encoded, Bytes plain) {
    /* One extra output byte detects over-expansion. This API cannot report
     * source consumption or EOS, so it is a comparison, never admission. */
    uint8_t *out=malloc(plain.n+1); if(!out) return false;
    size_t n=compression_decode_buffer(out,plain.n+1,encoded.p,encoded.n,NULL,COMPRESSION_LZFSE);
    bool ok=n==plain.n&&!memcmp(out,plain.p,n); free(out); return ok;
}

static unsigned failures, cases, stream_trials, invalid_buffer_exact, valid_stream_failures;
static void compare(const char *label, Bytes encoded, Bytes plain, bool valid, bool large) {
    char expected[65], actual[65]; sha_hex(plain.p,plain.n,expected);
    size_t framed=0, decoded=0;
    bool frame=lzfse_frame(encoded,RAW_LIMIT,&framed);
    bool frozen=decoded_hash(encoded,RAW_LIMIT,plain.n,actual,&decoded);
    bool frozen_exact=frozen&&decoded==plain.n&&!strcmp(actual,expected);
    bool buffer=buffer_exact(encoded,plain);
    const char *proposal_reason=NULL;size_t proposal_bytes=0;
    bool proposal=buffer_hash31av(encoded,RAW_LIMIT,plain.n,actual,&proposal_bytes,&proposal_reason);
    bool proposal_exact=proposal&&proposal_bytes==plain.n&&!strcmp(actual,expected);
    Identity identity;const char *identity_reason=NULL;
    bool completed=identity_buffer31av(encoded,&identity,&identity_reason);
    if(completed!=proposal || (completed && identity.raw_bytes!=proposal_bytes))failures++;
    if(valid ? (!frame||framed!=plain.n||!proposal_exact||!buffer) : (frozen_exact||proposal_exact)) failures++;
    const size_t chunks[]={31,4096,65535,65536,65537,262144};
    bool traces=true;
    for(size_t i=large?1:0;i<sizeof(chunks)/sizeof(chunks[0]);i++) {
        Trace t=trace_stream(encoded,plain.n,expected,chunks[i],encoded.n,true); stream_trials++;
        if(valid&&!t.exact) { traces=false; valid_stream_failures++; }
        if((!valid&&t.exact)||(!valid&&i==3)||!strcmp(t.reason,"PROCESS_ERROR")) {
            printf("{\"kind\":\"trace\",\"case\":\"%s\",\"chunk\":%zu,"
                   "\"reason\":\"%s\",\"decoded_bytes\":%zu,\"input_remaining\":%zu,"
                   "\"calls\":%zu,\"valid_control\":%s}\n",label,chunks[i],t.reason,
                   t.output,t.remaining,t.calls,valid?"true":"false");
        }
    }
    if(valid && (!frozen_exact || large)) {
        const size_t input_chunks[]={4096,32768,131072,262144,786432};
        for(size_t i=0;i<sizeof(input_chunks)/sizeof(input_chunks[0]);i++) {
            Trace t=trace_stream(encoded,plain.n,expected,65536,input_chunks[i],true);stream_trials++;
            printf("{\"kind\":\"source_chunk_trace\",\"case\":\"%s\",\"input_chunk\":%zu,"
                   "\"reason\":\"%s\",\"decoded_bytes\":%zu,\"input_remaining\":%zu,\"calls\":%zu}\n",
                   label,input_chunks[i],t.reason,t.output,t.remaining,t.calls);
        }
        Trace t=trace_stream(encoded,plain.n,expected,65536,encoded.n,false);stream_trials++;
        printf("{\"kind\":\"nonfinal_trace\",\"case\":\"%s\",\"reason\":\"%s\","
               "\"decoded_bytes\":%zu,\"input_remaining\":%zu,\"calls\":%zu}\n",
               label,t.reason,t.output,t.remaining,t.calls);
    }
    if(!valid&&buffer) invalid_buffer_exact++;
    cases++;
    printf("{\"kind\":\"case\",\"case\":\"%s\",\"valid_control\":%s,"
           "\"frame_accepted\":%s,\"frozen_exact\":%s,\"buffer_exact\":%s,"
           "\"stream_matrix_exact\":%s,\"proposal_exact\":%s,\"proposal_known_exact\":%s,\"proposal_reason\":\"%s\","
           "\"plain_bytes\":%zu,\"encoded_bytes\":%zu}\n",
           label,valid?"true":"false",frame?"true":"false",frozen_exact?"true":"false",
           buffer?"true":"false",traces?"true":"false",proposal_exact?"true":"false",
           completed&&identity.exact?"true":"false",proposal_reason,plain.n,encoded.n);
}

static uint8_t *encode(Bytes plain,size_t *n,bool streaming) {
    size_t cap=plain.n*2+4096; uint8_t *out=malloc(cap); if(!out) return NULL;
    if(!streaming) {
        *n=compression_encode_buffer(out,cap,plain.p,plain.n,NULL,COMPRESSION_LZFSE);
        if(!*n) { free(out); return NULL; } return out;
    }
    compression_stream s={0};
    if(compression_stream_init(&s,COMPRESSION_STREAM_ENCODE,COMPRESSION_LZFSE)!=COMPRESSION_STATUS_OK) {
        free(out);return NULL;
    }
    s.src_ptr=plain.p; s.src_size=plain.n; s.dst_ptr=out; s.dst_size=cap;
    compression_status status=compression_stream_process(&s,COMPRESSION_STREAM_FINALIZE);
    bool ok=status==COMPRESSION_STATUS_END&&!s.src_size;
    *n=cap-s.dst_size; compression_stream_destroy(&s);
    if(!ok) {free(out);return NULL;} return out;
}

static void generated(size_t n,unsigned pattern) {
    uint8_t *plain=malloc(n); if(!plain){failures++;return;}
    uint32_t random=0x19671234;
    for(size_t i=0;i<n;i++) {
        random^=random<<13;random^=random>>17;random^=random<<5;
        plain[i]=pattern==0?0:pattern==1?(uint8_t)((i*17)^(i>>4)):(uint8_t)random;
    }
    char label[80];
    for(unsigned method=0;method<2;method++) {
        size_t size=0;uint8_t *encoded=encode((Bytes){plain,n},&size,method!=0);
        if(!encoded){failures++;continue;}
        snprintf(label,sizeof(label),"generated_%zu_pattern%u_encoder%u",n,pattern,method);
        compare(label,(Bytes){encoded,size},(Bytes){plain,n},true,false);
        if(n==65536 && pattern==1 && method==0) {
            compare("truncated_eos",(Bytes){encoded,size-1},(Bytes){plain,n},false,false);
            compare("missing_eos",(Bytes){encoded,size-4},(Bytes){plain,n},false,false);
            uint8_t *trailer=malloc(size+1);
            if(trailer){memcpy(trailer,encoded,size);trailer[size]=0;
                compare("trailing_byte",(Bytes){trailer,size+1},(Bytes){plain,n},false,false);free(trailer);}
        }
        free(encoded);
    }
    free(plain);
}

static void raw_blocks(void) {
    enum {N=65537};uint8_t *plain=malloc(N),*encoded=malloc(N+20);
    if(!plain||!encoded){free(plain);free(encoded);failures++;return;}
    for(size_t i=0;i<N;i++)plain[i]=(uint8_t)i;
    memcpy(encoded,"bvx-",4);uint32_t n=65536;memcpy(encoded+4,&n,4);
    memcpy(encoded+8,plain,65536);memcpy(encoded+65544,"bvx-",4);n=1;
    memcpy(encoded+65548,&n,4);encoded[65552]=plain[65536];memcpy(encoded+65553,"bvx$",4);
    compare("two_uncompressed_blocks",(Bytes){encoded,N+20},(Bytes){plain,N},true,false);
    uint8_t invalid[]={ 'b','v','x','n',16,0,0,0,3,0,0,0,0,0,0,'b','v','x','$' };
    compare("framed_invalid_lzvn",(Bytes){invalid,sizeof(invalid)},(Bytes){plain,16},false,false);
    free(encoded);free(plain);
}

static bool candidate(const char *path) {
    const char prefix[]=WORKSPACE_ROOT "/build/";
    if(strncmp(path,prefix,sizeof(prefix)-1))return false;
    uint8_t *plain=NULL;size_t size=0;char sha[65];
    if(!read_file(path,RAW_LIMIT,true,&plain,&size))return false;
    sha_hex(plain,size,sha);
    if(size!=CANDIDATE_BYTES||strcmp(sha,CANDIDATE_SHA256)){free(plain);return false;}
    for(unsigned method=0;method<2;method++) {
        size_t encoded_size=0;uint8_t *encoded=encode((Bytes){plain,size},&encoded_size,method!=0);
        if(!encoded){failures++;continue;}
        compare(method?"own_candidate_stream_encoder":"own_candidate_buffer_encoder",
                (Bytes){encoded,encoded_size},(Bytes){plain,size},true,true);
        free(encoded);
    }
    free(plain);return true;
}

static int fixture(const char *path) {
    const char prefix[]=WORKSPACE_ROOT "/build/codec31av/";
    if(strncmp(path,prefix,sizeof(prefix)-1))return 2;
    uint8_t *data=NULL;size_t size=0;
    if(!read_file(path,FILE_LIMIT,true,&data,&size))return 2;
    Identity old,proposal;const char *reason=NULL;
    bool original=identify_object((Bytes){data,size},&old);
    bool completed=identity_buffer31av((Bytes){data,size},&proposal,&reason);
    printf("{\"kind\":\"fixture\",\"frozen_completed\":%s,\"frozen_exact\":%s,"
           "\"proposal_completed\":%s,\"proposal_exact\":%s,\"proposal_candidate_exact\":%s,"
           "\"reason\":\"%s\",\"native_ready\":false,\"host_queries\":false}\n",
           original?"true":"false",original&&old.exact?"true":"false",completed?"true":"false",
           completed&&proposal.exact?"true":"false",
           completed&&proposal.exact&&!strcmp(proposal.identity,"CANDIDATE")?"true":"false",reason);
    free(data);return 0;
}

int main(int argc,char **argv) {
    if(argc==1 || (argc==2&&!strcmp(argv[1],"--help"))) {
        puts("{\"status\":\"INERT\",\"scope\":\"OWN_WORKSPACE_FIXTURES_ONLY\",\"native_ready\":false}");return 0;
    }
    if(argc==2&&!strcmp(argv[1],"--selftest")) {
        const size_t sizes[]={1,7,8,63,64,4095,4096,65535,65536,65537,262144,1048576};
        for(size_t i=0;i<sizeof(sizes)/sizeof(sizes[0]);i++)for(unsigned p=0;p<3;p++)generated(sizes[i],p);
        raw_blocks();
    } else if(argc==3&&!strcmp(argv[1],"--candidate")) {
        if(!candidate(argv[2])){puts("{\"status\":\"REFUSED\",\"scope\":\"OWN_WORKSPACE_FIXTURES_ONLY\"}");return 2;}
    } else if(argc==3&&!strcmp(argv[1],"--fixture")) {
        int result=fixture(argv[2]);
        if(result)puts("{\"status\":\"REFUSED\",\"scope\":\"OWN_WORKSPACE_FIXTURES_ONLY\"}");
        return result;
    } else {puts("{\"status\":\"REFUSED\",\"scope\":\"OWN_WORKSPACE_FIXTURES_ONLY\"}");return 2;}
    printf("{\"kind\":\"summary\",\"status\":\"%s\",\"cases\":%u,\"stream_trials\":%u,"
           "\"failures\":%u,\"valid_stream_failures\":%u,\"invalid_buffer_exact\":%u,\"host_queries\":false,"
           "\"native_ready\":false,\"controller_integrated\":false}\n",
           failures?"FAIL":"PASS",cases,stream_trials,failures,valid_stream_failures,invalid_buffer_exact);
    return failures?1:0;
}
