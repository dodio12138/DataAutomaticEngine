#!/usr/bin/env python3
"""测试报告格式输出"""

import sys
sys.path.insert(0, '/Users/levy/WorkSpace/Program/HaidilaoService/DataAutomaticEngine/api')

from services.report_service import generate_daily_summary_text, generate_store_summary_text

print("=" * 50)
print("测试 1: 单日汇总格式")
print("=" * 50)
result = generate_daily_summary_text('2025-12-24', '2025-12-24')
print(result)

print("\n\n" + "=" * 50)
print("测试 2: 日期范围汇总格式")
print("=" * 50)
result = generate_daily_summary_text('2025-12-20', '2025-12-24')
print(result)

print("\n\n" + "=" * 50)
print("测试 3: 单店铺查询格式（精确匹配）")
print("=" * 50)
result = generate_store_summary_text('battersea', '2025-12-24', '2025-12-24')
print(result)

print("\n\n" + "=" * 50)
print("测试完成")
print("=" * 50)
