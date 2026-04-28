#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断配置管理工具问题
"""

import os
import sys
import json
from pathlib import Path

def diagnose_config_manager():
    """诊断配置管理工具的问题"""
    print("=== 配置管理工具诊断 ===")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"脚本所在目录: {os.path.dirname(os.path.abspath(__file__))}")
    print()
    
    # 测试配置文件路径
    config_paths = [
        "data/webui_config.json",
        "client_config.json",
        "user.json"
    ]
    
    for config_path in config_paths:
        print(f"检查配置文件: {config_path}")
        
        # 检查相对路径
        if os.path.exists(config_path):
            print(f"  ✅ 相对路径存在: {os.path.abspath(config_path)}")
        else:
            print(f"  ❌ 相对路径不存在")
            
        # 检查脚本目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, config_path)
        if os.path.exists(script_path):
            print(f"  ✅ 脚本目录存在: {script_path}")
        else:
            print(f"  ❌ 脚本目录不存在")
            
        # 检查上级目录
        parent_path = os.path.join(os.path.dirname(script_dir), config_path)
        if os.path.exists(parent_path):
            print(f"  ✅ 上级目录存在: {parent_path}")
        else:
            print(f"  ❌ 上级目录不存在")
        print()
    
    # 测试配置管理工具的路径查找逻辑
    print("=== 测试配置管理工具路径查找 ===")
    
    def _find_config_file(relative_path):
        """复制配置管理工具的路径查找逻辑"""
        # 首先尝试当前目录
        if os.path.exists(relative_path):
            return relative_path
            
        # 尝试脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, relative_path)
        if os.path.exists(script_path):
            return script_path
            
        # 尝试上级目录
        parent_path = os.path.join(os.path.dirname(script_dir), relative_path)
        if os.path.exists(parent_path):
            return parent_path
            
        # 如果都找不到，返回原始路径（让后续错误处理）
        return relative_path
    
    for config_path in config_paths:
        found_path = _find_config_file(config_path)
        print(f"{config_path} -> {found_path}")
        
        if os.path.exists(found_path):
            try:
                with open(found_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                print(f"  ✅ 可以正常读取JSON")
            except Exception as e:
                print(f"  ❌ JSON读取错误: {e}")
        else:
            print(f"  ❌ 文件不存在")

if __name__ == "__main__":
    diagnose_config_manager()
