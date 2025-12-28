"""负责登录、浏览器初始化和弹窗处理的模块"""
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from .selectors import SELECTORS


def init_browser(headless: bool = True):
    """初始化浏览器配置"""
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-component-update")
    options.add_argument("--disable-gpu")
    if headless:
        options.add_argument("--headless")
    
    # 启用性能日志以捕获网络请求
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.stylesheets": 2
    }
    options.add_experimental_option("prefs", prefs)
    
    service = Service("/usr/local/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def close_cookie_popup(driver, wait):
    """关闭 Cookie 弹窗"""
    try:
        # 等待 Cookie 弹窗出现
        cookie_button = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable(SELECTORS["cookie_reject"])
        )
        # 使用 JavaScript 点击
        driver.execute_script("arguments[0].click();", cookie_button)
        time.sleep(0.5)
        print("✅ 已关闭 Cookie 弹窗")
    except Exception as e:
        print(f"ℹ️ 未找到 Cookie 弹窗或已关闭")


def close_all_popups(driver, wait, timeout=2):
    """尝试关闭所有可能的弹窗"""
    print("\n开始尝试关闭所有弹窗...")
    
    # 等待页面稳定
    time.sleep(2)
    
    # 尝试多种关闭按钮选择器
    close_selectors = [
        # Cookie 弹窗
        (By.ID, "onetrust-reject-all-handler"),
        (By.ID, "onetrust-accept-btn-handler"),
        
        # 通用关闭按钮
        (By.XPATH, '//button[@aria-label="Close"]'),
        (By.XPATH, '//button[@aria-label="关闭"]'),
        (By.XPATH, '//button[contains(@class, "close")]'),
        (By.XPATH, '//button[text()="×"]'),
        (By.XPATH, '//button[contains(text(), "Close")]'),
        (By.XPATH, '//button[contains(text(), "Not now")]'),
    ]
    
    closed_count = 0
    for selector_type, selector_value in close_selectors:
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((selector_type, selector_value))
            )
            element.click()
            print(f"✅ 成功关闭弹窗 (选择器: {selector_value[:50]}...)")
            closed_count += 1
            time.sleep(0.5)
        except Exception:
            pass
    
    # 按 ESC 键尝试关闭模态框
    try:
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        print("✅ 已尝试按 ESC 键关闭弹窗")
        time.sleep(0.5)
    except Exception:
        pass
    
    print(f"\n弹窗关闭完成，共关闭了 {closed_count} 个弹窗\n")


def do_login(driver, wait, email: str, password: str):
    """登录 Deliveroo 账户"""
    driver.get("https://partner-hub.deliveroo.com/login")
    print("✅ 已打开登录页面，等待页面加载...")
    
    # 等待页面完全加载
    time.sleep(2)
    
    # 先尝试关闭 Cookie 弹窗
    try:
        close_cookie_popup(driver, wait)
    except Exception as e:
        print(f"⚠️ 关闭 Cookie 弹窗失败: {e}")
    
    # 输入邮箱
    email_input = wait.until(
        EC.presence_of_element_located(SELECTORS["login_email"])
    )
    email_input.clear()
    email_input.send_keys(email)
    print(f"✅ 已输入邮箱: {email}")
    
    # 输入密码
    password_input = wait.until(
        EC.presence_of_element_located(SELECTORS["login_password"])
    )
    password_input.clear()
    password_input.send_keys(password)
    print("✅ 已输入密码")
    
    # 等待以确保输入完成
    time.sleep(1)
    
    # 再次尝试关闭可能出现的弹窗
    try:
        close_all_popups(driver, wait, timeout=1)
    except Exception:
        pass
    
    # 定位登录按钮
    login_button = wait.until(
        EC.presence_of_element_located(SELECTORS["login_button"])
    )
    
    # 滚动到登录按钮位置
    try:
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", login_button)
        time.sleep(0.5)
    except Exception:
        pass
    
    # 使用 JavaScript 点击（更可靠）
    try:
        print("⏳ 尝试点击登录按钮...")
        driver.execute_script("arguments[0].click();", login_button)
        print("✅ 已通过 JavaScript 点击登录按钮")
    except Exception as e:
        print(f"⚠️ JavaScript 点击失败，尝试普通点击: {e}")
        try:
            # 回退到普通点击
            ActionChains(driver).move_to_element(login_button).click().perform()
            print("✅ 已通过 ActionChains 点击登录按钮")
        except Exception as e2:
            print(f"❌ 登录按钮点击失败: {e2}")
            raise
    
    # 等待登录完成
    print("⏳ 等待登录完成...")
    time.sleep(5)
    
    # 尝试关闭登录后可能出现的弹窗
    try:
        close_all_popups(driver, wait, timeout=2)
    except Exception:
        pass
    
    print("✅ 登录流程完成")


def open_orders_page(driver, org_id: str, branch_id: str, start_date: str, end_date: str):
    """跳转到订单页面"""
    url = f"https://partner-hub.deliveroo.com/orders?orgId={org_id}&branchId={branch_id}&startDate={start_date}&endDate={end_date}"
    driver.get(url)
    print(f"✅ 已跳转到订单页面：{url}")


def fetch_cookies(driver):
    """获取所有cookies"""
    cookies = driver.get_cookies()
    cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
    return cookie_dict
