# Feishu API连接问题诊断报告

## 诊断总结

✅ **API连接性**: 正常 - 可以成功访问 https://open.feishu.cn API端点  
✅ **认证凭证**: 有效 - App ID和App Secret可以成功获取access token  
✅ **代理支持**: 正常 - 支持HTTP代理和直连两种方式  
❌ **用户ID**: 无效 - 提供的用户ID `6421712345678901234` 不存在  

## 根本问题

**主要问题**: 用户ID `6421712345678901234` 在当前飞书组织中不存在

**API错误详情**:
- 错误代码: 99992360
- 错误消息: "The request you send is not a valid {user_id} or not exists"
- 状态: 用户ID格式正确但用户不存在

## 连接测试结果

### 1. 认证测试
```bash
# 成功获取access token
curl -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d '{"app_id":"cli_a751cdd4273d1013","app_secret":"16BmEvATAog0tgWaYpRWlbpiilicAvVs"}'

# 响应: {"code":0,"expire":6315,"msg":"ok","tenant_access_token":"..."}
```

### 2. 消息发送测试
```bash
# 用户ID不存在错误
curl -X POST "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=user_id" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"receive_id":"6421712345678901234","msg_type":"text","content":{"text":"test"}}'

# 响应: {"code":99992360,"msg":"...not exists..."}
```

### 3. 网络连接测试
- ✅ 直接连接: 正常 (延迟 ~86ms)
- ✅ 代理连接: 正常 (通过 localhost:8118)
- ✅ HTTPS证书: 有效
- ✅ DNS解析: 正常

## 解决方案

### 方法1: 获取有效用户ID (推荐)

使用提供的工具获取正确的用户ID:

```bash
# 运行用户ID获取工具
python get_feishu_user_id.py

# 或使用自定义凭证
python get_feishu_user_id.py YOUR_APP_ID YOUR_APP_SECRET
```

### 方法2: 通过飞书客户端获取

1. **打开飞书客户端或网页版**
2. **查看目标用户资料**
3. **复制用户ID** (通常在URL中或用户详情页面)
4. **用户ID格式**: 
   - `ou_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` (Open ID格式)
   - `1234567890123456789` (数字格式，10-20位)

### 方法3: 通过管理后台获取

1. **登录飞书管理后台**
2. **进入"通讯录管理"**
3. **查看用户详情获取用户ID**

## 代码修复建议

### 1. 环境配置更新

创建或更新 `.env` 文件:
```bash
# Feishu Configuration
FEISHU_APP_ID=cli_a751cdd4273d1013
FEISHU_APP_SECRET=16BmEvATAog0tgWaYpRWlbpiilicAvVs
FEISHU_DEFAULT_USER_ID=您的有效用户ID

# 可选：代理配置
# HTTPS_PROXY=http://localhost:8118
# HTTP_PROXY=http://localhost:8118
```

### 2. 用户ID验证增强

现有代码已包含用户ID格式验证，只需配置正确的用户ID即可:

```python
# src/adapters/feishu.py 中的验证逻辑已经完善
@staticmethod
def _is_valid_user_id(user_id: str) -> bool:
    """验证用户ID是否为有效格式"""
    if not user_id:
        return False
    # 检查是否为纯数字且长度合理
    return re.match(r'^\d{10,20}$', user_id) is not None
```

### 3. 错误处理改进

当前代码已包含完善的错误处理和重试机制:
- ✅ 连接超时处理 (30秒)
- ✅ 指数退避重试 (最多3次)
- ✅ 代理自动切换支持
- ✅ 详细的错误日志记录

## 测试验证步骤

### 1. 获取有效用户ID
```bash
python get_feishu_user_id.py
```

### 2. 配置环境变量
```bash
# 编辑 .env 文件
echo "FEISHU_DEFAULT_USER_ID=您的有效用户ID" >> .env
```

### 3. 测试API调用
```bash
# 启动服务
docker-compose up -d

# 测试Feishu消息发送
curl -X POST "http://localhost:18888/notifier/notify_feishu" \
  -H "Content-Type: application/json" \
  -d '{
    "app_id":"cli_a751cdd4273d1013",
    "app_secret":"16BmEvATAog0tgWaYpRWlbpiilicAvVs",
    "message":"测试消息 - API连接正常"
  }'
```

## 权限要求

如需访问用户列表API，应用需要以下权限之一:
- `contact:contact.base:readonly`
- `contact:department.organize:readonly`
- `contact:contact:access_as_app`
- `contact:contact:readonly`
- `contact:contact:readonly_as_app`

**权限申请链接**: https://open.feishu.cn/app/cli_a751cdd4273d1013/auth

## 网络环境配置

### 代理设置 (如需要)
```bash
# 在 .env 文件中配置
HTTPS_PROXY=http://localhost:8118
HTTP_PROXY=http://localhost:8118
NO_PROXY=localhost,127.0.0.1
```

### 防火墙要求
确保可以访问以下域名和端口:
- `open.feishu.cn:443` (HTTPS)
- 如使用代理: `localhost:8118`

## 常见问题解答

**Q: 为什么用户ID格式正确但仍然失败?**  
A: 用户ID格式正确不代表用户存在。需要使用组织内实际存在的用户ID。

**Q: 如何获取当前组织的用户列表?**  
A: 需要应用权限支持，或使用管理员账号通过管理后台查看。

**Q: 连接超时怎么办?**  
A: 代码已支持自动重试和代理切换，如仍有问题可检查网络设置。

**Q: 可以发送消息给群组吗?**  
A: 可以，需要将 `receive_id_type` 改为 `chat_id` 并提供群组ID。

## 诊断工具

项目提供了专用的诊断工具:

1. **`get_feishu_user_id.py`** - 用户ID获取和验证工具
2. **现有的重试机制** - 自动处理网络问题
3. **详细的日志记录** - 便于问题排查

使用这些工具可以快速定位和解决大部分Feishu API问题。

---

**诊断完成时间**: 2025-08-08  
**诊断工具版本**: notify-v1.0  
**API测试状态**: ✅ 认证成功，❌ 用户ID无效