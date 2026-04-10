import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

from services.panda.login import init_browser
from services.panda.selectors import SELECTORS
from store_config import store_login_user, store_login_password

store_name = "海底捞冒菜（Piccadilly）"
phone = store_login_user.get(store_name, "")
password = store_login_password.get(store_name, "")

print(f"store={store_name}")
print(f"phone={phone}")
print(f"password_len={len(password)}")

POPUP_SELECTORS = [
    "div.ant-modal",
    "div.ant-modal-root",
    "div.ant-message-notice",
    "div.ant-notification-notice",
    "[role='dialog']",
    "div.el-dialog",
    "div.el-message",
    "div.Toastify__toast",
    "div.swal2-popup",
    "div[aria-modal='true']",
    ".geetest_panel",
    ".geetest_popup_wrap",
    ".captcha",
]


def is_visible(el):
    try:
        return el.is_displayed()
    except Exception:
        return False


def short_text(el, n=220):
    try:
        t = (el.text or "").strip().replace("\n", " | ")
        return t[:n]
    except Exception:
        return ""


driver = init_browser(headless=True)
driver.set_page_load_timeout(30)

try:
    driver.get("https://merchant-uk.hungrypanda.co/login")
    time.sleep(1)

    driver.find_element(*SELECTORS["login_phone"]).send_keys(phone)
    driver.find_element(*SELECTORS["login_password"]).send_keys(password)
    driver.find_element(*SELECTORS["login_button_xpath"]).click()

    print("clicked_login=true")

    found_any = False
    for i in range(1, 11):
        time.sleep(1)
        current_url = driver.current_url
        title = driver.title
        print(f"tick={i} url={current_url} title={title}")

        visible_hits = []
        for css in POPUP_SELECTORS:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, css)
            except Exception:
                els = []
            for el in els:
                if is_visible(el):
                    visible_hits.append((css, short_text(el)))

        dedup = []
        seen = set()
        for css, txt in visible_hits:
            key = (css, txt)
            if key not in seen:
                seen.add(key)
                dedup.append((css, txt))

        if dedup:
            found_any = True
            for css, txt in dedup:
                print(f"popup_detected css={css} text={txt}")

        has_phone = len(driver.find_elements(*SELECTORS["login_phone"])) > 0
        has_pwd = len(driver.find_elements(*SELECTORS["login_password"])) > 0
        print(f"form_still_visible phone={has_phone} pwd={has_pwd}")

    print(f"popup_found={found_any}")
except WebDriverException as e:
    print("webdriver_error=", repr(e))
except Exception as e:
    print("diag_error=", repr(e))
finally:
    try:
        driver.quit()
    except Exception:
        pass
