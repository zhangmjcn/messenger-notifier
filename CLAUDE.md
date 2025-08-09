# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project is a Docker-deployed FastAPI notification service for sending messages to various platforms, primarily:
- Telegram groups
- Feishu (Lark) groups

## Architecture

### Core Components

1. **API Layer**: FastAPI-based RESTful endpoints for message sending
   - Service runs on port 18888
   - Uses notifier router group for organized API endpoints
   - `/notifier/notify_telegram` - Send messages to Telegram groups
   - `/notifier/notify_feishu` - Send messages to Feishu groups
   - Health check endpoints for monitoring

2. **Message Adapters**: Platform-specific implementations
   - `src/adapters/telegram.py` - Telegram Bot API integration
   - `src/adapters/feishu.py` - Feishu Open API integration with token-based authentication

3. **Configuration Management**: Multi-layer configuration system with priority levels
   - `.env` file configuration (highest priority)
   - docker-compose.yml environment variables (medium priority)
   - env_for_docker default configuration (lowest priority)

4. **Docker Deployment**
   - FastAPI service exposed on port 18888
   - Python source code in /src directory
   - Data persistence through /data directory mapping
   - Health checks and auto-restart policies

### Key Design Patterns

- **Adapter Pattern**: Each messaging platform has its own adapter implementation
- **Router Groups**: FastAPI router groups for organized API endpoint management
- **Multi-layer Configuration**: Hierarchical configuration system with environment priority
- **Logging System**: Using loguru for comprehensive logging across all components
- **Error Handling**: Centralized error handling with proper logging
- **Rate Limiting**: Built-in rate limiting for each platform's API

## Development Commands

### Environment Setup
```bash
# Using uv (recommended for development)
uv venv
source .venv/bin/activate  # Linux/Mac

# Install dependencies with uv
uv pip install fastapi uvicorn loguru python-telegram-bot requests pydantic python-dotenv

# Or using traditional pip
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

### Running Locally
```bash
# Start the API server using uv (for testing)
uv run src/main.py

# Or start with uvicorn
uvicorn src.main:app --host 0.0.0.0 --port 18888

# Or using Docker
docker-compose up --build
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_telegram.py

# Run with coverage
pytest --cov=src --cov-report=html
```

### Docker Operations
```bash
# Build Docker image
docker build -t notify-api:latest .

# Run container
docker run -p 18888:18888 --env-file .env notify-api:latest

# Using docker-compose
docker-compose up -d  # Start in detached mode
docker-compose down   # Stop and remove containers
docker-compose logs -f  # View logs
```

### Code Quality
```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## Configuration

### Environment Variables
Configuration follows priority order (.env > docker-compose.yml > env_for_docker defaults):
- `TELEGRAM_BOT_TOKEN` - Telegram bot token (必需)
- `TELEGRAM_DEFAULT_GROUP_ID` - Default telegram group ID (default: -868155406)
- `FEISHU_APP_ID` - Feishu application ID (可选，用于默认配置)
- `FEISHU_APP_SECRET` - Feishu application secret (可选，用于默认配置)
- `FEISHU_DEFAULT_USER_ID` - Default Feishu target user ID (可选)
- `API_PORT` - API server port (default: 18888)
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)

**重要配置说明**：
- **Telegram**: 需要在.env中配置`TELEGRAM_BOT_TOKEN`，这是必需的配置项
- **Feishu**: 当前API设计要求通过查询参数传递`app_id`和`app_secret`，支持动态凭据管理
  - .env中的`FEISHU_APP_ID`和`FEISHU_APP_SECRET`为可选配置（用于其他用途或将来扩展）
  - **注意**: 如需实现凭据从.env自动读取，需要进一步的API设计调整
- **默认值**: 所有平台都支持配置默认目标（群组ID或用户ID），简化API调用

**API演进计划**：
当前Feishu API需要在查询参数中传递凭据。如果需要实现凭据自动从.env读取的功能，可以考虑：
1. 修改API设计，使app_id和app_secret参数变为可选
2. 当查询参数未提供时，自动从环境变量读取凭据  
3. 这样既保持API灵活性，又支持简化的使用方式

**配置示例(.env文件)**：
```bash
# 必需配置 - Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_DEFAULT_GROUP_ID=-868155406

# 可选配置 - Feishu默认值
FEISHU_DEFAULT_USER_ID=6421712345678901234

# 服务配置
API_PORT=18888
LOG_LEVEL=INFO

# 代理配置（如果需要）
# HTTP_PROXY=http://proxy.company.com:8080
# HTTPS_PROXY=https://proxy.company.com:8080
# VERIFY_SSL=true
```

