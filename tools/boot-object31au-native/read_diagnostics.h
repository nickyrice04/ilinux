/* SPDX-License-Identifier: MIT */
#ifndef ILINUX31AU_READ_DIAGNOSTICS_H
#define ILINUX31AU_READ_DIAGNOSTICS_H
#include "diagnostics.h"
#include <CommonCrypto/CommonHMAC.h>
#include <string.h>

/* Observations from one already-bound selected read. The reference commitment
 * is ephemeral process memory ONLY; no serializer includes it. No path, policy
 * reference, identifier, input pointer or errno is exported or persisted. */
typedef struct {
    bool reference_present, read_attempted, read_succeeded;
    ObjectDiagnostics31AT object;
    bool reference_commitment_bound;
    char reference_commitment[65];
} ObjectRead31AU;

static ObjectRead31AU au_object_read;
static void au_object_reset(void) {
    au_object_read = (ObjectRead31AU){.object={.stage="NOT_OBSERVED",
        .identity="UNKNOWN",.container="UNCLASSIFIED",.codec="NONE"}};
}
static void au_reference_commitment(const char *coih,const char *nsih,const Profile *p,const ComparisonKey *key){
    if(!key||!key->loaded)return;
    CCHmacContext context;CCHmacInit(&context,kCCHmacAlgSHA256,key->bytes,sizeof(key->bytes));
    const char *parts[]={"ilinux31au-selected-reference-v1",p->sha,"LAB",coih,nsih};
    for(size_t i=0;i<sizeof(parts)/sizeof(parts[0]);i++)CCHmacUpdate(&context,parts[i],strlen(parts[i])+1);
    unsigned char digest[32];CCHmacFinal(&context,digest);static const char digits[]="0123456789abcdef";
    for(size_t i=0;i<32;i++){au_object_read.reference_commitment[i*2]=digits[digest[i]>>4];au_object_read.reference_commitment[i*2+1]=digits[digest[i]&15];}
    au_object_read.reference_commitment[64]=0;au_object_read.reference_commitment_bound=true;memset(digest,0,sizeof(digest));
}
#endif
