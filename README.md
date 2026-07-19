# NetBox Docker AIOps Agent - Tool Calling 智能运维系统

## 项目简介

这是一个基于 **Tool Calling** 架构的智能运维 Agent，专门为 NetBox Docker 环境设计的自动化运维解决方案。实现了从「异常发现」→「诊断分析」→「自动处置」的完整闭环运维流程。

**✨ 核心特性**
- 🤖 支持国内主流大模型（豆包、通义千问、智谱AI、DeepSeek）
- 🔄 零依赖检测模式，无需 API Key 即可运行
- 🛠️ 10+ 内置运维工具，支持自动诊断与修复
- 🎯 针对 NetBox 生态的专属优化

---

## 支持的模型提供商

| 模型提供商 | 配置名称 | 官方文档 |
|-----------|---------|---------|
| 豆包 (火山引擎) | `doubao` | https://www.volcengine.com/product/ark |
| 通义千问 (阿里云) | `qwen` | https://help.aliyun.com/product/154921.html |
| 智谱AI | `zhipu` | https://open.bigmodel.cn/dev/api |
| DeepSeek | `deepseek` | https://platform.deepseek.com/docs |
| OpenAI | `openai` | https://platform.openai.com/docs |
| 自定义兼容模型 | `custom` | 任意兼容 OpenAI API 的模型 |

---

## 架构设计

```
┌─────────────────────────────────────────────────────────────────────┐
│              Tool Calling Agent 智能运维闭环系统                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐     ┌───────────────┐     ┌──────────────────┐   │
│  │  异常发现    │     │   诊断分析     │     │    自动处置      │   │
│  │   (Detector) │────▶│   (Engine)     │────▶│  (Remediation)   │   │
│  └──────────────┘     └───────────────┘     └──────────────────┘   │
│         │                     │                       │            │
│         └─────────────────────┴───────────────────────┘            │
│                              ▲                                      │
│                              │                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   多模型适配层                                │   │
│  │    豆包 | 通义千问 | 智谱AI | DeepSeek | OpenAI | 自定义     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 核心功能

### 🔍 1. 异常发现 (Anomaly Detection)
- ✅ Docker 容器状态检测（运行/停止/重启）
- ✅ 磁盘空间使用率检测
- ✅ 系统内存使用率检测
- ✅ 配置文件完整性校验
- ✅ Docker 网络连通性检测
- ✅ 服务频繁重启异常检测
- ✅ NetBox 核心服务健康检查

### 🧠 2. 诊断分析 (Diagnostic Engine)
- ✅ 智能问题模式匹配
- ✅ 严重程度分级（critical/high/medium/low）
- ✅ 根因分析（RCA）
- ✅ 修复建议智能生成
- ✅ 问题优先级排序

### 🛠️ 3. Tool Calling 工具集（11 个工具）

| 工具名称 | 功能描述 |
|---------|---------|
| `analyze_docker_compose` | 分析 docker-compose 配置完整性 |
| `check_service_health` | 检查 Docker 服务健康状态 |
| `check_disk_space` | 检查磁盘空间使用情况 |
| `check_memory_usage` | 检查系统内存使用情况 |
| `inspect_container_logs` | 智能分析容器日志，定位错误 |
| `restart_service` | 重启指定服务（自动修复） |
| `prune_docker_resources` | 清理 Docker 未使用资源（自动修复） |
| `validate_env_config` | 验证环境配置文件 |
| `check_network_connectivity` | 检查容器间网络连通性 |
| `fix_config_issues` | 自动修复配置问题 |
| `final_report` | 生成结构化最终诊断报告 |

### ⚡ 4. 自动处置 (Remediation Engine)
- ✅ 安全动作自动执行
- ✅ 危险动作条件判断与提示
- ✅ 智能重试机制
- ✅ 操作审计日志
- ✅ 修复工作流编排

---

## 快速开始

### 前置要求
- Docker 及 Docker Compose
- Python 3.8+
- NetBox Docker 环境（可选，支持检测本地运行的 NetBox）

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量（AI 模式需要）

```bash
cp .env.example .env
# 编辑 .env 文件，配置你的模型提供商和 API Key
```

`.env` 配置示例：
```ini
# 选择模型提供商: openai, doubao, qwen, zhipu, deepseek, custom
PROVIDER=doubao

# 豆包配置示例
DOUBao_API_KEY=your-doubao-api-key-here
DOUBao_MODEL=doubao-pro-32k
DOUBao_BASE_URL=https://ark.cn-beijing.volces.com/api/v3

# 自动修复开关
ENABLE_AUTO_REMEDIATION=true
```

### 3. 运行 Agent

#### 🚀 模式 A: 完整闭环检测（零依赖，无需 API Key）

```bash
python main.py --mode full
```

#### 🤖 模式 B: AI Agent 驱动的 Tool Calling（需要配置 API Key）

```bash
# 使用 .env 中配置的模型
python main.py --mode ai

# 命令行指定模型提供商
python main.py --mode ai --provider doubao
python main.py --mode ai --provider qwen
python main.py --mode ai --provider zhipu

# 完全自定义配置
python main.py --mode ai --provider custom \
  --api-key your-api-key \
  --base-url https://your-api-endpoint.com/v1 \
  --model your-model-name
