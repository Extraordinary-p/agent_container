import os
import re
from typing import Dict, Any, List, Optional
from loguru import logger

class ToolExecutor:
    def __init__(self):
        try:
            import docker
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.warning(f"Docker client not available: {e}")
            self.docker_client = None
    
    def _auto_fill_params(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """自动填充缺失的参数 - 解决 LLM 不传参数的问题"""
        filled_args = arguments.copy()
        
        if tool_name == "analyze_docker_compose":
            if "file_path" not in filled_args or not filled_args["file_path"]:
                paths_to_try = ["./docker-compose.yml", "./netbox-docker/docker-compose.yml"]
                for path in paths_to_try:
                    if os.path.exists(path):
                        filled_args["file_path"] = path
                        break
                else:
                    filled_args["file_path"] = "./docker-compose.yml"
        
        if tool_name == "fix_docker_compose":
            if "file_path" not in filled_args or not filled_args["file_path"]:
                paths_to_try = ["./docker-compose.yml", "./netbox-docker/docker-compose.yml"]
                for path in paths_to_try:
                    if os.path.exists(path):
                        filled_args["file_path"] = path
                        break
                else:
                    filled_args["file_path"] = "./docker-compose.yml"
            if "dry_run" not in filled_args:
                filled_args["dry_run"] = True
        
        return filled_args
    
    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        tool_map = {
            "analyze_docker_compose": self._analyze_docker_compose,
            "check_all_containers": self._check_all_containers,
            "check_service_health": self._check_service_health,
            "check_disk_space": self._check_disk_space,
            "check_memory_usage": self._check_memory_usage,
            "inspect_container_logs": self._inspect_container_logs,  # + 加回去
            "start_service": self._start_service,
            "prune_docker_resources": self._prune_docker_resources,
            "fix_docker_compose": self._fix_docker_compose,
            "validate_env_config": self._validate_env_config,
            "final_report": self._final_report
        }
        
        if tool_name not in tool_map:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        
        try:
            arguments = self._auto_fill_params(tool_name, arguments)
            
            logger.info(f"Executing tool: {tool_name} with args: {arguments}")
            result = tool_map[tool_name](**arguments)
            logger.info(f"Tool {tool_name} executed successfully")
            return result
        except TypeError as e:
            logger.error(f"参数不匹配错误: {e}")
            return {
                "success": False, 
                "error": f"参数不匹配: {str(e)}",
                "received_args": list(arguments.keys())
            }
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _check_all_containers(self) -> Dict[str, Any]:
        """检测所有 NetBox 相关容器的状态（不需要参数）"""
        try:
            # 直接导入并使用 AnomalyDetector（真正有实现的版本）
            import sys
            import os
            
            # 临时添加路径避免导入问题
            ad_path = os.path.join(os.path.dirname(__file__), "..", "agent_core")
            if ad_path not in sys.path:
                sys.path.insert(0, ad_path)
            
            # 直接加载文件，避免 __init__.py 的依赖问题
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "anomaly_detector", 
                os.path.join(os.path.dirname(__file__), "..", "agent_core", "anomaly_detector.py")
            )
            ad_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ad_module)
            
            detector = ad_module.AnomalyDetector()
            result = detector.detect_containers()
            
            # 把 issues 对象转成字符串列表，方便 LLM 读取
            issues_list = []
            for issue in result.get("issues", []):
                issues_list.append(str(issue))
            
            return {
                "success": True,
                "total_containers": result.get("total_containers", 0),
                "running_containers": result.get("running_containers", 0),
                "stopped_containers": result.get("stopped_containers", 0),
                "issues_found": len(issues_list),
                "issues": issues_list,
                "details": result.get("container_details", []),
                "all_healthy": len(issues_list) == 0
            }
            
        except Exception as e:
            import traceback
            return {
                "success": False, 
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    def _check_service_health(self, service_name: str) -> Dict[str, Any]:
        """检查指定服务的健康状态"""
        if not self.docker_client:
            return {"success": False, "error": "Docker client not available"}
        
        try:
            containers = self.docker_client.containers.list(all=True)
            target_container = None
            
            for container in containers:
                if service_name in container.name:
                    target_container = container
                    break
            
            if not target_container:
                return {
                    "success": False,
                    "error": f"Service {service_name} not found",
                    "running_containers": [c.name for c in containers]
                }
            
            status = target_container.status
            health = target_container.attrs.get('State', {}).get('Health', {}).get('Status', 'unknown')
            
            port_bindings = target_container.attrs.get('HostConfig', {}).get('PortBindings', {})
            
            try:
                stats = target_container.stats(stream=False)
                memory_usage = stats.get('memory_stats', {}).get('usage', 0)
                memory_limit = stats.get('memory_stats', {}).get('limit', 1)
                cpu_stats = stats.get('cpu_stats', {})
                cpu_usage = cpu_stats.get('cpu_usage', {}).get('total_usage', 0)
                system_cpu_usage = cpu_stats.get('system_cpu_usage', 1)
                cpu_percent = (cpu_usage / system_cpu_usage) * 100 if system_cpu_usage > 0 else 0
            except:
                memory_usage = 0
                memory_limit = 1
                cpu_percent = 0
            
            return {
                "success": True,
                "service_name": service_name,
                "container_name": target_container.name,
                "status": status,
                "health": health,
                "is_running": status == "running",
                "port_bindings": port_bindings,
                "created_at": target_container.attrs.get('Created'),
                "restart_count": target_container.attrs.get('RestartCount', 0),
                "memory_usage_mb": round(memory_usage / (1024**2), 2),
                "memory_limit_gb": round(memory_limit / (1024**3), 2),
                "cpu_percent": round(cpu_percent, 2)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _check_disk_space(self, threshold: float = 85.0) -> Dict[str, Any]:
        """检查磁盘空间使用情况"""
        import psutil
        partitions = psutil.disk_partitions()
        disk_usage = []
        issues = []
        
        for partition in partitions:
            if 'loop' in partition.device or 'snap' in partition.mountpoint:
                continue
            
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                usage_percent = usage.percent
                
                disk_info = {
                    "mountpoint": partition.mountpoint,
                    "device": partition.device,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "usage_percent": usage_percent
                }
                disk_usage.append(disk_info)
                
                if usage_percent >= threshold:
                    issues.append(f"磁盘 {partition.mountpoint} 使用率过高: {usage_percent}%")
            except Exception as e:
                continue
        
        return {
            "success": True,
            "threshold": threshold,
            "disk_usage": disk_usage,
            "issues": issues,
            "has_issues": len(issues) > 0
        }
    
    def _check_memory_usage(self, threshold: float = 90.0) -> Dict[str, Any]:
        """检查内存使用情况"""
        import psutil
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        issues = []
        if mem.percent >= threshold:
            issues.append(f"内存使用率过高: {mem.percent}%")
        
        if swap.percent >= threshold and swap.total > 0:
            issues.append(f"Swap 使用率过高: {swap.percent}%")
        
        return {
            "success": True,
            "threshold": threshold,
            "memory": {
                "total_gb": round(mem.total / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "used_gb": round(mem.used / (1024**3), 2),
                "usage_percent": mem.percent
            },
            "swap": {
                "total_gb": round(swap.total / (1024**3), 2),
                "used_gb": round(swap.used / (1024**3), 2),
                "usage_percent": swap.percent
            },
            "issues": issues,
            "has_issues": len(issues) > 0
        }
    
    def _inspect_container_logs(self, container_name: str, tail_lines: int = 100) -> Dict[str, Any]:
        """检查容器日志"""
        if not self.docker_client:
            return {"success": False, "error": "Docker client not available"}
        
        try:
            containers = self.docker_client.containers.list(all=True)
            target_container = None
            
            for container in containers:
                if container_name in container.name:
                    target_container = container
                    break
            
            if not target_container:
                return {"success": False, "error": f"Container {container_name} not found"}
            
            logs = target_container.logs(tail=tail_lines, timestamps=True).decode('utf-8', errors='ignore')
            
            error_patterns = ['error', 'Error', 'ERROR', 'fatal', 'Fatal', 'FATAL', 'exception', 'Exception', 'failed', 'Failed']
            error_lines = []
            issues = []
            for line in logs.split('\n'):
                for pattern in error_patterns:
                    if pattern in line:
                        error_lines.append(line)
                        break
            
            # 将发现的错误转换为 issues
            if error_lines:
                issues.append(f"容器 {target_container.name} 日志发现 {len(error_lines)} 条错误")
            
            return {
                "success": True,
                "container_name": target_container.name,
                "total_lines": tail_lines,
                "errors_found": len(error_lines),
                "error_lines": error_lines[:20],
                "logs_sample": logs[:5000],
                "issues": issues,  # + 新增
                "has_issues": len(issues) > 0  # + 可选，和其他工具保持一致
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _restart_service(self, service_name: str) -> Dict[str, Any]:
        """重启指定服务"""
        if not self.docker_client:
            return {"success": False, "error": "Docker client not available"}

    def _start_service(self, service_name: str) -> Dict[str, Any]:
        """启动已停止的服务（容器）- 只启动，不重启正在运行的"""
        try:
            import subprocess
            # 先用 docker 命令行，兼容性更好
            result = subprocess.run(
                ['docker', 'start', service_name],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "action": "start",
                    "service_name": service_name,
                    "message": f"✅ 容器 {service_name} 已成功启动"
                }
            else:
                # 试试模糊匹配
                result2 = subprocess.run(
                    ['docker', 'ps', '-a', '--filter', f'name={service_name}', '--format', '{{.Names}}'],
                    capture_output=True, text=True, timeout=10
                )
                if result2.returncode == 0 and result2.stdout.strip():
                    actual_name = result2.stdout.strip().split('\n')[0]
                    result3 = subprocess.run(
                        ['docker', 'start', actual_name],
                        capture_output=True, text=True, timeout=30
                    )
                    if result3.returncode == 0:
                        return {
                            "success": True,
                            "action": "start",
                            "service_name": actual_name,
                            "message": f"✅ 容器 {actual_name} 已成功启动"
                        }
                
                return {
                    "success": False,
                    "error": f"启动失败: {result.stderr.strip()}"
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}

        
        try:
            containers = self.docker_client.containers.list(all=True)
            target_container = None
            
            for container in containers:
                if service_name in container.name:
                    target_container = container
                    break
            
            if not target_container:
                return {"success": False, "error": f"Service {service_name} not found"}
            
            logger.warning(f"Restarting service: {service_name} (container: {target_container.name})")
            target_container.restart()
            
            return {
                "success": True,
                "action": "restart",
                "service_name": service_name,
                "container_name": target_container.name,
                "message": f"服务 {target_container.name} 已成功重启"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _prune_docker_resources(self, prune_type: str = "all") -> Dict[str, Any]:
        """清理 Docker 资源"""
        if not self.docker_client:
            return {"success": False, "error": "Docker client not available"}
        
        try:
            results = {}
            
            if prune_type in ["all", "containers"]:
                pruned = self.docker_client.containers.prune()
                results["containers"] = pruned
            
            if prune_type in ["all", "images"]:
                pruned = self.docker_client.images.prune()
                results["images"] = pruned
            
            if prune_type in ["all", "volumes"]:
                pruned = self.docker_client.volumes.prune()
                results["volumes"] = pruned
            
            return {
                "success": True,
                "prune_type": prune_type,
                "results": results,
                "message": f"Docker {prune_type} 资源清理完成"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fix_docker_compose(self, file_path: str = "./docker-compose.yml", dry_run: bool = True) -> Dict[str, Any]:
        """修复 docker-compose.yml 配置文件"""
        from .config_fixer import ConfigFixManager
        
        manager = ConfigFixManager(dry_run=dry_run)
        result = manager.fix_docker_compose(file_path)
        
        return result
    
    def _analyze_docker_compose(self, file_path: str = "./docker-compose.yml") -> Dict[str, Any]:
        """分析 docker-compose.yml 配置文件"""
        if not os.path.exists(file_path):
            alt_path = f"./netbox-docker/{os.path.basename(file_path)}"
            if os.path.exists(alt_path):
                file_path = alt_path
            else:
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                    "issues": ["docker-compose.yml 文件不存在"]
                }
        
        try:
            from .config_fixer import ConfigFixManager
            manager = ConfigFixManager()
            
            issues = manager.check_docker_compose(file_path)
            
            services = []
            try:
                with open(file_path, 'r') as f:
                    for line in f:
                        match = re.match(r'^\s{2}([a-zA-Z0-9_-]+):\s*$', line)
                        if match:
                            services.append(match.group(1))
            except:
                pass
            
            return {
                "success": True,
                "file_analyzed": file_path,
                "services": services,
                "issues": [i["issue"] for i in issues],
                "issues_detail": issues
            }
            
        except Exception as e:
            return {"success": False, "error": f"分析错误: {str(e)}"}
    
    def _validate_env_config(self, env_file: str = ".env") -> Dict[str, Any]:
        """验证环境配置文件"""
        if not os.path.exists(env_file):
            alt_path = f"./netbox-docker/{env_file}"
            if os.path.exists(alt_path):
                env_file = alt_path
            else:
                return {
                    "success": False,
                    "error": f"Env file not found: {env_file}",
                    "issues": ["环境配置文件不存在"]
                }
        
        required_vars = [
            'POSTGRES_PASSWORD',
            'POSTGRES_DB',
            'NETBOX_SECRET_KEY',
            'SUPERUSER_PASSWORD'
        ]
        
        found_vars = {}
        missing_vars = []
        
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key = line.split('=', 1)[0].strip()
                    found_vars[key] = True
        
        for req_var in required_vars:
            if req_var not in found_vars:
                missing_vars.append(req_var)
        
        return {
            "success": len(missing_vars) == 0,
            "env_file": env_file,
            "missing_vars": missing_vars,
            "found_vars_count": len(found_vars),
            "issues": [f"缺少必需的环境变量: {var}" for var in missing_vars]
        }
    
    def _final_report(self, summary: str, issues_found: List[str], 
                     recommendations: List[str], actions_taken: List[str]) -> Dict[str, Any]:
        """生成最终报告"""
        report = {
            "success": True,
            "report_type": "final_diagnosis",
            "summary": summary,
            "issues_found": issues_found,
            "recommendations": recommendations,
            "actions_taken": actions_taken,
        }
        
        logger.info("=" * 60)
        logger.info("最终诊断报告")
        logger.info("=" * 60)
        logger.info(f"总结: {summary}")
        logger.info(f"发现问题: {len(issues_found)} 个")
        for issue in issues_found:
            logger.info(f"  - {issue}")
        logger.info(f"修复建议: {len(recommendations)} 条")
        for rec in recommendations:
            logger.info(f"  - {rec}")
        logger.info(f"已执行动作: {len(actions_taken)} 个")
        for action in actions_taken:
            logger.info(f"  - {action}")
        logger.info("=" * 60)
        
        return report