### API Endpoints

#### Send Telegram Message
```bash
POST /notifier/notify_telegram?group_id=-868155406
Content-Type: text/plain

你好
```

**参数说明**：
- `group_id` (查询参数，可选): Telegram群组ID，默认值从环境变量`TELEGRAM_DEFAULT_GROUP_ID`获取
- Request Body: 纯文本消息内容，默认值为"你好"

**使用示例**：
```bash
# 使用默认群组发送默认消息
curl -X POST "http://localhost:18888/notifier/notify_telegram" \
  -H "Content-Type: text/plain" \
  -d "你好"

# 指定群组ID发送自定义消息
curl -X POST "http://localhost:18888/notifier/notify_telegram?group_id=-123456789" \
  -H "Content-Type: text/plain" \
  -d "自定义消息内容"
```

#### Send Feishu Message
```bash
POST /notifier/notify_feishu?app_id=your_app_id&app_secret=your_app_secret&receive_id=user_id
Content-Type: text/plain

你好
```

**参数说明**：
- `app_id` (查询参数，必需): Feishu应用ID
- `app_secret` (查询参数，必需): Feishu应用密钥  
- `receive_id` (查询参数，可选): 接收方用户ID，默认值从环境变量`FEISHU_DEFAULT_USER_ID`获取
- Request Body: 纯文本消息内容，默认值为"你好"

**使用示例**：
```bash
# 发送消息到指定用户
curl -X POST "http://localhost:18888/notifier/notify_feishu?app_id=cli_xxxxx&app_secret=yyyyyyy&receive_id=6421712345678901234" \
  -H "Content-Type: text/plain" \
  -d "飞书消息内容"

# 使用默认用户ID（如果已在环境变量中配置）
curl -X POST "http://localhost:18888/notifier/notify_feishu?app_id=cli_xxxxx&app_secret=yyyyyyy" \
  -H "Content-Type: text/plain" \
  -d "使用默认用户的消息"
```

**API设计优势**：
- **统一消息格式**: 所有平台都使用text/plain body，简化消息发送
- **灵活凭据管理**: Feishu支持查询参数传递凭据，适应不同部署场景
- **智能默认值**: 支持环境变量默认配置，简化常用场景的API调用
- **便于测试**: 查询参数设计便于在Swagger UI和curl中测试
- **向后兼容**: 保持现有配置方式，确保部署无缝迁移

**API实现细节**：

**notify_telegram**:
- 接收`text/plain`格式的request body作为消息内容
- 通过查询参数`group_id`指定目标群组，支持默认值机制
- 使用Telegram Bot API发送消息到指定群组
- 返回标准化响应格式，包含消息ID和时间戳信息
- 支持消息内容验证和错误处理

**notify_feishu**:
- 接收`text/plain`格式的request body作为消息内容  
- 通过查询参数传递必需的`app_id`和`app_secret`凭据
- 支持可选的`receive_id`参数，可使用环境变量默认值
- 两步API调用流程：
  1. 获取tenant access token: `https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal`
  2. 发送消息: `https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=user_id`
- 智能ID处理逻辑：优先使用查询参数 > 环境变量默认值 > 报错
- 返回标准化响应格式，包含消息ID和时间戳信息

**新API设计特性**：
- **简化的消息传递**: 统一使用text/plain body，消除JSON包装的复杂性
- **灵活的凭据管理**: Feishu API支持每次请求传递不同凭据，适应多租户场景
- **智能默认值处理**: 所有可选参数都有合理的默认值机制
- **标准化响应格式**: 统一的API响应结构，便于客户端处理
- **完善的错误处理**: 详细的参数验证和错误消息，提高API易用性

## Project Structure Guidelines

```
notify/
├── src/
│   ├── adapters/       # Platform-specific message adapters
│   │   ├── telegram.py # Telegram Bot API integration
│   │   └── feishu.py   # Feishu Open API integration
│   ├── routers/        # FastAPI router groups
│   │   └── notifier.py # Notifier router group
│   ├── config/         # Configuration management
│   │   └── settings.py # Multi-layer configuration handling
│   ├── utils/          # Utility functions
│   └── main.py         # FastAPI application entry point
├── data/               # Docker-mapped data directory
├── tests/              # Test files
├── .env.example        # Example environment variables
├── .env                # Actual environment variables (git-ignored)
├── env_for_docker      # Default Docker environment variables
├── docker-compose.yml  # Docker Compose configuration (port 18888)
├── Dockerfile          # Docker build instructions
├── requirements.txt    # Python dependencies
└── pyproject.toml     # uv project configuration
```

