#!/usr/bin/env python3
"""
飞书多维表格同步服务
从 daily_sales_summary 表同步数据到飞书多维表格
支持增量更新和全量同步
"""
import os
import sys
from datetime import datetime, timedelta, date
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import json


class FeishuBitableSync:
    """飞书多维表格同步器"""
    
    def __init__(self):
        # 飞书应用配置
        self.app_id = os.environ.get("FEISHU_APP_ID")
        self.app_secret = os.environ.get("FEISHU_APP_SECRET")
        self.app_token = os.environ.get("FEISHU_BITABLE_APP_TOKEN")  # 多维表格 app_token
        self.table_id = os.environ.get("FEISHU_BITABLE_TABLE_ID")    # 数据表 table_id
        
        # 用户 Access Token（优先使用，如果配置了的话）
        self.user_access_token = os.environ.get("FEISHU_USER_ACCESS_TOKEN")
        
        # DEBUG: 打印环境变量状态
        print(f"DEBUG - USER_ACCESS_TOKEN 配置: {'已设置' if self.user_access_token else '未设置'}")
        if self.user_access_token:
            print(f"DEBUG - TOKEN前缀: {self.user_access_token[:10]}...")
        
        if not all([self.app_token, self.table_id]):
            raise ValueError("缺少飞书配置：FEISHU_BITABLE_APP_TOKEN, FEISHU_BITABLE_TABLE_ID")
        
        # 获取 access_token
        # 优先使用 user_access_token，否则使用 tenant_access_token
        if self.user_access_token:
            print("✅ 使用 user_access_token（用户身份）")
            self.access_token = self.user_access_token
        else:
            if not all([self.app_id, self.app_secret]):
                raise ValueError("缺少飞书配置：FEISHU_APP_ID, FEISHU_APP_SECRET")
            print("✅ 使用 tenant_access_token（应用身份）")
            self.access_token = self._get_tenant_access_token()
        
        # 飞书 API 基础 URL
        self.base_url = "https://open.feishu.cn/open-apis"
        
        # 数据库配置
        self.db_config = {
            "host": os.environ.get("DB_HOST", "db"),
            "port": int(os.environ.get("DB_PORT", "5432")),
            "dbname": os.environ.get("DB_NAME", "delivery_data"),
            "user": os.environ.get("DB_USER", "delivery_user"),
            "password": os.environ.get("DB_PASSWORD", "delivery_pass"),
        }
    
    def _get_tenant_access_token(self) -> str:
        """获取tenant_access_token"""
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json"}
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        if result.get("code") != 0:
            raise Exception(f"获取access_token失败: {result}")
        
        return result["tenant_access_token"]
    
    def get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)
    
    def ensure_table_fields(self):
        """确保飞书表格中存在所有需要的字段，如果不存在则创建"""
        required_fields = {
            "日期": {"type": 5, "property": {}},  # 日期类型
            "店铺代码": {"type": 1, "property": {}},  # 文本类型
            "店铺名称": {  # 单选类型
                "type": 3,
                "property": {
                    "options": [
                        {"name": "海底捞冒菜（巴特西）"},
                        {"name": "海底捞冒菜（Brent）"},
                        {"name": "海底捞冒菜（东伦敦）"},
                        {"name": "海底捞火锅（Piccadilly）"},
                        {"name": "海底捞冒菜（Piccadilly）"},
                        {"name": "海底捞冒菜（塔桥）"}
                    ]
                }
            },
            "平台": {  # 单选类型
                "type": 3, 
                "property": {
                    "options": [
                        {"name": "deliveroo"},
                        {"name": "hungrypanda"}
                    ]
                }
            },
            "总销售额": {"type": 2, "property": {"formatter": "0.00"}},  # 数字类型
            "净销售额": {"type": 2, "property": {"formatter": "0.00"}},  # 数字类型
            "订单数": {"type": 2, "property": {"formatter": "0"}},  # 数字类型（整数）
            "平均订单价值": {"type": 2, "property": {"formatter": "0.00"}},  # 数字类型
        }
        
        # 获取现有字段
        url = f"{self.base_url}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/fields"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        result = response.json()
        
        if result.get("code") != 0:
            print(f"⚠️  获取字段列表失败: {result.get('code')} - {result.get('msg')}")
            return
        
        existing_fields = {item["field_name"]: item for item in result.get("data", {}).get("items", [])}
        print(f"📋 表格现有字段: {list(existing_fields.keys())}")
        
        # 创建缺失的字段
        for field_name, field_config in required_fields.items():
            if field_name not in existing_fields:
                print(f"➕ 创建字段: {field_name}")
                create_url = f"{self.base_url}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/fields"
                data = {
                    "field_name": field_name,
                    "type": field_config["type"],
                    "property": field_config["property"]
                }
                
                create_response = requests.post(create_url, headers=headers, json=data)
                create_result = create_response.json()
                
                if create_result.get("code") == 0:
                    print(f"   ✅ 字段 '{field_name}' 创建成功")
                else:
                    print(f"   ❌ 字段 '{field_name}' 创建失败: {create_result.get('msg')}")
        
        print("✅ 字段检查完成\n")
    
    def fetch_daily_summary(self, start_date: str = None, end_date: str = None, 
                           store_code: str = None, platform: str = None) -> List[Dict[str, Any]]:
        """
        从数据库获取每日销售汇总数据
        
        Args:
            start_date: 开始日期 YYYY-MM-DD，不传则默认为昨天（用于定时任务）
            end_date: 结束日期 YYYY-MM-DD，不传则默认为昨天（用于定时任务）
            store_code: 店铺代码，可选
            platform: 平台，可选
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # 如果都不传参数，默认获取昨天的数据（用于定时任务增量同步）
        if start_date is None and end_date is None:
            yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
            start_date = yesterday
            end_date = yesterday
        
        query = """
            SELECT 
                date,
                store_code,
                store_name,
                platform,
                gross_sales,
                net_sales,
                order_count,
                avg_order_value,
                created_at,
                updated_at
            FROM daily_sales_summary
        """
        
        where_clauses = []
        params = []
        
        # 如果指定了日期范围，添加日期过滤
        if start_date and end_date:
            where_clauses.append("date >= %s AND date <= %s")
            params.extend([start_date, end_date])
        elif start_date:
            where_clauses.append("date >= %s")
            params.append(start_date)
        elif end_date:
            where_clauses.append("date <= %s")
            params.append(end_date)
        # 如果都不传，则查询所有数据（不添加日期过滤）
        
        if store_code:
            where_clauses.append("store_code = %s")
            params.append(store_code)
        
        if platform:
            where_clauses.append("platform = %s")
            params.append(platform)
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY date ASC, store_code, platform"  # 按日期从旧到新排序
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return results
    
    def get_existing_records(self) -> Dict[str, str]:
        """
        获取飞书表格中现有记录
        返回 {唯一键: record_id} 的映射
        唯一键格式：date_storecode_platform
        """
        records_map = {}
        page_token = None
        
        url = f"{self.base_url}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        while True:
            params = {"page_size": 500}
            if page_token:
                params["page_token"] = page_token
            
            response = requests.get(url, headers=headers, params=params)
            result = response.json()
            
            if result.get("code") != 0:
                print(f"获取记录失败: {result.get('code')} - {result.get('msg')}")
                break
            
            data = result.get("data", {})
            items = data.get("items")
            
            # 如果 items 为 None 或空列表，跳出循环
            if not items:
                break
            
            for record in items:
                fields = record.get("fields", {})
                record_id = record.get("record_id", "")
                
                # 构建唯一键
                date_val = fields.get("日期", "")
                store_code = fields.get("店铺代码", "")
                platform = fields.get("平台", "")
                
                if date_val and store_code and platform:
                    # 日期可能是时间戳（毫秒），需要转换
                    if isinstance(date_val, (int, float)):
                        date_obj = datetime.fromtimestamp(date_val / 1000)
                        date_str = date_obj.strftime('%Y-%m-%d')
                    else:
                        date_str = str(date_val)
                    
                    unique_key = f"{date_str}_{store_code}_{platform}"
                    records_map[unique_key] = record_id
            
            # 检查是否有下一页
            if not data.get("has_more"):
                break
            page_token = data.get("page_token")
        
        print(f"飞书表格现有记录数: {len(records_map)}")
        return records_map
    
    def create_record(self, data: Dict[str, Any]) -> bool:
        """创建新记录"""
        # 转换日期为时间戳（毫秒）
        date_obj = datetime.strptime(str(data['date']), '%Y-%m-%d')
        date_timestamp = int(date_obj.timestamp() * 1000)
        
        fields = {
            "日期": date_timestamp,
            "店铺代码": data['store_code'],
            "店铺名称": data['store_name'] or "",
            "平台": data['platform'],
            "总销售额": float(data['gross_sales']) if data['gross_sales'] else 0.0,
            "净销售额": float(data['net_sales']) if data['net_sales'] else 0.0,
            "订单数": int(data['order_count']) if data['order_count'] else 0,
            "平均订单价值": float(data['avg_order_value']) if data['avg_order_value'] else 0.0,
        }
        
        url = f"{self.base_url}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records"
        print(f"DEBUG - 创建记录 URL: {url}")
        print(f"DEBUG - APP_TOKEN末尾: ...{self.app_token[-10:]}")
        print(f"DEBUG - TABLE_ID: {self.table_id}")
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {"fields": fields}
        
        response = requests.post(url, headers=headers, json=payload)
        print(f"DEBUG - Status Code: {response.status_code}")
        print(f"DEBUG - Response Text: {response.text[:500]}")  # 只打印前500字符
        
        try:
            result = response.json()
        except Exception as e:
            print(f"JSON解析失败: {e}")
            print(f"完整响应: {response.text}")
            return False
        
        if result.get("code") == 0:
            print(f"✅ 创建记录: {data['date']} {data['store_code']} {data['platform']}")
            return True
        else:
            print(f"❌ 创建失败: {result.get('code')} - {result.get('msg')}")
            return False
    
    def update_record(self, record_id: str, data: Dict[str, Any]) -> bool:
        """更新现有记录"""
        # 转换日期为时间戳（毫秒）
        date_obj = datetime.strptime(str(data['date']), '%Y-%m-%d')
        date_timestamp = int(date_obj.timestamp() * 1000)
        
        fields = {
            "日期": date_timestamp,
            "店铺代码": data['store_code'],
            "店铺名称": data['store_name'] or "",
            "平台": data['platform'],
            "总销售额": float(data['gross_sales']) if data['gross_sales'] else 0.0,
            "净销售额": float(data['net_sales']) if data['net_sales'] else 0.0,
            "订单数": int(data['order_count']) if data['order_count'] else 0,
            "平均订单价值": float(data['avg_order_value']) if data['avg_order_value'] else 0.0,
        }
        
        url = f"{self.base_url}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/{record_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {"fields": fields}
        
        response = requests.put(url, headers=headers, json=payload)
        result = response.json()
        
        if result.get("code") == 0:
            print(f"🔄 更新记录: {data['date']} {data['store_code']} {data['platform']}")
            return True
        else:
            print(f"❌ 更新失败: {result.get('code')} - {result.get('msg')}")
            return False
    
    def sync_to_feishu(self, start_date: str = None, end_date: str = None,
                      store_code: str = None, platform: str = None) -> Dict[str, int]:
        """
        同步数据到飞书多维表格
        
        Returns:
            统计信息：{"created": 新增数, "updated": 更新数, "failed": 失败数}
        """
        print(f"=== 开始同步数据到飞书多维表格 ===")
        if start_date and end_date:
            print(f"时间范围: {start_date} ~ {end_date}")
        elif start_date:
            print(f"时间范围: {start_date} ~ 至今")
        elif end_date:
            print(f"时间范围: 最早 ~ {end_date}")
        else:
            print(f"时间范围: 全部数据")
        if store_code:
            print(f"店铺: {store_code}")
        if platform:
            print(f"平台: {platform}")
        print()
        
        # 0. 确保表格字段存在
        print("🔍 检查表格字段...")
        self.ensure_table_fields()
        
        # 1. 获取数据库数据
        db_records = self.fetch_daily_summary(start_date, end_date, store_code, platform)
        print(f"从数据库获取 {len(db_records)} 条记录\n")
        
        if not db_records:
            print("没有数据需要同步")
            return {"created": 0, "updated": 0, "failed": 0}
        
        # 2. 获取飞书现有记录
        existing_records = self.get_existing_records()
        
        # 3. 逐条同步
        stats = {"created": 0, "updated": 0, "failed": 0}
        
        for record in db_records:
            date_str = str(record['date'])
            unique_key = f"{date_str}_{record['store_code']}_{record['platform']}"
            
            if unique_key in existing_records:
                # 更新现有记录
                record_id = existing_records[unique_key]
                if self.update_record(record_id, record):
                    stats["updated"] += 1
                else:
                    stats["failed"] += 1
            else:
                # 创建新记录
                if self.create_record(record):
                    stats["created"] += 1
                else:
                    stats["failed"] += 1
        
        print(f"\n=== 同步完成 ===")
        print(f"✅ 新增: {stats['created']}")
        print(f"🔄 更新: {stats['updated']}")
        print(f"❌ 失败: {stats['failed']}")
        
        return stats


def main():
    """主函数：支持命令行参数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="飞书多维表格同步服务")
    parser.add_argument("--start-date", type=str, help="开始日期 YYYY-MM-DD（默认7天前）")
    parser.add_argument("--end-date", type=str, help="结束日期 YYYY-MM-DD（默认今天）")
    parser.add_argument("--store-code", type=str, help="店铺代码（可选）")
    parser.add_argument("--platform", type=str, help="平台：panda/deliveroo（可选）")
    
    args = parser.parse_args()
    
    try:
        syncer = FeishuBitableSync()
        syncer.sync_to_feishu(
            start_date=args.start_date,
            end_date=args.end_date,
            store_code=args.store_code,
            platform=args.platform
        )
        sys.exit(0)
    except Exception as e:
        print(f"❌ 同步失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
