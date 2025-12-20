"""负责登录和浏览器初始化的模块。"""
import time
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .selectors import SELECTORS


def init_browser(headless: bool = True):
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    if headless:
        options.add_argument("--headless")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-component-update")

    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.stylesheets": 2
    }
    options.add_experimental_option("prefs", prefs)
    service = Service("/usr/local/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def do_login(driver, wait, phone: str, password: str):
    driver.get("https://merchant-uk.hungrypanda.co/master/login")
    wait.until(EC.presence_of_element_located(SELECTORS["login_phone"])).send_keys(phone)
    driver.find_element(*SELECTORS["login_password"]).send_keys(password)
    wait.until(EC.element_to_be_clickable(SELECTORS["login_button_xpath"]) ) .click()
    # wait for branch management to appear as login success signal
    wait.until(EC.presence_of_element_located(SELECTORS["branch_management_text"]))
    # small wait to ensure session cookies stabilized
    time.sleep(0.3)
