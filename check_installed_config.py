#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查安装后的配置文件
"""

import json
import os

def check_installed_config():
    """检查安装后的配置文件"""
    print("=== 检查安装后的配置文件 ===")
    
    # 检查可能的安装路径
    possible_paths = [
        "D:\\MSST WebUI",
        "C:\\Program Files\\MSST WebUI",
        "C:\\Program Files (x86)\\MSST WebUI"
    ]
    
    for install_path in possible_paths:
        if os.path.exists(install_path):
            print(f"找到安装路径: {install_path}")
            
            # 检查配置文件
            config_files = [
                "data\\webui_config.json",
                "client_config.json",
                "user.json"
            ]
            
            for config_file in config_files:
                full_path = os.path.join(install_path, config_file)
                if os.path.exists(full_path):
                    print(f"\n检查配置文件: {full_path}")
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        print(f"文件大小: {len(content)} 字符")
                        print(f"前200个字符:")
                        print(content[:200])
                        
                        # 尝试解析JSON
                        config = json.loads(content)
                        print("✅ JSON格式正确")
                        
                        # 检查路径字段
                        if "settings" in config:
                            settings = config["settings"]
                            for field in ["input_dir", "output_dir", "cache_dir", "user_dir"]:
                                if field in settings:
                                    print(f"  {field}: {settings[field]}")
                                    
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON格式错误: {e}")
                        print(f"错误位置: 第{e.lineno}行，第{e.colno}列")
                        
                        # 显示错误位置附近的内容
                        lines = content.split('\n')
                        if e.lineno <= len(lines):
                            error_line = lines[e.lineno - 1]
                            print(f"错误行内容: {error_line}")
                            if e.colno <= len(error_line):
                                print(f"错误位置: {' ' * (e.colno - 1)}^")
                                
                    except Exception as e:
                        print(f"❌ 读取错误: {e}")
                else:
                    print(f"❌ 配置文件不存在: {full_path}")
            
            break
    else:
        print("❌ 未找到安装路径")

if __name__ == "__main__":
    check_installed_config()
