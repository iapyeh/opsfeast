"""FreeBSD pkg ordering port; upstream libpkg/pkg_version.c rules.

/*-
 * SPDX-License-Identifier: LicenseRef-scancode-bsd-unchanged
 *
 * Copyright (c) 2011 Philippe Pepiot <phil@philpep.org>
 * Copyright (c) 2014 Vsevolod Stakhov <vsevolod@FreeBSD.org>
 * All rights reserved.
 * 
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer
 *    in this position and unchanged.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 * 
 * THIS SOFTWARE IS PROVIDED BY THE AUTHOR(S) ``AS IS'' AND ANY EXPRESS OR
 * IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
 * OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
 * IN NO EVENT SHALL THE AUTHOR(S) BE LIABLE FOR ANY DIRECT, INDIRECT,
 * INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
 * NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
 * THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */



Source: https://github.com/freebsd/pkg/blob/master/libpkg/pkg_version.c
The original notice above is retained unchanged.
"""
import re


def _split(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9.*+,:_~!-]{1,1024}',value):raise ValueError('invalid_freebsd_package_version')
    value=value.rsplit('-',1)[-1]
    match=re.fullmatch(r'([^_,]+)(?:_([0-9]+))?(?:,([0-9]+))?',value)
    if not match:raise ValueError('invalid_freebsd_package_version')
    return int(match[3] or 0),match[1].lower(),int(match[2] or 0)


def _component(value,pos):
    n=-1;letter=0;patch=0;hasstage=True
    match=re.match(r'[0-9]+',value[pos:])
    if match:n=int(match[0]);pos+=len(match[0]);hasstage=False
    elif pos<len(value) and value[pos]=='*':
        end=value.find('+',pos);return (-2,0,0),len(value) if end<0 else end
    if pos<len(value) and value[pos].isalpha():
        stage=next((s for s in ('pl','snap','alpha','beta','pre','rc') if value.startswith(s,pos) and (pos+len(s)==len(value) or not value[pos+len(s)].isalpha())),None)
        if stage and not hasstage:return (n,0,0),pos
        if stage:letter=0 if stage=='pl' else ord(stage[0])-ord('a')+2;pos+=len(stage)
        else:
            letter=ord(value[pos])-ord('a')+2
            while pos<len(value) and value[pos].isalpha():pos+=1
        match=re.match(r'[0-9]+',value[pos:]);patch=int(match[0]) if match else -1
        if match:pos+=len(match[0])
    while pos<len(value) and not value[pos].isalnum() and value[pos] not in '+*':pos+=1
    return (n,letter,patch),pos


def compare(a,b):
    ae,a,ar=_split(a);be,b,br=_split(b)
    sign=lambda x,y:(x>y)-(x<y)
    if ae!=be:return sign(ae,be)
    i=j=0
    while i<len(a) or j<len(b):
        blocked_a=i==len(a) or a[i]=='+';blocked_b=j==len(b) or b[j]=='+'
        av,bv=(0,0,0),(0,0,0)
        if not blocked_a:av,i=_component(a,i)
        if not blocked_b:bv,j=_component(b,j)
        if blocked_a and blocked_b:
            i+=i<len(a);j+=j<len(b)
        elif av!=bv:return sign(av,bv)
    return sign(ar,br)
