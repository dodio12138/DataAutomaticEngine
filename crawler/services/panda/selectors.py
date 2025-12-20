"""页面元素定位（方便平台变更时维护）"""
from selenium.webdriver.common.by import By

# 这些定位作为示例，具体可根据页面变化调整
SELECTORS = {
    "login_phone": (By.ID, "phone"),
    "login_password": (By.ID, "password"),
    "login_button_xpath": (By.XPATH, '//button[span[text()="Login"]]'),
    "branch_management_text": (By.XPATH, '//div[contains(text(),"Branch Management")]'),
    "store_row_button": lambda store_id: (By.XPATH, f'//tr[@data-row-key="{store_id}"]//button'),
    "order_manage_url": "https://merchant-uk.hungrypanda.co/order/ordermanage",
    "table_row_css": (By.CSS_SELECTOR, "tbody.ant-table-tbody tr"),
    "modal_body_css": (By.CSS_SELECTOR, "div.ant-modal-body"),
    "modal_close_css": (By.CSS_SELECTOR, "button.ant-modal-close"),
    "pagination_class": (By.CLASS_NAME, "ant-pagination"),
}
