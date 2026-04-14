#!/usr/bin/env python3
"""
Deliveroo 每日销售汇总（一次登录，复用会话）
- 复用 selenium 登录后获取 Bearer Token
- 使用固定 branch_drn_id 映射一次跑多店
- 通过 requests 直接调用 summary API
"""
import os
import time
import json
from datetime import datetime, timezone
from typing import List
from zoneinfo import ZoneInfo

import psycopg2
import requests
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By

from . import login
from .selectors import HEADERS_TEMPLATE
from store_config import store_code_map, store_dict_deliveroo

SUMMARY_URL = "https://partner-hub.deliveroo.com/api-gw/sales/v2/summary"
ORG_ID = os.getenv("DELIVEROO_ORG_ID", "526324")
MARKET = os.getenv("DELIVEROO_MARKET", "GB")
LONDON_TZ = ZoneInfo("Europe/London")


def _build_utc_day_range(date_str: str) -> tuple[str, str]:
    """将英国本地自然日转换为 UTC 时间区间（ISO-8601 + Z）。"""
    day = datetime.strptime(date_str, "%Y-%m-%d")
    local_start = day.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=LONDON_TZ)
    local_end = day.replace(hour=23, minute=59, second=59, microsecond=999000, tzinfo=LONDON_TZ)

    utc_start = local_start.astimezone(timezone.utc)
    utc_end = local_end.astimezone(timezone.utc)
    from_iso = utc_start.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    to_iso = utc_end.strftime("%Y-%m-%dT%H:%M:%S.%f")[:23] + "Z"
    return from_iso, to_iso


def _setup_session_like_orders(driver) -> tuple[requests.Session, dict]:
    """从 cookies 获取 token，创建基础 session（不含店铺特定的 org_id）"""
    cookies = login.fetch_cookies(driver)
    print(f"✅ 获取到的 cookies: {cookies}")

    auth_token = cookies.get('token')
    if auth_token:
        print(f"\n🔑 找到 token: {auth_token[:50]}...")
    else:
        print(f"\n⚠️ 警告：未在 cookies 中找到 token，请求可能会失败")

    # 构建基础 headers
    headers = HEADERS_TEMPLATE.copy()
    if auth_token:
        headers['Authorization'] = f"Bearer {auth_token}"
        print("✅ 已添加 Authorization 头")
    else:
        print("⚠️ 未添加 Authorization 头")

    # 创建 session 并注入 cookies
    session = requests.Session()
    for name, value in cookies.items():
        session.cookies.set(name, value)
    session.headers.update(headers)
    return session, headers


def _extract_restaurant_drn_id(driver) -> str | None:
    """从浏览器性能日志中捕获包含 restaurant UUID 的 API 请求（参考 fetch_orders 的实现）"""
    try:
        import re
        logs = driver.get_log('performance')
        print(f"   📊 获取到 {len(logs)} 条性能日志")
        
        restaurant_ids = set()
        
        for entry in logs:
            try:
                log = json.loads(entry['message'])['message']
                if log.get('method') == 'Network.requestWillBeSent':
                    url = log.get('params', {}).get('request', {}).get('url', '')
                    # 查找包含 /restaurants/{UUID}/ 的请求
                    if 'restaurant-hub-data-api.deliveroo.net/api/restaurants/' in url:
                        # 提取 UUID 格式的 restaurant_id
                        match = re.search(r'/restaurants/([a-f0-9\-]+)/', url)
                        if match:
                            rid = match.group(1)
                            restaurant_ids.add(rid)
                            print(f"   🔍 找到 API 请求: {url[:80]}...")
                            print(f"   🔍 提取到 restaurant_id: {rid}")
            except Exception:
                pass
        
        if restaurant_ids:
            captured_id = list(restaurant_ids)[0]
            print(f"   ✅ 提取到 restaurant_drn_id: {captured_id}")
            return captured_id
        else:
            print(f"   ⚠️ 未在网络日志中找到 restaurant_id")
            return None
    except Exception as e:
        print(f"   ❌ 提取 restaurant_drn_id 失败: {e}")
        return None


def _fetch_one_day(session: requests.Session, branch_drn_id: str, date_str: str, headers: dict) -> dict | None:
    from_iso, to_iso = _build_utc_day_range(date_str)
    payload = {
        "branch_drn_ids": [branch_drn_id],
        "from": from_iso,
        "to": to_iso,
        "market": MARKET,
        "payment_type": "all",
    }
    print("   📡 请求:")
    print("   URL:", SUMMARY_URL)
    print("   Payload:", json.dumps(payload, ensure_ascii=False))
    resp = session.post(SUMMARY_URL, json=payload, headers=headers, timeout=30)
    print("   Status:", resp.status_code)
    if resp.status_code != 200:
        print("   ❌ 请求失败:", resp.text[:500])
        return None
    data = resp.json()
    print("   ✅ 响应示例:", json.dumps(data, ensure_ascii=False)[:500])

    def _as_pounds(v) -> float:
        if v is None:
            return 0.0
        if isinstance(v, (int, float)):
            return round(v / 100, 2)
        if isinstance(v, dict):
            # 可能的字段名：value/amount/minor/pence
            for key in ("value", "amount", "minor", "pence"):
                if key in v and isinstance(v[key], (int, float)):
                    return round(v[key] / 100, 2)
            # 兜底：尝试首个数值
            for val in v.values():
                if isinstance(val, (int, float)):
                    return round(val / 100, 2)
        return 0.0

    def _as_int(v) -> int:
        if v is None:
            return 0
        if isinstance(v, int):
            return v
        if isinstance(v, float):
            return int(v)
        if isinstance(v, dict):
            for key in ("value", "count", "total"):
                if key in v and isinstance(v[key], (int, float)):
                    return int(v[key])
            for val in v.values():
                if isinstance(val, (int, float)):
                    return int(val)
        return 0

    return {
        "gross_sales": _as_pounds(data.get("gross_sales")),
        "net_sales": _as_pounds(data.get("net_sales")),
        "order_count": _as_int(data.get("accepted_orders")),
        "avg_order_value": _as_pounds(data.get("average_order_value")),
    }


