__license__= "AGPL-3.0"
__author__ = "Sucial https://github.com/SUC-DriverOld"

import json
import locale
import platform
import yaml
import tkinter as tk
import gradio as gr
import logging
from tkinter import filedialog
from ml_collections import ConfigDict

from utils.constant import *
from utils.logger import get_logger, set_log_level
from tools.i18n import I18nAuto


# load and save config files
def load_configs(config_path):
    def get_user_config_path(original_path):
        """获取用户配置文件路径"""
        import tempfile
        import os
        
        user_temp = tempfile.gettempdir()
        user_config_dir = os.path.join(user_temp, "MSST_WebUI_Config")
        filename = os.path.basename(original_path)
        return os.path.join(user_config_dir, filename)
    
    def load_from_path(path):
        """从指定路径加载配置"""
        if path.endswith('.json'):
            with open(path, 'r', encoding="utf-8") as f:
                return json.load(f)
        elif path.endswith('.yaml') or path.endswith('.yml'):
            with open(path, 'r', encoding="utf-8") as f:
                return ConfigDict(yaml.load(f, Loader=yaml.FullLoader))
    
    try:
        # 尝试从原始路径加载
        return load_from_path(config_path)
    except (FileNotFoundError, PermissionError) as e:
        # 如果原始路径不可访问，尝试从用户目录加载
        user_config_path = get_user_config_path(config_path)
        if os.path.exists(user_config_path):
            try:
                logger.info(f"Loading configuration from user directory: {user_config_path}")
                return load_from_path(user_config_path)
            except Exception as user_error:
                logger.error(f"Failed to load configuration from user directory: {user_error}")
        
        # 如果用户目录也不可用，尝试从备份加载
        if config_path.endswith('webui_config.json'):
            backup_path = config_path.replace('data/', 'data_backup/')
            try:
                logger.warning(f"Loading configuration from backup: {backup_path}")
                return load_from_path(backup_path)
            except Exception as backup_error:
                logger.error(f"Failed to load backup configuration: {backup_error}")
        
        # 重新抛出原始异常
        raise e

