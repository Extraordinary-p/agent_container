#!/usr/bin/env python3
"""测试自动修复功能"""
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("🔧 测试容器自动修复功能")
print("=" * 60)

# 先手动停止一个容器来测试
import subprocess
print("\n📋 当前容器状态:")
result = subprocess.run(
    ['docker', 'ps', '-a', '--format', '{{.Names}}|{{.Status}}'],
    capture_output=True, text=True
)

containers = []
for line in result.stdout.strip().split('\n'):
    if line and '|' in line:
        name, status = line.split('|', 1)
        containers.append({"name": name, "status": status})
        icon = "🟢" if 'Up' in status else "🔴"
        print(f"  {icon} {name}: {status}")

# 找一个停止的或者停止一个来测试
stopped = [c for c in containers if 'Up' not in c['status'] and 'netbox' in c['name'].lower()]

if stopped:
    print(f"\n🎯 发现已停止的容器: {stopped[0]['name']}")
else:
    # 停止一个容器来测试
    running = [c for c in containers if 'Up' in c['status'] and 'netbox' in c['name'].lower()]
    if running:
        print(f"\n⚠️ 停止一个容器用于测试: {running[0]['name']}")
        subprocess.run(['docker', 'stop', running[0]['name']], capture_output=True)
    else:
        print("\n❌ 没有找到 NetBox 容器，请先启动 Docker Compose")
        print("   cd netbox-docker && docker compose up -d")
        sys.exit(1)

# 现在测试自动修复
print("\n" + "=" * 60)
print("🔬 执行自动检测 + 修复...")
print("=" * 60)

from tools.tool_executor import ToolExecutor
executor = ToolExecutor()

# 1. 先检测所有容器状态
result = executor.execute("check_all_containers", {})
print(f"\n检测结果: {result.get('issues_found', 0)} 个问题")
for issue in result.get('issues', []):
    print(f"   ❌ {issue.get('message')}")

# 2. 从问题中提取服务名并启动
import re
for issue in result.get('issues', []):
    msg = issue.get('message', '')
    match = re.search(r'容器\s*([a-zA-Z0-9_-]+)\s*已停止', msg)
    if match:
        container_name = match.group(1)
        print(f"\n🔧 正在启动停止的容器: {container_name}")
        fix_result = executor.execute("start_service", {"service_name": container_name})
        
        if fix_result.get('success'):
            print(f"   ✅ {fix_result.get('message')}")
        else:
            print(f"   ❌ {fix_result.get('error')}")

print("\n" + "=" * 60)
print("📊 最终容器状态:")
print("=" * 60)

result = subprocess.run(
    ['docker', 'ps', '-a', '--format', '{{.Names}}|{{.Status}}'],
    capture_output=True, text=True
)
for line in result.stdout.strip().split('\n'):
    if line and '|' in line:
        name, status = line.split('|', 1)
        if 'netbox' in name.lower():
            icon = "🟢" if 'Up' in status else "🔴"
            print(f"  {icon} {name}: {status}")

print("\n" + "=" * 60)
print("✅ 自动修复功能测试完成！")
print("=" * 60)
print("""
现在你可以:

1. 手动停止一个容器:
   docker stop netbox-docker-netbox-1

2. 运行完整检测 + 自动修复:
   python main.py --mode full

3. 查看结果:
   docker ps

Agent 会:
  ✅ 检测到停止的容器
  ✅ 自动提取容器名
  ✅ 执行 docker start 启动
  ✅ 报告修复结果
""")
