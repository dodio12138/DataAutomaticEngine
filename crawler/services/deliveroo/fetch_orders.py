"""负责获取订单列表和订单详情的核心模块"""
import time
import json
import random
import re
import datetime
import requests
from selenium.webdriver.support.ui import WebDriverWait

from .login import init_browser, do_login, open_orders_page, fetch_cookies
from .selectors import API_ENDPOINTS, HEADERS_TEMPLATE
from .storage import save_order_details_to_file, save_order_list_to_file, save_partial_data, save_orders_to_db
from store_config import store_dict_deliveroo, store_name_to_code


class DeliverooScraper:
    """Deliveroo订单爬虫类"""

    def __init__(self, store_name, start_date, end_date,
                 email="zheng499@hotmail.com", password="990924ng6666", restaurant_id=None):
        """
        初始化爬虫
        
        Args:
            store_name: 店铺名称
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            email: 登录邮箱
            password: 登录密码
            restaurant_id: API请求的restaurant ID，如果不提供将自动捕获
        """
        self.store_name = store_name
        self.store_id = store_dict_deliveroo[store_name]
        self.start_date = start_date
        self.end_date = end_date
        self.email = email
        self.password = password
        self.restaurant_id = restaurant_id
        
        self.driver = init_browser()
        self.wait = WebDriverWait(self.driver, 10)
        self.session = None

    def login(self):
        """执行登录流程"""
        do_login(self.driver, self.wait, self.email, self.password)

    def navigate_to_orders(self):
        """跳转到订单页面"""
        org_id, branch_id = self.store_id.split("-")
        open_orders_page(self.driver, org_id, branch_id, self.start_date, self.end_date)
        time.sleep(2)

    def capture_restaurant_id_from_network(self):
        """从浏览器网络日志中捕获 restaurant_id"""
        try:
            print("\n开始捕获网络请求...")
            self.driver.execute_cdp_cmd('Network.enable', {})
            time.sleep(3)
            
            logs = self.driver.get_log('performance')
            print(f"获取到 {len(logs)} 条性能日志")
            
            restaurant_ids = set()
            matching_urls = []
            
            for entry in logs:
                try:
                    log = json.loads(entry['message'])['message']
                    if log.get('method') == 'Network.requestWillBeSent':
                        url = log.get('params', {}).get('request', {}).get('url', '')
                        if 'restaurant-hub-data-api.deliveroo.net/api/restaurants/' in url:
                            matching_urls.append(url)
                            if '/orders' in url:
                                match = re.search(r'/restaurants/([a-f0-9\-]+)/', url)
                                if match:
                                    rid = match.group(1)
                                    restaurant_ids.add(rid)
                                    print(f"🔍 找到匹配的URL: {url[:100]}...")
                                    print(f"🔍 提取到 restaurant_id: {rid}")
                except Exception:
                    pass
            
            print(f"\n共找到 {len(matching_urls)} 个匹配的 API 请求")
            print(f"提取到 {len(restaurant_ids)} 个不同的 restaurant_id")
            
            if restaurant_ids:
                captured_id = list(restaurant_ids)[0]
                print(f"✅ 将使用 restaurant_id: {captured_id}")
                return captured_id
            else:
                print("❌ 未能从网络请求中捕获到 restaurant_id")
                return None
        except Exception as e:
            print(f"❌ 捕获 restaurant_id 失败: {e}")
            return None

    def setup_session(self):
        """设置requests session"""
        cookies = fetch_cookies(self.driver)
        print(f"✅ 获取到的 cookies: {cookies}")
        
        auth_token = cookies.get('token')
        if auth_token:
            print(f"\n🔑 找到 token: {auth_token[:50]}...")
        else:
            print(f"\n❌ 警告：未在 cookies 中找到 token，请求可能会失败")
        
        # 如果没有提供 restaurant_id，尝试从网络请求中捕获
        if not self.restaurant_id:
            print(f"\n{'='*60}")
            print(f"正在尝试从网络请求中捕获 restaurant_id...")
            print(f"{'='*60}")
            
            print("\n刷新页面以触发网络请求...")
            self.driver.refresh()
            time.sleep(5)
            
            captured_id = self.capture_restaurant_id_from_network()
            
            if captured_id:
                self.restaurant_id = captured_id
                print(f"\n✅ 成功自动捕获 restaurant_id: {self.restaurant_id}\n")
            else:
                print(f"\n❌ 自动捕获失败")
                print(f"\n请手动提供 restaurant_id:")
                print(f"1. 在浏览器中打开开发者工具 (F12 或 Cmd+Option+I)")
                print(f"2. 切换到 Network 标签页")
                print(f"3. 筛选 XHR 或 Fetch 请求")
                print(f"4. 刷新页面，查找包含 'restaurants' 和 'orders' 的请求")
                print(f"5. 从URL中复制 restaurant_id (UUID格式)")
                print(f"\n当前URL: {self.driver.current_url}")
                
                manual_id = input("\n请输入 restaurant_id (或按 Enter 跳过): ").strip()
                if manual_id:
                    self.restaurant_id = manual_id
                    print(f"✅ 使用手动输入的 restaurant_id: {self.restaurant_id}")
                else:
                    print(f"\n❌ 未提供 restaurant_id，无法继续")
                    return False
        
        # 设置请求头
        org_id, branch_id = self.store_id.split("-")
        headers = HEADERS_TEMPLATE.copy()
        headers['x-roo-org-id'] = org_id
        
        if auth_token:
            headers['Authorization'] = f"Bearer {auth_token}"
            print(f"✅ 已添加 Authorization 头")
        else:
            print(f"⚠️ 警告：未找到 token，请求可能会失败")
        
        # 创建session并设置cookies
        self.session = requests.Session()
        for name, value in cookies.items():
            self.session.cookies.set(name, value)
        
        self.session.headers.update(headers)
        return True

    def fetch_orders_list(self):
        """获取所有订单列表（分页）"""
        api_url = API_ENDPOINTS["orders_list"].format(restaurant_id=self.restaurant_id)
        
        params = {
            'payment_type': 'all',
            'limit': '20',
            'date': self.start_date,
            'end_date': self.end_date,
            'starting_after': '',
            'sort_date': '',
            'with_summary': 'no'
        }
        
        all_orders = []
        page_num = 1
        starting_after = ''
        sort_date = ''
        
        print(f"\n{'='*60}")
        print(f"正在请求订单列表...")
        print(f"Restaurant ID: {self.restaurant_id}")
        print(f"URL: {api_url}")
        print(f"参数: {params}")
        print(f"{'='*60}\n")
        
        try:
            while True:
                params['starting_after'] = starting_after
                params['sort_date'] = sort_date
                
                print(f"\n📄 正在获取第 {page_num} 页数据...")
                print(f"   starting_after: {starting_after if starting_after else '(首页)'}")
                print(f"   sort_date: {sort_date if sort_date else '(不需要)'}")
                
                response = self.session.get(api_url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                if isinstance(data, dict):
                    orders = data.get('orders', data.get('data', []))
                    has_more = data.get('has_more', False)
                    
                    if orders:
                        all_orders.extend(orders)
                        print(f"   ✅ 获取到 {len(orders)} 条订单，累计 {len(all_orders)} 条")
                        
                        page_limit = int(params.get('limit', 20))
                        has_more_data = (len(orders) == page_limit) or has_more
                        
                        print(f"   📑 本页订单数: {len(orders)}, 分页大小: {page_limit}, 继续请求: {has_more_data}")
                        
                        if has_more_data:
                            if isinstance(orders[-1], dict):
                                starting_after = orders[-1].get('order_id', orders[-1].get('id', ''))
                                timeline = orders[-1].get('timeline', {})
                                if timeline:
                                    sort_date = timeline.get('placed_at', timeline.get('created_at', ''))
                            
                            if not starting_after:
                                starting_after = data.get('next_cursor', data.get('next', ''))
                            
                            if starting_after:
                                print(f"   🔄 继续获取下一页，使用游标: {starting_after[:30]}...")
                                if sort_date:
                                    print(f"      排序日期: {sort_date}")
                                page_num += 1
                                time.sleep(1)
                            else:
                                print(f"   ⚠️ 无法获取下一页游标，停止分页")
                                break
                        else:
                            print(f"   ✅ 已获取所有数据")
                            break
                    else:
                        print(f"   ℹ️ 本页没有订单数据")
                        break
                else:
                    if isinstance(data, list):
                        all_orders.extend(data)
                        print(f"   ✅ 获取到 {len(data)} 条订单")
                    break
            
            print(f"\n{'='*60}")
            print(f"✅ 成功获取所有订单列表")
            print(f"📊 总共获取: {len(all_orders)} 条订单")
            print(f"📄 总共请求: {page_num} 页")
            print(f"{'='*60}\n")
            
            return all_orders, page_num
            
        except requests.exceptions.RequestException as e:
            print(f"\n❌ 请求失败: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"响应状态码: {e.response.status_code}")
                print(f"响应内容: {e.response.text}")
            
            if all_orders:
                save_partial_data(all_orders, self.store_name, self.api_start_date, self.api_end_date)
            
            return all_orders, page_num

    def fetch_order_details(self, orders):
        """获取每个订单的详细信息"""
        if not orders:
            return [], []
        
        print(f"\n{'='*60}")
        print(f"开始获取每个订单的详细信息...")
        print(f"{'='*60}\n")
        
        order_details = []
        failed_orders = []
        
        for idx, order in enumerate(orders, 1):
            order_id = order.get('order_id', order.get('id', ''))
            if not order_id:
                print(f"⚠️ 订单 {idx}/{len(orders)} 没有order_id，跳过")
                continue
            
            # 随机延迟 1-3 秒
            delay = random.uniform(1, 3)
            print(f"\n📝 [{idx}/{len(orders)}] 获取订单详情: {order_id}")
            print(f"   ⏰ 随机延迟 {delay:.2f} 秒...")
            time.sleep(delay)
            
            try:
                detail_url = API_ENDPOINTS["order_detail"].format(order_id=order_id)
                detail_response = self.session.get(detail_url, timeout=30)
                detail_response.raise_for_status()
                
                detail_data = detail_response.json()
                order_details.append(detail_data)
                print(f"   ✅ 成功获取订单详情")
                
            except requests.exceptions.RequestException as e:
                print(f"   ❌ 获取失败: {e}")
                failed_orders.append({'order_id': order_id, 'error': str(e)})
        
        print(f"\n{'='*60}")
        print(f"✅ 订单详情获取完成")
        print(f"📊 成功: {len(order_details)} 条")
        print(f"❌ 失败: {len(failed_orders)} 条")
        print(f"{'='*60}\n")
        
        return order_details, failed_orders

    def run(self):
        """运行完整的爬取流程"""
        try:
            # 登录
            self.login()
            
            # 跳转到订单页面
            self.navigate_to_orders()
            
            # 设置session和获取token
            if not self.setup_session():
                return
            
            # 获取订单列表
            all_orders, page_num = self.fetch_orders_list()
            
            if not all_orders:
                print("❌ 未获取到任何订单")
                return
            
            # 获取订单详情
            order_details, failed_orders = self.fetch_order_details(all_orders)
            
            # 保存数据
            final_data = {
                'summary': {
                    'total_orders': len(all_orders),
                    'total_pages': page_num,
                    'detail_success': len(order_details),
                    'detail_failed': len(failed_orders),
                    'date_range': {
                        'start': self.start_date,
                        'end': self.end_date
                    }
                },
                'orders': order_details,
                'failed_orders': failed_orders
            }
            
            save_order_details_to_file(final_data, self.store_name, 
                                      self.start_date, self.end_date)
            
            # 保存原始订单数据到数据库
            try:
                if order_details:
                    store_code = store_name_to_code.get(self.store_name)
                    # 将日期字符串转换为 datetime 对象
                    start_dt = datetime.datetime.strptime(self.start_date, '%Y-%m-%d')
                    end_dt = datetime.datetime.strptime(self.end_date, '%Y-%m-%d')
                    # 设置为当天的开始和结束时间
                    start_dt = datetime.datetime.combine(start_dt.date(), datetime.time.min)
                    end_dt = datetime.datetime.combine(end_dt.date(), datetime.time.max)
                    
                    inserted = save_orders_to_db(
                        order_details,
                        platform='deliveroo',
                        start_time=start_dt,
                        end_time=end_dt,
                        store_code=store_code,
                        store_name=self.store_name,
                    )
                    print(f"✅ 已写入数据库 {inserted} 条 Deliveroo 订单")
                else:
                    print("⚠️ 无订单数据写入数据库")
            except Exception as e:
                print(f"❌ 写入数据库时发生错误: {e}")
                import traceback
                traceback.print_exc()
            
            # 显示订单详情示例
            if order_details:
                print(f"\n订单详情示例 (第一条):")
                print(json.dumps(order_details[0], ensure_ascii=False, indent=2)[:800] + "...")
            
            print("\n✅ 所有任务完成！")
            
        except Exception as e:
            print(f"\n❌ 执行过程中出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.driver.quit()
