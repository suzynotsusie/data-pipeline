#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
from collections import defaultdict

# Read CSV
procs = []
with open('../data/thutuc/data.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    procs = list(reader)

# Group by category
categories = defaultdict(list)
for p in procs:
    categories[p['Lĩnh vực']].append(p)

print('📊 Phân loại thủ tục:')
print(f'Tổng số: {len(procs)}\n')
for cat in sorted(categories.keys()):
    print(f'{cat}: {len(categories[cat])} thủ tục')
    for p in categories[cat][:3]:
        print(f'  - {p["Mã số"]}: {p["Tên"][:60]}')
    if len(categories[cat]) > 3:
        print(f'  ... và {len(categories[cat]) - 3} thủ tục khác')
    print()

# Gợi ý folder cần tạo
print('\n💡 Gợi ý:')
for cat in sorted(categories.keys()):
    folder_name = cat.lower().replace(', ', '_').replace(' ', '_')
    print(f'- {cat} → Folder: {folder_name}/')
