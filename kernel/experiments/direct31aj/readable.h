/* SPDX-License-Identifier: MIT */
/* Original 3x5 ASCII glyphs; console text only, no font/framebuffer access. */
#ifndef ILINUX31AJ_READABLE_H
#define ILINUX31AJ_READABLE_H
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

enum { READABLE_CAP=4096, READABLE_COLUMNS=78, READABLE_ROWS=35 };
enum readable_result { READABLE_WAIT, READABLE_OK, READABLE_FAIL, READABLE_TIME };
enum readable_scope { READABLE_NATIVE, READABLE_VM, READABLE_DEMO };
struct readable_state {
    int tick,passed,created,expected;
    enum readable_result cpu,ram,timer;
    enum readable_scope scope;
};
#define RB(a,b,c,d,e) ((uint16_t)(((a)<<12)|((b)<<9)|((c)<<6)|((d)<<3)|(e)))
static uint16_t readable_glyph(char c) {
    /* Each row is three original binary pixels, most significant row first. */
    switch(c) {
    case '0':return RB(7,5,5,5,7); case '1':return RB(2,6,2,2,7);
    case '2':return RB(7,1,7,4,7); case '3':return RB(7,1,7,1,7);
    case '4':return RB(5,5,7,1,1); case '5':return RB(7,4,7,1,7);
    case '6':return RB(7,4,7,5,7); case '7':return RB(7,1,2,2,2);
    case '8':return RB(7,5,7,5,7); case '9':return RB(7,5,7,1,7);
    case 'A':return RB(2,5,7,5,5); case 'C':return RB(7,4,4,4,7);
    case 'D':return RB(6,5,5,5,6); case 'E':return RB(7,4,6,4,7);
    case 'F':return RB(7,4,6,4,4); case 'I':return RB(7,2,2,2,7);
    case 'J':return RB(1,1,1,5,7); case 'K':return RB(5,5,6,5,5);
    case 'L':return RB(4,4,4,4,7); case 'M':return RB(5,7,7,5,5);
    case 'N':return RB(5,7,7,7,5); case 'O':return RB(7,5,5,5,7);
    case 'P':return RB(7,5,7,4,4); case 'R':return RB(6,5,6,5,5);
    case 'T':return RB(7,2,2,2,2); case 'U':return RB(5,5,5,5,7);
    case 'V':return RB(5,5,5,5,2); case 'W':return RB(5,5,7,7,5);
    case '/':return RB(1,1,2,4,4); case ' ':return 0;
    default:return 0;
    }
}
#undef RB
static const char *readable_word(enum readable_result status) {
    static const char *const names[]={"WAIT","OK","FAIL","TIME"};
    return (unsigned)status<4?names[status]:NULL;
}
static size_t readable_render(char *output,size_t cap,const struct readable_state *s) {
    if(!output || !cap)return 0;
    output[0]=0;
    if(!s || s->tick<0 || s->tick>60 || s->passed<0 || s->created<0 || s->expected<0 ||
       s->passed>s->created || s->created>64 || s->expected>64 ||
       !readable_word(s->cpu) || !readable_word(s->ram) || !readable_word(s->timer) ||
       (unsigned)s->scope>READABLE_DEMO)return 0;
    if(s->cpu==READABLE_OK && (!s->expected || s->passed!=s->expected || s->created!=s->expected))return 0;
    char lines[6][11]={{0}};
    const char *scope=s->scope==READABLE_NATIVE?"NATIVE":s->scope==READABLE_VM?"VM":"DEMO";
    snprintf(lines[0],sizeof(lines[0]),"31AJ");
    snprintf(lines[1],sizeof(lines[1]),"%s T%02d",scope,s->tick);
    snprintf(lines[2],sizeof(lines[2]),"CPU%02d/%02d",s->passed,s->expected);
    snprintf(lines[3],sizeof(lines[3]),"CPU %s",readable_word(s->cpu));
    snprintf(lines[4],sizeof(lines[4]),"RAM %s",readable_word(s->ram));
    snprintf(lines[5],sizeof(lines[5]),"TMR %s",readable_word(s->timer));
    char buffer[READABLE_CAP];size_t at=0;
    for(unsigned line=0;line<6;line++) {
        size_t count=strlen(lines[line]);
        if(!count || count>10)return 0;
        for(unsigned row=0;row<5;row++) {
            for(size_t col=0;col<count;col++) {
                unsigned bits=(readable_glyph(lines[line][col])>>(12-row*3))&7;
                for(unsigned pixel=0;pixel<3;pixel++) {
                    if(at+2>=sizeof(buffer))return 0;
                    char fill=bits&(4U>>pixel)?'#':' ';
                    buffer[at++]=fill;buffer[at++]=fill;
                }
                if(col+1<count) {if(at+2>=sizeof(buffer))return 0;buffer[at++]=' ';buffer[at++]=' ';}
            }
            if(at+1>=sizeof(buffer))return 0;
            buffer[at++]='\n';
        }
        if(line+1<6) {if(at+1>=sizeof(buffer))return 0;buffer[at++]='\n';}
    }
    if(at+1>cap)return 0;
    buffer[at]=0;memcpy(output,buffer,at+1);return at;
}
#endif
