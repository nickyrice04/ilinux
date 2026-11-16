/* SPDX-License-Identifier: MIT */
#include "codec.h"
/* Builder verifies original AJ core and reviewed AV proposal, derives only
 * three fixed buffer failure labels, and leaves every frozen source intact. */
#include "core.c"
#include "buffer_proposal.c"

void object_diagnostics31aw(Bytes input,ObjectDiagnostics31AW *out) {
    *out=(ObjectDiagnostics31AW){.stage="INPUT_BOUND_REJECTED",.identity="UNKNOWN",
        .container="UNCLASSIFIED",.codec="NONE",.decode_reason="NOT_APPLICABLE"};
    if(!input.p&&input.n)return;
    Identity authoritative;const char *reason=NULL;
    bool completed=identity_buffer31av(input,&authoritative,&reason);
    out->recognizer_completed=completed;
    out->known_exact=completed&&authoritative.exact;
    out->candidate_exact=out->known_exact&&!strcmp(authoritative.identity,"CANDIDATE");
    /* Only known finite labels may leave this pure adapter. */
    const char *labels[]={"CANDIDATE","BOOT021","31AF","31AI"};
    out->identity="UNKNOWN";
    for(size_t i=0;i<4;i++)if(!strcmp(authoritative.identity,labels[i]))out->identity=labels[i];
    if(!input.n||input.n>FILE_LIMIT)return;
    if(out->known_exact) {
        out->container=!strcmp(authoritative.framing,"IMG4")?"IMG4":
            !strcmp(authoritative.framing,"IM4P")?"IM4P":"RAW";
        out->codec=!strcmp(authoritative.codec,"LZFSE")?"LZFSE":"NONE";
        out->decode_reason=!strcmp(out->codec,"LZFSE")?"DECODED":"NOT_APPLICABLE";
        out->stage="KNOWN_MATCHED";return;
    }
    Bytes body=input;uint64_t declared=0;bool keybag=false;out->container="RAW";
    if(input.p[0]==0x30) {
        const char *framing=NULL;
        if(!payload(input,&body,&declared,&keybag,&framing)) {
            out->container="UNCLASSIFIED";out->stage="DER_FRAMING_REJECTED";return;
        }
        out->container=!strcmp(framing,"IMG4")?"IMG4":"IM4P";
    }
    if(keybag){out->codec="KEYBAG_BLOCKED";out->stage="KEYBAG_BLOCKED";return;}
    if(lzfse_magic(body)) {
        out->codec="LZFSE";
        if(!body.n||body.n>COMPRESSED_LIMIT){out->stage="COMPRESSED_BOUND_REJECTED";return;}
        size_t framed=0;
        if(!lzfse_frame(body,RAW_LIMIT,&framed)){out->stage="LZFSE_FRAME_REJECTED";return;}
        if(declared&&framed!=declared){out->stage="DECLARED_SIZE_MISMATCH";return;}
        out->stage=completed?"DECODED_UNMATCHED":"DECODE_REJECTED";
        out->decode_reason=completed?"DECODED":reason;
        return;
    }
    if(declared){out->stage="UNCOMPRESSED_DECLARATION_REJECTED";return;}
    if(body.n>=3&&!memcmp(body.p,"\x1f\x8b\x08",3)) {
        out->codec="GZIP_UNSUPPORTED";out->stage="GZIP_UNSUPPORTED";return;
    }
    out->stage=body.n>RAW_LIMIT?"UNCOMPRESSED_BOUND_REJECTED":"UNCOMPRESSED_UNMATCHED";
}

CodecCapability31AW codec_capability31aw(void) {
    enum{N=1048576,CAP=N*2+4096};
    CodecCapability31AW result={.attempted=true,.reason="ALLOCATION_ERROR"};
    uint8_t *plain=malloc(N),*encoded=malloc(CAP);
    if(!plain||!encoded){free(plain);free(encoded);return result;}
    uint32_t state=0x19671234;
    for(size_t i=0;i<N;i++){state^=state<<13;state^=state>>17;state^=state<<5;plain[i]=(uint8_t)state;}
    char expected[65],actual[65];sha_hex(plain,N,expected);
    size_t encoded_bytes=compression_encode_buffer(encoded,CAP,plain,N,NULL,COMPRESSION_LZFSE);
    if(!encoded_bytes||encoded_bytes>=CAP){result.reason="ENCODE_FAILED";goto done;}
    size_t bytes=0;const char *why=NULL;
    bool decoded=buffer_hash31av((Bytes){encoded,encoded_bytes},N,N,actual,&bytes,&why);
    result.positive_exact=decoded&&bytes==N&&!strcmp(expected,actual);
    encoded[encoded_bytes]=0;
    bool trailing=!buffer_hash31av((Bytes){encoded,encoded_bytes+1},N,N,actual,&bytes,&why);
    bool truncated=!buffer_hash31av((Bytes){encoded,encoded_bytes-1},N,N,actual,&bytes,&why);
    uint8_t bad[]={'b','v','x','n',16,0,0,0,3,0,0,0,0,0,0,'b','v','x','$'};
    bool invalid=!buffer_hash31av((Bytes){bad,sizeof(bad)},N,16,actual,&bytes,&why);
    bool bound=!buffer_hash31av((Bytes){encoded,COMPRESSED_LIMIT+1},N,N,actual,&bytes,&why);
    bool saturation=false;
    if(encoded_bytes>=8) {
        uint32_t raw=le32(encoded+4);
        if(raw>1) {
            uint32_t smaller=raw-1;
            for(unsigned i=0;i<4;i++)encoded[4+i]=(uint8_t)(smaller>>(8*i));
            saturation=!buffer_hash31av((Bytes){encoded,encoded_bytes},N,0,actual,&bytes,&why);
        }
    }
    result.negative_refused=trailing&&truncated&&invalid&&bound&&saturation;
    result.passed=result.positive_exact&&result.negative_refused;
    result.reason=result.passed?"PASS":!result.positive_exact?"POSITIVE_CONTROL_FAILED":"NEGATIVE_CONTROL_FAILED";
done:
    free(encoded);free(plain);return result;
}
