#!/usr/bin/env python3
"""
简单测试程序（不需要任何依赖）
直接测试容器检测 + 自动修复功能
"""
import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 直接加载 anomaly_detector.py
import importlib.util
spec = importlib.util.spec_from_file_location("ad", "agent_core/anomaly_detector.py")
ad = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ad)

AnomalyDetector = ad.AnomalyDetector

def print_sep(char="=", length=70):
    print("\n" + char * length)

print("=" * 70)
print("   NetBox Docker AIOps Agent - 容器检测 + 自动修复")
print("=" * 70)

# 1. 检测
print_sep("-")
print("🔍 阶段 1: 检测容器异常")
print_sep("-")

detector = AnomalyDetector()
result = detector.detect_containers()

print(f"\n  检测到 {result['total_containers']} 个容器")
print(f"  运行中: {result['running_containers']} 个")
print(f"  已停止: {result['stopped_containers']} 个")
print(f"  异常数: {len(result['issues'])} 个")

for i, issue in enumerate(result['issues'], 1):
    print(f"\n    {i}. {issue}")

# 2. 详细分析
if result.get('container_details'):
    print_sep("-")
    print("📊 阶段 2: 根因分析")
    print_sep("-")
    
    for detail in result['container_details']:
        print(f"\n  📦 {detail['container']}")
        print(f"    退出码: {detail['exit_code']} → {detail['exit_code_meaning']}")
        
        if detail.get('errors_found', 0) > 0:
            print(f"    发现错误:")
            for err in detail['error_details']:
                print(f"      ❌ {err['type']}: {err['description']}")

# 3. 自动修复
stopped_containers = []
import re
for issue in result['issues']:
    match = re.search(r'容器\s*([a-zA-Z0-9_-]+)\s*已停止', issue)
    if match:
        stopped_containers.append(match.group(1))

if stopped_containers:
    print_sep("-")
    print("🔧 阶段 3: 自动修复")
    print_sep("-")
    
    for container_name in stopped_containers:
        print(f"\n  正在启动: {container_name}")
        result = subprocess.run(
            ['docker', 'start', container_name],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"    ✅ {container_name} 启动成功！")
        else:
            print(f"    ❌ 启动失败: {result.stderr.strip()}")

# 4. 最终状态
print_sep("=")
print("📋 最终容器状态")
print_sep("=")

final_result = detector.detect_containers()
print(f"\n  运行中: {final_result['running_containers']} 个")
print(f"  已停止: {final_result['stopped_containers']} 个")

if final_result['stopped_containers'] == 0:
    print("\n  ✅ 所有容器运行正常！")
else:
    print(f"\n  ⚠️ 仍有 {final_result['stopped_containers']} 个容器未启动")

print("\n" + "=" * 70)
