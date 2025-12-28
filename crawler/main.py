"""爬虫主入口：可被 scheduler 调用或直接执行。

支持通过环境变量选择店铺、平台与时间范围：
- PLATFORM: 'panda' 或 'deliveroo' （默认 'panda'）
- STORE_CODE 或 STORE_NAME
- START_DATE, END_DATE （YYYY-MM-DD）
"""
from services.panda.fetch_orders import HungryPandaScraper
from services.deliveroo.fetch_orders import DeliverooScraper
import datetime
import os
import sys
from store_config import (
    store_code_map,
    store_name_to_code,
    store_login_user,
    store_login_password,
    store_dict_deliveroo,
)


def _resolve_stores_from_env():
    """解析 STORE_CODE/STORE_CODES/STORE_NAME 环境变量，返回英文代码列表。
    规则：
    - STORE_CODES 为逗号分隔，包含 'all' 则表示全部店铺
    - STORE_CODE='all' 表示全部店铺；否则单个代码
    - STORE_NAME 指定中文名，将被映射到英文代码
    - 若均未提供，返回空列表（视为无店铺）
    """
    codes_raw = os.environ.get("STORE_CODES")
    code = os.environ.get("STORE_CODE")
    name = os.environ.get("STORE_NAME")

    if codes_raw:
        parts = [p.strip() for p in codes_raw.split(",") if p.strip()]
        if any(p.lower() == "all" for p in parts):
            return list(store_code_map.keys())
        return parts
    if code:
        if code.strip().lower() == "all":
            return list(store_code_map.keys())
        return [code]
    if name:
        mapped = store_name_to_code.get(name)
        return [mapped] if mapped else []
    return []


def main(start_date: str = None, end_date: str = None):
    # 默认使用“昨天 - 今天”的时间范围
    # 允许通过环境变量覆盖
    start_env = os.environ.get("START_DATE")
    end_env = os.environ.get("END_DATE")
    if start_env:
        start_date = start_env
    if end_env:
        end_date = end_env

    if not start_date or not end_date:
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        start_date = yesterday.strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')

    # 获取平台参数（默认 panda）
    platform = os.environ.get("PLATFORM", "panda").lower()
    if platform not in ['panda', 'deliveroo']:
        print(f"不支持的平台：{platform}，支持的平台：panda, deliveroo")
        sys.exit(1)

    # 解析店铺列表：必须传入店铺或 'all'
    codes = _resolve_stores_from_env()
    if not codes:
        print("未指定店铺。请通过 STORE_CODE=code、STORE_CODES=code1,code2 或 STORE_CODE=all 传入。")
        sys.exit(1)

    print(f"✅ 开始爬取 [{platform.upper()}] 平台数据")
    print(f"📅 时间范围：{start_date} - {end_date}")
    print(f"🏪 店铺列表：{codes}\n")

    for code in codes:
        store_name = store_code_map.get(code)
        if not store_name:
            print(f"跳过未知店铺代码：{code}")
            continue
        
        print(f"\n{'='*60}")
        print(f"开始爬取店铺：{store_name}（{code}）")
        print(f"{'='*60}\n")
        
        if platform == 'panda':
            # HungryPanda 爬虫
            phone = store_login_user.get(store_name) or os.environ.get("PHONE") or ""
            password = store_login_password.get(store_name) or os.environ.get("PASSWORD") or ""
            scraper = HungryPandaScraper(
                store_name, 
                start_date, 
                end_date, 
                phone=phone, 
                password=password
            )
            scraper.run()
        
        elif platform == 'deliveroo':
            # Deliveroo 爬虫
            email = os.environ.get("DELIVEROO_EMAIL") or "zheng499@hotmail.com"
            password = os.environ.get("DELIVEROO_PASSWORD") or "990924ng6666"
            restaurant_id = os.environ.get("DELIVEROO_RESTAURANT_ID") or None
            
            # 检查店铺是否在 Deliveroo 配置中
            if store_name not in store_dict_deliveroo:
                print(f"⚠️ 店铺 {store_name} 不在 Deliveroo 配置中，跳过")
                continue
            
            scraper = DeliverooScraper(
                store_name,
                start_date,
                end_date,
                email=email,
                password=password,
                restaurant_id=restaurant_id
            )
            scraper.run()
        
        print(f"\n✅ 店铺 {store_name} 爬取完成\n")


if __name__ == "__main__":
    main()
