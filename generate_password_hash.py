#!/usr/bin/env python3
"""
密码哈希生成工具
用于为 MSST WebUI 生成 SHA256 密码哈希
"""

import hashlib
import sys
import json
from pathlib import Path

def generate_sha256_hash(password):
    """生成SHA256密码哈希"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def create_user_config(username, password, output_path="user.json"):
    """创建用户配置文件"""
    password_hash = generate_sha256_hash(password)
    
    user_config = {
        username: {
            "psw": password_hash,
            "is_admin": True
        }
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(user_config, f, indent=4, ensure_ascii=False)
    
    return password_hash

def main():
    """主函数"""
    if len(sys.argv) != 3:
        print("Usage: python generate_password_hash.py <username> <password>")
        print("用法: python generate_password_hash.py <用户名> <密码>")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    
    # 生成密码哈希
    password_hash = generate_sha256_hash(password)
    
    # 输出结果
    print(f"Username: {username}")
    print(f"Password Hash (SHA256): {password_hash}")
    
    # 创建用户配置文件
    try:
        create_user_config(username, password)
        print(f"User configuration saved to: user.json")
        print(f"用户配置已保存到: user.json")
    except Exception as e:
        print(f"Error creating user config: {e}")
        print(f"创建用户配置时出错: {e}")

if __name__ == "__main__":
    main()