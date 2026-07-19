import re
from typing import Dict, Any, List, Optional, Callable
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_fixed

class RemediationEngine:
    def __init__(self, tool_executor, enable_auto: bool = True):
        self.tool_executor = tool_executor
        self.enable_auto = enable_auto
        self.executed_actions: List[Dict[str, Any]] = []
        self.failed_actions: List[Dict[str, Any]] = []
        
        self.safe_actions = {
            "start_service": True,
            "inspect_container_logs": True,
            "validate_env_config": True,
            "check_network_connectivity": True,
            "check_disk_space": True,
            "check_memory_usage": True,
            "analyze_docker_compose": True,
            "check_service_health": True
        }
        
        self.conditional_actions = {
            "restart_service": self._can_restart_service,
            "prune_docker_resources": self._can_prune_resources
        }
    
    def _extract_service_name_from_issue(self, issue_text: str) -> Optional[str]:
        """从问题描述中智能提取服务名称
        
        例子:
            "容器 netbox-docker-netbox-worker-1 状态异常" → "netbox-worker"
            "postgres 服务无法连接" → "postgres"
            "redis 频繁重启" → "redis"
        """
        # 常见服务名模式
        patterns = [
            r"容器\s*([a-zA-Z0-9_-]+?)(?:-[\d]+)?\s*状态",  # 提取: netbox-docker-netbox-worker-1
            r"服务\s*([a-zA-Z0-9_-]+)\s*",
            r"([a-zA-Z0-9_-]+)\s*(?:容器|服务|频繁重启|异常)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, issue_text)
            if match:
                extracted = match.group(1)
                # 简化服务名 (取关键部分)
                for keyword in ["worker", "netbox", "postgres", "redis", "nginx"]:
                    if keyword in extracted.lower():
                        return keyword
                return extracted
        
        # 如果没匹配到，返回 None
        return None
    
    def _build_params_for_action(self, action_name: str, issue_text: str = "") -> Dict[str, Any]:
        """为处置动作智能构建参数
        
        解决: LLM 不传参数时，自动从上下文推断
        """
        params = {}
        
        if action_name in ["restart_service", "start_service"]:
            service_name = self._extract_service_name_from_issue(issue_text)
            if service_name:
                params["service_name"] = service_name
                logger.debug(f"从问题描述提取服务名: {service_name}")
            else:
                params["service_name"] = "netbox"  # 默认值
        
        elif action_name == "inspect_container_logs":
            service_name = self._extract_service_name_from_issue(issue_text)
            if service_name:
                params["container_name"] = service_name
            else:
                params["container_name"] = "netbox"
            params["tail_lines"] = 100
        
        elif action_name == "prune_docker_resources":
            params["prune_type"] = "all"
        
        elif action_name == "validate_env_config":
            params["env_file"] = ".env"
        
        return params
    
    def execute_remediation(self, action_name: str, params: Dict[str, Any] = None, 
                           issue_text: str = "") -> Dict[str, Any]:
        """执行修复动作
        
        Args:
            action_name: 动作名称
            params: 参数字典 (如果为空会自动推断)
            issue_text: 问题描述文本，用于智能提取参数
        """
        # ✅ 关键修复: 如果参数为空，自动从问题描述推断
        if not params:
            params = self._build_params_for_action(action_name, issue_text)
            logger.info(f"为动作 {action_name} 自动推断参数: {params}")
        
        if action_name in self.safe_actions:
            return self._execute_safe_action(action_name, params)
        
        if action_name in self.conditional_actions:
            if self.conditional_actions[action_name]():
                return self._execute_action(action_name, params)
            else:
                return {
                    "success": False,
                    "action": action_name,
                    "reason": "执行条件不满足，跳过自动执行"
                }
        
        if not self.enable_auto:
            return {
                "success": False,
                "action": action_name,
                "reason": "自动修复已禁用，建议手动执行"
            }
        
        return self._execute_action(action_name, params)
    
    def _execute_safe_action(self, action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = self.tool_executor.execute(action_name, params)
            action_record = {
                "action": action_name,
                "params": params,
                "result": result,
                "timestamp": self._get_timestamp()
            }
            self.executed_actions.append(action_record)
            return result
        except Exception as e:
            self.failed_actions.append({
                "action": action_name,
                "params": params,
                "error": str(e),
                "timestamp": self._get_timestamp()
            })
            raise
    
    @retry(stop=stop_after_attempt(2), wait=wait_fixed(5))
    def _execute_action(self, action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        logger.warning(f"执行修复动作: {action_name}, 参数: {params}")
        try:
            result = self.tool_executor.execute(action_name, params)
            
            action_record = {
                "action": action_name,
                "params": params,
                "result": result,
                "timestamp": self._get_timestamp()
            }
            self.executed_actions.append(action_record)
            
            if result.get("success"):
                logger.info(f"修复动作 {action_name} 执行成功")
            else:
                logger.error(f"修复动作 {action_name} 执行失败: {result.get('error')}")
            
            return result
        except Exception as e:
            self.failed_actions.append({
                "action": action_name,
                "params": params,
                "error": str(e),
                "timestamp": self._get_timestamp()
            })
            raise
    
    def _can_restart_service(self) -> bool:
        return self.enable_auto
    
    def _can_prune_resources(self) -> bool:
        disk_check = self.tool_executor._check_disk_space(80)
        return disk_check.get("has_issues", False)
    
    def execute_workflow(self, workflow: List[Dict[str, Any]]) -> Dict[str, Any]:
        results = []
        success_count = 0
        failure_count = 0
        
        for step in workflow:
            action_name = step.get("action")
            params = step.get("params", {})
            issue_text = step.get("issue_text", "")  # 支持传入问题描述
            
            logger.info(f"执行工作流步骤: {action_name}")
            result = self.execute_remediation(action_name, params, issue_text)
            results.append({
                "action": action_name,
                "params": params,
                "result": result
            })
            
            if result.get("success"):
                success_count += 1
            else:
                failure_count += 1
        
        return {
            "success": failure_count == 0,
            "total_steps": len(workflow),
            "success_count": success_count,
            "failure_count": failure_count,
            "results": results
        }
    
    def get_remediation_statistics(self) -> Dict[str, Any]:
        return {
            "total_actions_executed": len(self.executed_actions),
            "total_actions_failed": len(self.failed_actions),
            "success_rate": len(self.executed_actions) / (len(self.executed_actions) + len(self.failed_actions)) 
                           if (len(self.executed_actions) + len(self.failed_actions)) > 0 else 0,
            "recent_actions": self.executed_actions[-5:]
        }
    
    def rollback_last_action(self) -> Dict[str, Any]:
        if not self.executed_actions:
            return {"success": False, "message": "没有可回滚的动作"}
        
        last_action = self.executed_actions[-1]
        action_name = last_action["action"]
        
        rollback_map = {
            "restart_service": "服务重启无法回滚",
            "prune_docker_resources": "资源清理无法回滚"
        }
        
        if action_name in rollback_map:
            return {
                "success": False,
                "message": rollback_map[action_name],
                "action": action_name
            }
        
        return {
            "success": False,
            "message": f"不支持回滚动作: {action_name}"
        }
    
    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()
