# 飞书 User Access Token 获取指南

## 为什么需要 User Access Token？

当飞书多维表格使用**用户身份权限**（user_access_token）时，需要以用户身份进行授权，而不是应用身份（tenant_access_token）。

## 方法一：在线获取（推荐）

### 1. 打开飞书开放平台
访问：https://open.feishu.cn/app/{你的APP_ID}/console

### 2. 进入"开发调试"
- 左侧菜单选择 **"开发调试"**
- 选择 **"身份验证"** 或 **"API调试台"**

### 3. 获取 User Access Token
- 在调试台中，选择使用 **"用户身份"（User Access Token）**
- 点击 **"获取 User Access Token"** 按钮
- 系统会自动跳转到授权页面
- 授权后，复制生成的 `user_access_token`

### 4. 配置到 .env 文件
```bash
# 在 .env 文件中添加或更新：
FEISHU_USER_ACCESS_TOKEN=u-xxxxxx.xxxxxxxxxxxxxxxxx
```

**注意：** user_access_token 有效期较短（通常 2 小时），需要定期刷新！

---

## 方法二：通过 API 获取（自动化）

### 1. 在飞书开放平台配置重定向URI
- 进入你的应用 → **"安全设置"**
- 添加重定向URI：`http://localhost:8000/feishu/callback`

### 2. 运行获取脚本
```bash
python3 get_feishu_user_token.py
```

### 3. 按提示操作
1. 脚本会生成授权链接，在浏览器中打开
2. 完成授权后，复制回调URL中的 `code` 参数
3. 将 code 粘贴到脚本提示中
4. 脚本会自动获取 user_access_token

---

## 方法三：使用 Refresh Token 自动刷新

如果你已经有 `refresh_token`，可以添加自动刷新功能：

```bash
# 在 .env 中配置：
FEISHU_USER_REFRESH_TOKEN=your_refresh_token_here
```

系统会在 token 过期前自动刷新。

---

## 快速测试

配置好 `FEISHU_USER_ACCESS_TOKEN` 后：

```bash
# 重启服务
docker compose restart api

# 测试同步
./sync_feishu_bitable.sh
```

---

## 常见问题

### Q: Token 过期怎么办？
A: 重新执行上述步骤获取新的 token，或配置 refresh_token 实现自动刷新。

### Q: 还是提示 403 Forbidden？
A: 确认以下几点：
1. 用户（你自己）是否是多维表格的协作者且有编辑权限
2. 在飞书开放平台，应用是否已开通 `bitable:app` 权限（用户身份）
3. user_access_token 是否有效（未过期）

### Q: 如何查看 token 是否有效？
A: 可以使用飞书开放平台的 API 调试台测试，或查看同步日志输出。

