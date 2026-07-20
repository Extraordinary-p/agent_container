import os
import re
import subprocess
from typing import Dict, Any, List, Optional
from datetime import datetime

class AnomalyDetector:
    def __init__(self, netbox_path: str = "./netbox-docker"):
        self.netbox_path = netbox_path
    
    def _run_docker_command(self, cmd_args: List[str]) -> str:
        """执行 docker 命令并返回结果"""
        try:
            result = subprocess.run(
                ["docker"] + cmd_args,
                #执行结果不会显示在终端，而是保存到 result 对象中。
                capture_output=True,
                text=True,
                timeout=15
            )
            return result.stdout if result.returncode == 0 else ""
        except FileNotFoundError:
            print("  ⚠️ 未找到 docker 命令，请确保 Docker 已安装")
            return ""
        except PermissionError:
            print("  ⚠️ Docker 权限不足，请确保 Docker Desktop 已启动")
            return ""
        except Exception as e:
            print(f"  ⚠️ Docker 命令执行失败: {e}")
            return ""
    
    def _get_all_containers_status(self) -> List[Dict[str, Any]]:
        """获取所有相关容器的详细状态"""
        containers = []
        
        output = self._run_docker_command([
            "ps", "-a",
            "--format", "{{.Names}}|{{.Status}}|{{.Ports}}|{{.CreatedAt}}"
        ])

        # 1. 把输出按换行符拆成一行一行，然后循环处理每一行
        for line in output.strip().split('\n'):

            # 2. 校验：如果这行是空的，或者行里没有|分隔符，直接跳过（不处理垃圾数据）
            if not line or '|' not in line:
                continue

            # 3. 用|把一行切成好几段（比如 "容器名|状态|退出码" → ["容器名", "状态", "退出码"]）
            parts = line.split('|')

            # 4. 确保至少有2段数据（避免越界错误），才继续处理
            if len(parts) >= 2:
                name = parts[0]
                # 只关注 NetBox 相关容器
                if not any(k in name.lower() for k in ['netbox', 'postgres', 'redis', 'nginx', 'valkey']):
                    continue
                
                status = parts[1]
                # 从 Status 中提取退出码: "Exited (137) 5 minutes ago" -> "137"
                import re
                exit_match = re.search(r'Exited \((\d+)\)', status)
                exit_code = exit_match.group(1) if exit_match else "0"
                is_running = 'Up' in status
                
                containers.append({
                    "name": name,
                    "status": status,
                    "exit_code": exit_code,
                    "is_running": is_running,
                    "ports": parts[2] if len(parts) > 2 else "",
                    "created_at": parts[3] if len(parts) > 3 else ""
                })
        
        return containers
    
    def _get_container_logs(self, container_name: str, tail: int = 50) -> List[str]:
        """获取容器最后 N 行日志"""
        output = self._run_docker_command(["logs", "--tail", str(tail), container_name])
        return [line for line in output.strip().split('\n') if line]
    
    def _analyze_container_stop_reason(self, container: Dict[str, Any]) -> Dict[str, Any]:
        """分析容器停止的根因"""
        logs = self._get_container_logs(container["name"], tail=100)
        
        # 错误模式匹配
        error_patterns = {
            "OOMKilled": ("内存溢出", "容器使用内存超过限制，被系统杀死"),
            "error": ("程序错误", "应用内部错误导致崩溃"),
            "Error": ("程序错误", "应用内部错误导致崩溃"),
            "connection refused": ("网络连接失败", "无法连接到依赖服务（如数据库）"),
            "could not connect": ("数据库连接失败", "PostgreSQL/Redis 连接失败"),
            "permission denied": ("权限错误", "文件或目录权限不足"),
            "no such file": ("文件缺失", "配置文件或目录缺失"),
            "Address already in use": ("端口被占用", "容器需要的端口被占用"),
            "FATAL": ("致命错误", "数据库或应用致命错误"),
        }
        
        found_errors = []
        for line in logs[-30:]:  # 只看最后 30 行
            for pattern, (error_type, description) in error_patterns.items():
                if pattern in line:
                    found_errors.append({
                        "type": error_type,
                        "description": description,
                        "log_line": line.strip()
                    })
        
        # 分析退出码
        exit_code = container.get("exit_code", "")
        exit_code_meanings = {
            "0": "正常退出",
            "1": "通用错误",
            "2": "误用 Shell 命令",
            "126": "无法执行命令（权限问题）",
            "127": "命令未找到",
            "128": "无效退出参数",
            "137": "收到 SIGKILL 信号（OOM 或手动 kill）",
            "139": "段错误（Segmentation Fault）",
            "143": "收到 SIGTERM 信号（正常停止）",
        }
        
        return {
            "container": container["name"],
            "exit_code": exit_code,
            "exit_code_meaning": exit_code_meanings.get(exit_code, "未知退出码"),
            "status": container["status"],
            "errors_found": len(found_errors),
            "error_details": found_errors[:5],  # 最多显示 5 个
            "log_tail": logs[-10:]  # 最后 10 行日志
        }
    
    def detect_containers(self) -> Dict[str, Any]:
        """专门检测容器异常（核心修复）"""
        containers = self._get_all_containers_status()
        
        if len(containers) == 0:
            print("  ⚠️ 未检测到 NetBox 容器，请检查:")
            print("     1. Docker Desktop 是否已启动")
            print("     2. 是否已执行 cd netbox-docker && docker compose up -d")
        issues = []
        container_details = []
        
        for container in containers:
            # 1. 已停止的容器 → 高优先级问题
            if not container["is_running"]:
                # 深度分析停止原因
                analysis = self._analyze_container_stop_reason(container)
                
                # 构建问题描述
                if analysis["errors_found"] > 0:
                    main_error = analysis["error_details"][0]
                    issue = f"🔴 容器 {container['name']} 已停止 (状态: {container['status']}) → {main_error['type']}: {main_error['description']}"
                else:
                    issue = f"🔴 容器 {container['name']} 已停止 (状态: {container['status']}) → 退出码: {analysis['exit_code']} ({analysis['exit_code_meaning']})"
                
                issues.append(issue)
                container_details.append(analysis)
            
            # 2. 频繁重启检测（重启计数）
            else:
                # 检查是否在最近几分钟内重启过
                restart_output = self._run_docker_command([
                    "inspect", container["name"], "--format", "{{.RestartCount}}"
                ])
                restart_count = int(restart_output.strip()) if restart_output.strip().isdigit() else 0
                
                if restart_count >= 3:
                    issues.append(f"🟠 容器 {container['name']} 频繁重启 (已重启 {restart_count} 次)")
                    container_details.append({
                        "container": container["name"],
                        "issue": "频繁重启",
                        "restart_count": restart_count
                    })
        
        return {
            "total_containers": len(containers),
            "stopped_containers": len([c for c in containers if not c["is_running"]]),
            "running_containers": len([c for c in containers if c["is_running"]]),
            "issues": issues,
            "container_details": container_details
        }
    
    def _check_disk_space(self) -> List[str]:
        """检查磁盘空间"""
        issues = []
        try:
            import psutil
            for partition in psutil.disk_partitions():
                if 'loop' in partition.device or 'snap' in partition.mountpoint:
                    continue
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    if usage.percent >= 90:
                        issues.append(f"🔴 磁盘 {partition.mountpoint} 严重不足: {usage.percent:.1f}%")
                    elif usage.percent >= 85:
                        issues.append(f"🟠 磁盘 {partition.mountpoint} 使用率较高: {usage.percent:.1f}%")
                except:
                    pass
        except:
            pass
        return issues
    
    def _check_memory(self) -> List[str]:
        """检查内存使用"""
        issues = []
        try:
            import psutil
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            if mem.percent >= 95:
                issues.append(f"🔴 内存严重不足: {mem.percent:.1f}%")
            elif mem.percent >= 90:
                issues.append(f"🟠 内存使用率过高: {mem.percent:.1f}%")
            
            if swap.percent >= 90 and swap.total > 0:
                issues.append(f"🟠 Swap 使用率过高: {swap.percent:.1f}%")
        except:
            pass
        return issues
    
    def _check_env_config(self) -> List[str]:
        """检查环境变量"""
        issues = []
        env_file = os.path.join(self.netbox_path, ".env")
        if not os.path.exists(env_file):
            return issues
        
        required_vars = ["POSTGRES_PASSWORD", "POSTGRES_DB", "NETBOX_SECRET_KEY", "SUPERUSER_PASSWORD"]
        found_vars = set()
        
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key = line.split('=', 1)[0].strip()
                    found_vars.add(key)
        
        missing = [v for v in required_vars if v not in found_vars]
        for v in missing:
            issues.append(f"🟡 缺少必需环境变量: {v}")
        
        return issues
    
    def detect_all(self) -> Dict[str, Any]:
        """完整检测"""
        all_issues = []
        
        # 1. 容器检测（最高优先级）
        container_result = self.detect_containers()
        all_issues.extend(container_result["issues"])
        
        # 2. 资源检测
        all_issues.extend(self._check_memory())
        all_issues.extend(self._check_disk_space())
        
        # 3. 配置检测
        all_issues.extend(self._check_env_config())
        
        # 按严重程度排序
        severity_order = {"🔴": 0, "🟠": 1, "🟡": 2, "🟢": 3}
        all_issues.sort(key=lambda x: severity_order.get(x[:2], 9))
        
        return {
            "total_issues": len(all_issues),
            "issues": all_issues,
            "has_anomalies": len(all_issues) > 0,
            "containers": container_result
        }
    
    def check_specific_service(self, service_name: str) -> Dict[str, Any]:
        """检查特定服务"""
        containers = self._get_all_containers_status()
        
        for c in containers:
            if service_name.lower() in c["name"].lower():
                if not c["is_running"]:
                    analysis = self._analyze_container_stop_reason(c)
                    return {"found": True, "container": c, "analysis": analysis}
                else:
                    return {"found": True, "container": c, "running": True}
        
        return {"found": False, "message": f"未找到服务: {service_name}"}
