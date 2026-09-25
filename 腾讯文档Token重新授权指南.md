# 腾讯文档Token重新授权指南

## 📋 当前状态

### 服务状态
- ✅ tencent-doc-filler服务已启动
- ✅ 运行在：http://127.0.0.1:8090
- ⚠️ refresh_token未配置，无法自动刷新
- 当前配置状态：
  - book_id: `300000000$WKhAHYepeKoQ`
  - next_row: 507
  - configured: true

---

## 🔄 OAuth重新授权步骤

### Step 1: 获取授权URL

**请求**：
```bash
curl http://127.0.0.1:8090/oauth/authorize-url
```

**响应**：
```json
{
  "url": "https://docs.qq.com/oauth/v2/authorize?client_id=94860fc7955d43919af8c94e6b0cbd20&redirect_uri=https://docs.qq.com&response_type=code&scope=all&state=repair-form"
}
```

---

### Step 2: 访问授权页面

**复制上面的URL并在浏览器中打开**：
```
https://docs.qq.com/oauth/v2/authorize?client_id=94860fc7955d43919af8c94e6b0cbd20&redirect_uri=https://docs.qq.com&response_type=code&scope=all&state=repair-form
```

**操作步骤**：
1. 使用有权限访问目标表格的QQ账号登录
2. 点击"授权"按钮
3. 授权后会跳转到：`https://docs.qq.com?code=AUTHORIZATION_CODE&state=repair-form`

---

### Step 3: 获取Authorization Code

**从跳转后的URL中提取code参数**：

浏览器地址栏显示：
```
https://docs.qq.com?code=XXXXXXXXXXX&state=repair-form
```

**复制`code=`后面的值**（这就是Authorization Code）

---

### Step 4: 交换Access Token

**使用code换取Token**：
```bash
curl "http://127.0.0.1:8090/oauth/callback?code=YOUR_AUTHORIZATION_CODE&state=repair-form"
```

**替换`YOUR_AUTHORIZATION_CODE`为Step 3获取的code**

**成功响应示例**：
```json
{
  "ok": true,
  "state": "repair-form",
  "user_id": "4b4a634c579741149fbeb4ef6f8f2dea",
  "expires_in": 2592000,
  "message": "授权成功，token 已写入 token.json"
}
```

---

### Step 5: 验证新Token

**检查服务健康状态**：
```bash
curl http://127.0.0.1:8090/health
```

**应该看到**：
```json
{
  "status": "ok",
  "configured": true,
  "has_refresh_token": true,  // 注意这里应该变为true
  ...
}
```

**检查token文件**：
```bash
cat tencent-doc-filler/token.json
```

应该包含新的`access_token`和`refresh_token`。

---

## 📝 完整命令序列（复制执行）

```bash
# 1. 获取授权URL
curl -s http://127.0.0.1:8090/oauth/authorize-url | jq -r '.url'

# 2. 复制输出的URL，在浏览器中打开，完成授权

# 3. 从浏览器地址栏复制code参数，替换下面的YOUR_CODE
curl "http://127.0.0.1:8090/oauth/callback?code=YOUR_CODE&state=repair-form"

# 4. 验证
curl -s http://127.0.0.1:8090/health | jq '.'
```

---

## 🔍 授权URL参数说明

| 参数 | 值 | 说明 |
|------|-----|------|
| `client_id` | `94860fc7955d43919af8c94e6b0cbd20` | 你的应用ID |
| `redirect_uri` | `https://docs.qq.com` | 授权后跳转地址 |
| `response_type` | `code` | OAuth 2.0授权码模式 |
| `scope` | `all` | 请求所有权限 |
| `state` | `repair-form` | 防CSRF攻击的状态参数 |

---

## ⚠️ 常见问题

### Q1: 授权后跳转到404页面
**原因**：redirect_uri配置为`https://docs.qq.com`，不是真实的回调地址  
**解决**：没关系！只需要从浏览器地址栏复制code参数即可

### Q2: code换取token失败
**可能原因**：
- code已过期（5分钟有效期）
- code已被使用过（一次性）
- client_secret配置错误

**解决**：重新走授权流程获取新的code

### Q3: 提示"未配置client_secret"
**检查**：
```bash
grep TENCENT_DOC_CLIENT_SECRET tencent-doc-filler/.env
```

**如果为空**，需要从腾讯文档开放平台获取并配置：
```env
TENCENT_DOC_CLIENT_SECRET=your-secret-here
```

### Q4: Token有效期多久？
- Access Token: **30天**
- Refresh Token: **永久有效**（除非用户撤销授权）

### Q5: 如何自动刷新Token？
配置了refresh_token后，代码会自动刷新：
```python
# tencent_client.py 中已实现
async def refresh_access_token(self):
    # 使用refresh_token换取新的access_token
    ...
```

---

## 📂 授权后的文件变化

### token.json（更新后）
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...(新Token)",
  "refresh_token": "新的refresh_token",
  "open_id": "4b4a634c579741149fbeb4ef6f8f2dea",
  "book_id": "300000000$WKhAHYepeKoQ",
  "updated_at": "2026-09-20T..."
}
```

### .env（手动更新）
建议同步更新.env中的Token：
```env
TENCENT_DOC_ACCESS_TOKEN=新的access_token
TENCENT_DOC_REFRESH_TOKEN=新的refresh_token
```

---

## 🎯 测试授权是否成功

### 测试1: 健康检查
```bash
curl http://127.0.0.1:8090/health
```

### 测试2: 获取字段列表
```bash
curl http://127.0.0.1:8090/api/repair/fields
```

### 测试3: Dry Run提交工单
```bash
curl -X POST "http://127.0.0.1:8090/api/repair/fill?dry_run=true" \
  -H "Authorization: Bearer change-me" \
  -H "Content-Type: application/json" \
  -d '{
    "故障教室": "测试教室",
    "报修时间": "2026-09-20",
    "周次": "第1周",
    "报修类型": "测试",
    "报修人": "测试",
    "报修人学院": "测试学院",
    "是否为外聘老师": "否",
    "报修方式": "测试",
    "处理人": "测试",
    "是否更换设备": "否",
    "处理情况": "测试",
    "故障发生原因": "测试",
    "处理方式": "测试"
  }'
```

如果返回成功，说明授权完成！

---

## 📞 需要帮助？

如果授权过程中遇到问题，请提供：
1. 授权URL（可以部分打码）
2. 错误信息截图
3. `curl http://127.0.0.1:8090/health` 的输出

---

**创建时间**：2026-09-20  
**服务状态**：✅ 运行中（端口8090）
