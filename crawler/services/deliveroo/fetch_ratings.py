#!/usr/bin/env python3
"""
Deliveroo 店铺评分爬取（一次登录，复用会话）
- 复用 daily_summary 的函数获取 token
- 导航到评分页面并从 current_rating API 响应中提取评分数据
"""
import os
import time
import json
from typing import List

import psycopg2
import requests
from selenium.webdriver.support.ui import WebDriverWait

from . import login
from .daily_summary import _setup_session_like_orders, _extract_restaurant_drn_id
from store_config import store_code_map, store_dict_deliveroo


def _save_to_db(store_code: str, store_name: str, date_str: str, rating_data: dict) -> bool:
    """
    保存评分数据到数据库
    
    Args:
        store_code: 店铺英文代码
        store_name: 店铺中文名称
        date_str: 日期字符串 (YYYY-MM-DD)
        rating_data: 评分数据字典
    
    Returns:
        bool: 是否成功
    """
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
        
        breakdown = rating_data.get('rating_breakdown', {})
        
        cursor.execute(
            """
            INSERT INTO store_ratings (
                date, store_code, store_name, platform, branch_drn_id,
                average_rating, rating_count,
                five_star_count, four_star_count, three_star_count,
                two_star_count, one_star_count,
                created_at, updated_at
            ) VALUES (
                %s, %s, %s, 'deliveroo', %s,
                %s, %s,
                %s, %s, %s, %s, %s,
                NOW(), NOW()
            )
            ON CONFLICT (date, store_code, platform)
            DO UPDATE SET
                store_name = EXCLUDED.store_name,
                branch_drn_id = EXCLUDED.branch_drn_id,
                average_rating = EXCLUDED.average_rating,
                rating_count = EXCLUDED.rating_count,
                five_star_count = EXCLUDED.five_star_count,
                four_star_count = EXCLUDED.four_star_count,
                three_star_count = EXCLUDED.three_star_count,
                two_star_count = EXCLUDED.two_star_count,
                one_star_count = EXCLUDED.one_star_count,
                updated_at = NOW()
            """,
            (
                date_str,
                store_code,
                store_name,
                rating_data.get('branch_drn_id'),
                rating_data.get('average_rating'),
                rating_data.get('rating_count'),
                breakdown.get('five_star_count', 0),
                breakdown.get('four_star_count', 0),
                breakdown.get('three_star_count', 0),
                breakdown.get('two_star_count', 0),
                breakdown.get('one_star_count', 0),
            ),
        )
        conn.commit()
        cursor.close()
        conn.close()
        print("   ✅ 入库完成")
        return True
    except Exception as e:
        print("   ❌ 入库失败:", e)
        import traceback
        traceback.print_exc()
        return False


