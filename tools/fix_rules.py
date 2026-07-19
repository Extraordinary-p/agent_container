"""
配置修复规则中心
==================
所有的检测规则和修复动作都集中在这里定义
便于查看、修改和扩展

规则格式:
{
    "id": "唯一标识",
    "name": "规则名称",
    "description": "规则描述",
    "severity": "low|medium|high|critical",  # 严重程度
    "safe": True|False,                      # 是否安全（自动执行）
    "detect": func(content) -> issues,      # 检测逻辑
    "fix": func(content, issue) -> content, # 修复逻辑
}
"""
import re
from typing import List, Dict, Any, Tuple, Callable

# ============================================================
# 1. docker-compose.yml 修复规则
# ============================================================

def _dc_detect_missing_restart(lines: List[str]) -> List[str]:
    """检测缺少 restart 策略的服务"""
    issues = []
    current_service = None
    has_restart = False
    
    service_pattern = re.compile(r'^\s{2}([a-zA-Z0-9_-]+):\s*$')
    restart_pattern = re.compile(r'^\s{4}restart:')
    
    for line in lines:
        service_match = service_pattern.match(line)
        if service_match:
            if current_service and not has_restart:
                issues.append(f"服务 {current_service} 缺少 restart 策略")
            current_service = service_match.group(1)
            has_restart = False
            continue
        
        if current_service and restart_pattern.match(line):
            has_restart = True
        
        if current_service and re.match(r'^[^ ]', line):
            if not has_restart:
                issues.append(f"服务 {current_service} 缺少 restart 策略")
            current_service = None
    
    if current_service and not has_restart:
        issues.append(f"服务 {current_service} 缺少 restart 策略")
    
    return issues

def _dc_fix_missing_restart(lines: List[str], issue: str) -> Tuple[List[str], str]:
    """为服务添加 restart: always"""
    service_name = issue.split("服务 ")[1].split(" 缺少")[0]
    
    service_pattern = re.compile(rf'^\s{{2}}{service_name}:\s*$')
    new_lines = []
    i = 0
    fixed = False
    
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        
        if service_pattern.match(line):
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                if re.match(r'^\s{4}\S', next_line):
                    new_lines.append(f"    restart: always\n")
                    fixed = True
                    break
                if re.match(r'^\s{2}[a-zA-Z0-9_-]+:', next_line):
                    new_lines.append(f"    restart: always\n")
                    fixed = True
                    break
                j += 1
            i = j - 1
        i += 1
    
    if fixed:
        return new_lines, f"为服务 {service_name} 添加了 restart: always"
    return lines, ""

def _dc_detect_missing_healthcheck(lines: List[str]) -> List[str]:
    """检测缺少 healthcheck 的服务"""
    issues = []
    current_service = None
    has_healthcheck = False
    
    service_pattern = re.compile(r'^\s{2}([a-zA-Z0-9_-]+):\s*$')
    check_pattern = re.compile(r'^\s{4}healthcheck:')
    
    important_services = ['netbox', 'nginx', 'postgres', 'redis']
    
    for line in lines:
        service_match = service_pattern.match(line)
        if service_match:
            if current_service and not has_healthcheck and current_service in important_services:
                issues.append(f"服务 {current_service} 缺少健康检查配置")
            current_service = service_match.group(1)
            has_healthcheck = False
            continue
        
        if current_service and check_pattern.match(line):
            has_healthcheck = True
        
        if current_service and re.match(r'^[^ ]', line):
            if not has_healthcheck and current_service in important_services:
                issues.append(f"服务 {current_service} 缺少健康检查配置")
            current_service = None
    
    if current_service and not has_healthcheck and current_service in important_services:
        issues.append(f"服务 {current_service} 缺少健康检查配置")
    
    return issues

def _dc_fix_missing_healthcheck(lines: List[str], issue: str) -> Tuple[List[str], str]:
    """为服务添加健康检查"""
    service_name = issue.split("服务 ")[1].split(" 缺少")[0]
    
    # 根据服务类型生成不同的健康检查
    healthcheck_configs = {
        'netbox': """    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8080/ || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3\n""",
        'nginx': """    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:80/ || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3\n""",
        'postgres': """    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U netbox"]
      interval: 10s
      timeout: 5s
      retries: 5\n""",
        'redis': """    healthcheck:
      test: ["CMD-SHELL", "redis-cli ping || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5\n"""
    }
    
    config = healthcheck_configs.get(service_name, healthcheck_configs['netbox'])
    service_pattern = re.compile(rf'^\s{{2}}{service_name}:\s*$')
    new_lines = []
    i = 0
    fixed = False
    
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        
        if service_pattern.match(line):
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                if re.match(r'^\s{4}\S', next_line):
                    new_lines.append(config)
                    fixed = True
                    break
                j += 1
            i = j - 1
        i += 1
    
    if fixed:
        return new_lines, f"为服务 {service_name} 添加了健康检查配置"
    return lines, ""

# ============================================================
# 2. .env 文件修复规则
# ============================================================

