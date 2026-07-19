#!/usr/bin/env python3
"""
完全零依赖的 Docker 容器检测脚本
用于快速验证检测功能
"""
import os
import re
import subprocess
from typing import Dict, Any, List

def run_docker_cmd(cmd_args: List[str]) -> str:
    try:
        result = subprocess.run(
            ["docker"] + cmd_args,
            capture_output=True,
            text=True,
            timeout=15
        )
        return result.stdout if result.returncode == 0 else ""
    except:
        return ""

def get_all_containers() -> List[Dict[str, Any]]:
    containers = []
    output = run_docker_cmd([
        "ps", "-a", 
        "--format", "{{.Names}}|{{.Status}}"
    ])
    
    for line in output.strip().split('\n'):
        if not line or '|' not in line:
            continue
        parts = line.split('|')
        if len(parts) >= 2:
            name = parts[0]
            if not any(k in name.lower() for k in ['netbox', 'postgres', 'redis', 'nginx', 'valkey']):
                continue
            
            status = parts[1]
            exit_code = parts[2] if len(parts) > 2 else ""
            is_running = 'Up' in status
            
            containers.append({
                "name": name,
                "status": status,
                "exit_code": exit_code,
                "is_running": is_running
            })
    
    return containers

def get_container_logs(container_name: str, tail: int = 50) -> List[str]:
    output = run_docker_cmd(["logs", "--tail", str(tail), container_name])
    return [line for line in output.strip().split('\n') if line]

def analyze_stop_reason(container: Dict[str, Any]) -> Dict[str, Any]:
    logs = get_container_logs(container["name"], tail=100)
    
    error_patterns = {
        "OOMKilled": "内存溢出",
        "error": "程序错误",
        "Error": "程序错误",
        "connection refused": "网络连接失败",
        "could not connect": "数据库连接失败",
        "permission denied": "权限错误",
        "no such file": "文件缺失",
        "Address already in use": "端口被占用",
        "FATAL": "致命错误",
    }
    
    found_errors = []
    for line in logs[-30:]:
        for pattern, error_type in error_patterns.items():
            if pattern in line:
                found_errors.append({
                    "type": error_type,
                    "log_line": line.strip()
                })
    
    exit_code_meanings = {
        "0": "正常退出",
        "1": "通用错误",
        "126": "权限不足",
        "127": "命令未找到",
        "137": "SIGKILL 被杀死",
        "139": "段错误",
        "143": "SIGTERM 正常停止",
    }
    
    return {
        "container": container["name"],
        "exit_code": container["exit_code"],
        "exit_code_meaning": exit_code_meanings.get(container["exit_code"], "未知"),
        "errors_found": len(found_errors),
        "error_details": found_errors[:5],
        "log_tail": logs[-10:]
    }

def start_container(container_name: str) -> Dict[str, Any]:
    result = subprocess.run(
        ['docker', 'start', container_name],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode == 0:
        return {"success": True, "message": f"✅ {container_name} 已启动"}
    else:
        return {"success": False, "error": result.stderr.strip()}

def main():
    print("=" * 70)
    print("   NetBox Docker - 零依赖检测 + 自动修复")
    print("=" * 70)
    
    # 1. 检测
    print("\n🔍 阶段 1: 检测容器状态")
    print("-" * 70)
    
    containers = get_all_containers()
    
    if not containers:
        print("  ⚠️  未检测到 NetBox 相关容器")
        print("     请检查:")
        print("       1. Docker Desktop 是否已启动")
        print("       2. 是否已执行: cd netbox-docker && docker compose up -d")
        return
    
    stopped = [c for c in containers if not c['is_running']]
    running = [c for c in containers if c['is_running']]
    
    print(f"  检测到 {len(containers)} 个 NetBox 相关容器")
    print(f"    🟢 运行中: {len(running)} 个")
    print(f"    🔴 已停止: {len(stopped)} 个")
    
    if stopped:
        print(f"\n  已停止的容器:")
        for c in stopped:
            analysis = analyze_stop_reason(c)
            if analysis["errors_found"] > 0:
                main_error = analysis["error_details"][0]
                print(f"    - {c['name']} → {main_error['type']}: {main_error['log_line'][:80]}")
            else:
                print(f"    - {c['name']} → 退出码: {analysis['exit_code']} ({analysis['exit_code_meaning']})")
    
    # 2. 自动修复
    if stopped:
        print("\n🔧 阶段 2: 自动修复")
        print("-" * 70)
        
        for c in stopped:
            print(f"\n  正在启动: {c['name']}")
            result = start_container(c['name'])
            if result['success']:
                print(f"    {result['message']}")
            else:
                print(f"    ❌ {result['error']}")
    
    # 3. 最终状态
    print("\n📊 最终状态")
    print("-" * 70)
    containers = get_all_containers()
    running = len([c for c in containers if c['is_running']])
    stopped = len([c for c in containers if not c['is_running']])
    
    print(f"  🟢 运行中: {running} 个")
    print(f"  🔴 已停止: {stopped} 个")
    
    if stopped == 0:
        print("\n✅ 所有容器运行正常！")
    else:
        print(f"\n⚠️ 仍有 {stopped} 个容器未启动")

if __name__ == "__main__":
    main()
