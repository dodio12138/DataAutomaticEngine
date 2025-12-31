#!/usr/bin/env python3
"""
Deliveroo 店铺评分爬虫批量运行脚本
- 支持 --stores all 或 逗号分隔的英文店铺代码
- 支持 --date 单日（YYYY-MM-DD）
- 一次登录，复用会话，逐店铺请求评分 API 并入库
"""
import argparse
import sys
from datetime import datetime
from typing import List

from services.deliveroo.fetch_ratings import run_ratings_batch
from store_config import store_code_map, store_dict_deliveroo


def parse_args():
    parser = argparse.ArgumentParser(description="Run Deliveroo store ratings crawler batch")
    parser.add_argument("--stores", type=str, default="all", help="英文店铺代码，或 'all'")
    return parser.parse_args()


def expand_stores(stores_arg: str) -> List[str]:
    """扩展店铺参数为代码列表"""
    if not stores_arg or stores_arg.strip().lower() == "all":
        # 返回所有 Deliveroo 店铺
        return [code for code, name in store_code_map.items() 
                if name in store_dict_deliveroo]
    parts = [p.strip() for p in stores_arg.split(",") if p.strip()]
    return parts


def main():
    """主函数"""
    args = parse_args()
    stores = expand_stores(args.stores)
    
    from datetime import datetime, timedelta
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    print("=== Deliveroo Store Ratings Crawler ===")
    print("Stores:", stores)
    print("记录日期（前一天）:", yesterday)
    
    if not stores:
        print("❌ 未解析到店铺代码，退出")
        sys.exit(1)
    
    try:
        result = run_ratings_batch(stores)
        print("\n=== 执行结果 ===")
        print(result)
        
        # 根据结果设置退出码
        if result.get("failed", 0) > 0:
            sys.exit(1)
        else:
            sys.exit(0)
    except Exception as e:
        import traceback
        print("❌ 执行失败:", e)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
