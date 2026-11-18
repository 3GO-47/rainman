import sys
p=sys.argv[1]; s=open(p,encoding='utf-8').read()
a="'test',sub:'metaprop'}]},\n"; b="',c:'test',sub:'metav2'},\n"
assert s.count(a)==1 and s.count(b)==1
s=s.replace(a,"'test',sub:'metaprop'},\n").replace(b,"',c:'test',sub:'metav2'}]},\n")
open(p,'w',encoding='utf-8').write(s); print('fixed')