## Important Notes

1. **Security**: Never commit `.env` files or expose API tokens in code
2. **Rate Limiting**: Respect platform API rate limits (Telegram: 30 msgs/sec, Feishu: varies by tier)
3. **Error Handling**: All API calls should have proper error handling and retry logic
4. **Logging**: Use structured logging for better debugging in production
5. **Testing**: Write tests for new adapters and API endpoints before deployment

## Deployment Checklist

Before deploying to production:
1. Ensure all environment variables are configured
2. Run full test suite
3. Build and test Docker image locally
4. Verify health check endpoints are working
5. Configure proper logging and monitoring
6. Set up rate limiting based on platform requirements
7. Implement proper authentication for API endpoints

## Claude Code 工作流程 - 调度员角色

### 角色定义
Claude Code 在此项目中扮演**任务调度员**的角色，负责：
- 接收和理解用户需求
- 将复杂任务分解为具体的子任务
- 合理调度各种专业子代理(SubAgents)完成任务
- 确保任务质量和完成度

**重要原则：Claude本身不直接处理具体的编程任务，而是作为调度员将任务分配给最适合的SubAgent执行。**

### 子代理调度策略
当面对编程任务时，遵循以下调度原则：

1. **选择最适合的子代理**
   - 优先选择对当前问题最有针对性的SubAgent
   - 避免使用过于通用的代理处理专业问题
   - 根据任务类型匹配相应专业能力
   - **禁止Claude直接编写代码、修改文件或执行具体实现任务**

2. **任务执行流程**
   ```
   用户需求 → 任务分析 → 选择子代理 → SubAgent执行任务 → 测试验证 → 问题修复 → 完成确认
   ```

3. **质量控制循环**
   - 编码/配置任务完成后，必须调度debug-environment-manager进行验证
   - 如果测试未通过，重新分配任务给相应代理解决问题
   - 重复此过程直至问题完全解决并通过验证

4. **任务分工明确**
   - Claude仅负责：任务理解、分解、代理选择、进度跟踪
   - SubAgent负责：具体代码编写、文件修改、配置更新、测试执行
   - 严格遵循"调度不执行"的原则

### 子代理类型和用途

1. **code-writer-optimizer**: 编写新代码或优化现有代码
   - 专注于代码质量和简洁性
   - 适用于功能实现、重构等任务

2. **architecture-maintainer**: 维护项目架构和设计
   - 确保设计一致性
   - 验证实现是否符合架构决策

3. **debug-environment-manager**: 管理调试和测试环境
   - 启动/停止测试环境
   - 快速验证代码功能

4. **network-operations-specialist**: 处理网络相关操作
   - API调用、数据获取
   - 网络连接问题排查

### 任务质量标准

每个任务完成必须满足：
- ✅ 功能正确实现
- ✅ 代码风格符合项目规范
- ✅ 通过相关测试验证
- ✅ 符合架构设计要求
- ✅ 包含必要的文档说明

### 验证和测试要求

所有测试和验证工作必须通过SubAgent执行，Claude不直接运行命令：

1. **自动化测试**: 调度debug-environment-manager使用 `pytest` 运行相关测试
2. **代码质量检查**: 调度code-writer-optimizer执行：
   - `black src/ tests/` - 代码格式化
   - `flake8 src/ tests/` - 代码风格检查
   - `mypy src/` - 类型检查
3. **功能测试**: 调度debug-environment-manager启动服务并验证API端点功能
4. **集成测试**: 调度network-operations-specialist验证与外部服务(Telegram、Feishu)的集成

### SubAgent调度禁令

**严格禁止Claude执行以下操作：**
- 直接使用Edit、Write、MultiEdit等工具修改代码
- 直接使用Bash工具执行命令
- 直接进行文件操作或配置更改
- 绕过SubAgent直接完成实现任务

**Claude只能使用以下工具进行调度：**
- Task工具：调度SubAgent执行具体任务
- Read、Glob、Grep工具：了解项目结构和需求
- TodoWrite工具：跟踪任务进度