def run_ratings_batch(store_codes: List[str]) -> dict:
    """
    一次登录，批量爬取多个店铺的评分数据
    评分数据为实时数据，但记录为前一天的日期
    
    Args:
        store_codes: 店铺代码列表
    
    Returns:
        dict: 执行结果统计
    """
    print("\n🚀 启动浏览器并登录...")
    driver = login.init_browser(headless=True)
    wait = WebDriverWait(driver, 20)
    
    try:
        email = os.getenv("DELIVEROO_EMAIL") or "zheng499@hotmail.com"
        password = os.getenv("DELIVEROO_PASSWORD") or "990924ng6666"
        driver.get("https://partner-hub.deliveroo.com/login")
        login.do_login(driver, wait, email, password)
        
        # 创建基础 session（从 daily_summary 复用）
        session, headers = _setup_session_like_orders(driver)

        # 计算前一天日期（评分数据为实时，但记录为昨天）
        from datetime import datetime, timedelta
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        results = {"success": 0, "failed": 0, "details": []}
        print("\n📦 店铺:", store_codes)
        print("📅 记录日期（前一天）:", yesterday)

        for code in store_codes:
            store_name = store_code_map.get(code)
            if not store_name:
                print(f"❌ 未知店铺代码: {code}")
                results["failed"] += 1
                results["details"].append({"code": code, "status": "UNKNOWN_CODE"})
                continue
            
            # 获取店铺的 org_id 和 branch_id
            if store_name not in store_dict_deliveroo:
                print(f"❌ 店铺 {store_name} 不在 Deliveroo 配置中")
                results["failed"] += 1
                results["details"].append({"code": code, "status": "NOT_IN_CONFIG"})
                continue
            
            org_branch = store_dict_deliveroo[store_name]
            org_id, branch_id = org_branch.split("-")
            print(f"\n{'='*60}\n🏪 {store_name} ({code}) [org: {org_id}, branch: {branch_id}]\n{'='*60}")
            
            # 先导航到 orders 页面以获取 restaurant_drn_id (UUID)
            print(f"   🔄 导航到 orders 页面获取 UUID...")
            from .login import open_orders_page
            open_orders_page(driver, org_id, branch_id, yesterday, yesterday)
            
            # 刷新页面以触发后台 API 请求
            print(f"   🔄 刷新页面以触发后台 API 请求...")
            driver.refresh()
            time.sleep(3)
            
            # 从性能日志中提取该店铺的真实 restaurant_drn_id (UUID)
            restaurant_drn_id = _extract_restaurant_drn_id(driver)
            if not restaurant_drn_id:
                print(f"   ❌ 未能提取 restaurant_drn_id")
                results["failed"] += 1
                results["details"].append({"code": code, "status": "NO_DRN_ID"})
                continue
            
            # 现在导航到该店铺的 reviews 页面
            print(f"   🔄 导航到店铺评分页面...")
            reviews_url = f"https://partner-hub.deliveroo.com/reviews?orgId={org_id}&branchId={branch_id}&dateRangePreset=last_7_days"
            driver.get(reviews_url)
            time.sleep(2)  # 等待页面加载
            
            # 使用获取到的 restaurant_drn_id 调用评分 API
            print(f"   📡 调用评分 API...")
            headers['x-roo-org-id'] = org_id
            
            try:
                payload = {"branchDrnIds": [restaurant_drn_id]}
                rating_url = "https://partner-hub.deliveroo.com/api-gw/reviews/v2/current_rating"
                
                resp = session.post(rating_url, json=payload, headers=headers, timeout=30)
                print(f"   Status: {resp.status_code}")
                
                if resp.status_code != 200:
                    print(f"   ❌ API 请求失败: {resp.text[:300]}")
                    results["failed"] += 1
                    results["details"].append({"code": code, "status": "API_ERROR"})
                    continue
                
                rating_response = resp.json()
                print(f"   ✅ 获取到评分响应")
                
            except Exception as e:
                print(f"   ❌ API 调用异常: {e}")
                results["failed"] += 1
                results["details"].append({"code": code, "status": "API_EXCEPTION"})
                continue
            
            # 解析评分数据
            if 'CurrentRating' in rating_response and len(rating_response['CurrentRating']) > 0:
                rating_item = rating_response['CurrentRating'][0]
                
                rating_data = {
                    'branch_drn_id': rating_item.get('branch_drn_id', ''),
                    'average_rating': rating_item.get('average_rating', 0),
                    'rating_count': rating_item.get('rating_count', 0),
                    'rating_breakdown': rating_item.get('rating_breakdown', {})
                }
                
                breakdown = rating_data['rating_breakdown']
                print(f"   ✅ 评分数据:")
                print(f"      平均评分: {rating_data['average_rating']}")
                print(f"      评价总数: {rating_data['rating_count']}")
                print(f"      五星: {breakdown.get('five_star_count', 0)}")
                print(f"      四星: {breakdown.get('four_star_count', 0)}")
                print(f"      三星: {breakdown.get('three_star_count', 0)}")
                print(f"      二星: {breakdown.get('two_star_count', 0)}")
                print(f"      一星: {breakdown.get('one_star_count', 0)}")
                
                # 保存到数据库（使用前一天日期）
                success = _save_to_db(code, store_name, yesterday, rating_data)
                if success:
                    results["success"] += 1
                    results["details"].append({"code": code, "status": "OK"})
                    print("  ✅ 成功")
                else:
                    results["failed"] += 1
                    results["details"].append({"code": code, "status": "FAILED_DB"})
                    print("  ❌ 数据库保存失败")
            else:
                print(f"   ❌ 响应格式异常或无数据")
                results["failed"] += 1
                results["details"].append({"code": code, "status": "INVALID_RESPONSE"})

        return results
    finally:
        try:
            driver.quit()
        except Exception:
            pass
