 # 腾讯文档API接口与Token配置指南

## 📋 目录
- [当前配置概览](#当前配置概览)
- [OAuth认证凭证](#oauth认证凭证)
- [API接口说明](#api接口说明)
- [Token管理](#token管理)
- [表格配置](#表格配置)
- [完整配置示例](#完整配置示例)
- [API调用示例](#api调用示例)
- [故障排查](#故障排查)

---

## 🔑 当前配置概览

### 基础认证信息
| 配置项 | 当前值 | 说明 |
|--------|--------|------|
| **Client ID** | `94860fc7955d43919af8c94e6b0cbd20` | 应用标识 |
| **Client Secret** | `（未在.env中显示）` | 应用密钥（敏感信息） |
| **Open ID** | `4b4a634c579741149fbeb4ef6f8f2dea` | 用户标识 |
| **Access Token** | `<ACCESS_TOKEN_已脱敏>` | 访问令牌（JWT格式） |
| **Refresh Token** | `（空）` | 刷新令牌（未配置） |

### 目标表格信息
| 配置项 | 当前值 | 说明 |
|--------|--------|------|
| **表格URL** | `https://docs.qq.com/sheet/DV0toQUhZZXBlS29R?tab=BB08J2` | 綦江校区设备报修表 |
| **Encoded ID** | `DV0toQUhZZXBlS29R` | URL中的表格标识 |
| **Sheet ID** | `BB08J2` | 工作表标签ID |
| **Book ID** | `300000000$WKhAHYepeKoQ` | 内部文件ID（已转换） |

### 数据写入配置
| 配置项 | 当前值 | 说明 |
|--------|--------|------|
| **数据起始行** | `484` | 当前从第484行开始写入 |
| **下一行** | `507` | 下次将写入第507行 |
| **最后写入行** | `506` | 最近一次写入的行号 |
| **数据列范围** | `B:N`（13列） | A列为序号，B~N为业务数据 |
| **最后更新时间** | `2026-06-16 00:18:29 UTC` | 行号最后更新时间 |

---

## 🔐 OAuth认证凭证

### 1. Access Token（访问令牌）
```
<ACCESS_TOKEN_已脱敏>
```

**Token解析**（JWT Payload）：
```json
{
  "clt": "94860fc7955d43919af8c94e6b0cbd20",  // Client ID
  "typ": 1,                                    // Token类型
  "exp": 1783394144.798008,                    // 过期时间（Unix时间戳）
  "iat": 1780802144.798008,                    // 签发时间
  "sub": "4b4a634c579741149fbeb4ef6f8f2dea"   // Open ID
}
```

**过期时间**：
- 签发时间：`2026-06-07 03:15:44 UTC`
- 过期时间：`2026-07-07 03:15:44 UTC`（**约30天有效期**）
- ⚠️ **注意**：Token将在2026年7月7日过期，需要及时刷新

### 2. 认证Header格式
```http
Access-Token: <ACCESS_TOKEN_已脱敏>
Client-Id: 94860fc7955d43919af8c94e6b0cbd20
Open-Id: <已脱敏>
Accept: application/json
```

### 3. OAuth授权流程

#### Step 1: 获取授权URL
```bash
GET http://127.0.0.1:8090/oauth/authorize-url
```

**响应示例**：
```json
{
  "url": "https://docs.qq.com/oauth/v2/authorize?client_id=94860fc7955d43919af8c94e6b0cbd20&redirect_uri=https://docs.qq.com&response_type=code&scope=all&state=repair-form"
}
```

#### Step 2: 用户授权并获取code
浏览器访问授权URL，用户同意后跳转至：
```
https://docs.qq.com?code=AUTHORIZATION_CODE&state=repair-form
```

#### Step 3: 交换Access Token
```bash
GET http://127.0.0.1:8090/oauth/callback?code=AUTHORIZATION_CODE&state=repair-form
```

**响应示例**：
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

## 🌐 API接口说明

### 腾讯文档官方API基地址
```
OAuth: https://docs.qq.com/oauth/v2
OpenAPI: https://docs.qq.com/openapi
```

### 本地服务API（tencent-doc-filler）
**服务地址**：`http://127.0.0.1:8090`

---

### 1. 健康检查
```http
GET /health
```

**响应示例**：
```json
{
  "status": "ok",
  "configured": true,
  "has_refresh_token": false,
  "book_id": "300000000$WKhAHYepeKoQ",
  "encoded_id": "DV0toQUhZZXBlS29R",
  "sheet_id": "BB08J2",
  "data_start_row": 484,
  "next_row": 507,
  "row_state": {
    "next_row": 507,
    "data_start_row": 484,
    "last_written_row": 506,
    "updated_at": "2026-06-16T00:18:29.770117+00:00",
    "note": "auto_after_fill"
  },
  "fields": [
    "故障教室", "报修时间", "周次", "报修类型", "报修人",
    "报修人学院", "是否为外聘老师", "报修方式", "处理人",
    "是否更换设备", "处理情况", "故障发生原因", "处理方式"
  ]
}
```

---

### 2. 提交报修工单（核心接口）
```http
POST /api/repair/fill
Authorization: Bearer change-me
Content-Type: application/json
```

**请求Body**：
```json
{
  "故障教室": "A301",
  "报修时间": "2026-06-16",
  "周次": "第14周",
  "报修类型": "水电维修",
  "报修人": "张三",
  "报修人学院": "计算机学院",
  "是否为外聘老师": "否",
  "报修方式": "QQ群聊",
  "处理人": "李四",
  "是否更换设备": "否",
  "处理情况": "已处理",
  "故障发生原因": "自然损坏",
  "处理方式": "维修",
  "row": null
}
```

**查询参数**：
- `dry_run=true` - 预览模式，不实际写入
- `sync_row=true` - 写入前导出表格同步行号（每日限9次）

**成功响应**：
```json
{
  "ok": true,
  "dry_run": false,
  "result": {
    "book_id": "300000000$WKhAHYepeKoQ",
    "sheet_id": "BB08J2",
    "range": "BB08J2!B507:N507",
    "row": 507,
    "columns": "B:N",
    "value_count": 13,
    "values": [
      "A301", "2026/6/16", "14", "水电维修", "张三",
      "计算机学院", "否", "QQ群聊", "李四",
      "否", "已处理", "自然损坏", "维修"
    ],
    "formatted": {
      "故障教室": "A301",
      "报修时间": "2026/6/16",
      "周次": "14",
      ...
    }
  },
  "missing_fields": []
}
```

**字段缺失响应**：
```json
{
  "ok": false,
  "missing_fields": ["故障教室", "报修人"]
}
```

---

### 3. 同步下一行行号
```http
POST /api/repair/sync-row
Authorization: Bearer change-me
```

**功能**：导出xlsx解析最后一行，自动更新`next_row`  
**限制**：每日限调用9次  

**响应示例**：
```json
{
  "ok": true,
  "next_row": 507
}
```

---

### 4. 查询当前行号状态
```http
GET /api/repair/row
Authorization: Bearer change-me
```

**响应示例**：
```json
{
  "ok": true,
  "next_row": 507,
  "data_start_row": 484,
  "last_written_row": 506,
  "updated_at": "2026-06-16T00:18:29.770117+00:00",
  "note": "auto_after_fill"
}
```

---

### 5. 手动设置下一行行号
```http
PUT /api/repair/row
Authorization: Bearer change-me
Content-Type: application/json
```

**请求Body**：
```json
{
  "next_row": 520,
  "note": "手动跳过损坏的行"
}
```

**响应**：同查询接口

---

### 6. 获取字段列表
```http
GET /api/repair/fields
```

**响应示例**：
```json
{
  "fields": [
    "故障教室", "报修时间", "周次", "报修类型", "报修人",
    "报修人学院", "是否为外聘老师", "报修方式", "处理人",
    "是否更换设备", "处理情况", "故障发生原因", "处理方式"
  ]
}
```

---

## 🔄 Token管理

### Token存储文件

#### 1. token.json（OAuth凭证）
**路径**：`tencent-doc-filler/token.json`

```json
{
  "access_token": "<ACCESS_TOKEN_已脱敏>",
  "refresh_token": "",
  "open_id": "<已脱敏>",
  "book_id": "300000000$WKhAHYepeKoQ",
  "updated_at": "2026-06-07T03:18:02.966392+00:00"
}
```

#### 2. next_row.json（行号状态）
**路径**：`tencent-doc-filler/next_row.json`

```json
{
  "next_row": 507,
  "updated_at": "2026-06-16T00:18:29.770117+00:00",
  "note": "auto_after_fill",
  "last_written_row": 506
}
```

### Token刷新机制

**当前问题**：`refresh_token`为空，无法自动刷新  

**解决方案**：
1. **临时方案**：Token过期前重新授权
2. **长期方案**：在OAuth授权时确保获取`refresh_token`

**刷新Token的API调用**（如果有refresh_token）：
```http
GET https://docs.qq.com/oauth/v2/token?client_id=CLIENT_ID&client_secret=CLIENT_SECRET&grant_type=refresh_token&refresh_token=REFRESH_TOKEN
```

---

## 📊 表格配置

### 目标表格结构
```
表格名称：綦江校区设备报修表
表格URL：https://docs.qq.com/sheet/DV0toQUhZZXBlS29R?tab=BB08J2
```

### 列结构（A~N列）
| 列 | 字段名 | 说明 | 示例 |
|----|--------|------|------|
| A | 序号 | 表格自动生成（不写入） | 1, 2, 3... |
| B | 故障教室 | 必填 | A301 |
| C | 报修时间 | 必填，自动格式化 | 2026/6/16 |
| D | 周次 | 必填，提取数字 | 14 |
| E | 报修类型 | 必填 | 水电维修 |
| F | 报修人 | 必填 | 张三 |
| G | 报修人学院 | 必填 | 计算机学院 |
| H | 是否为外聘老师 | 必填，"是"或"否" | 否 |
| I | 报修方式 | 必填 | QQ群聊 |
| J | 处理人 | 必填 | 李四 |
| K | 是否更换设备 | 必填，"是"或"否" | 否 |
| L | 处理情况 | 必填 | 已处理 |
| M | 故障发生原因 | 必填 | 自然损坏 |
| N | 处理方式 | 必填 | 维修 |

### 写入范围示例
```
当前行507: BB08J2!B507:N507
下一行508: BB08J2!B508:N508
```

---

## 📝 完整配置示例

### .env文件（生产环境）
```env
# 服务配置
TENCENT_DOC_FILLER_HOST=127.0.0.1
TENCENT_DOC_FILLER_PORT=8090
TENCENT_DOC_FILLER_API_TOKEN=your-secure-api-token-here

# 腾讯文档OAuth凭证
TENCENT_DOC_CLIENT_ID=94860fc7955d43919af8c94e6b0cbd20
TENCENT_DOC_CLIENT_SECRET=<已脱敏>
TENCENT_DOC_ACCESS_TOKEN=<ACCESS_TOKEN_已脱敏>
TENCENT_DOC_REFRESH_TOKEN=<已脱敏>
TENCENT_DOC_OPEN_ID=<已脱敏>
TENCENT_DOC_REDIRECT_URI=https://docs.qq.com

# 目标表格
TENCENT_DOC_SHEET_URL=https://docs.qq.com/sheet/DV0toQUhZZXBlS29R?tab=BB08J2
TENCENT_DOC_ENCODED_ID=DV0toQUhZZXBlS29R
TENCENT_DOC_SHEET_ID=BB08J2
TENCENT_DOC_BOOK_ID=300000000$WKhAHYepeKoQ

# 数据配置
TENCENT_DOC_DATA_START_ROW=484
TENCENT_DOC_SYNC_BEFORE_FILL=false
```

---

## 🔨 API调用示例

### Python示例
```python
import httpx

# 配置
BASE_URL = "http://127.0.0.1:8090"
API_TOKEN = "change-me"
headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# 提交工单
async def submit_repair():
    data = {
        "故障教室": "A301",
        "报修时间": "2026-06-16",
        "周次": "第14周",
        "报修类型": "水电维修",
        "报修人": "张三",
        "报修人学院": "计算机学院",
        "是否为外聘老师": "否",
        "报修方式": "QQ群聊",
        "处理人": "李四",
        "是否更换设备": "否",
        "处理情况": "已处理",
        "故障发生原因": "自然损坏",
        "处理方式": "维修"
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/api/repair/fill",
            headers=headers,
            json=data
        )
        print(resp.json())
```

### cURL示例
```bash
# 健康检查
curl http://127.0.0.1:8090/health

# 提交工单（dry_run模式）
curl -X POST http://127.0.0.1:8090/api/repair/fill?dry_run=true \
  -H "Authorization: Bearer change-me" \
  -H "Content-Type: application/json" \
  -d '{
    "故障教室": "A301",
    "报修时间": "2026-06-16",
    "周次": "第14周",
    "报修类型": "水电维修",
    "报修人": "张三",
    "报修人学院": "计算机学院",
    "是否为外聘老师": "否",
    "报修方式": "QQ群聊",
    "处理人": "李四",
    "是否更换设备": "否",
    "处理情况": "已处理",
    "故障发生原因": "自然损坏",
    "处理方式": "维修"
  }'

# 查询当前行号
curl -H "Authorization: Bearer change-me" \
  http://127.0.0.1:8090/api/repair/row

# 手动设置行号
curl -X PUT http://127.0.0.1:8090/api/repair/row \
  -H "Authorization: Bearer change-me" \
  -H "Content-Type: application/json" \
  -d '{"next_row": 510, "note": "跳过错误行"}'
```

---

## 🛠️ 故障排查

### 常见问题

#### 1. 401 Unauthorized
**原因**：Token过期或无效  
**解决**：
```bash
# 检查token过期时间
curl http://127.0.0.1:8090/health

# 重新授权
curl http://127.0.0.1:8090/oauth/authorize-url
```

#### 2. 写入行号不正确
**原因**：`next_row.json`状态不准确  
**解决**：
```bash
# 同步最新行号（每日限9次）
curl -X POST -H "Authorization: Bearer change-me" \
  http://127.0.0.1:8090/api/repair/sync-row

# 或手动设置
curl -X PUT -H "Authorization: Bearer change-me" \
  -H "Content-Type: application/json" \
  -d '{"next_row": 520, "note": "manual_fix"}' \
  http://127.0.0.1:8090/api/repair/row
```

#### 3. 字段缺失
**原因**：必填字段未提供  
**解决**：检查响应中的`missing_fields`数组

#### 4. book_id转换失败
**原因**：encoded_id无效或权限不足  
**解决**：
- 检查表格URL是否正确
- 确认账号有权限访问该表格
- 直接在.env中配置`TENCENT_DOC_BOOK_ID`

---

## 📌 重要提示

### ⚠️ 安全注意事项
1. **敏感信息保护**
   - `client_secret`绝不能泄露
   - `access_token`应定期轮换
   - `.env`文件不应提交到版本控制

2. **Token有效期**
   - Access Token有效期：30天
   - 当前Token将在**2026年7月7日**过期
   - 建议配置`refresh_token`实现自动刷新

3. **API调用限制**
   - 导出同步行号：每日限9次
   - 建议使用本地`next_row.json`管理行号

4. **并发写入**
   - 多个服务同时写入可能导致行号冲突
   - 建议通过单一服务（tencent-doc-filler）统一写入

### 📚 参考资料
- [腾讯文档开放平台](https://docs.qq.com/open/document/app/get_started.html)
- [OAuth 2.0 规范](https://oauth.net/2/)
- [FastAPI文档](https://fastapi.tiangolo.com/)

---

**文档版本**：v1.0  
**最后更新**：2026-09-20  
**维护者**：Ling项目组