def _save_to_db(store_code: str, store_name: str, date_str: str, data: dict) -> bool:
    try:
        conn = psycopg2.connect(
            host=os.environ.get("DB_HOST", "db"),
            port=os.environ.get("DB_PORT", "5432"),
            dbname=os.environ.get("DB_NAME", "delivery_data"),
            user=os.environ.get("DB_USER", "delivery_user"),
            password=os.environ.get("DB_PASSWORD", "delivery_pass"),
            connect_timeout=3,
        )
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO daily_sales_summary (
                date, store_code, store_name, platform,
                gross_sales, net_sales, order_count, avg_order_value,
                created_at, updated_at
            ) VALUES (
                %s, %s, %s, 'deliveroo',
                %s, %s, %s, %s,
                NOW(), NOW()
            )
            ON CONFLICT (date, store_code, platform)
            DO UPDATE SET
                store_name = EXCLUDED.store_name,
                gross_sales = EXCLUDED.gross_sales,
                net_sales = EXCLUDED.net_sales,
                order_count = EXCLUDED.order_count,
                avg_order_value = EXCLUDED.avg_order_value,
                updated_at = NOW()
            """,
            (
                date_str,
                store_code,
                store_name,
                data["gross_sales"],
                data["net_sales"],
                data["order_count"],
                data["avg_order_value"],
            ),
        )
        conn.commit()
        cursor.close()
        conn.close()
        print("   ✅ 入库完成")
        return True
    except Exception as e:
        print("   ❌ 入库失败:", e)
        return False


def run_daily_summary_batch(store_codes: List[str], dates: List[str]) -> dict:
    """一次登录，批量跑多个店铺 + 多天"""
    print("\n🚀 启动浏览器并登录...")
    driver = login.init_browser(headless=True)
    wait = WebDriverWait(driver, 20)
    try:
        email = os.getenv("DELIVEROO_EMAIL") or "zheng499@hotmail.com"
        password = os.getenv("DELIVEROO_PASSWORD") or "990924ng6666"
        driver.get("https://partner-hub.deliveroo.com/login")
        login.do_login(driver, wait, email, password)
        
        # 创建基础 session
        session, headers = _setup_session_like_orders(driver)

        results = {"success": 0, "failed": 0, "details": []}
        print("\n📦 店铺:", store_codes)
        print("📅 日期:", dates)

        for code in store_codes:
            store_name = store_code_map.get(code)
            if not store_name:
                print(f"❌ 未知店铺代码: {code}")
                results["failed"] += 1
                continue
            
            # 获取店铺的 org_id 和 branch_id
            if store_name not in store_dict_deliveroo:
                print(f"❌ 店铺 {store_name} 不在 Deliveroo 配置中")
                results["failed"] += 1
                continue
            
            org_branch = store_dict_deliveroo[store_name]
            org_id, branch_id = org_branch.split("-")
            print(f"\n{'='*60}\n🏪 {store_name} ({code}) [org: {org_id}, branch: {branch_id}]\n{'='*60}")
            
            # 导航到该店铺的 orders 页面
            print(f"   🔄 导航到店铺专属页面...")
            login.open_orders_page(driver, org_id, branch_id, dates[0], dates[0])
            
            # 刷新页面以触发网络请求（参考 fetch_orders）
            print(f"   🔄 刷新页面以触发后台 API 请求...")
            driver.refresh()
            time.sleep(3)  # 等待后台请求完成
            
            # 从性能日志中提取该店铺的真实 restaurant_id (UUID)
            restaurant_drn_id = _extract_restaurant_drn_id(driver)
            if not restaurant_drn_id:
                print(f"   ❌ 未能提取 restaurant_drn_id，跳过该店铺")
                results["failed"] += len(dates)
                for d in dates:
                    results["details"].append({"code": code, "date": d, "status": "FAILED_NO_DRN_ID"})
                continue
            
            # 更新 headers 中的 x-roo-org-id 为该店铺的 branch_id
            headers['x-roo-org-id'] = branch_id
            
            for d in dates:
                print(f"  📅 {d}")
                data = _fetch_one_day(session, restaurant_drn_id, d, headers)
                if not data:
                    results["failed"] += 1
                    results["details"].append({"code": code, "date": d, "status": "FAILED"})
                    print("  ❌ 失败")
                else:
                    _save_to_db(code, store_name, d, data)
                    results["success"] += 1
                    results["details"].append({"code": code, "date": d, "status": "OK"})
                    print("  ✅ 成功")

        return results
    finally:
        try:
            driver.quit()
        except Exception:
            pass
