# NetBox Docker AIOps Agent - Tool Calling 智能运维系统

## 项目简介

这是一个真正具备 Tool Calling 结构的智能运维 Agent，专门针对 NetBox Docker 环境设计。实现了从"异常发现"到"诊断分析"再到"自动处置"的完整闭环。

**支持国内模型**：豆包、通义千问、智谱AI、DeepSeek 等兼容 OpenAI API 的模型。

## 支持的模型提供商

| 模型提供商 | 配置名称 | 官方文档 |
|-----------|---------|---------|
| 豆包 (火山引擎) | `doubao` | https://www.volcengine.com/product/ark |
| 通义千问 (阿里云) | `qwen` | https://help.aliyun.com/product/154921.html |
| 智谱AI | `zhipu` | https://open.bigmodel.cn/dev/api |
| DeepSeek | `deepseek` | https://platform.deepseek.com/docs |
| OpenAI | `openai` | https://platform.openai.com/docs |
| 自定义模型 | `custom` | 任意兼容 OpenAI API 的模型 |

## 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                     Tool Calling Agent 闭环                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐    │
│  │  异常发现   │    │  诊断分析    │    │   自动处置      │    │
│  │  (Detector) │───▶│   (Engine)   │───▶│ (Remediation)   │    │
│  └─────────────┘    └──────────────┘    └─────────────────┘    │
│         │                    │                      │           │
│         └────────────────────┴──────────────────────┘           │
│                           ▲                                      │
│                           │                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │   模型层 (支持国内模型)                                  │   │
│  │   豆包 | 通义千问 | 智谱AI | DeepSeek | 自定义           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 核心功能

### 1. 异常发现 (Anomaly Detection)
- ✅ 磁盘空间检测
- ✅ 内存使用率检测
- ✅ 容器状态检测
- ✅ 配置文件完整性检测
- ✅ Docker 网络检测
- ✅ 服务频繁重启检测

### 2. 诊断分析 (Diagnostic Engine)
- ✅ 问题模式匹配
- ✅ 严重程度分级 (critical/high/medium/low)
- ✅ 根因分析
- ✅ 修复建议生成
- ✅ 优先级排序

### 3. Tool Calling 工具集 (10+ 工具)

| 工具名称 | 功能描述 |
|---------|---------|
| `analyze_docker_compose` | 分析 docker-compose 配置 |
| `check_service_health` | 检查 Docker 服务健康状态 |
| `check_disk_space` | 检查磁盘空间使用情况 |
| `check_memory_usage` | 检查系统内存使用情况 |
| `inspect_container_logs` | 检查容器日志查找错误 |
| `restart_service` | 重启指定服务（自动修复） |
| `prune_docker_resources` | 清理 Docker 未使用资源（自动修复） |
| `validate_env_config` | 验证环境配置文件 |
| `check_network_connectivity` | 检查容器间网络连通性 |
| `final_report` | 生成最终诊断报告 |

### 4. 自动处置 (Remediation Engine)
- ✅ 安全动作自动执行
- ✅ 危险动作条件判断
- ✅ 重试机制
- ✅ 动作记录审计
- ✅ 工作流编排

## 安装与使用

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

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

#### 模式 A: 完整闭环检测（无需 API Key）

```bash
python main.py --mode full
```

#### 模式 B: AI Agent 驱动的 Tool Calling（需要配置 API Key）

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

#### 模式 C: 手动检测指定服务

```bash
python main.py --mode manual --service netbox
```

## 命令行参数

```
--mode: 运行模式 (full/ai/manual)
--provider: 模型提供商 (openai/doubao/qwen/zhipu/deepseek/custom)
--api-key: API Key
--base-url: API 地址
--model: 模型名称
--auto-remediate: 启用自动修复
--no-auto-remediate: 禁用自动修复
```

## 运行示例

```
================================================================================
NetBox Docker AIOps Agent - 完整异常处理闭环演示
================================================================================

[阶段 1] 异常发现 - 正在检查系统状态...
  - 检测到 2 个异常
    1. 容器 netbox-docker-netbox-1 状态异常: exited
    2. 磁盘 / 使用过高: 87.3%

[阶段 2] 诊断分析 - 正在分析异常原因...
  - 分析摘要: 发现 1 个高优先级问题，建议尽快修复
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

## 项目文件结构

```
netbox-aiops-agent/
├── agent_core/              # Agent 核心模块
│   ├── __init__.py
│   ├── agent.py            # AI Agent 主逻辑 (支持多模型)
│   ├── anomaly_detector.py # 异常发现模块
│   ├── diagnostic_engine.py # 诊断分析引擎
│   └── remediation_engine.py # 自动处置引擎
├── tools/                   # Tool Calling 工具
│   ├── __init__.py
│   ├── tool_definitions.py  # 10+ 工具定义
│   └── tool_executor.py    # 工具执行器
├── config/                  # 配置管理
│   ├── __init__.py
│   └── settings.py         # 多模型配置
├── utils/                   # 工具函数
├── main.py                  # 主入口
├── demo.py                  # 演示脚本
├── requirements.txt         # 依赖清单
├── .env.example            # 环境变量示例
└── README.md                # 项目文档
```

## Tool Calling 工作原理

1. **系统提示词**: 定义 Agent 的角色、职责和工作流程
2. **工具定义**: 以 OpenAI Function Calling 格式定义所有可用工具
3. **LLM 决策**: LLM 根据当前上下文决定调用哪个工具
4. **工具执行**: 执行具体的检查或处置动作
5. **结果反馈**: 将工具执行结果返回给 LLM
6. **迭代循环**: 重复直到问题解决或达到最大迭代次数
7. **报告生成**: 生成最终诊断报告

## 安全特性

- 动作分级：安全动作 / 条件动作 / 危险动作
- 自动重试机制
- 执行审计日志
- 可配置的自动修复开关

## 针对 NetBox Docker 的优化

- 专门识别 NetBox 核心服务（netbox/postgres/redis/nginx）
- 针对 NetBox 常见配置问题的诊断逻辑
- Docker Compose 配置分析
- 环境变量验证（POSTGRES_PASSWORD, NETBOX_SECRET_KEY 等）

## 注意事项

1. AI Agent 模式需要有效的 API Key
2. 自动处置功能默认开启，可通过 `--no-auto-remediate` 禁用
3. 国内模型需要使用兼容 OpenAI API 的接入方式
4. 建议在非生产环境先测试运行

## 许可证

MIT License
