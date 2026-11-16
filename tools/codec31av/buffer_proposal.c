/* SPDX-License-Identifier: MIT */
/* Include after the unchanged pinned core.c. This pure proposal deliberately
 * reuses its strict frame walker. It is not linked into any target collector. */
static bool buffer_hash31av(Bytes encoded,size_t maximum,uint64_t declared,
                           char digest[65],size_t *output,const char **reason) {
    *output=0;*reason="INPUT_BOUND";
    if(!encoded.p||!encoded.n||encoded.n>COMPRESSED_LIMIT||!maximum||maximum>RAW_LIMIT)return false;
    size_t framed=0;*reason="FRAME_REJECTED";
    if(!lzfse_frame(encoded,maximum,&framed))return false;
    *reason="DECLARED_SIZE_MISMATCH";
    if(declared&&framed!=declared)return false;
    *reason="OUTPUT_BOUND";
    if(framed>maximum||framed==SIZE_MAX)return false;
    /* Decode into one EXTRA byte. The API may return destination capacity
     * after truncation; exact capacity would not prove complete expansion. */
    size_t capacity=framed+1;
    uint8_t *plain=malloc(capacity);*reason="ALLOCATION_ERROR";
    if(!plain)return false;
    size_t decoded=compression_decode_buffer(plain,capacity,encoded.p,encoded.n,NULL,COMPRESSION_LZFSE);
    bool ok=decoded==framed && (!declared||decoded==declared);
    *reason=ok?"DECODED":"DECODE_REJECTED";
    if(ok){sha_hex(plain,decoded,digest);*output=decoded;}
    free(plain);return ok;
}

static bool identity_buffer31av(Bytes data,Identity *out,const char **reason) {
    /* Same raw/keybag/DER framing/known-hash requirements as original. Only
     * compressed decoding is proposed differently; no guessed identity. */
    memset(out,0,sizeof(*out));strcpy(out->identity,"UNKNOWN");
    strcpy(out->framing,"RAW");strcpy(out->codec,"NONE");*reason="INPUT_BOUND";
    if(!data.p||!data.n||data.n>FILE_LIMIT)return false;
    if(data.n==ROLLBACK_BYTES||data.n==442368||data.n==153190400||data.n==(size_t)CANDIDATE_BYTES) {
        char direct[65];sha_hex(data.p,data.n,direct);const char *label=known(data.n,direct);
        if(strcmp(label,"UNKNOWN")){strcpy(out->identity,label);out->raw_bytes=data.n;
            out->exact=true;*reason="KNOWN_MATCHED";return true;}
    }
    Bytes body=data;uint64_t declared=0;bool keybag=false;
    if(data.p[0]==0x30) {
        const char *framing=NULL;*reason="DER_FRAMING_REJECTED";
        if(!payload(data,&body,&declared,&keybag,&framing))return false;
        strcpy(out->framing,framing);
    }
    if(keybag){strcpy(out->codec,"KEYBAG_BLOCKED");*reason="KEYBAG_BLOCKED";return true;}
    char digest[65];size_t n=body.n;
    if(lzfse_magic(body)) {
        strcpy(out->codec,"LZFSE");
        if(!buffer_hash31av(body,RAW_LIMIT,declared,digest,&n,reason))return false;
    } else {
        *reason="UNCOMPRESSED_REJECTED";
        if(declared||(body.n>=3&&!memcmp(body.p,"\x1f\x8b\x08",3))||body.n>RAW_LIMIT)return false;
        sha_hex(body.p,body.n,digest);
    }
    const char *label=known(n,digest);strcpy(out->identity,label);out->raw_bytes=n;
    out->exact=strcmp(label,"UNKNOWN")!=0;
    *reason=out->exact?"KNOWN_MATCHED":"DECODED_UNMATCHED";return true;
}
