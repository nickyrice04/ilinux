/* SPDX-License-Identifier: MIT */
/* Pure original console-format tests; no hardware or diagnostic workloads. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "readable.h"
static unsigned checks;
#define CHECK(x) do {assert(x);checks++;} while(0)
static struct readable_state valid(void) {
    return (struct readable_state){.tick=60,.passed=18,.created=18,.expected=18,
        .cpu=READABLE_OK,.ram=READABLE_OK,.timer=READABLE_OK,.scope=READABLE_NATIVE};
}
static void bounds(const char *text,size_t size) {
    unsigned rows=0,columns=0,max=0;
    for(size_t i=0;i<size;i++) {
        CHECK(text[i]=='#' || text[i]==' ' || text[i]=='\n');
        if(text[i]=='\n') {if(columns>max)max=columns;columns=0;rows++;}else columns++;
    }
    CHECK(rows==READABLE_ROWS);CHECK(max<=READABLE_COLUMNS);CHECK(columns==0);CHECK(text[size]==0);
}
int main(void) {
    struct readable_state s=valid();char guarded[READABLE_CAP+4];memset(guarded,'@',sizeof(guarded));
    size_t n=readable_render(guarded+2,READABLE_CAP,&s);CHECK(n>0);bounds(guarded+2,n);
    CHECK(guarded[0]=='@' && guarded[1]=='@' && guarded[READABLE_CAP+2]=='@' && guarded[READABLE_CAP+3]=='@');
    char copy[READABLE_CAP];CHECK(readable_render(copy,sizeof(copy),&s)==n);CHECK(!memcmp(copy,guarded+2,n+1));
    char tiny[4]={'@','@','@','@'};CHECK(!readable_render(tiny+1,1,&s));CHECK(tiny[0]=='@' && tiny[1]==0 && tiny[2]=='@' && tiny[3]=='@');
    CHECK(!readable_render(NULL,0,&s));CHECK(!readable_render(copy,sizeof(copy),NULL));
    for(int kind=0;kind<8;kind++) {
        s=valid();
        switch(kind) {
        case 0:s.tick=-1;break;case 1:s.tick=61;break;case 2:s.passed=19;break;
        case 3:s.expected=65;break;case 4:s.cpu=(enum readable_result)99;break;
        case 5:s.scope=(enum readable_scope)99;break;case 6:s.expected=0;break;
        case 7:s.passed=17;break;
        }
        CHECK(!readable_render(copy,sizeof(copy),&s));CHECK(copy[0]==0);
    }
    for(int kind=0;kind<4;kind++) {
        s=valid();s.cpu=(enum readable_result)kind;s.scope=READABLE_DEMO;
        if(kind!=READABLE_OK) {s.passed=1;s.created=1;}
        n=readable_render(copy,sizeof(copy),&s);CHECK(n>0);bounds(copy,n);
    }
    s=valid();s.scope=READABLE_VM;s.expected=s.created=s.passed=4;
    n=readable_render(copy,sizeof(copy),&s);CHECK(n>0);bounds(copy,n);
    printf("{\"scope\":\"ORIGINAL_ASCII_PANEL_TESTS\",\"status\":\"PASS\",\"assertions\":%u,\"max_columns\":%d,\"rows\":%d,\"hardware_access\":false}\n",checks,READABLE_COLUMNS,READABLE_ROWS);
    return 0;
}
