#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MSST WebUI 模型目录修复工具
用于解决模型目录不存在的问题
"""

import os
import sys
import json

def fix_model_paths():
    """修复模型路径配置"""
    print("=== MSST WebUI 模型目录修复工具 ===")
    
    # 获取当前工作目录
    current_dir = os.getcwd()
    print(f"当前工作目录: {current_dir}")
    
    # 检查配置文件
    config_file = "data/webui_config.json"
    if not os.path.exists(config_file):
        print(f"❌ 配置文件不存在: {config_file}")
        return False
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")
        return False
    
    # 检查和修复VR模型目录
    pretrain_vr_path = os.path.join(current_dir, "pretrain", "VR_Models")
    if os.path.exists(pretrain_vr_path):
        # 使用正斜杠格式
        fixed_path = pretrain_vr_path.replace('\\', '/')
        config['settings']['uvr_model_dir'] = fixed_path
        print(f"✓ 修复VR模型目录: {fixed_path}")
    else:
        print(f"❌ VR模型目录不存在: {pretrain_vr_path}")
        print("请确保pretrain/VR_Models目录存在")
        return False
    
    # 检查其他模型目录
    model_types = ["multi_stem_models", "single_stem_models", "vocal_models"]
    for model_type in model_types:
        model_path = os.path.join(current_dir, "pretrain", model_type)
        if os.path.exists(model_path):
            print(f"✓ 模型目录存在: {model_type}")
        else:
            print(f"⚠ 模型目录不存在: {model_type}")
            # 创建目录
            try:
                os.makedirs(model_path, exist_ok=True)
                print(f"✓ 已创建目录: {model_path}")
            except Exception as e:
                print(f"❌ 创建目录失败: {e}")
    
    # 保存修复后的配置
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        print("✓ 配置文件已保存")
        return True
    except Exception as e:
        print(f"❌ 保存配置文件失败: {e}")
        return False

if __name__ == "__main__":
    success = fix_model_paths()
    if success:
        print("\n🎉 模型目录修复完成！")
        print("现在可以重新运行程序。")
    else:
        print("\n❌ 修复失败，请检查上述错误信息。")
    
    # 检查是否是安装过程中调用（通过命令行参数）
    if len(sys.argv) > 1 and sys.argv[1] == "--silent":
        # 静默模式，不等待用户输入
        sys.exit(0 if success else 1)
    else:
        # 交互模式，等待用户输入
        input("按Enter键退出...")