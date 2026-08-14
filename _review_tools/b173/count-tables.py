# -*- coding: utf-8 -*-
import os, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
root = r'F:\CamelTv-batch173-review\test-platform-v2\backend\app\models'
tables = set()
for dp, dn, fn in os.walk(root):
    for f in fn:
        if f.endswith('.py'):
            p = os.path.join(dp, f)
            try:
                txt = open(p, encoding='utf-8').read()
            except Exception:
                continue
            for m in re.finditer(r'__tablename__\s*=\s*["\']([^"\']+)["\']', txt):
                tables.add(m.group(1))
print('TOTAL:', len(tables))
print(sorted(tables))
