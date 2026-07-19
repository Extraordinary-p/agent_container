from typing import List, Dict, Any
from pydantic import BaseModel

class ToolParameter(BaseModel):
    type: str
    description: str
    enum: List[str] = []

class ToolFunction(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]

class Tool(BaseModel):
    type: str = "function"
    function: ToolFunction

TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "analyze_docker_compose",
            "description": "分析 docker-compose.yml 文件，检查配置问题",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "docker-compose.yml 文件路径"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_all_containers",
            "description": "自动检测所有 NetBox 相关容器的运行状态，发现已停止或频繁重启的问题",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "start_service",
            "description": "启动已停止的 Docker 服务（容器），不重启正在运行的服务",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {
                        "type": "string",
                        "description": "要启动的服务名称或容器名，如 netbox、postgres、redis 等"
                    }
                },
                "required": ["service_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_service_health",
            "description": "检查指定 Docker 服务的健康状态",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {
                        "type": "string",
                        "description": "要检查的服务名称，如 netbox、postgres、redis 等"
                    }
                },
                "required": ["service_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_disk_space",
            "description": "检查系统磁盘空间使用情况，识别空间不足问题",
            "parameters": {
                "type": "object",
                "properties": {
                    "threshold": {
                        "type": "number",
                        "description": "磁盘使用率告警阈值（百分比），默认 85%"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_memory_usage",
            "description": "检查系统内存使用情况，识别内存不足问题",
            "parameters": {
                "type": "object",
                "properties": {
                    "threshold": {
                        "type": "number",
                        "description": "内存使用率告警阈值（百分比），默认 90%"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_container_logs",
            "description": "检查指定容器的日志，查找错误和异常信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "container_name": {
                        "type": "string",
                        "description": "容器名称或ID"
                    },
                    "tail_lines": {
                        "type": "number",
                        "description": "获取最后多少行日志，默认 100 行"
                    }
                },
                "required": ["container_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "restart_service",
            "description": "重启指定的 Docker 服务（仅在确认需要时使用）",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {
                        "type": "string",
                        "description": "要重启的服务名称"
                    }
                },
                "required": ["service_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "prune_docker_resources",
            "description": "清理 Docker 未使用的资源（镜像、容器、网络）",
            "parameters": {
                "type": "object",
                "properties": {
                    "prune_type": {
                        "type": "string",
                        "enum": ["all", "images", "containers", "volumes"],
                        "description": "清理类型"
                    }
                },
                "required": ["prune_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fix_docker_compose",
            "description": "修复 docker-compose.yml 配置文件中的问题",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "docker-compose.yml 文件路径"
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "是否只预览不实际修改"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validate_env_config",
            "description": "验证环境配置文件，检查缺失的变量和无效的配置",
            "parameters": {
                "type": "object",
                "properties": {
                    "env_file": {
                        "type": "string",
                        "description": "环境配置文件路径，默认 .env"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "final_report",
            "description": "生成最终诊断报告，总结发现的问题、诊断建议和已执行的处置动作",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "诊断总结"
                    },
                    "issues_found": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "发现的问题列表"
                    },
                    "recommendations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "修复建议列表"
                    },
                    "actions_taken": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "已执行的处置动作列表"
                    }
                },
                "required": ["summary", "issues_found", "recommendations", "actions_taken"]
            }
        }
    }
]

def get_tools_list() -> List[Dict[str, Any]]:
    return TOOLS
