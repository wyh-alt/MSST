#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MSST WebUI 安装验证脚本
用于验证安装是否成功完成
"""

import os
import sys
import json
import subprocess
import socket
from pathlib import Path

def check_file_exists(file_path, description):
    """检查文件是否存在"""
    if os.path.exists(file_path):
        print(f"✓ {description}: {file_path}")
        return True
    else:
        print(f"✗ {description}: {file_path} (未找到)")
        return False

def check_directory_exists(dir_path, description):
    """检查目录是否存在"""
    if os.path.isdir(dir_path):
        print(f"✓ {description}: {dir_path}")
        return True
    else:
        print(f"✗ {description}: {dir_path} (未找到)")
        return False

def check_config_file(config_file, description):
    """检查配置文件"""
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"✓ {description}: {config_file}")
            return True
        except Exception as e:
            print(f"✗ {description}: {config_file} (格式错误: {e})")
            return False
    else:
        print(f"✗ {description}: {config_file} (未找到)")
        return False

def check_port_available(port):
    """检查端口是否可用"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        if result == 0:
            print(f"⚠ 端口 {port} 已被占用")
            return False
        else:
            print(f"✓ 端口 {port} 可用")
            return True
    except Exception as e:
        print(f"✗ 端口 {port} 检查失败: {e}")
        return False

def check_python_environment(workenv_path):
    """检查Python环境"""
    python_exe = os.path.join(workenv_path, "python.exe")
    if os.path.exists(python_exe):
        try:
            result = subprocess.run([python_exe, "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"✓ Python环境: {version}")
                return True
            else:
                print(f"✗ Python环境: 无法获取版本信息")
                return False
        except Exception as e:
            print(f"✗ Python环境: 运行失败 ({e})")
            return False
    else:
        print(f"✗ Python环境: {python_exe} 未找到")
        return False

def main():
    """主验证函数"""
    print("=" * 60)
    print("MSST WebUI 安装验证")
    print("=" * 60)
    print()
    
    # 获取当前目录作为安装目录
    install_dir = os.getcwd()
    print(f"安装目录: {install_dir}")
    print()
    
    # 检查结果统计
    total_checks = 0
    passed_checks = 0
    
    # 1. 检查主要程序文件
    print("1. 主要程序文件检查:")
    print("-" * 30)
    
    main_files = [
        ("webUI.py", "主程序文件"),
        ("client.py", "客户端文件"),
        ("MSST.bat", "启动脚本"),
        ("config_manager.py", "配置管理工具"),
        ("README.md", "说明文档")
    ]
    
    for file_name, description in main_files:
        total_checks += 1
        if check_file_exists(os.path.join(install_dir, file_name), description):
            passed_checks += 1
    
    print()
    
    # 2. 检查目录结构
    print("2. 目录结构检查:")
    print("-" * 30)
    
    directories = [
        ("workenv", "Python环境目录"),
        ("clientui", "客户端UI目录"),
        ("inference", "推理模块目录"),
        ("modules", "模型模块目录"),
        ("webui", "WebUI模块目录"),
        ("data", "数据目录"),
        ("configs", "配置目录"),
        ("docs", "文档目录"),
        ("logs", "日志目录"),
        ("cache", "缓存目录"),
        ("input", "输入目录"),
        ("results", "结果目录")
    ]
    
    for dir_name, description in directories:
        total_checks += 1
        if check_directory_exists(os.path.join(install_dir, dir_name), description):
            passed_checks += 1
    
    print()
    
    # 3. 检查配置文件
    print("3. 配置文件检查:")
    print("-" * 30)
    
    config_files = [
        ("data/webui_config.json", "WebUI配置文件"),
        ("user.json", "用户配置文件"),
        ("client_config.json", "客户端配置文件"),
        ("install_config.json", "安装配置记录")
    ]
    
    for config_file, description in config_files:
        total_checks += 1
        if check_config_file(os.path.join(install_dir, config_file), description):
            passed_checks += 1
    
    print()
    
    # 4. 检查Python环境
    print("4. Python环境检查:")
    print("-" * 30)
    
    total_checks += 1
    if check_python_environment(os.path.join(install_dir, "workenv")):
        passed_checks += 1
    
    print()
    
    # 5. 检查端口配置
    print("5. 端口配置检查:")
    print("-" * 30)
    
    # 读取配置文件中的端口设置
    config_file = os.path.join(install_dir, "data", "webui_config.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            port = config.get('settings', {}).get('port', 7860)
            total_checks += 1
            if check_port_available(port):
                passed_checks += 1
        except Exception as e:
            print(f"✗ 无法读取端口配置: {e}")
            total_checks += 1
    else:
        print("✗ 配置文件不存在，无法检查端口")
        total_checks += 1
    
    print()
    
    # 6. 检查用户配置
    print("6. 用户配置检查:")
    print("-" * 30)
    
    user_file = os.path.join(install_dir, "user.json")
    if os.path.exists(user_file):
        try:
            with open(user_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
            if users:
                for username, user_info in users.items():
                    is_admin = user_info.get('is_admin', False)
                    admin_status = "管理员" if is_admin else "普通用户"
                    print(f"✓ 用户: {username} ({admin_status})")
                passed_checks += 1
            else:
                print("✗ 没有配置用户")
        except Exception as e:
            print(f"✗ 用户配置文件格式错误: {e}")
    else:
        print("✗ 用户配置文件不存在")
    
    total_checks += 1
    print()
    
    # 7. 检查安装记录
    print("7. 安装记录检查:")
    print("-" * 30)
    
    install_config_file = os.path.join(install_dir, "install_config.json")
    if os.path.exists(install_config_file):
        try:
            with open(install_config_file, 'r', encoding='utf-8') as f:
                install_config = json.load(f)
            print(f"✓ 安装路径: {install_config.get('install_path', '未知')}")
            print(f"✓ 安装日期: {install_config.get('install_date', '未知')}")
            print(f"✓ 版本: {install_config.get('version', '未知')}")
            passed_checks += 1
        except Exception as e:
            print(f"✗ 安装记录文件格式错误: {e}")
    else:
        print("✗ 安装记录文件不存在")
    
    total_checks += 1
    print()
    
    # 总结
    print("=" * 60)
    print("验证结果总结")
    print("=" * 60)
    print(f"总检查项: {total_checks}")
    print(f"通过检查: {passed_checks}")
    print(f"失败检查: {total_checks - passed_checks}")
    print(f"通过率: {(passed_checks/total_checks)*100:.1f}%")
    print()
    
    if passed_checks == total_checks:
        print("🎉 恭喜！安装验证完全通过！")
        print("MSST WebUI 已成功安装并配置完成。")
        print()
        print("下一步操作:")
        print("1. 双击 MSST.bat 启动程序")
        print("2. 或使用配置管理工具修改设置")
        print("3. 访问 http://localhost:端口号 使用WebUI")
    elif passed_checks >= total_checks * 0.8:
        print("⚠ 安装基本成功，但有一些小问题。")
        print("建议检查失败的检查项，但程序应该可以正常运行。")
    else:
        print("❌ 安装存在问题，建议重新安装。")
        print("请检查失败的检查项并解决问题。")
    
    print()
    print("按任意键退出...")
    input()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n验证被用户中断")
    except Exception as e:
        print(f"\n\n验证过程中发生错误: {e}")
        input("按任意键退出...")
