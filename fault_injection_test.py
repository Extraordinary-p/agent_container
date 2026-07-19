#!/usr/bin/env python3
"""
NetBox AIOps Agent - 故障注入测试工具
用于验证系统的异常发现、诊断分析和自动处置能力
"""
import os
import sys
import subprocess
import time

print("=" * 70)
print("  NetBox AIOps Agent - 故障注入测试工具")
print("=" * 70)

print("""
📋 可用的故障场景:

  1. 🛑 停止 NetBox 容器 (验证服务异常检测)
  2. 📁 模拟磁盘空间不足 (创建大文件)
  3. ⚙️  修改 docker-compose.yml (配置错误检测)
  4. 🔄 制造容器频繁重启 (循环重启容器)
  5. 🔐 删除/修改环境变量 (配置缺失检测)
  6. 🧪 一键注入所有故障 (极限测试)

  9. ✅ 恢复所有故障 (清理测试环境)
  0. ❌ 退出
""")

NETBOX_PATH = "/Users/wangxudong/Documents/learning-cloud/pythonproject20260403/MarkDown_Learning_book/Aiops/Agent_tools_project_version1/netbox-docker"

def run_cmd(cmd, cwd=None):
    """执行命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, 
                              capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def test_stop_container():
    """测试场景1: 停止 NetBox 容器"""
    print("\n" + "=" * 60)
    print("场景 1: 停止 NetBox 容器")
    print("=" * 60)
    
    success, out, err = run_cmd("docker ps --filter name=netbox --format '{{.Names}}'")
    containers = out.strip().split('\n') if success else []
    containers = [c for c in containers if c]
    
    if not containers:
        print("❌ 没有找到运行中的 NetBox 容器")
        return
    
    target = containers[0]
    print(f"🎯 目标容器: {target}")
    
    print(f"🛑 正在停止容器...")
    success, out, err = run_cmd(f"docker stop {target}")
    
    if success:
        print("✅ 容器已停止")
        print("\n📝 预期系统行为:")
        print("  1. check_service_health 检测到 netbox 状态异常")
        print("  2. 诊断引擎标记为 HIGH 优先级问题")
        print("  3. 建议重启服务，或自动执行 restart_service")
        print("\n💡 运行验证: python main.py --mode full")
    else:
        print(f"❌ 停止失败: {err}")

def test_disk_space():
    """测试场景2: 模拟磁盘空间不足"""
    print("\n" + "=" * 60)
    print("场景 2: 模拟磁盘空间不足")
    print("=" * 60)
    
    # 创建一个 512MB 的测试文件
    test_file = "/Users/wangxudong/Documents/learning-cloud/pythonproject20260403/MarkDown_Learning_book/Aiops/Agent_tools_project_version1/netbox-docker/large_test_file.tmp"
    file_size_mb = 512
    
    print(f"📁 创建 {file_size_mb}MB 测试文件...")
    
    try:
        with open(test_file, "wb") as f:
            f.write(b"0" * 1024 * 1024 * file_size_mb)
        
        print(f"✅ 测试文件已创建: {test_file}")
        print(f"   文件大小: {file_size_mb} MB")
        print("\n📝 预期系统行为:")
        print("  1. check_disk_space 检测到磁盘使用率上升")
        print("  2. 如果超过阈值 (默认 85%)，触发告警")
        print("  3. 建议 prune_docker_resources 清理资源")
        print("\n💡 运行验证: python main.py --mode full")
        print(f"\n⚠️  记得测试完后删除文件: rm {test_file}")
    except Exception as e:
        print(f"❌ 创建文件失败: {e}")

def test_compose_config():
    """测试场景3: 修改 docker-compose.yml 制造配置错误"""
    print("\n" + "=" * 60)
    print("场景 3: 修改 docker-compose.yml 配置")
    print("=" * 60)
    
    compose_path = os.path.join(NETBOX_PATH, "docker-compose.yml")
    backup_path = os.path.join(NETBOX_PATH, "docker-compose.yml.backup")
    
    if not os.path.exists(compose_path):
        print(f"❌ 找不到配置文件: {compose_path}")
        return
    
    # 备份原文件
    import shutil
    shutil.copy(compose_path, backup_path)
    print(f"✅ 原文件已备份: {backup_path}")
    
    # 修改配置 - 注释掉 restart 策略
    with open(compose_path, "r") as f:
        content = f.read()
    
    # 替换 restart: always 为 # restart: always (注释掉)
    modified = content.replace("restart: always", "# restart: always")
    
    if modified == content:
        print("⚠️  没有找到 'restart: always'，尝试其他修改...")
        # 在 netbox 服务中注入一个无效配置
        if "netbox:" in content:
            modified = content.replace("netbox:", "netbox:\n    # INVALID_CONFIG_INJECTED\n    invalid_option: test")
    
    with open(compose_path, "w") as f:
        f.write(modified)
    
    print("✅ 已注入配置问题")
    print("\n📝 注入的问题:")
    print("  - 注释掉了 restart 策略 (缺少重启配置)")
    print("\n📝 预期系统行为:")
    print("  1. analyze_docker_compose 检测到配置问题")
    print("  2. warnings 中提示缺少 restart 策略")
    print("  3. 建议修复配置文件")
    print("\n💡 运行验证: python main.py --mode full")
    print("\n⚠️  记得测试完后恢复: cp {backup_path} {compose_path}")

def test_container_restart():
    """测试场景4: 制造容器频繁重启"""
    print("\n" + "=" * 60)
    print("场景 4: 制造容器频繁重启")
    print("=" * 60)
    
    success, out, err = run_cmd("docker ps --filter name=redis --format '{{.Names}}'")
    containers = out.strip().split('\n') if success else []
    containers = [c for c in containers if c]
    
    if not containers:
        print("❌ 没有找到 redis 容器")
        return
    
    target = containers[0]
    print(f"🎯 目标容器: {target}")
    
    print(f"🔄 执行 3 次重启循环...")
    for i in range(3):
        print(f"   第 {i+1} 次重启...")
        run_cmd(f"docker restart {target}")
        time.sleep(2)
    
    print("✅ 重启完成")
    print("\n📝 预期系统行为:")
    print("  1. check_service_health 检测到 restart_count > 0")
    print("  2. 诊断引擎标记为频繁重启问题")
    print("  3. 建议 inspect_container_logs 检查崩溃原因")
    print("\n💡 运行验证: python main.py --mode full")

def test_env_config():
    """测试场景5: 修改/删除环境变量"""
    print("\n" + "=" * 60)
    print("场景 5: 删除环境变量配置")
    print("=" * 60)
    
    env_path = os.path.join(NETBOX_PATH, ".env")
    backup_path = os.path.join(NETBOX_PATH, ".env.backup")
    
    if not os.path.exists(env_path):
        print(f"❌ 找不到配置文件: {env_path}")
        return
    
    # 备份
    import shutil
    shutil.copy(env_path, backup_path)
    print(f"✅ 原文件已备份: {backup_path}")
    
    # 删除 POSTGRES_PASSWORD
    with open(env_path, "r") as f:
        lines = f.readlines()
    
    modified = []
    for line in lines:
        if line.strip().startswith("POSTGRES_PASSWORD="):
            modified.append(f"# {line}  # COMMENTED FOR TEST")
        else:
            modified.append(line)
    
    with open(env_path, "w") as f:
        f.writelines(modified)
    
    print("✅ 已注释掉 POSTGRES_PASSWORD 配置")
    print("\n📝 预期系统行为:")
    print("  1. validate_env_config 检测到缺失 POSTGRES_PASSWORD")
    print("  2. 标记为 critical 级别问题")
    print("  3. 建议恢复配置文件")
    print("\n💡 运行验证: python main.py --mode full")
    print(f"\n⚠️  记得测试完后恢复: cp {backup_path} {env_path}")

def test_all_faults():
    """测试场景6: 一键注入所有故障"""
    print("\n" + "=" * 60)
    print("场景 6: 极限测试 - 注入所有故障")
    print("=" * 60)
    
    print("⚠️  即将注入以下故障:")
    print("  1. 停止 NetBox 容器")
    print("  2. 创建大文件模拟磁盘不足")
    print("  3. 修改 docker-compose.yml")
    print("  4. 制造容器频繁重启")
    print("  5. 注释掉 POSTGRES_PASSWORD")
    
    confirm = input("\n确认执行? (yes/no): ")
    if confirm.lower() != "yes":
        print("已取消")
        return
    
    print("\n🚀 开始注入故障...")
    
    # 执行所有故障注入
    test_stop_container()
    test_disk_space()
    test_compose_config()
    test_container_restart()
    test_env_config()
    
    print("\n" + "=" * 60)
    print("🎉 所有故障已注入完成！")
    print("=" * 60)
    print("\n现在运行完整测试来验证系统能力:")
    print("  python main.py --mode full")
    print("\n或者用 AI Agent 模式:")
    print("  python main.py --mode ai --provider doubao")

def restore_all():
    """恢复所有故障"""
    print("\n" + "=" * 60)
    print("恢复所有故障")
    print("=" * 60)
    
    # 1. 恢复容器
    print("🔄 重启所有 NetBox 容器...")
    run_cmd("docker start $(docker ps -a --filter name=netbox -q)")
    
    # 2. 删除测试文件
    test_file = "./large_test_file.tmp"
    if os.path.exists(test_file):
        print(f"🗑️ 删除测试文件: {test_file}")
        os.remove(test_file)
    
    # 3. 恢复 docker-compose.yml
    compose_backup = os.path.join(NETBOX_PATH, "docker-compose.yml.backup")
    compose_path = os.path.join(NETBOX_PATH, "docker-compose.yml")
    if os.path.exists(compose_backup):
        print(f"📄 恢复 docker-compose.yml")
        import shutil
        shutil.copy(compose_backup, compose_path)
    
    # 4. 恢复 .env
    env_backup = os.path.join(NETBOX_PATH, ".env.backup")
    env_path = os.path.join(NETBOX_PATH, ".env")
    if os.path.exists(env_backup):
        print(f"📄 恢复 .env 配置")
        import shutil
        shutil.copy(env_backup, env_path)
    
    print("\n✅ 所有故障已恢复！")

def main():
    while True:
        choice = input("\n请选择测试场景 (0-9): ").strip()
        
        if choice == "1":
            test_stop_container()
        elif choice == "2":
            test_disk_space()
        elif choice == "3":
            test_compose_config()
        elif choice == "4":
            test_container_restart()
        elif choice == "5":
            test_env_config()
        elif choice == "6":
            test_all_faults()
        elif choice == "9":
            restore_all()
        elif choice == "0":
            print("\n👋 再见！")
            break
        else:
            print("❌ 无效选项")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 已取消")
