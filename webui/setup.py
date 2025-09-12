__license__= "AGPL-3.0"
__author__ = "Sucial https://github.com/SUC-DriverOld"

import os
import shutil
import tempfile
from webui.utils import i18n, logger
from utils.constant import *
from webui.utils import load_configs, save_configs, log_level_debug, get_main_link


def create_directory_with_fallback(dir_path, dir_name="directory"):
    """
    智能目录创建函数，支持权限检测和回退机制
    如果在安装目录创建失败，则回退到用户目录
    """
    try:
        # 尝试在指定路径创建目录
        os.makedirs(dir_path, exist_ok=True)
        logger.debug(f"Successfully created {dir_name}: {dir_path}")
        return dir_path
    except PermissionError:
        # 权限被拒绝，尝试在用户目录创建
        logger.warning(f"Permission denied for {dir_path}, using user directory fallback")
        
        # 获取用户临时目录
        user_temp = tempfile.gettempdir()
        fallback_base = os.path.join(user_temp, "MSST_WebUI")
        
        # 使用原始目录名作为子目录
        original_dirname = os.path.basename(dir_path.rstrip(os.sep))
        fallback_path = os.path.join(fallback_base, original_dirname)
        
        try:
            os.makedirs(fallback_path, exist_ok=True)
            logger.info(f"Created {dir_name} in user directory: {fallback_path}")
            return fallback_path
        except Exception as fallback_error:
            logger.error(f"Failed to create {dir_name} in user directory: {fallback_error}")
            # 返回原路径，让调用者决定如何处理
            return dir_path
    except Exception as e:
        logger.error(f"Unexpected error creating {dir_name} {dir_path}: {e}")
        return dir_path


def setup_directories():
    """
    设置所需的目录结构，使用智能权限处理
    """
    logger.debug("Setting up directory structure")
    
    # 创建工作目录列表
    directories = [
        ("input", "输入目录"),
        ("results", "输出目录"),
        ("cache", "缓存目录"),
        ("logs", "日志目录")
    ]
    
    created_dirs = {}
    
    for dir_name, display_name in directories:
        created_path = create_directory_with_fallback(dir_name, display_name)
        created_dirs[dir_name] = created_path
        
        # 如果路径发生了变化，记录并可能需要更新环境变量
        if os.path.abspath(created_path) != os.path.abspath(dir_name):
            logger.info(f"{display_name}重定向到: {created_path}")
    
    # 创建主缓存目录（可配置）
    try:
        # 尝试从配置中获取缓存路径
        main_cache_path = os.environ.get('MSST_CACHE_DIR', 'E:/MSSTcache')
        main_cache_created = create_directory_with_fallback(main_cache_path, "主缓存目录")
        created_dirs["main_cache"] = main_cache_created
        
        # 更新环境变量
        os.environ['MSST_CACHE_DIR'] = main_cache_created
        
    except Exception as e:
        logger.warning(f"无法创建主缓存目录，将使用本地缓存: {e}")
        created_dirs["main_cache"] = created_dirs["cache"]
    
    return created_dirs


def copy_folders():
    if os.path.exists("configs"):
        shutil.rmtree("configs")
    shutil.copytree("configs_backup", "configs")
    if os.path.exists("data"):
        shutil.rmtree("data")
    shutil.copytree("data_backup", "data")


def update_configs_folder():
    config_dir = "configs"
    config_backup_dir = "configs_backup"

    for dirpath, _, files in os.walk(config_backup_dir):
        relative_path = os.path.relpath(dirpath, config_backup_dir)
        target_dir = os.path.join(config_dir, relative_path)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        for file in files:
            source_file = os.path.join(dirpath, file)
            target_file = os.path.join(target_dir, file)
            if not os.path.exists(target_file):
                shutil.copyfile(source_file, target_file)


def set_debug(args):
    debug = False
    if os.path.isfile(WEBUI_CONFIG):
        debug = load_configs(WEBUI_CONFIG)["settings"].get("debug", False)
    if args.debug or debug:
        os.environ["CUDA_LAUNCH_BLOCKING"] = '1'
        log_level_debug(True)
    else:
        import warnings
        warnings.filterwarnings("ignore")
        log_level_debug(False)


def setup_webui():
    logger.debug("Starting WebUI setup")

    # 使用智能目录创建功能
    created_dirs = setup_directories()
    
    # 获取实际创建的缓存目录路径
    cache_dir = created_dirs.get("cache", "cache")
    main_cache_dir = created_dirs.get("main_cache", cache_dir)

    webui_config = load_configs(WEBUI_CONFIG)
    logger.debug(f"Loading WebUI config: {webui_config}")
    version = webui_config.get("version", None)

    if not version:
        try: 
            version = load_configs("data/version.json")["version"]
        except:
            copy_folders()
            version = PACKAGE_VERSION
            logger.warning("Can't find old version, copying backup folders")

    if version != PACKAGE_VERSION:
        logger.info(i18n("检测到") + version + i18n("旧版配置, 正在更新至最新版") + PACKAGE_VERSION)
        webui_config_backup = load_configs(WEBUI_CONFIG_BACKUP)

        for module in ["training", "inference", "tools", "settings"]:
            for key in webui_config_backup[module].keys():
                try: 
                    webui_config_backup[module][key] = webui_config[module][key]
                except KeyError: 
                    continue

        if os.path.exists("data"):
            shutil.rmtree("data")
        shutil.copytree("data_backup", "data")

        update_configs_folder()
        logger.debug("Copied new configs from configs_backup to configs")

        save_configs(webui_config_backup, WEBUI_CONFIG)
        webui_config = webui_config_backup
        logger.debug("Merging old config with new config")

    # 智能处理缓存清理
    if webui_config["settings"].get("auto_clean_cache", False):
        try:
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
            create_directory_with_fallback(cache_dir, "缓存目录")
            logger.info(i18n("成功清理Gradio缓存"))
        except Exception as e:
            logger.warning(f"清理缓存时出错: {e}，将继续运行")

    # 设置环境变量
    main_link = get_main_link()
    
    try:
        os.environ["HF_HOME"] = os.path.abspath(MODEL_FOLDER)
        os.environ["HF_ENDPOINT"] = "https://" + main_link
        os.environ["PATH"] += os.pathsep + os.path.abspath("ffmpeg/bin/")
        os.environ["GRADIO_TEMP_DIR"] = os.path.abspath(cache_dir)

        logger.debug("Set HF_HOME to: " + os.path.abspath(MODEL_FOLDER))
        logger.debug("Set HF_ENDPOINT to: " + "https://" + main_link)
        logger.debug("Set ffmpeg PATH to: " + os.path.abspath("ffmpeg/bin/"))
        logger.debug("Set GRADIO_TEMP_DIR to: " + os.path.abspath(cache_dir))
        
        # 如果主缓存目录与本地缓存不同，也设置环境变量
        if main_cache_dir != cache_dir:
            os.environ["MSST_MAIN_CACHE"] = os.path.abspath(main_cache_dir)
            logger.debug("Set MSST_MAIN_CACHE to: " + os.path.abspath(main_cache_dir))
            
    except Exception as e:
        logger.warning(f"设置环境变量时出错: {e}，将使用默认配置")

    return webui_config
