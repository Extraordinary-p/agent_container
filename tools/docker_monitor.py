"""
Docker 容器监控工具
===================
批量检测所有容器状态，不需要传具体服务名
"""
import re
from typing import List, Dict, Any

def get_all_container_status(docker_client=None) -> List[Dict[str, Any]]:
    """获取所有容器的状态（不依赖 Docker SDK 也能工作）
    
    Args:
        docker_client: 可选的 Docker SDK client
    
    Returns:
        容器状态列表
    """
    containers = []
    
    # 方式 1: 使用 Docker SDK
    if docker_client:
        try:
            for c in docker_client.containers.list(all=True):
                containers.append({
                    "name": c.name,
                    "status": c.status,
                    "is_running": c.status == "running",
                    "restart_count": c.attrs.get('RestartCount', 0),
                    "id": c.short_id
                })
            return containers
        except:
            pass
    
    # 方式 2: 使用 docker 命令行（更可靠）
    import subprocess
    try:
        result = subprocess.run(
            ['docker', 'ps', '-a', '--format', '{{.Names}}|{{.Status}}|{{.ID}}'],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('|')
                if len(parts) >= 2:
                    name = parts[0]
                    status = parts[1].lower()
                    containers.append({
                        "name": name,
                        "status": status,
                        "is_running": "up" in status,
                        "restart_count": 0,  # 简单模式不统计重启次数
                        "id": parts[2] if len(parts) > 2 else ""
                    })
    except Exception as e:
        pass
    
    return containers

def detect_container_issues(docker_client=None) -> List[Dict[str, Any]]:
    """检测所有容器问题
    
    返回问题列表:
    - 状态异常（已停止）
    - 频繁重启
    """
    containers = get_all_container_status(docker_client)
    issues = []
    
    for c in containers:
        # 只关注 NetBox 相关容器
        if not any(key in c['name'].lower() for key in ['netbox', 'postgres', 'redis', 'nginx']):
            continue
        
        # 检查是否停止
        if not c['is_running']:
            issues.append({
                "type": "container_stopped",
                "severity": "high",
                "container": c['name'],
                "message": f"容器 {c['name']} 已停止运行",
                "suggested_fix": "执行 restart_service 重启"
            })
        
        # 检查频繁重启（需要 docker SDK）
        if c.get('restart_count', 0) >= 3:
            issues.append({
                "type": "frequent_restart",
                "severity": "high",
                "container": c['name'],
                "restart_count": c['restart_count'],
                "message": f"容器 {c['name']} 频繁重启 ({c['restart_count']} 次)",
                "suggested_fix": "检查 inspect_container_logs 排查原因"
            })
    
    return issues
