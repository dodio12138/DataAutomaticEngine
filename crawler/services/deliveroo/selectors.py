"""页面元素定位和API端点配置"""
from selenium.webdriver.common.by import By

# 页面元素定位器
SELECTORS = {
    "login_email": (By.CSS_SELECTOR, 'input[data-testid="login-email"]'),
    "login_password": (By.CSS_SELECTOR, 'input[data-testid="login-password"]'),
    "login_button": (By.CSS_SELECTOR, 'button[data-testid="login-submit"]'),
    "cookie_reject": (By.ID, "onetrust-reject-all-handler"),
    "cookie_accept": (By.ID, "onetrust-accept-btn-handler"),
}

# API端点
API_ENDPOINTS = {
    "orders_list": "https://restaurant-hub-data-api.deliveroo.net/api/restaurants/{restaurant_id}/orders",
    "order_detail": "https://restaurant-hub-data-api.deliveroo.net/api/orders/{order_id}",
}

# 请求头模板
HEADERS_TEMPLATE = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Referer': 'https://partner-hub.deliveroo.com/',
    'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'x-hub-api-caller': 'https://partner-hub.deliveroo.com',
}
