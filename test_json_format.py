#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试JSON格式生成
"""

import json

def test_json_generation():
    """测试JSON格式生成"""
    # 模拟安装脚本生成的JSON内容
    user_dir = r"C:\Users\Administrator\AppData\Local\MSST_WebUI\user"
    cache_dir = r"C:\Users\Administrator\AppData\Local\MSST_WebUI\cache"
    temp_dir = r"C:\Users\Administrator\AppData\Local\MSST_WebUI\cache\temp"
    app_path = r"D:\MSST WebUI"
    
    # 测试webui_config.json格式
    webui_config = {
        "version": "1.7.0 v2",
        "inference": {
            "model_type": "multi_stem_models",
            "selected_model": None,
            "input_dir": user_dir,
            "store_dir": user_dir,
            "device": None,
            "output_format": "wav",
            "force_cpu": False,
            "instrumental": None,
            "use_tta": False,
            "preset": "test_preset.json",
            "preset_use_tta": False,
            "extra_output_dir": False,
            "vr_select_model": None,
            "vr_window_size": 512,
            "vr_aggression": 5,
            "vr_batch_size": 2,
            "vr_primary_stem_only": False,
            "vr_secondary_stem_only": False,
            "vr_post_process_threshold": 0.2,
            "vr_invert_spect": False,
            "vr_enable_tta": False,
            "vr_high_end_process": False,
            "vr_enable_post_process": False,
            "ensemble_type": None,
            "ensemble_use_tta": False,
            "ensemble_extract_inst": False,
            "ensemble_preset": None
        },
        "tools": {
            "store_dir": None,
            "output_format": "wav",
            "sample_rate": 44100,
            "channels": 2,
            "wav_bit_depth": "PCM-16",
            "flac_bit_depth": "16-bit",
            "mp3_bit_rate": "320k",
            "ogg_bit_rate": "320k",
            "merge_audio_input": None
        },
        "training": {
            "model_type": None,
            "config_path": None,
            "dataset_type": None,
            "dataset_path": None,
            "valid_path": None,
            "num_workers": 0,
            "device": None,
            "seed": 0,
            "pin_memory": False,
            "use_multistft_loss": False,
            "use_mse_loss": False,
            "use_l1_loss": False,
            "accelerate": False,
            "pre_valid": False,
            "metrics": None,
            "metrics_scheduler": None,
            "results_path": None
        },
        "settings": {
            "uvr_model_dir": f"{app_path}\\pretrain\\VR_Models",
            "port": 7860,
            "language": "Auto",
            "download_link": "Auto",
            "local_link": False,
            "share_link": False,
            "auto_clean_cache": True,
            "debug": False,
            "theme": "theme_blue.json",
            "wav_bit_depth": "FLOAT",
            "flac_bit_depth": "PCM_24",
            "mp3_bit_rate": "320k",
            "input_dir": user_dir,
            "output_dir": user_dir,
            "cache_dir": cache_dir,
            "user_dir": user_dir
        }
    }
    
    # 测试客户端配置
    client_config = {
        "client_port": 7861,
        "server_port": 7860,
        "server_address": "localhost",
        "user_dir": user_dir,
        "cache_dir": cache_dir,
        "temp_dir": temp_dir,
        "auto_clean_temp": True,
        "max_file_size": 100,
        "allowed_formats": [
            "wav",
            "mp3",
            "flac",
            "m4a",
            "ogg"
        ]
    }
    
    # 测试用户配置
    user_config = {
        "admin": {
            "psw": "TEMP_admin123",
            "is_admin": True
        }
    }
    
    # 测试安装配置
    install_config = {
        "install_path": app_path,
        "port": 7860,
        "username": "admin",
        "user_dir": user_dir,
        "cache_dir": cache_dir,
        "install_date": "2025-01-08 10:25:52",
        "version": "1.0.0"
    }
    
    # 测试JSON序列化
    configs = {
        "webui_config.json": webui_config,
        "client_config.json": client_config,
        "user.json": user_config,
        "install_config.json": install_config
    }
    
    for filename, config in configs.items():
        try:
            json_str = json.dumps(config, indent=4, ensure_ascii=False)
            # 验证可以重新解析
            parsed = json.loads(json_str)
            print(f"✅ {filename} - JSON格式正确")
            print(f"   文件大小: {len(json_str)} 字符")
            
            # 检查路径字段
            if "settings" in config:
                settings = config["settings"]
                for field in ["input_dir", "output_dir", "cache_dir", "user_dir"]:
                    if field in settings:
                        print(f"   {field}: {settings[field]}")
                        
        except Exception as e:
            print(f"❌ {filename} - JSON格式错误: {e}")

if __name__ == "__main__":
    test_json_generation()
