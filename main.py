#!/usr/bin/env python3
"""
NetBox Docker AIOps Agent 主程序
支持 3 种运行模式:
  --mode full    : 零依赖检测 + 自动修复
  --mode ai      : AI Agent (需要 API Key 和相关依赖)  
  --mode manual  : 手动检测模式
"""
import sys
import os
import argparse

# ========== 零依赖的核心功能（复制自 simple_docker_check.py）==========
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
    except Exception as e:
        if "permission denied" in str(e):
            print("\n  ⚠️  Docker 权限错误！请确保:")
            print("     1. Docker Desktop 已启动（顶部菜单栏有鲸鱼图标）")
            print("     2. 等待 Docker 完全启动后再试")
        return ""

def get_all_containers() -> List[Dict[str, Any]]:
    containers = []
    output = run_docker_cmd([
        "ps", "-a", 
        "--format", "{{.Names}}|{{.Status}}|{{.ExitCode}}"
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
        "OOMKilled": "内存溢出，容器被系统杀死",
        "error": "程序内部错误",
        "Error": "程序内部错误",
        "connection refused": "网络连接失败，无法连接依赖服务",
        "could not connect": "数据库连接失败，请检查 PostgreSQL/Redis",
        "permission denied": "文件或目录权限不足",
        "no such file": "配置文件或目录缺失",
        "Address already in use": "端口被占用，请检查端口冲突",
        "FATAL": "致命错误，请检查数据库配置",
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
        "126": "权限不足，无法执行命令",
        "127": "命令未找到",
        "137": "SIGKILL 信号被杀死（OOM 内存溢出或手动 kill）",
        "139": "段错误，程序崩溃",
        "143": "SIGTERM 信号正常停止",
    }
    
    return {
        "container": container["name"],
        "exit_code": container["exit_code"],
        "exit_code_meaning": exit_code_meanings.get(container["exit_code"], "未知退出码"),
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
        return {"success": True, "message": f"✅ {container_name} 已成功启动"}
    else:
        return {"success": False, "error": result.stderr.strip()}

def check_disk_and_memory() -> List[str]:
    issues = []
    try:
        import psutil
        mem = psutil.virtual_memory()
        if mem.percent >= 90:
            issues.append(f"🔴 内存使用率过高: {mem.percent:.1f}%")
        elif mem.percent >= 85:
            issues.append(f"🟠 内存使用率较高: {mem.percent:.1f}%")
        
        swap = psutil.swap_memory()
        if swap.percent >= 90 and swap.total > 0:
            issues.append(f"🟠 Swap 使用率过高: {swap.percent:.1f}%")
        
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
    except ImportError:
        pass
    except Exception as e:
        pass
    
    return issues

# ========== 运行模式实现 ==========

def run_full_cycle():
    """纯本地的 检测→诊断→修复 闭环"""
    print("\n" + "=" * 70)
    print("   🚀 NetBox Docker AIOps Agent - 完整运维闭环")
    print("=" * 70)
    
    # 1. 异常检测
    print("\n🔍 阶段 1: 异常检测")
    print("-" * 70)
    
    containers = get_all_containers()
    
    if not containers:
        print("\n  ⚠️  未检测到 NetBox 相关容器")
        print("     请检查:")
        print("       1. Docker Desktop 是否已启动（顶部菜单栏鲸鱼图标变绿）")
        print("       2. 是否已执行: cd netbox-docker && docker compose up -d")
        print("\n  💡 提示: 刚启动 Docker 需要等 1-2 分钟才能连接上")
        return
    
    stopped = [c for c in containers if not c['is_running']]
    running = [c for c in containers if c['is_running']]
    
    print(f"  检测到 {len(containers)} 个 NetBox 相关容器")
    print(f"    🟢 运行中: {len(running)} 个")
    print(f"    🔴 已停止: {len(stopped)} 个")
    
    all_issues = []
    
    if stopped:
        print(f"\n  📋 停止的容器详情:")
        for c in stopped:
            analysis = analyze_stop_reason(c)
            if analysis["errors_found"] > 0:
                main_error = analysis["error_details"][0]
                issue = f"🔴 容器 {c['name']} 已停止 → {main_error['type']}: {main_error['log_line'][:80]}"
                print(f"    {issue}")
                all_issues.append(issue)
            else:
                issue = f"🔴 容器 {c['name']} 已停止 → 退出码 {analysis['exit_code']} ({analysis['exit_code_meaning']})"
                print(f"    {issue}")
                all_issues.append(issue)
    
    # 资源检测
    resource_issues = check_disk_and_memory()
    all_issues.extend(resource_issues)
    for issue in resource_issues:
        print(f"    {issue}")
    
    if len(all_issues) == 0:
        print("\n✅ 系统运行正常，未发现异常")
        return
    
    # 2. 自动修复
    if stopped:
        print("\n🔧 阶段 2: 自动修复")
        print("-" * 70)
        
        fixed_count = 0
        for c in stopped:
            print(f"\n  正在启动: {c['name']}")
            result = start_container(c['name'])
            if result['success']:
                print(f"    {result['message']}")
                fixed_count += 1
            else:
                print(f"    ❌ {result['error']}")
    
    # 3. 最终报告
    print("\n" + "=" * 70)
    print("  📊 最终诊断报告")
    print("=" * 70)
    
    containers_final = get_all_containers()
    running_final = len([c for c in containers_final if c['is_running']])
    stopped_final = len([c for c in containers_final if not c['is_running']])
    
    print(f"\n  检测到问题: {len(all_issues)} 个")
    print(f"  已自动修复: {len(stopped) - stopped_final} 个容器")
    print(f"  当前运行中: {running_final} 个容器")
    print(f"  当前已停止: {stopped_final} 个容器")
    
    if stopped_final == 0:
        print("\n✅ 所有容器运行正常！")
    else:
        print(f"\n⚠️ 仍有 {stopped_final} 个容器未能自动启动")
        for c in containers_final:
            if not c['is_running']:
                print(f"    - {c['name']}: {c['status']}")
    
    print("\n" + "=" * 70)
    print("  💡 建议:")
    print("     - 定期运行此脚本检查系统健康状态")
    print("     - 如容器频繁崩溃，请检查日志: docker logs <容器名>")
    print("     - 配置告警，及时发现异常")
    print("=" * 70)

def run_manual_mode():
    """手动检测模式"""
    print("=" * 70)
    print("   手动检测模式")
    print("=" * 70)
    
    containers = get_all_containers()
    
    if not containers:
        print("\n  ⚠️  未检测到 NetBox 相关容器")
        return
    
    print(f"\n  共 {len(containers)} 个容器:\n")
    for c in containers:
        icon = "🟢" if c['is_running'] else "🔴"
        print(f"  {icon} {c['name']}")
        print(f"     状态: {c['status']}")
        if not c['is_running']:
            analysis = analyze_stop_reason(c)
            print(f"     退出码: {analysis['exit_code']} ({analysis['exit_code_meaning']})")
            if analysis['errors_found'] > 0:
                print(f"     发现 {analysis['errors_found']} 个错误:")
                for err in analysis['error_details'][:3]:
                    print(f"       - {err['type']}")
        print()

def run_ai_agent(args):
    """AI Agent 模式 - 懒加载依赖"""
    print("=" * 70)
    print("   AI Agent 模式 - Tool Calling")
    print("=" * 70)
    print("\n  ⚠️  此模式需要安装依赖: pip install openai python-dotenv loguru")
    print("  请先配置 .env 文件填入 API Key")
    print("\n  💡 如只是想测试检测功能，请使用: python main.py --mode full")
    
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from agent_core.agent import AIOpsAgent
        agent = AIOpsAgent(provider=args.provider)
        agent.run_diagnosis_cycle("全面检查 NetBox 环境")
    except ImportError as e:
        print(f"\n  ❌ 导入失败: {e}")
        print("  解决方案: pip install openai python-dotenv loguru")
    except Exception as e:
        print(f"\n  ❌ 执行失败: {e}")

def main():
    parser = argparse.ArgumentParser(description="NetBox Docker AIOps Agent")
    parser.add_argument("--mode", choices=["full", "ai", "manual"], default="full",
                       help="运行模式: full(完整闭环), ai(AI Agent模式), manual(手动检测)")
    parser.add_argument("--provider", choices=["openai", "doubao", "qwen", "zhipu", "deepseek", "custom"],
                       default="doubao", help="AI 模型提供商")
    
    args = parser.parse_args()
    
    if args.mode == "full":
        run_full_cycle()
    elif args.mode == "ai":
        run_ai_agent(args)
    elif args.mode == "manual":
        run_manual_mode()

if __name__ == "__main__":
    main()
