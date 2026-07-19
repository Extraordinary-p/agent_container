"""
⚠️ 配置修复工具暂时禁用
之前的实现存在 bug：会把 restart 配置加到错误的位置
需要重新设计后再启用
"""
from typing import Dict, Any, List

class ConfigFixManager:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
    
    def check_docker_compose(self, file_path: str) -> List[Dict[str, Any]]:
        """仅检测，不修复"""
        return []
    
    def fix_docker_compose(self, file_path: str) -> Dict[str, Any]:
        """禁用修复"""
        return {
            "success": True,
            "dry_run": True,
            "fixes_applied": [],
            "skipped_reason": "配置修复工具暂时禁用（需要重新实现）"
        }