def save_configs(config, config_path):
    def get_user_config_path(original_path):
        """获取用户配置文件路径"""
        import tempfile
        import os
        
        # 获取用户临时目录
        user_temp = tempfile.gettempdir()
        # 创建MSST配置目录
        user_config_dir = os.path.join(user_temp, "MSST_WebUI_Config")
        os.makedirs(user_config_dir, exist_ok=True)
        
        # 使用原始文件名
        filename = os.path.basename(original_path)
        return os.path.join(user_config_dir, filename)
    
    def save_to_path(config, path):
        """保存配置到指定路径"""
        if path.endswith('.json'):
            with open(path, 'w', encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        elif path.endswith('.yaml') or path.endswith('.yml'):
            with open(path, 'w', encoding="utf-8") as f:
                yaml.dump(config.to_dict(), f)
    
    try:
        # 尝试保存到原始路径
        save_to_path(config, config_path)
        logger.debug(f"Configuration saved to: {config_path}")
    except PermissionError as e:
        # 权限被拒绝，保存到用户目录
        user_config_path = get_user_config_path(config_path)
        try:
            save_to_path(config, user_config_path)
            logger.warning(f"Permission denied for {config_path}, saved to user directory: {user_config_path}")
            
            # 更新常量文件中的路径引用（仅对特定配置文件）
            if config_path == WEBUI_CONFIG:
                import utils.constant
                utils.constant.WEBUI_CONFIG = user_config_path
                logger.info(f"Updated WEBUI_CONFIG path to: {user_config_path}")
                
        except Exception as fallback_error:
            logger.error(f"Failed to save configuration to user directory {user_config_path}: {fallback_error}")
            # 最后的回退：显示警告但不崩溃
            logger.warning("Configuration changes will not be persisted for this session")
    except Exception as e:
        logger.error(f"Unexpected error saving configuration to {config_path}: {e}")

def color_config(config):
    def format_dict(d):
        items = []
        for k, v in sorted(d.items()):
            colored_key = f"\033[0;33m{k}\033[0m"
            if isinstance(v, dict):
                formatted_value = f"{{{format_dict(v)}}}"
            else:
                formatted_value = str(v)
            items.append(f"{colored_key}: {formatted_value}")
        return ", ".join(items)
    return f"{{{format_dict(config)}}}"


# get language from config file and setup i18n, model download main link
def get_language():
    try:
        config = load_configs(WEBUI_CONFIG)
        language = config['settings'].get('language', "Auto")
    except:
        language = "Auto"

    if language == "Auto":
        language = locale.getdefaultlocale()[0]
    return language

def get_main_link():
    try:
        config = load_configs(WEBUI_CONFIG)
        main_link = config['settings']['download_link']
    except:
        main_link = "Auto"

    if main_link == "Auto":
        main_link = "hf-mirror.com" if get_language() == "zh_CN" else "huggingface.co"
    return main_link

logger = get_logger()
i18n = I18nAuto(get_language())


# webui restart function
def webui_restart():
    logger.info("Restarting WebUI...")
    os.execl(PYTHON, PYTHON, *sys.argv)


# setup webui debug mode
def log_level_debug(isdug):
    try:
        config = load_configs(WEBUI_CONFIG)
    except Exception as e:
        logger.warning(f"Could not load config for debug setting: {e}")
        # 即使无法加载配置，也要设置日志级别
        if isdug:
            set_log_level(logger, logging.DEBUG)
            logger.info("Console log level set to \033[34mDEBUG\033[0m")
            return i18n("已开启调试日志")
        else:
            set_log_level(logger, logging.INFO)
            logger.info("Console log level set to \033[32mINFO\033[0m")
            return i18n("已关闭调试日志")
    
    if isdug:
        set_log_level(logger, logging.DEBUG)
        config["settings"]["debug"] = True
        try:
            save_configs(config, WEBUI_CONFIG)
            logger.info("Console log level set to \033[34mDEBUG\033[0m")
        except Exception as e:
            logger.warning(f"Debug level set but could not save config: {e}")
        return i18n("已开启调试日志")
    else:
        set_log_level(logger, logging.INFO)
        config["settings"]["debug"] = False
        try:
            save_configs(config, WEBUI_CONFIG)
            logger.info("Console log level set to \033[32mINFO\033[0m")
        except Exception as e:
            logger.warning(f"Debug level set but could not save config: {e}")
        return i18n("已关闭调试日志")


'''
following 5 functions are used for loading and getting model information.
- load_selected_model: return downloaded model list according to selected model type
- load_msst_model: return all downloaded msst model list
- get_msst_model: return model path, config path, model type, download link according to model name
- load_vr_model: return all downloaded uvr model list
- get_vr_model: return primary stem, secondary stem, model url, model path according to model name
'''
def load_selected_model(model_type=None):
    if not model_type:
        webui_config = load_configs(WEBUI_CONFIG)
        model_type = webui_config["inference"]["model_type"]
    if model_type:
        downloaded_model = []
        
        # 智能路径处理：尝试多种可能的模型目录位置
        possible_model_dirs = [
            os.path.join(MODEL_FOLDER, model_type),  # 相对路径
            os.path.join(os.getcwd(), MODEL_FOLDER, model_type),  # 当前工作目录
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", MODEL_FOLDER, model_type),  # 脚本相对路径
            os.path.join(os.path.abspath(MODEL_FOLDER), model_type) if os.path.exists(MODEL_FOLDER) else None  # 绝对路径
        ]
        
        # 过滤掉None值
        possible_model_dirs = [d for d in possible_model_dirs if d is not None]
        
        # 尝试各种可能的路径
        model_dir = None
        for dir_path in possible_model_dirs:
            try:
                normalized_path = os.path.abspath(dir_path)
                if os.path.exists(normalized_path):
                    model_dir = normalized_path
                    logger.debug(f"Found model directory for {model_type}: {model_dir}")
                    break
            except Exception as e:
                logger.debug(f"Failed to check model directory {dir_path}: {e}")
                continue
        
        # Check if model directory exists
        if not model_dir:
            logger.warning(f"Model directory does not exist for type: {model_type}")
            logger.warning(f"Tried paths: {possible_model_dirs}")
            return []
        
        try:
            for files in os.listdir(model_dir):
                if files.endswith(('.ckpt', '.th', '.chpt')):
                    try: 
                        get_msst_model(files, model_type)
                        downloaded_model.append(files)
                    except: 
                        continue
        except OSError as e:
            logger.error(f"Error accessing model directory {model_dir}: {e}")
            return []
        
        return downloaded_model
    return []

def load_msst_model():
    config = load_configs(MSST_MODEL)
    model_list = []
    
    # 为每个模型类型尝试多种可能的路径
    for keys in config.keys():
        possible_model_dirs = [
            os.path.join(MODEL_FOLDER, keys),  # 相对路径
            os.path.join(os.getcwd(), MODEL_FOLDER, keys),  # 当前工作目录
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", MODEL_FOLDER, keys),  # 脚本相对路径
            os.path.join(os.path.abspath(MODEL_FOLDER), keys) if os.path.exists(MODEL_FOLDER) else None  # 绝对路径
        ]
        
        # 过滤掉None值
        possible_model_dirs = [d for d in possible_model_dirs if d is not None]
        
        # 尝试各种可能的路径
        model_dir = None
        for dir_path in possible_model_dirs:
            try:
                normalized_path = os.path.abspath(dir_path)
                if os.path.exists(normalized_path):
                    model_dir = normalized_path
                    logger.debug(f"Found MSST model directory for {keys}: {model_dir}")
                    break
            except Exception as e:
                logger.debug(f"Failed to check MSST model directory {dir_path}: {e}")
                continue
        
        # Check if model directory exists
        if not model_dir:
            logger.warning(f"Model directory does not exist: {keys}")
            logger.debug(f"Tried paths for {keys}: {possible_model_dirs}")
            continue
        
        try:
            for files in os.listdir(model_dir):
                if files.endswith(('.ckpt', '.th', '.chpt')):
                    model_list.append(files)
        except OSError as e:
            logger.error(f"Error accessing model directory {model_dir}: {e}")
            continue
    
    return model_list

def get_msst_model(model_name, model_type=None):
    config = load_configs(MSST_MODEL)
    main_link = get_main_link()
    model_type = [model_type] if model_type else config.keys()

    for keys in model_type:
        for model in config[keys]:
            if model["name"] == model_name:
                model_type = model["model_type"]
                model_path = os.path.join(MODEL_FOLDER, keys, model_name)
                config_path = model["config_path"]
                download_link = model["link"]
                try:
                    download_link = download_link.replace("huggingface.co", main_link)
                except:
                    pass
                return model_path, config_path, model_type, download_link

    if os.path.isfile(os.path.join(UNOFFICIAL_MODEL, "unofficial_msst_model.json")):
        unofficial_config = load_configs(os.path.join(UNOFFICIAL_MODEL, "unofficial_msst_model.json"))
        for keys in model_type:
            for model in unofficial_config[keys]:
                if model["name"] == model_name:
                    model_type = model["model_type"]
                    model_path = os.path.join(MODEL_FOLDER, keys, model_name)
                    config_path = model["config_path"]
                    download_link = model["link"]
                    return model_path, config_path, model_type, download_link
    raise gr.Error(i18n("模型不存在!"))

def load_vr_model():
    downloaded_model = []
    config = load_configs(WEBUI_CONFIG)
    vr_model_path = config['settings']['uvr_model_dir']
    
    # 规范化路径分隔符，避免 D:\\... 之类路径导致找不到目录
    if isinstance(vr_model_path, str):
        vr_model_path = vr_model_path.replace('\\\\', '/').replace('\\', '/')
    
    # 智能路径处理和回退机制
    possible_paths = [
        vr_model_path,  # 配置文件中的原始路径
        os.path.abspath(vr_model_path),  # 绝对路径
        os.path.join(os.getcwd(), "pretrain", "VR_Models"),  # 当前工作目录下的相对路径
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pretrain", "VR_Models"),  # 脚本相对路径
        "pretrain/VR_Models",  # 简单相对路径
        "./pretrain/VR_Models"  # 当前目录相对路径
    ]
    
    # 尝试各种可能的路径
    final_vr_model_path = None
    for path in possible_paths:
        try:
            if isinstance(path, str):
                path = path.replace('\\', '/')
                normalized_path = os.path.abspath(path)
                if os.path.isdir(normalized_path):
                    final_vr_model_path = normalized_path
                    logger.info(f"Found VR model directory: {final_vr_model_path}")
                    break
        except Exception as e:
            logger.debug(f"Failed to check path {path}: {e}")
            continue
    
    # 若目录不存在，给出更友好的错误和解决建议
    if not final_vr_model_path:
        error_msg = f"VR模型目录不存在，请检查以下可能的路径：\n"
        for i, path in enumerate(possible_paths, 1):
            try:
                abs_path = os.path.abspath(path) if isinstance(path, str) else str(path)
                error_msg += f"{i}. {abs_path}\n"
            except:
                error_msg += f"{i}. {path}\n"
        error_msg += "\n解决方案：\n"
        error_msg += "1. 在设置中重新配置VR模型目录路径\n"
        error_msg += "2. 确保pretrain/VR_Models目录存在\n"
        error_msg += "3. 检查目录权限设置"
        raise gr.Error(i18n(error_msg))
    
    # 更新配置文件中的路径为找到的有效路径（使用正斜杠格式）
    try:
        if final_vr_model_path != vr_model_path:
            config['settings']['uvr_model_dir'] = final_vr_model_path.replace('\\', '/')
            save_configs(config, WEBUI_CONFIG)
            logger.info(f"Updated VR model path in config: {final_vr_model_path}")
    except Exception as e:
        logger.warning(f"Failed to update config with new VR model path: {e}")
    
    # 扫描模型文件
    try:
        for files in os.listdir(final_vr_model_path):
            if files.endswith('.pth'):
                try: 
                    get_vr_model(files)
                    downloaded_model.append(files)
                except: 
                    continue
    except OSError as e:
        logger.error(f"Error accessing VR model directory {final_vr_model_path}: {e}")
        raise gr.Error(i18n(f"无法访问VR模型目录: {final_vr_model_path}. 错误: {e}"))
    
    return downloaded_model

def get_vr_model(model):
    config = load_configs(VR_MODEL)
    model_path = load_configs(WEBUI_CONFIG)['settings']['uvr_model_dir']
    if isinstance(model_path, str):
        model_path = model_path.replace('\\\\', '/').replace('\\', '/')
    main_link = get_main_link()

    for keys in config.keys():
        if keys == model:
            primary_stem = config[keys]["primary_stem"]
            secondary_stem = config[keys]["secondary_stem"]
            model_url = config[keys]["download_link"]
            try:
                model_url = model_url.replace("huggingface.co", main_link)
            except: 
                pass
            return primary_stem, secondary_stem, model_url, model_path

    if os.path.isfile(os.path.join(UNOFFICIAL_MODEL, "unofficial_vr_model.json")):
        unofficial_config = load_configs(os.path.join(UNOFFICIAL_MODEL, "unofficial_vr_model.json"))
        for keys in unofficial_config.keys():
            if keys == model:
                primary_stem = unofficial_config[keys]["primary_stem"]
                secondary_stem = unofficial_config[keys]["secondary_stem"]
                model_url = unofficial_config[keys]["download_link"]
                return primary_stem, secondary_stem, model_url, model_path
    raise gr.Error(i18n("模型不存在!"))


# get model size and sha256 according to model name and model_info.json
def load_model_info(model_name):
    model_info = load_configs(MODELS_INFO)
    if model_name in model_info.keys():
        model_size = model_info[model_name].get("model_size", "Unknown")
        share256 = model_info[model_name].get("sha256", "Unknown")
        if model_size != "Unknown":
            model_size = round(int(model_size) / 1024 / 1024, 2)
    else:
        model_size = "Unknown"
        share256 = "Unknown"
    return model_size, share256


# update dropdown model list in webui according to selected model type
def update_model_name(model_type):
    if model_type == "UVR_VR_Models":
        model_map = load_vr_model()
        return gr.Dropdown(label=i18n("选择模型"), choices=model_map, interactive=True)
    else:
        model_map = load_selected_model(model_type)
        return gr.Dropdown(label=i18n("选择模型"), choices=model_map, interactive=True)


# change button visibility according to selected inference type
def change_to_audio_infer():
    return (gr.Button(i18n("输入音频分离"), variant="primary", visible=True),
            gr.Button(i18n("输入文件夹分离"), variant="primary", visible=False))

def change_to_folder_infer():
    return (gr.Button(i18n("输入音频分离"), variant="primary", visible=False),
            gr.Button(i18n("输入文件夹分离"), variant="primary", visible=True))


'''
following 4 functions are used for file and folder selection and open selected folder
- select_folder: use tkinter to select a folder and return the selected folder path
- select_yaml_file: use tkinter to select a yaml file and return the selected file path
- select_file: use tkinter to select a file and return the selected file path
- open_folder: open the selected folder in file explorer according to the selected folder path
'''
def select_folder():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    selected_dir = filedialog.askdirectory()
    root.destroy()
    return selected_dir

def select_yaml_file():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    selected_file = filedialog.askopenfilename(
        filetypes=[('YAML files', '*.yaml')])
    root.destroy()
    return selected_file

def select_file():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    selected_file = filedialog.askopenfilename(
        filetypes=[('All files', '*.*')])
    root.destroy()
    return selected_file

def open_folder(folder):
    if folder == "":
        raise gr.Error(i18n("请先选择文件夹!"))
    os.makedirs(folder, exist_ok=True)
    absolute_path = os.path.abspath(folder)
    if platform.system() == "Windows":
        os.system(f"explorer {absolute_path}")
    elif platform.system() == "Darwin":
        os.system(f"open {absolute_path}")
    else:
        os.system(f"xdg-open {absolute_path}")


# error manager, add more detailed solutions according to the error message
def detailed_error(e):
    e = str(e)
    m = None

    if "CUDA out of memory" in e or "CUBLAS_STATUS_NOT_INITIALIZED" in e:
        m = i18n("显存不足, 请尝试减小batchsize值和chunksize值后重试。")
    elif "页面文件太小" in e or "DataLoader worker" in e or "DLL load failed while" in e or "[WinError 1455]" in e:
        m = i18n("内存不足，请尝试增大虚拟内存后重试。若分离时出现此报错，也可尝试将推理音频裁切短一些，分段分离。")
    elif "ffprobe not found" in e:
        m = i18n("FFmpeg未找到，请检查FFmpeg是否正确安装。若使用的是整合包，请重新安装。")
    elif "failed reading zip archive" in e:
        m = i18n("模型损坏，请重新下载并安装模型后重试。")
    elif ("No such file or directory" in e or "系统找不到" in e or "[WinError 3]" in e or "[WinError 2]" in e
          or "The system cannot find the file specified" in e):
        m = i18n("文件或路径不存在，请根据错误指示检查是否存在该文件。")

    if m:
        e = m + "\n" + e
    return e