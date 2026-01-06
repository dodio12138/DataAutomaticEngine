#!/usr/bin/env python3
"""
每小时销售数据飞书同步服务
将 hourly_sales 表数据同步到飞书多维表格
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


class FeishuHourlySalesSync:
    """飞书每小时销售数据同步器"""
    
    def __init__(self):
        try:
            # 飞书应用配置
            self.app_token = os.environ.get("FEISHU_HOURLY_SALES_APP_TOKEN")  # 多维表格 app_token
            self.table_id = os.environ.get("FEISHU_HOURLY_SALES_TABLE_ID")    # 数据表 table_id
            
            if not all([self.app_token, self.table_id]):
                raise ValueError("缺少飞书配置：FEISHU_HOURLY_SALES_APP_TOKEN, FEISHU_HOURLY_SALES_TABLE_ID")
            
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
    
    def fetch_hourly_sales(self, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """
        从数据库获取每小时销售数据，并补全所有24小时时段（缺失的填0）
        
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
        
        # 1. 获取所有店铺和平台组合
        cursor.execute("""
            SELECT DISTINCT store_code, store_name, platform
            FROM hourly_sales
            WHERE date >= %s AND date <= %s
            ORDER BY store_code, platform
        """, (start_date, end_date))
        store_platform_combos = cursor.fetchall()
        
        # 2. 获取实际数据
        cursor.execute("""
            SELECT 
                date_time,
                date,
                hour,
                store_code,
                store_name,
                platform,
                order_count,
                total_sales
            FROM hourly_sales
            WHERE date >= %s AND date <= %s
        """, (start_date, end_date))
        actual_data = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # 3. 构建实际数据的快速查找字典
        actual_dict = {}
        for row in actual_data:
            key = f"{row['date']}_{row['hour']}_{row['store_code']}_{row['platform']}"
            actual_dict[key] = dict(row)
        
        # 4. 生成所有日期范围
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        date_range = []
        current = start_dt
        while current <= end_dt:
            date_range.append(current.date())
            current += timedelta(days=1)
        
        # 5. 补全所有时段（0-23小时）
        complete_records = []
        for combo in store_platform_combos:
            store_code = combo['store_code']
            store_name = combo['store_name']
            platform = combo['platform']
            
            for date_obj in date_range:
                for hour in range(24):
                    key = f"{date_obj}_{hour}_{store_code}_{platform}"
                    
                    if key in actual_dict:
                        # 使用实际数据
                        complete_records.append(actual_dict[key])
                    else:
                        # 补全缺失数据（订单量和销售额为0）
                        date_time = datetime.combine(date_obj, datetime.min.time()) + timedelta(hours=hour)
                        complete_records.append({
                            'date_time': date_time,
                            'date': date_obj,
                            'hour': hour,
                            'store_code': store_code,
                            'store_name': store_name,
                            'platform': platform,
                            'order_count': 0,
                            'total_sales': 0.0
                        })
        
        # 按时间、店铺、平台排序
        complete_records.sort(key=lambda x: (x['date_time'], x['store_code'], x['platform']))
        
        return complete_records
    
    def get_existing_records(self) -> Dict[str, str]:
        """
        获取飞书表格中现有记录
        返回 {唯一键: record_id} 的映射
        唯一键格式：datetime_storecode_platform
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
                date_time_val = fields.get("时间", "")
                store_code = fields.get("店铺代码", "")
                platform = fields.get("平台", "")
                
                if date_time_val and store_code and platform:
                    # 时间可能是时间戳（毫秒），需要转换
                    if isinstance(date_time_val, (int, float)):
                        dt_obj = datetime.fromtimestamp(date_time_val / 1000)
                        dt_str = dt_obj.strftime('%Y-%m-%d %H:%M')
                    else:
                        dt_str = str(date_time_val)
                    
                    unique_key = f"{dt_str}_{store_code}_{platform}"
                    records_map[unique_key] = record_id
            
            # 检查是否有下一页
            if not data.get("has_more"):
                break
            page_token = data.get("page_token")
        
        print(f"飞书表格现有记录数: {len(records_map)}")
        return records_map
    
    def create_record(self, data: Dict[str, Any]) -> bool:
        """创建新记录"""
        # 转换时间为时间戳（毫秒）
        if isinstance(data['date_time'], datetime):
            date_time_timestamp = int(data['date_time'].timestamp() * 1000)
        else:
            dt_obj = datetime.strptime(str(data['date_time']), '%Y-%m-%d %H:%M:%S')
            date_time_timestamp = int(dt_obj.timestamp() * 1000)
        
        # 转换日期为时间戳（毫秒）
        if isinstance(data['date'], date):
            date_timestamp = int(datetime.combine(data['date'], datetime.min.time()).timestamp() * 1000)
        else:
            date_obj = datetime.strptime(str(data['date']), '%Y-%m-%d')
            date_timestamp = int(date_obj.timestamp() * 1000)
        
        fields = {
            "时间": date_time_timestamp,
            "日期": date_timestamp,
            "小时": int(data['hour']),
            "店铺代码": data['store_code'],
            "店铺名称": data['store_name'] or data['store_code'],
            "平台": data['platform'],
            "订单量": int(data['order_count']) if data['order_count'] else 0,
            "销售额": float(data['total_sales']) if data['total_sales'] else 0.0,
        }
        
        url = f"{self.base_url}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {"fields": fields}
        
        response = requests.post(url, headers=headers, json=payload)
        result = response.json()
        
        if result.get("code") == 0:
            return True
        else:
            print(f"❌ 创建失败: {result.get('code')} - {result.get('msg')}")
            return False
    
    def update_record(self, record_id: str, data: Dict[str, Any]) -> bool:
        """更新现有记录"""
        # 转换时间为时间戳（毫秒）
        if isinstance(data['date_time'], datetime):
            date_time_timestamp = int(data['date_time'].timestamp() * 1000)
        else:
            dt_obj = datetime.strptime(str(data['date_time']), '%Y-%m-%d %H:%M:%S')
            date_time_timestamp = int(dt_obj.timestamp() * 1000)
        
        # 转换日期为时间戳（毫秒）
        if isinstance(data['date'], date):
            date_timestamp = int(datetime.combine(data['date'], datetime.min.time()).timestamp() * 1000)
        else:
            date_obj = datetime.strptime(str(data['date']), '%Y-%m-%d')
            date_timestamp = int(date_obj.timestamp() * 1000)
        
        fields = {
            "时间": date_time_timestamp,
            "日期": date_timestamp,
            "小时": int(data['hour']),
            "店铺代码": data['store_code'],
            "店铺名称": data['store_name'] or data['store_code'],
            "平台": data['platform'],
            "订单量": int(data['order_count']) if data['order_count'] else 0,
            "销售额": float(data['total_sales']) if data['total_sales'] else 0.0,
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
            return True
        else:
            print(f"❌ 更新失败: {result.get('code')} - {result.get('msg')}")
            return False
    
    def sync_to_feishu(self, start_date: str = None, end_date: str = None) -> Dict[str, int]:
        """
        同步数据到飞书多维表格
        
        Returns:
            统计信息：{"created": 新增数, "updated": 更新数, "failed": 失败数}
        """
        print(f"=== 开始同步每小时数据到飞书多维表格 ===")
        if start_date and end_date:
            print(f"时间范围: {start_date} ~ {end_date}")
        else:
            yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
            print(f"时间范围: {yesterday} (昨天)")
        print()
        
        # 1. 获取数据库数据
        db_records = self.fetch_hourly_sales(start_date, end_date)
        print(f"从数据库获取 {len(db_records)} 条记录\n")
        
        if not db_records:
            print("没有数据需要同步")
            return {"created": 0, "updated": 0, "failed": 0}
        
        # 2. 获取飞书现有记录
        existing_records = self.get_existing_records()
        
        # 3. 逐条同步
        stats = {"created": 0, "updated": 0, "failed": 0}
        
        for record in db_records:
            # 构建唯一键
            if isinstance(record['date_time'], datetime):
                dt_str = record['date_time'].strftime('%Y-%m-%d %H:%M')
            else:
                dt_obj = datetime.strptime(str(record['date_time']), '%Y-%m-%d %H:%M:%S')
                dt_str = dt_obj.strftime('%Y-%m-%d %H:%M')
            
            unique_key = f"{dt_str}_{record['store_code']}_{record['platform']}"
            
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
            
            # 每10条打印一次进度
            total_processed = stats["created"] + stats["updated"] + stats["failed"]
            if total_processed % 10 == 0:
                print(f"  已处理 {total_processed}/{len(db_records)} 条...")
        
        print(f"\n=== 同步完成 ===")
        print(f"✅ 新增: {stats['created']}")
        print(f"🔄 更新: {stats['updated']}")
        print(f"❌ 失败: {stats['failed']}")
        
        return stats


def main():
    """主函数：支持命令行参数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="同步每小时销售数据到飞书")
    parser.add_argument("--start-date", type=str, help="开始日期 YYYY-MM-DD（默认昨天）")
    parser.add_argument("--end-date", type=str, help="结束日期 YYYY-MM-DD（默认昨天）")
    parser.add_argument("--date", type=str, help="单个日期 YYYY-MM-DD（默认昨天）")
    
    args = parser.parse_args()
    
    start_date = args.start_date or args.date
    end_date = args.end_date or args.date
    
    try:
        syncer = FeishuHourlySalesSync()
        syncer.sync_to_feishu(start_date, end_date)
        sys.exit(0)
    except Exception as e:
        print(f"❌ 同步失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
