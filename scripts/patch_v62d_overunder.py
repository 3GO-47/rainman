import sys
p=sys.argv[1]; s=open(p,encoding='utf-8').read()
a=s.index("function metaProp2(root='#metaprop2'"); b=s.index("\n}\n",a)+3; src=s[a:b]
pairs=[("<b class=\"${x.evSide==='O'?'ov':'un'}\">${x.evSide}</b> <b>${x.ev>=0?'+':''}${(100*x.ev).toFixed(0)}%</b>","<b class=\"${x.evSide==='O'?'ov':'un'}\">${x.evSide==='O'?'OVER':'UNDER'}</b> <b>${x.ev>=0?'+':''}${(100*x.ev).toFixed(0)}%</b>"),
("${x.agSide?x.agSide+' ':''}${Math.max(x.agO,x.agU)}/${x.agN}","${x.agSide?(x.agSide==='O'?'OVER ':'UNDER '):''}${Math.max(x.agO,x.agU)}/${x.agN}"),
("x=>`<b class=\"rise\">${x.evSide} ${x.ev>=0?'+':''}${(100*x.ev).toFixed(0)}%</b>`","x=>`<b class=\"rise\">${x.evSide==='O'?'OVER':'UNDER'} ${x.ev>=0?'+':''}${(100*x.ev).toFixed(0)}%</b>`"),
("B(`O ${x.agO}/${x.agN}`","B(`OVER ${x.agO}/${x.agN}`"),("B(`U ${x.agU}/${x.agN}`","B(`UNDER ${x.agU}/${x.agN}`")]
n=0
for o,nw in pairs:
    if src.count(o)==1: src=src.replace(o,nw); n+=1
    else: assert nw in src, o[:60]
s=s[:a]+src+s[b:]; open(p,'w',encoding='utf-8').write(s); print('ou62', n, 'replacements')
