import sys
p=sys.argv[1]; s=open(p,encoding='utf-8').read()
if '/* v62c */' not in s:
    s=s.replace('</style>', "/* v62c */#metaprop2 .lgrid{grid-template-columns:1fr!important}#metaprop2 .lgt td.md{white-space:nowrap}\n</style>",1); open(p,'w',encoding='utf-8').write(s); print('css62 applied')
else: print('already')
