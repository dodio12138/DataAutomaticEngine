#!/usr/bin/env python3
"""
店铺评分数据飞书同步服务
将 store_ratings 表数据同步到飞书多维表格
"""
import os
import sys
from datetime import datetime, timedelta, date
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import json
from token_manager import FeishuTokenManager


class FeishuStoreRatingsSync:
    """飞书店铺评分数据同步器"""
    
    def __init__(self):
        try:
            # 飞书应用配置
            self.app_token = os.environ.get("FEISHU_RATINGS_APP_TOKEN")  # 多维表格 app_token
            self.table_id = os.environ.get("FEISHU_RATINGS_TABLE_ID")    # 数据表 table_id
            
            if not all([self.app_token, self.table_id]):
                raise ValueError("缺少飞书配置：FEISHU_RATINGS_APP_TOKEN, FEISHU_RATINGS_TABLE_ID")
            
            # 使用 TokenManager 自动管理 token（支持自动刷新）
            self.token_manager = FeishuTokenManager()
            self.access_token = self.token_manager.get_access_token()
            
            # 飞书 API 基础 URL
            self.base_url = "https://open.feishu.cn/open-apis"
        except Exception as e:
            print(f"❌ 初始化失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
        
        # 数据库配置
        self.db_config = {
            "host": os.environ.get("DB_HOST", "db"),
            "port": int(os.environ.get("DB_PORT", "5432")),
            "dbname": os.environ.get("DB_NAME", "delivery_data"),
            "user": os.environ.get("DB_USER", "delivery_user"),
            "password": os.environ.get("DB_PASSWORD", "delivery_pass"),
        }
    
    def get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)
    
    def fetch_store_ratings(self, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """
        从数据库获取店铺评分数据
        
        Args:
            start_date: 开始日期 YYYY-MM-DD，不传则默认为昨天
            end_date: 结束日期 YYYY-MM-DD，不传则默认为昨天
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # 如果都不传参数，默认获取昨天的数据（用于定时任务增量同步）
        if start_date is None and end_date is None:
            yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
            start_date = yesterday
            end_date = yesterday
        
        cursor.execute("""
            SELECT 
                date,
                store_code,
                store_name,
                platform,
                branch_drn_id,
                average_rating,
                rating_count,
                five_star_count,
                four_star_count,
                three_star_count,
                two_star_count,
                one_star_count,
                created_at,
                updated_at
            FROM store_ratings
            WHERE date >= %s AND date <= %s
            ORDER BY date, store_code, platform
        """, (start_date, end_date))
        
        records = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return [dict(row) for row in records]
    
    def get_existing_records(self) -> Dict[str, str]:
        """
        获取飞书表格中现有记录
        返回 {唯一键: record_id} 的映射
        """
        url = f"{self.base_url}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/search"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        existing_map = {}
        page_token = None
        page_count = 0
        
        try:
            while True:
                page_count += 1
                print(f"📖 获取飞书表格记录（第 {page_count} 页）...")
                
                payload = {
                    "page_size": 500,
                    "automatic_fields": False
                }
                if page_token:
                    payload["page_token"] = page_token
                
                response = requests.post(url, headers=headers, json=payload)
                
                if response.status_code != 200:
                    print(f"⚠️  获取记录失败 [{response.status_code}]: {response.text}")
                    break
                
                data = response.json()
                if data.get("code") != 0:
                    print(f"⚠️  API返回错误: {data.get('msg')}")
                    break
                
                items = data.get("data", {}).get("items", [])
                print(f"   获取到 {len(items)} 条记录")
                
                for item in items:
                    record_id = item.get("record_id")
                    fields = item.get("fields", {})
                    
                    # 提取字段
                    date_value = fields.get("日期")
                    store_code = fields.get("店铺代码")
                    platform = fields.get("平台")
                    
                    if date_value and store_code and platform:
                        # 日期字段可能是时间戳（毫秒）
                        if isinstance(date_value, int):
                            date_str = datetime.fromtimestamp(date_value / 1000).strftime('%Y-%m-%d')
                        else:
                            date_str = date_value
                        
                        # 构建唯一键：日期_店铺代码_平台
                        unique_key = f"{date_str}_{store_code}_{platform}"
                        existing_map[unique_key] = record_id
                
                # 检查是否还有下一页
                has_more = data.get("data", {}).get("has_more", False)
                if not has_more:
                    break
                page_token = data.get("data", {}).get("page_token")
            
            print(f"✅ 共获取 {len(existing_map)} 条已存在记录")
            return existing_map
        
        except Exception as e:
            print(f"❌ 获取飞书表格记录失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}
    
    def create_record(self, record: Dict[str, Any]) -> bool:
        """创建飞书表格记录"""
        url = f"{self.base_url}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # 日期转换为时间戳（毫秒）
        date_obj = record['date'] if isinstance(record['date'], date) else datetime.strptime(str(record['date']), '%Y-%m-%d').date()
        date_timestamp = int(datetime.combine(date_obj, datetime.min.time()).timestamp() * 1000)
        
        # 构建字段
        fields = {
            "日期": date_timestamp,
            "店铺代码": record.get('store_code', ''),
            "店铺名称": record.get('store_name', ''),
            "平台": record.get('platform', 'deliveroo'),
            "分店ID": record.get('branch_drn_id', ''),
            "平均评分": float(record.get('average_rating', 0)),
            "评价数": int(record.get('rating_count', 0)),
            "五星": int(record.get('five_star_count', 0)),
            "四星": int(record.get('four_star_count', 0)),
            "三星": int(record.get('three_star_count', 0)),
            "二星": int(record.get('two_star_count', 0)),
            "一星": int(record.get('one_star_count', 0))
        }
        
        payload = {"fields": fields}
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200 and response.json().get("code") == 0:
                return True
            else:
                print(f"⚠️  创建失败: {response.text}")
                return False
        except Exception as e:
            print(f"❌ 创建记录异常: {str(e)}")
            return False
    
    def update_record(self, record_id: str, record: Dict[str, Any]) -> bool:
        """更新飞书表格记录"""
        url = f"{self.base_url}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/{record_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # 日期转换为时间戳（毫秒）
        date_obj = record['date'] if isinstance(record['date'], date) else datetime.strptime(str(record['date']), '%Y-%m-%d').date()
        date_timestamp = int(datetime.combine(date_obj, datetime.min.time()).timestamp() * 1000)
        
        # 构建字段
        fields = {
            "日期": date_timestamp,
            "店铺代码": record.get('store_code', ''),
            "店铺名称": record.get('store_name', ''),
            "平台": record.get('platform', 'deliveroo'),
            "分店ID": record.get('branch_drn_id', ''),
            "平均评分": float(record.get('average_rating', 0)),
            "评价数": int(record.get('rating_count', 0)),
            "五星": int(record.get('five_star_count', 0)),
            "四星": int(record.get('four_star_count', 0)),
            "三星": int(record.get('three_star_count', 0)),
            "二星": int(record.get('two_star_count', 0)),
            "一星": int(record.get('one_star_count', 0))
        }
        
        payload = {"fields": fields}
        
        try:
            response = requests.put(url, headers=headers, json=payload)
            if response.status_code == 200 and response.json().get("code") == 0:
                return True
            else:
                print(f"⚠️  更新失败: {response.text}")
                return False
        except Exception as e:
            print(f"❌ 更新记录异常: {str(e)}")
            return False
    
    def sync(self, start_date: str = None, end_date: str = None):
        """
        同步店铺评分数据到飞书
        
        Args:
            start_date: 开始日期，默认为昨天
            end_date: 结束日期，默认为昨天
        """
        print("=" * 60)
        print("🚀 开始店铺评分数据同步")
        print("=" * 60)
        
        # 1. 从数据库获取数据
        print("\n📊 从数据库获取评分数据...")
        records = self.fetch_store_ratings(start_date, end_date)
        
        if not records:
            print("⚠️  未找到评分数据")
            return
        
        print(f"✅ 获取到 {len(records)} 条评分记录")
        
        # 显示日期范围
        dates = sorted(set(str(r['date']) for r in records))
        print(f"📅 日期范围: {dates[0]} ~ {dates[-1]}")
        
        # 2. 获取飞书表格已有记录
        print("\n📖 获取飞书表格已有记录...")
        existing_map = self.get_existing_records()
        
        # 3. 同步数据
        print("\n📤 同步数据到飞书表格...")
        created_count = 0
        updated_count = 0
        failed_count = 0
        
        for i, record in enumerate(records, 1):
            date_str = str(record['date'])
            store_code = record['store_code']
            platform = record['platform']
            
            # 构建唯一键
            unique_key = f"{date_str}_{store_code}_{platform}"
            
            print(f"[{i}/{len(records)}] {unique_key} - ", end="")
            
            if unique_key in existing_map:
                # 更新已有记录
                record_id = existing_map[unique_key]
                if self.update_record(record_id, record):
                    print("✅ 更新成功")
                    updated_count += 1
                else:
                    print("❌ 更新失败")
                    failed_count += 1
            else:
                # 创建新记录
                if self.create_record(record):
                    print("✅ 创建成功")
                    created_count += 1
                else:
                    print("❌ 创建失败")
                    failed_count += 1
        
        # 4. 输出统计
        print("\n" + "=" * 60)
        print("📊 同步完成统计")
        print("=" * 60)
        print(f"✅ 创建: {created_count} 条")
        print(f"🔄 更新: {updated_count} 条")
        print(f"❌ 失败: {failed_count} 条")
        print(f"📝 总计: {len(records)} 条")
        print("=" * 60)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="同步店铺评分数据到飞书多维表格")
    parser.add_argument("--start-date", help="开始日期 YYYY-MM-DD（默认昨天）")
    parser.add_argument("--end-date", help="结束日期 YYYY-MM-DD（默认昨天）")
    parser.add_argument("--date", help="单个日期 YYYY-MM-DD（默认昨天）")
    
    args = parser.parse_args()
    
    # 参数处理
    start_date = args.start_date
    end_date = args.end_date
    
    if args.date:
        start_date = args.date
        end_date = args.date
    
    try:
        syncer = FeishuStoreRatingsSync()
        syncer.sync(start_date=start_date, end_date=end_date)
    except Exception as e:
        print(f"\n❌ 同步失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
