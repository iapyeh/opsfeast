"""Native Debian and RPM EVR ordering, not semantic-version comparison."""
import re


def _check(value):
    if not isinstance(value,str) or not value or len(value)>1024 or not re.fullmatch(r'[A-Za-z0-9.+_~^:\-]+',value):
        raise ValueError('unsupported_package_version')
    return value


def _epoch(value):
    _check(value)
    if ':' not in value:return 0,value
    epoch,rest=value.split(':',1)
    if not epoch.isdigit() or not rest or ':' in rest:raise ValueError('invalid_package_epoch')
    return int(epoch),rest


def _sign(a,b):return (a>b)-(a<b)


def _deb_part(a,b):
    def order(char):
        if char=='~':return -1
        if not char or char.isdigit():return 0
        if char.isalpha():return ord(char)
        return ord(char)+256
    i=j=0
    while i<len(a) or j<len(b):
        while (i<len(a) and not a[i].isdigit()) or (j<len(b) and not b[j].isdigit()):
            ac=a[i] if i<len(a) else '';bc=b[j] if j<len(b) else ''
            if order(ac)!=order(bc):return _sign(order(ac),order(bc))
            if i<len(a):i+=1
            if j<len(b):j+=1
        while i<len(a) and a[i]=='0':i+=1
        while j<len(b) and b[j]=='0':j+=1
        ai=i;bj=j
        while i<len(a) and a[i].isdigit():i+=1
        while j<len(b) and b[j].isdigit():j+=1
        if i-ai!=j-bj:return _sign(i-ai,j-bj)
        if a[ai:i]!=b[bj:j]:return _sign(a[ai:i],b[bj:j])
    return 0


def debian(a,b):
    ae,a=_epoch(a);be,b=_epoch(b)
    if ae!=be:return _sign(ae,be)
    if '^' in a+b or '_' in a+b:raise ValueError('invalid_debian_version')
    av,sep,ar=a.rpartition('-');bv,bsep,br=b.rpartition('-')
    if not sep:av,ar=a,'0'
    if not bsep:bv,br=b,'0'
    if not av or not bv or not av[0].isdigit() or not bv[0].isdigit():raise ValueError('invalid_debian_version')
    return _deb_part(av,bv) or _deb_part(ar,br)


def _rpm_part(a,b):
    i=j=0
    while i<len(a) or j<len(b):
        while i<len(a) and not a[i].isalnum() and a[i] not in '~^':i+=1
        while j<len(b) and not b[j].isalnum() and b[j] not in '~^':j+=1
        ac=a[i] if i<len(a) else '';bc=b[j] if j<len(b) else ''
        if ac=='~' or bc=='~':
            if ac!='~':return 1
            if bc!='~':return -1
            i+=1;j+=1;continue
        if ac=='^' or bc=='^':
            if not ac:return -1
            if not bc:return 1
            if ac!='^':return 1
            if bc!='^':return -1
            i+=1;j+=1;continue
        if not ac or not bc:return _sign(bool(ac),bool(bc))
        numeric=ac.isdigit();ai=i;bj=j
        while i<len(a) and (a[i].isdigit() if numeric else a[i].isalpha()):i+=1
        while j<len(b) and (b[j].isdigit() if numeric else b[j].isalpha()):j+=1
        if i==ai:return -1
        if j==bj:return 1 if numeric else -1
        av,bv=a[ai:i],b[bj:j]
        if numeric:
            av,bv=av.lstrip('0'),bv.lstrip('0')
            if len(av)!=len(bv):return _sign(len(av),len(bv))
        if av!=bv:return _sign(av,bv)
    return 0


def rpm(a,b):
    ae,a=_epoch(a);be,b=_epoch(b)
    if ae!=be:return _sign(ae,be)
    av,sep,ar=a.rpartition('-');bv,bsep,br=b.rpartition('-')
    if not sep:av,ar=a,''
    if not bsep:bv,br=b,''
    return _rpm_part(av,bv) or _rpm_part(ar,br)


def compare(a,b,scheme):
    if scheme=='deb':return debian(a,b)
    if scheme=='rpm':return rpm(a,b)
    raise ValueError('unsupported_version_scheme')