def _env_detect_missing_vars(lines: List[str]) -> List[str]:
    """检测缺失的必需环境变量"""
    required_vars = [
        'POSTGRES_PASSWORD',
        'POSTGRES_DB',
        'NETBOX_SECRET_KEY',
        'SUPERUSER_PASSWORD',
    ]
    
    existing_vars = set()
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key = line.split('=')[0].strip()
            existing_vars.add(key)
    
    issues = []
    for req_var in required_vars:
        if req_var not in existing_vars:
            issues.append(f"缺少必需的环境变量: {req_var}")
    
    return issues

def _env_fix_missing_vars(lines: List[str], issue: str) -> Tuple[List[str], str]:
    """添加缺失的环境变量"""
    var_name = issue.split(": ")[1].strip()
    
    default_values = {
        'POSTGRES_PASSWORD': 'NetBoxPassword123',
        'POSTGRES_DB': 'netbox',
        'NETBOX_SECRET_KEY': 'GenerateARandomStringHereMinimum50Chars',
        'SUPERUSER_PASSWORD': 'admin',
    }
    
    if lines and not lines[-1].endswith('\n'):
        lines.append('\n')
    
    lines.append(f"\n# Auto-added by AIOps Agent\n")
    lines.append(f"{var_name}={default_values.get(var_name, 'changeme')}\n")
    
    return lines, f"添加了环境变量 {var_name}"

# ============================================================
# 3. 常用端口配置检测
# ============================================================

def _dc_detect_port_exposure(lines: List[str]) -> List[str]:
    """检测重要服务是否暴露了端口"""
    issues = []
    
    # 检查 nginx 是否暴露 80 端口
    nginx_found = False
    nginx_has_ports = False
    in_nginx = False
    
    for line in lines:
        if re.match(r'^\s{2}nginx:', line):
            nginx_found = True
            in_nginx = True
            continue
        
        if in_nginx and re.match(r'^\s{4}ports:', line):
            nginx_has_ports = True
            break
        
        if in_nginx and re.match(r'^\s{2}[a-zA-Z0-9_-]+:', line):
            break
    
    if nginx_found and not nginx_has_ports:
        issues.append("nginx 服务未配置端口映射（需要 80 端口）")
    
    return issues

def _dc_fix_port_exposure(lines: List[str], issue: str) -> Tuple[List[str], str]:
    """为 nginx 添加端口映射"""
    service_pattern = re.compile(r'^\s{2}nginx:\s*$')
    new_lines = []
    i = 0
    fixed = False
    
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        
        if service_pattern.match(line):
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                if re.match(r'^\s{4}\S', next_line):
                    new_lines.append("""    ports:
      - "80:80"\n""")
                    fixed = True
                    break
                j += 1
            i = j - 1
        i += 1
    
    if fixed:
        return new_lines, "为 nginx 添加了端口映射 80:80"
    return lines, ""

# ============================================================
# 所有修复规则的注册表
# ============================================================

DOCKER_COMPOSE_RULES = [
    {
        "id": "docker_compose_restart_policy",
        "name": "添加 restart 策略",
        "description": "为缺少 restart 配置的服务添加 always 策略",
        "category": "docker_compose",
        "severity": "medium",
        "safe": True,
        "auto_apply": True,
        "detect": _dc_detect_missing_restart,
        "fix": _dc_fix_missing_restart,
    },
    {
        "id": "docker_compose_healthcheck",
        "name": "添加健康检查",
        "description": "为 netbox/nginx/postgres/redis 添加 healthcheck 配置",
        "category": "docker_compose",
        "severity": "medium",
        "safe": True,
        "auto_apply": True,
        "detect": _dc_detect_missing_healthcheck,
        "fix": _dc_fix_missing_healthcheck,
    },
    {
        "id": "docker_compose_ports",
        "name": "添加端口映射",
        "description": "为 nginx 添加 80 端口映射",
        "category": "docker_compose",
        "severity": "high",
        "safe": True,
        "auto_apply": True,
        "detect": _dc_detect_port_exposure,
        "fix": _dc_fix_port_exposure,
    },
]

ENV_FILE_RULES = [
    {
        "id": "env_missing_vars",
        "name": "添加必需环境变量",
        "description": "添加 NetBox 必需的环境变量配置",
        "category": "env",
        "severity": "critical",
        "safe": True,
        "auto_apply": True,
        "detect": _env_detect_missing_vars,
        "fix": _env_fix_missing_vars,
    },
]

ALL_RULES = DOCKER_COMPOSE_RULES + ENV_FILE_RULES

# ============================================================
# 规则查询接口
# ============================================================

def get_rules_by_category(category: str) -> List[Dict]:
    """按类别获取规则"""
    return [r for r in ALL_RULES if r["category"] == category]

def get_rules_by_severity(severity: str) -> List[Dict]:
    """按严重程度获取规则"""
    return [r for r in ALL_RULES if r["severity"] == severity]

def get_auto_apply_rules() -> List[Dict]:
    """获取可以自动应用的规则"""
    return [r for r in ALL_RULES if r["auto_apply"]]

def list_all_rules() -> Dict[str, Any]:
    """列出所有规则摘要"""
    return {
        "total_rules": len(ALL_RULES),
        "categories": list(set(r["category"] for r in ALL_RULES)),
        "rules": [
            {
                "id": r["id"],
                "name": r["name"],
                "category": r["category"],
                "severity": r["severity"],
                "safe": r["safe"]
            }
            for r in ALL_RULES
        ]
    }