```

#### 🔧 模式 C: 手动检测指定服务

```bash
python main.py --mode manual --service netbox
```

---

## 命令行参数详解

| 参数 | 说明 | 可选值 |
|------|------|--------|
| `--mode` | 运行模式 | `full` / `ai` / `manual` |
| `--provider` | 模型提供商 | `openai` / `doubao` / `qwen` / `zhipu` / `deepseek` / `custom` |
| `--api-key` | API Key | 字符串 |
| `--base-url` | API 基础地址 | URL 字符串 |
| `--model` | 模型名称 | 字符串 |
| `--auto-remediate` | 启用自动修复 | 开关 |
| `--no-auto-remediate` | 禁用自动修复 | 开关 |

---

## 运行示例

```
================================================================================
          NetBox Docker AIOps Agent - 完整异常处理闭环演示
================================================================================

[阶段 1] 异常发现 - 正在检查系统状态...
  ✓ 检测到 2 个异常
    1. 容器 netbox-docker-netbox-1 状态异常: exited
    2. 磁盘 / 使用过高: 87.3%

[阶段 2] 诊断分析 - 正在分析异常原因...
  ✓ 分析摘要: 发现 1 个高优先级问题，建议尽快修复
    - 严重问题: 0 个
    - 高优先级: 1 个
    - 中优先级: 1 个

[阶段 3] 自动处置 - 执行修复动作...
  处理问题: 容器 netbox-docker-netbox-1 状态异常: exited
    ✓ inspect_container_logs - 执行成功
    ✓ validate_env_config - 执行成功
    ✓ restart_service - 执行成功

[阶段 4] 生成最终报告...
================================================================================
                          最终诊断报告
================================================================================
```

---

## 项目文件结构

```
Agent_tools_project_version1/
├── agent_core/                    # 🧠 Agent 核心模块
│   ├── __init__.py
│   ├── agent.py                  # AI Agent 主逻辑（多模型支持）
│   ├── anomaly_detector.py       # 异常发现引擎
│   ├── diagnostic_engine.py      # 诊断分析引擎
│   └── remediation_engine.py     # 自动处置引擎
│
├── tools/                         # 🛠️ Tool Calling 工具集
│   ├── __init__.py
│   ├── tool_definitions.py       # 工具定义（OpenAI Function 格式）
│   ├── tool_executor.py          # 工具执行器
│   ├── docker_monitor.py         # Docker 监控工具
│   ├── config_fixer.py           # 配置自动修复
│   └── fix_rules.py              # 修复规则库
│
├── config/                        # ⚙️ 配置管理
│   ├── __init__.py
│   └── settings.py               # 多模型配置管理
│
├── utils/                         # 🔧 工具函数
│
├── main.py                        # 🚀 主入口程序
├── simple_run.py                  # 简化运行脚本
├── simple_docker_check.py         # Docker 检查脚本
├── fault_injection_test.py        # 故障注入测试
├── test_auto_fix.py               # 自动修复测试
├── requirements.txt               # 📦 Python 依赖
├── .env.example                   # 环境变量示例
├── .env                           # 本地环境配置
│
├── netbox-docker/                 # 📦 NetBox Docker 环境（子目录）
│
├── TEST_REPORT.md                 # 📊 测试报告
├── TEST_REPORT_AI_AGENT.md        # 🤖 AI Agent 测试报告
└── FAULT_TESTING_GUIDE.md         # 📖 故障测试指南
```

---

## Tool Calling 工作原理

1. **系统提示词**: 定义 Agent 的角色、职责和工作流程
2. **工具定义**: 以 OpenAI Function Calling 标准格式定义所有可用工具
3. **LLM 决策**: 大模型根据当前上下文智能决定调用哪个工具
4. **工具执行**: 安全执行具体的检查或处置动作
5. **结果反馈**: 将工具执行结果结构化返回给 LLM
6. **迭代循环**: 重复决策-执行过程，直到问题解决或达到最大迭代次数
7. **报告生成**: 生成结构化的最终诊断报告

---

## 安全特性

- 🛡️ **动作分级**: 安全动作 / 条件动作 / 危险动作三级分类
- 🔄 **自动重试**: 失败操作智能重试机制
- 📝 **审计日志**: 所有操作完整记录
- ⚙️ **可配置**: 自动修复功能可通过开关控制
- ✋ **人工确认**: 危险操作需要人工确认

---

## NetBox Docker 专属优化

- 🎯 **服务识别**: 专门识别 NetBox 核心服务（netbox/postgres/redis/nginx/valkey）
- 🔍 **专属诊断**: 针对 NetBox 常见配置问题的诊断逻辑
- 📋 **配置分析**: Docker Compose 配置深度分析
- ✅ **环境验证**: NetBox 关键环境变量验证（POSTGRES_PASSWORD, NETBOX_SECRET_KEY 等）

---

## 测试与验证

项目包含完整的测试套件：
- `fault_injection_test.py` - 故障注入测试
- `test_auto_fix.py` - 自动修复功能测试
- `simple_docker_check.py` - 基础 Docker 环境检查

详细测试报告请查看：
- [TEST_REPORT.md](./TEST_REPORT.md)
- [TEST_REPORT_AI_AGENT.md](./TEST_REPORT_AI_AGENT.md)
- [FAULT_TESTING_GUIDE.md](./FAULT_TESTING_GUIDE.md)

---

## 注意事项

1. AI Agent 模式需要有效的 API Key
2. 自动处置功能默认开启，可通过 `--no-auto-remediate` 禁用
3. 国内模型需要使用兼容 OpenAI API 的接入方式
4. 建议在非生产环境先进行充分测试

---

## 许可证

MIT License
