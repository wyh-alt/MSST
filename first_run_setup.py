#!/usr/bin/env python3
"""
MSST WebUI 首次启动配置脚本
用于安装后的首次运行时进行必要的配置和检查
"""

import os
import sys
import json
import hashlib
from pathlib import Path

def setup_first_run():
    """执行首次运行配置"""
    print("=== MSST WebUI First Run Setup ===")
    print("=== MSST WebUI 首次运行配置 ===")
    
    success = True
    
    try:
        # 检查并处理用户配置文件
        if process_user_config():
            print("✓ User configuration processed successfully")
            print("✓ 用户配置处理成功")
        else:
            print("⚠ Warning: User configuration processing failed")
            print("⚠ 警告: 用户配置处理失败")
            success = False
        
        # 检查缓存目录
        if check_cache_directory():
            print("✓ Cache directory verified")
            print("✓ 缓存目录验证成功")
        else:
            print("⚠ Warning: Cache directory check failed")
            print("⚠ 警告: 缓存目录检查失败")
            success = False
        
        # 检查必要的目录
        if create_required_directories():
            print("✓ Required directories created")
            print("✓ 必要目录创建成功")
        else:
            print("⚠ Warning: Failed to create some directories")
            print("⚠ 警告: 部分目录创建失败")
            success = False
        
        # 验证配置文件
        if verify_config_files():
            print("✓ Configuration files verified")
            print("✓ 配置文件验证成功")
        else:
            print("⚠ Warning: Configuration file verification failed")
            print("⚠ 警告: 配置文件验证失败")
            success = False
        
        if success:
            print("\n✅ First run setup completed successfully!")
            print("✅ 首次运行配置完成！")
        else:
            print("\n⚠ First run setup completed with warnings")
            print("⚠ 首次运行配置完成，但有警告")
        
    except Exception as e:
        print(f"\n❌ Error during first run setup: {e}")
        print(f"❌ 首次运行配置时出错: {e}")
        return False
    
    return success

def process_user_config():
    """处理用户配置文件，将临时密码转换为哈希"""
    user_file = Path("user.json")
    
    if not user_file.exists():
        print("No user configuration file found")
        print("未找到用户配置文件")
        return True
    
    try:
        with open(user_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
        
        modified = False
        for username, user_data in users.items():
            password = user_data.get('psw', '')
            
            # 检查是否是临时密码
            if password.startswith('TEMP_'):
                actual_password = password[5:]  # 去掉 'TEMP_' 前缀
                
                # 生成SHA256哈希
                password_hash = hashlib.sha256(actual_password.encode('utf-8')).hexdigest()
                
                # 更新用户数据
                users[username]['psw'] = password_hash
                
                # 删除说明字段（如果存在）
                if '_note' in users[username]:\n                    del users[username]['_note']\n                \n                print(f\"Password for user '{username}' has been hashed\")\n                print(f\"用户 '{username}' 的密码已哈希化\")\n                modified = True\n        \n        # 如果有修改，保存文件\n        if modified:\n            with open(user_file, 'w', encoding='utf-8') as f:\n                json.dump(users, f, indent=4, ensure_ascii=False)\n            print(\"User configuration file updated\")\n            print(\"用户配置文件已更新\")\n        \n        return True\n        \n    except Exception as e:\n        print(f\"Error processing user config: {e}\")\n        print(f\"处理用户配置时出错: {e}\")\n        return False\n\ndef check_cache_directory():\n    \"\"\"检查缓存目录\"\"\"\n    try:\n        # 从环境变量获取缓存目录\n        cache_dir = os.environ.get('GRADIO_TEMP_DIR')\n        \n        if cache_dir:\n            cache_path = Path(cache_dir)\n            cache_path.mkdir(parents=True, exist_ok=True)\n            \n            # 检查是否可写\n            test_file = cache_path / \"test_write.tmp\"\n            try:\n                test_file.write_text(\"test\")\n                test_file.unlink()\n                print(f\"Cache directory is writable: {cache_dir}\")\n                print(f\"缓存目录可写: {cache_dir}\")\n                return True\n            except Exception as e:\n                print(f\"Cache directory is not writable: {e}\")\n                print(f\"缓存目录不可写: {e}\")\n                return False\n        else:\n            print(\"No cache directory specified in environment\")\n            print(\"环境变量中未指定缓存目录\")\n            return True  # 不是错误，使用默认目录\n        \n    except Exception as e:\n        print(f\"Error checking cache directory: {e}\")\n        print(f\"检查缓存目录时出错: {e}\")\n        return False\n\ndef create_required_directories():\n    \"\"\"创建必要的目录\"\"\"\n    required_dirs = [\n        \"logs\",\n        \"cache\", \n        \"tmpdir\",\n        \"input\",\n        \"results\"\n    ]\n    \n    success = True\n    \n    for dir_name in required_dirs:\n        try:\n            Path(dir_name).mkdir(exist_ok=True)\n        except Exception as e:\n            print(f\"Failed to create directory '{dir_name}': {e}\")\n            print(f\"创建目录 '{dir_name}' 失败: {e}\")\n            success = False\n    \n    return success\n\ndef verify_config_files():\n    \"\"\"验证配置文件\"\"\"\n    config_files = [\n        \"data/webui_config.json\",\n        \"config.json\"\n    ]\n    \n    success = True\n    \n    for config_file in config_files:\n        config_path = Path(config_file)\n        \n        if config_path.exists():\n            try:\n                with open(config_path, 'r', encoding='utf-8') as f:\n                    json.load(f)  # 验证JSON格式\n            except Exception as e:\n                print(f\"Invalid JSON in '{config_file}': {e}\")\n                print(f\"'{config_file}' 中的JSON格式无效: {e}\")\n                success = False\n        else:\n            # 某些配置文件不存在不是错误\n            if config_file == \"config.json\":\n                continue\n            print(f\"Configuration file missing: {config_file}\")\n            print(f\"配置文件缺失: {config_file}\")\n            success = False\n    \n    return success\n\ndef main():\n    \"\"\"主函数\"\"\"\n    if len(sys.argv) > 1 and sys.argv[1] == \"--check-only\":\n        print(\"Running configuration check only...\")\n        print(\"仅运行配置检查...\")\n    \n    success = setup_first_run()\n    \n    if not success:\n        print(\"\\nSome issues were found during setup.\")\n        print(\"安装过程中发现一些问题。\")\n        print(\"The application should still work, but you may want to check the warnings above.\")\n        print(\"应用程序应该仍然可以工作，但您可能需要检查上述警告。\")\n    \n    return 0 if success else 1\n\nif __name__ == \"__main__\":\n    exit(main())