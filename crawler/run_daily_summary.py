#!/usr/bin/env python3
"""
Deliveroo 每日销售汇总批量运行脚本
- 支持 --stores all 或 逗号分隔的英文店铺代码
- 支持 --dates 单日，或以逗号分隔的起止日期（YYYY-MM-DD,YYYY-MM-DD）
- 一次登录，复用会话，逐店铺逐日期请求 summary API 并入库
"""
import argparse
import sys
from datetime import datetime, timedelta
from typing import List

from services.deliveroo.daily_summary import run_daily_summary_batch
from store_config import store_code_map


def parse_args():
    parser = argparse.ArgumentParser(description="Run Deliveroo daily sales summary batch")
    parser.add_argument("--stores", type=str, default="all", help="英文店铺代码，或 'all'")
    parser.add_argument("--dates", type=str, help="单日 YYYY-MM-DD，或范围 'YYYY-MM-DD,YYYY-MM-DD'", required=False)
    return parser.parse_args()


def expand_stores(stores_arg: str) -> List[str]:
    if not stores_arg or stores_arg.strip().lower() == "all":
        return list(store_code_map.keys())
    parts = [p.strip() for p in stores_arg.split(",") if p.strip()]
    return parts


def expand_dates(dates_arg: str | None) -> List[str]:
    if not dates_arg:
        # 默认当天
        return [datetime.today().strftime("%Y-%m-%d")]
    dates_arg = dates_arg.strip()
    if "," in dates_arg:
        start_str, end_str = [p.strip() for p in dates_arg.split(",", 1)]
        start = datetime.strptime(start_str, "%Y-%m-%d")
        end = datetime.strptime(end_str, "%Y-%m-%d")
        days = []
        cur = start
        while cur <= end:
            days.append(cur.strftime("%Y-%m-%d"))
            cur += timedelta(days=1)
        return days
    else:
        # 单日
        datetime.strptime(dates_arg, "%Y-%m-%d")  # 校验格式
        return [dates_arg]


def main():
    args = parse_args()
    stores = expand_stores(args.stores)
    dates = expand_dates(args.dates)

    print("=== Deliveroo Daily Summary Batch ===")
    print("Stores:", stores)
    print("Dates:", dates)

    if not stores:
        print("未解析到店铺代码，退出")
        sys.exit(1)

    try:
        result = run_daily_summary_batch(stores, dates)
        print("\n=== 执行结果 ===")
        print(result)
    except Exception as e:
        print("执行失败:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
