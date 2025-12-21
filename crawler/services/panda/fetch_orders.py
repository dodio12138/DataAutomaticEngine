import time
import datetime
import gzip
import re
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from .selectors import SELECTORS
from .login import init_browser, do_login
from store_config import store_dict_panda
from .storage import save_raw_json
from store_config import store_name_to_code


class HungryPandaScraper:
    """按职责拆分后的爬虫类：负责分页、打开 modal、提取信息并保存原始详情。"""

    def __init__(self, store_name, start_time=None, end_time=None, phone="7346357000", password="hdl12345"):
        self.store_id = store_dict_panda[store_name]
        self.store_name = store_name
        self.start_time = self.parse_time(start_time)
        self.end_time = self.parse_time(end_time)
        try:
            if self.start_time and self.end_time and self.start_time > self.end_time:
                tmp = self.start_time
                self.start_time = self.end_time
                self.end_time = tmp
                print(f"注意：检测到传入的时间范围 start > end，已自动交换为 {self.start_time} - {self.end_time}")
        except Exception:
            pass
        self.driver = init_browser()
        self.wait = WebDriverWait(self.driver, 10)
        self.orders_data = []
        self.phone = phone
        self.password = password

    @staticmethod
    def parse_time(time_str):
        if not time_str:
            return None
        try:
            return datetime.datetime.fromisoformat(time_str)
        except ValueError:
            return datetime.datetime.strptime(time_str, '%Y-%m-%d')

    def login(self):
        do_login(self.driver, self.wait, self.phone, self.password)

    # ... keep extract_order_details, extract_json_from_text, fetch_details, scrape_orders, save_to_csv, run
    # 为了避免重复代码块过长，这里保留核心实现从原文件复制并稍微调整引用

    # 已移除详细字段提取函数（extract_order_details）
    # 该爬虫现在只负责：登录、翻页、点击订单、捕获与保存原始 XHR 响应（raw JSON 或文本）。

    # 已移除 extract_json_from_text。保存逻辑将只尝试直接解析每条原始响应为 JSON。

    def fetch_details(self, latest_only: bool = True, timeout: float = 0):
        if timeout and timeout > 0:
            start = time.time()
            while time.time() - start < timeout:
                try:
                    reqs = list(self.driver.requests)
                except Exception:
                    reqs = []
                if reqs:
                    break
                time.sleep(0.1)

        try:
            requests_list = list(self.driver.requests)
        except Exception:
            requests_list = []

        candidates = []
        for req in requests_list:
            try:
                if "detail" in req.url and req.method and req.method.upper() == "POST" and getattr(req, 'response', None):
                    candidates.append(req)
            except Exception:
                continue

        if not candidates:
            print("未捕获到包含 'details' 的 XHR 请求。")
            return None

        target_req = candidates[-1] if latest_only else candidates[0]

        try:
            resp = target_req.response
            if not resp or not getattr(resp, 'body', None):
                print("匹配的请求没有响应体。")
                return None

            resp_bytes = resp.body
            try:
                if resp.headers.get("Content-Encoding") == "gzip":
                    resp_text = gzip.decompress(resp_bytes).decode('utf-8', errors='ignore')
                else:
                    resp_text = resp_bytes.decode('utf-8', errors='ignore')
            except Exception as e:
                print(f"解码响应时出错: {e}")
                resp_text = None

            if not resp_text:
                print("响应解码失败或为空。")
                return None

            # 尝试从响应文本中解析订单时间（优先使用 JSON 结构）
            fetched_time = ""
            try:
                parsed = json.loads(resp_text)
                fetched_time = (
                    parsed.get('data', {}).get('createTimeStr')
                    or parsed.get('data', {}).get('createTime')
                    or parsed.get('createTime')
                    or parsed.get('createTimeStr')
                    or ""
                )
            except Exception:
                # 回退：用正则查找常见字段名
                m = re.search(r'"createTimeStr"\s*:\s*"([^"]+)"', resp_text)
                if m:
                    fetched_time = m.group(1)
                else:
                    m2 = re.search(r'"createTime"\s*:\s*"([^"]+)"', resp_text)
                    if m2:
                        fetched_time = m2.group(1)

            print(f"捕获到原始详情（最新匹配）来自 URL: {target_req.url} 订单时间: {fetched_time}")
            return resp_text
        except Exception as e:
            print(f"读取匹配请求响应时出错: {e}")
            return None

    def scrape_orders(self):
        self.login()
        self.driver.get("https://merchant-uk.hungrypanda.co/master/branchStore/storeList")
        btn = self.wait.until(EC.presence_of_element_located(
            (By.XPATH, f'//tr[@data-row-key="{self.store_id}"]//button')
        ))
        self.driver.execute_script("arguments[0].click();", btn)
        self.wait.until(lambda d: len(d.window_handles) > 1)
        self.driver.switch_to.window(self.driver.window_handles[-1])
        self.driver.get(SELECTORS["order_manage_url"])
        self.wait.until(EC.presence_of_element_located(SELECTORS["table_row_css"]))

        stop_scraping = False
        print("等待分页元素加载...")
        try:
            pagination = self.wait.until(EC.presence_of_element_located(SELECTORS["pagination_class"]))
        except TimeoutException:
            print("分页元素加载超时，请检查页面是否正确加载。")
            raise
        total_pages = int(pagination.find_elements(By.CLASS_NAME, "ant-pagination-item")[-1].text)

        for page in range(1, total_pages + 1):
            if stop_scraping:
                break
            print(f"Processing page {page}/{total_pages}")
            rows = self.wait.until(EC.presence_of_all_elements_located(SELECTORS["table_row_css"]))
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < 6:
                    continue
                base_info = [cell.text.strip() for cell in cells[:6]]
                link = cells[5].find_element(By.TAG_NAME, "a")
                try:
                    self.driver.requests.clear()
                except Exception:
                    pass

                self.driver.execute_script("arguments[0].click();", link)
                modal = self.wait.until(EC.visibility_of_element_located(SELECTORS["modal_body_css"]))

                # 先尝试从 modal 中读取订单时间，用于决定是否需要请求 XHR
                order_time_str = ""
                order_dt = None
                start_wait = time.time()
                while time.time() - start_wait < 2:
                    try:
                        order_time_str = modal.find_element(By.XPATH, './/div[contains(text(),"Order created time")]/following-sibling::div').text
                        if order_time_str:
                            break
                    except Exception:
                        pass
                    time.sleep(0.12)

                if order_time_str:
                    try:
                        try:
                            order_dt = datetime.datetime.strptime(order_time_str, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            order_dt = datetime.datetime.fromisoformat(order_time_str)
                    except Exception:
                        order_dt = None

                # 决定是否需要 fetch XHR：
                # - 若能解析到 order_dt，则仅当 order_dt 在 start/end 范围内时才 fetch
                # - 若无法解析到时间（order_dt is None），回退为 fetch（保守策略）
                should_fetch = False
                if order_dt:
                    in_after = (not self.start_time) or (order_dt >= self.start_time)
                    in_before = (not self.end_time) or (order_dt <= self.end_time)
                    should_fetch = in_after and in_before
                    if not in_after and self.start_time and order_dt < self.start_time:
                        # 如果发现比 start_time 更早，设置停止标志并中止后续分页抓取
                        stop_scraping = True
                else:
                    should_fetch = True

                if not should_fetch:
                    # 关闭 modal 并跳过 fetch
                    try:
                        self.driver.execute_script("arguments[0].click();",
                                                   self.wait.until(EC.element_to_be_clickable(SELECTORS["modal_close_css"])))
                        self.wait.until(EC.invisibility_of_element(modal))
                    except Exception:
                        pass
                    # 若设置了停止标志，退出当前行循环
                    if stop_scraping:
                        break
                    continue

                # 需要获取详细 XHR
                print(f"点击订单详情，准备捕获 XHR（订单时间: {order_time_str or 'unknown'}）...")
                time.sleep(0.2)
                fetched_raw = self.fetch_details(timeout=4)
                # 直接保存原始响应（可能为 JSON 字符串或其它文本），保持 None 也写入占位
                self.orders_data.append(fetched_raw)
                # 尝试关闭 modal（若存在），不影响主流程
                try:
                    self.driver.execute_script("arguments[0].click();",
                                               self.wait.until(EC.element_to_be_clickable(SELECTORS["modal_close_css"])))
                    self.wait.until(EC.invisibility_of_element(modal))
                except Exception:
                    pass

            if not stop_scraping and page < total_pages:
                nxt = pagination.find_element(By.CSS_SELECTOR, "li.ant-pagination-next button")
                self.driver.execute_script("arguments[0].click();", nxt)
                time.sleep(1)

    def save_raw_json(self):
        # 将 orders_data 中的原始响应尝试解析为 JSON，解析失败则写入 None
        raw_objects = []
        for raw_val in self.orders_data:
            if not raw_val:
                raw_objects.append(None)
                continue
            try:
                parsed = json.loads(raw_val)
                raw_objects.append(parsed)
            except Exception:
                raw_objects.append(None)

        # 调用通用存储接口（当前实现为本地文件），同时尝试写入 Postgres
        save_raw_json(raw_objects, self.store_name, self.start_time, self.end_time, dest='file')

        # 过滤掉 None 元素并写入数据库（save_orders_to_db 会基于 createTimeStr 过滤前一天）
        try:
            from .storage import save_orders_to_db
            valid_objs = [obj for obj in raw_objects if isinstance(obj, dict)]
            if valid_objs:
                code = store_name_to_code.get(self.store_name)
                inserted = save_orders_to_db(
                    valid_objs,
                    platform='panda',
                    start_time=self.start_time,
                    end_time=self.end_time,
                    store_code=code,
                    store_name=self.store_name,
                )
                print(f"已写入数据库 {inserted} 条订单（前一天过滤、去重后）")
            else:
                print("未发现可写入数据库的原始详情（全部为 None 或解析失败）")
        except Exception as e:
            print(f"写入数据库时发生错误: {e}")

    def run(self):
        t0 = time.time()
        self.scrape_orders()
        self.save_raw_json()
        try:
            self.driver.quit()
        except Exception:
            pass
        print(f"总运行时间: {time.time() - t0:.2f}秒")
