from typing import Dict, Any, List, Optional
from loguru import logger
import json

class DiagnosticEngine:
    def __init__(self):
        self.issue_patterns = {
            "container_stopped": {
                "pattern": "状态异常",
                "severity": "high",
                "diagnosis": "容器停止运行",
                "recommendations": [
                    "检查容器日志: inspect_container_logs",
                    "尝试重启服务: restart_service",
                    "检查环境变量配置: validate_env_config"
                ]
            },
            "frequent_restart": {
                "pattern": "频繁重启",
                "severity": "high",
                "diagnosis": "容器崩溃重启循环",
                "recommendations": [
                    "分析崩溃日志: inspect_container_logs",
                    "检查资源限制配置",
                    "验证数据库连接: check_network_connectivity"
                ]
            },
            "disk_full": {
                "pattern": "使用率过高",
                "severity": "medium",
                "diagnosis": "磁盘空间不足",
                "recommendations": [
                    "清理 Docker 资源: prune_docker_resources",
                    "删除旧的日志文件",
                    "扩展磁盘空间"
                ]
            },
            "memory_high": {
                "pattern": "内存使用率过高",
                "severity": "medium",
                "diagnosis": "系统内存压力大",
                "recommendations": [
                    "重启内存消耗大的服务",
                    "增加系统内存",
                    "调整容器内存限制"
                ]
            },
            "missing_config": {
                "pattern": "不存在",
                "severity": "critical",
                "diagnosis": "配置文件缺失",
                "recommendations": [
                    "检查环境变量: validate_env_config",
                    "从示例文件创建配置",
                    "重新克隆仓库（如果文件损坏）"
                ]
            },
            "network_issue": {
                "pattern": "网络不存在",
                "severity": "medium",
                "diagnosis": "Docker 网络问题",
                "recommendations": [
                    "重启 Docker 服务",
                    "重新创建网络: docker network create",
                    "重新启动 compose 栈"
                ]
            }
        }
    
    def analyze_issues(self, detected_issues: List[str]) -> Dict[str, Any]:
        analysis_results = []
        
        for issue in detected_issues:
            matched_pattern = self._match_pattern(issue)
            analysis_results.append({
                "issue": issue,
                "matched_pattern": matched_pattern,
                "severity": self._get_severity(matched_pattern),
                "diagnosis": self._get_diagnosis(matched_pattern),
                "recommendations": self._get_recommendations(matched_pattern)
            })
        
        priority_issues = sorted(
            analysis_results,
            key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["severity"], 99)
        )
        
        return {
            "total_issues": len(detected_issues),
            "issues_analyzed": priority_issues,
            "critical_count": sum(1 for r in analysis_results if r["severity"] == "critical"),
            "high_count": sum(1 for r in analysis_results if r["severity"] == "high"),
            "medium_count": sum(1 for r in analysis_results if r["severity"] == "medium"),
            "summary": self._generate_summary(analysis_results)
        }
    
    def _match_pattern(self, issue: str) -> Optional[str]:
        for pattern_name, pattern_data in self.issue_patterns.items():
            if pattern_data["pattern"] in issue:
                return pattern_name
        return "unknown"
    
    def _get_severity(self, pattern_name: Optional[str]) -> str:
        if pattern_name and pattern_name in self.issue_patterns:
            return self.issue_patterns[pattern_name]["severity"]
        return "low"
    
    def _get_diagnosis(self, pattern_name: Optional[str]) -> str:
        if pattern_name and pattern_name in self.issue_patterns:
            return self.issue_patterns[pattern_name]["diagnosis"]
        return "需要进一步分析"
    
    def _get_recommendations(self, pattern_name: Optional[str]) -> List[str]:
        if pattern_name and pattern_name in self.issue_patterns:
            return self.issue_patterns[pattern_name]["recommendations"]
        return ["进一步使用诊断工具分析"]
    
    def _generate_summary(self, analysis_results: List[Dict[str, Any]]) -> str:
        critical = sum(1 for r in analysis_results if r["severity"] == "critical")
        high = sum(1 for r in analysis_results if r["severity"] == "high")
        medium = sum(1 for r in analysis_results if r["severity"] == "medium")
        
        if critical > 0:
            return f"严重问题！发现 {critical} 个关键故障，需要立即处理"
        elif high > 0:
            return f"发现 {high} 个高优先级问题，建议尽快修复"
        elif medium > 0:
            return f"系统运行基本正常，但有 {medium} 个需要关注的问题"
        else:
            return "系统运行正常，未发现严重问题"
    
    def get_remediation_steps(self, pattern_name: str, issue_text: str = "") -> Dict[str, Any]:
        """获取修复步骤
        
        Args:
            pattern_name: 问题模式名称
            issue_text: 问题描述文本，用于提取额外信息
        """
        remediation_map = {
            "container_stopped": {
                "steps": [
                    {"action": "inspect_container_logs", "params": {}},
                    {"action": "validate_env_config", "params": {}},
                    {"action": "restart_service", "params": {}}
                ],
                "auto_apply": True
            },
            "config_missing": {
                "steps": [
                    {"action": "validate_env_config", "params": {}},
                    {"action": "analyze_docker_compose", "params": {}},
                    {"action": "fix_docker_compose", "params": {"dry_run": True}}  # 安全模式
                ],
                "auto_apply": True
            },
            "disk_full": {
                "steps": [
                    {"action": "prune_docker_resources", "params": {"prune_type": "all"}},
                ],
                "auto_apply": True
            },
            "frequent_restart": {
                "steps": [
                    {"action": "inspect_container_logs", "params": {"tail_lines": 200}},
                    {"action": "check_network_connectivity", "params": {}}
                ],
                "auto_apply": False
            },
            "missing_config": {
                "steps": [
                    {"action": "validate_env_config", "params": {}}
                ],
                "auto_apply": False
            }
        }
        
        return remediation_map.get(pattern_name, {
            "steps": [],
            "auto_apply": False
        })
