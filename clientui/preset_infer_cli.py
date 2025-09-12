import os
import sys

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

import argparse
import time
import shutil
import json
from pathlib import Path
from webui.preset import Presets
from webui.utils import load_configs, get_vr_model, get_msst_model
from webui.setup import setup_webui, set_debug
from utils.constant import *
from utils.logger import get_logger

def get_cache_dir():
    """获取缓存目录"""
    try:
        with open('client_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('cache_dir', 'E:/MSSTcache/')
    except (FileNotFoundError, json.JSONDecodeError):
        return "E:/MSSTcache/"  # 默认目录

# 导入任务进度追踪
try:
    from clientui.task_progress import task_progress
except ImportError:
    task_progress = None

logger = get_logger()


def update_progress(input_folder, processed_count):
    """
    更新任务处理进度
    """
    if not task_progress:
        return
        
    # 尝试查找任务目录
    try:
        # 查找包含mission.json或mission_*.json的父目录
        current_dir = Path(input_folder)
        mission_dir = None
        
        # 先检查当前目录
        mission_files = list(current_dir.glob('mission*.json'))
        if mission_files:
            mission_dir = str(current_dir)
        else:
            # 检查父目录
            parent_dir = current_dir.parent
            mission_files = list(parent_dir.glob('mission*.json'))
            if mission_files:
                mission_dir = str(parent_dir)
        
        if mission_dir:
            # 更新进度
            task_progress.update_progress(mission_dir, {'processed_files': processed_count})
    except Exception as e:
        print(f"更新进度时出错: {e}")


def main(input_folder, store_dir, preset_path, output_format, skip_existing_files=False):
    print(f"调试信息 - preset_infer_cli.main: 开始执行")
    print(f"调试信息 - 输入文件夹: {input_folder}")
    print(f"调试信息 - 输出目录: {store_dir}")
    print(f"调试信息 - 预设路径: {preset_path}")
    print(f"调试信息 - 输出格式: {output_format}")
    print(f"调试信息 - 跳过已有文件: {skip_existing_files}")
    
    # 检查输入路径
    try:
        if os.path.exists(input_folder):
            print(f"调试信息 - 输入路径存在")
            if os.path.isdir(input_folder):
                print(f"调试信息 - 输入路径是目录")
                files = os.listdir(input_folder)
                print(f"调试信息 - 输入目录包含 {len(files)} 个文件/文件夹")
            else:
                print(f"调试信息 - 输入路径不是目录")
        else:
            print(f"调试信息 - 输入路径不存在: {input_folder}")
    except Exception as e:
        print(f"调试信息 - 检查输入路径时出错: {e}")
    
    preset_data = load_configs(preset_path)
    preset_version = preset_data.get("version", "Unknown version")
    if preset_version not in SUPPORTED_PRESET_VERSION:
        logger.error(f"Unsupported preset version: {preset_version}, supported version: {SUPPORTED_PRESET_VERSION}")

    os.makedirs(store_dir, exist_ok=True)

    direct_output = store_dir

    # 检查最终步骤的结果文件是否已存在，并识别缺失的文件
    missing_input_files = []
    if skip_existing_files:
        final_step = preset_data["flow"][-1]  # 获取最后一步
        final_outputs = final_step.get("output_to_storage", [])
        
        print(f"调试信息 - 最终步骤输出: {final_outputs}")
        
        if final_outputs:  # 如果最后一步有输出到存储的文件
            # 获取输入文件夹中的所有音频文件
            input_files = []
            for file in os.listdir(input_folder):
                if file.lower().endswith(('.wav', '.flac', '.mp3', '.m4a', '.aac')):
                    input_files.append(file)
            
            print(f"调试信息 - 输入文件数量: {len(input_files)}")
            
            if input_files:
                # 检查所有输入文件的最终输出是否都存在
                # 由于预设处理过程中文件名会被修改，我们需要检查最终的文件名格式
                all_final_outputs_exist = True
                missing_output_files = []
                
                # 获取预设的所有步骤，用于构建最终文件名
                preset_steps = preset_data["flow"]
                for input_file in input_files:
                    base_name = os.path.splitext(input_file)[0]
                    
                    # 构建最终文件名：经过所有步骤后的文件名
                    final_filename = base_name
                    for step in preset_steps:
                        if step.get("input_to_next"):
                            final_filename += f"_{step['input_to_next']}"
                    
                    # 如果最后一步有输出到存储，文件名就是当前构建的文件名
                    # 不需要额外添加后缀，因为input_to_next已经包含了最终的文件名部分
                    
                    output_file = os.path.join(store_dir, f"{final_filename}.{output_format}")
                    if not os.path.exists(output_file):
                        all_final_outputs_exist = False
                        missing_output_files.append(output_file)
                        missing_input_files.append(input_file)  # 记录对应的输入文件
                
                print(f"调试信息 - 所有最终输出文件都存在: {all_final_outputs_exist}")
                if missing_output_files:
                    print(f"调试信息 - 缺失的输出文件数量: {len(missing_output_files)}")
                    print(f"调试信息 - 需要处理的输入文件数量: {len(missing_input_files)}")
                    print(f"调试信息 - 缺失的文件: {missing_output_files[:5]}...")  # 只显示前5个
                
                if all_final_outputs_exist:
                    logger.info(f"跳过预设处理: 所有最终结果文件已存在")
                    print(f"调试信息 - 跳过预设处理: 所有最终结果文件已存在")
                    return

    # 如果有缺失的文件，创建只包含缺失文件的临时目录
    if missing_input_files:
        print(f"调试信息 - 创建临时目录，只处理缺失的文件")
        import uuid
        task_id = str(uuid.uuid4())[:8]  # 使用UUID的前8位作为任务ID
        TEMP_PATH = os.path.join(get_cache_dir(), f"preset_task_{task_id}")
        
        print(f"调试信息 - 临时路径: {TEMP_PATH}")
        
        if os.path.exists(TEMP_PATH):
            shutil.rmtree(TEMP_PATH)
        os.makedirs(TEMP_PATH, exist_ok=True)
        
        # 创建只包含缺失文件的临时输入目录
        temp_input_dir = os.path.join(TEMP_PATH, "temp_input")
        os.makedirs(temp_input_dir, exist_ok=True)
        
        # 复制缺失的文件到临时目录
        for missing_file in missing_input_files:
            src_path = os.path.join(input_folder, missing_file)
            dst_path = os.path.join(temp_input_dir, missing_file)
            shutil.copy2(src_path, dst_path)
            print(f"调试信息 - 复制文件: {missing_file}")
        
        input_to_use = temp_input_dir
        print(f"调试信息 - 临时输入目录包含 {len(missing_input_files)} 个文件")
    else:
        # 如果没有缺失文件，使用原始输入目录
        input_to_use = input_folder
        import uuid
        task_id = str(uuid.uuid4())[:8]  # 使用UUID的前8位作为任务ID
        TEMP_PATH = os.path.join(get_cache_dir(), f"preset_task_{task_id}")
        
        print(f"调试信息 - 临时路径: {TEMP_PATH}")
        
        if os.path.exists(TEMP_PATH):
            shutil.rmtree(TEMP_PATH)
        os.makedirs(TEMP_PATH, exist_ok=True)
    
    tmp_store_dir = os.path.join(TEMP_PATH, "step_1_output")
    os.makedirs(tmp_store_dir, exist_ok=True)

    preset = Presets(preset_data, force_cpu=False, use_tta=False, logger=logger)

    logger.info(f"Starting preset inference process, use presets: {preset_path}")
    logger.debug(f"presets: {preset.presets}")
    logger.debug(f"total_steps: {preset.total_steps}, store_dir: {store_dir}, output_format: {output_format}")

    if not preset.is_exist_models()[0]:
        logger.error(f"Model {preset.is_exist_models()[1]} not found")

    start_time = time.time()
    current_step = 0

    for step in range(preset.total_steps):
        if current_step == 0:
            # 第一步使用已经确定的input_to_use（可能是原始目录或临时目录）
            pass
        if preset.total_steps - 1 > current_step > 0:
            if input_to_use != input_folder and input_to_use != os.path.join(TEMP_PATH, "temp_input"):
                shutil.rmtree(input_to_use)
            input_to_use = tmp_store_dir
            tmp_store_dir = os.path.join(TEMP_PATH, f"step_{current_step + 1}_output")
        if preset.total_steps == 1:
            # 单步处理：保持原始输入，输出直接到最终目录
            tmp_store_dir = store_dir
        elif current_step == preset.total_steps - 1:
            # 多步流程的最后一步：将上一步输出作为输入
            input_to_use = tmp_store_dir
            tmp_store_dir = store_dir

        data = preset.get_step(step)
        model_type = data["model_type"]
        model_name = data["model_name"]
        input_to_next = data["input_to_next"]
        output_to_storage = data["output_to_storage"]

        logger.info(f"\033[33mStep {current_step + 1}: Running inference using {model_name}\033[0m")
        
        # 统计已处理的文件数量
        processed_files = 0
        try:
            if os.path.exists(direct_output):
                for root, _, files in os.walk(direct_output):
                    processed_files += sum(1 for f in files if f.lower().endswith(('.wav', '.flac', '.mp3')))
            # 更新进度
            update_progress(input_folder, processed_files)
        except Exception as e:
            logger.error(f"统计处理文件数量时出错: {e}")

        if model_type == "UVR_VR_Models":
            primary_stem, secondary_stem, _, _ = get_vr_model(model_name)
            storage = {primary_stem: [], secondary_stem: []}
            storage[input_to_next].append(tmp_store_dir)
            for stem in output_to_storage:
                storage[stem].append(direct_output)

            logger.debug(f"input_to_next: {input_to_next}, output_to_storage: {output_to_storage}, storage: {storage}")
            result = preset.vr_infer(model_name, input_to_use, storage, output_format, skip_existing_files)
            if result[0] == 0:
                logger.error(f"Failed to run VR model {model_name}, error: {result[1]}")
                return
        else:
            model_path, config_path, msst_model_type, _ = get_msst_model(model_name)
            stems = load_configs(config_path).training.get("instruments", [])
            storage = {stem: [] for stem in stems}
            storage[input_to_next].append(tmp_store_dir)
            for stem in output_to_storage:
                storage[stem].append(direct_output)

            logger.debug(f"input_to_next: {input_to_next}, output_to_storage: {output_to_storage}, storage: {storage}")
            result = preset.msst_infer(msst_model_type, config_path, model_path, input_to_use, storage, output_format, skip_existing_files)
            if result[0] == 0:
                logger.error(f"Failed to run MSST model {model_name}, error: {result[1]}")
                return
        current_step += 1

    if os.path.exists(TEMP_PATH):
        shutil.rmtree(TEMP_PATH)
    
    # 统计最终处理的文件数量
    processed_files = 0
    try:
        if os.path.exists(store_dir):
            for root, _, files in os.walk(store_dir):
                processed_files += sum(1 for f in files if f.lower().endswith(('.wav', '.flac', '.mp3')))
        # 更新最终进度
        update_progress(input_folder, processed_files)
    except Exception as e:
        logger.error(f"统计最终处理文件数量时出错: {e}")

    logger.info(f"\033[33mPreset: {preset_path} inference process completed, results saved to {store_dir}, "
                f"time cost: {round(time.time() - start_time, 2)}s\033[0m")


def main_batch(input_folders, store_dir, preset_path, output_format, skip_existing_files=False):
    """
    批量处理多个文件夹，复用已加载的模型
    """
    print(f"调试信息 - preset_infer_cli.main_batch: 开始批量执行")
    print(f"调试信息 - 输入文件夹列表: {input_folders}")
    print(f"调试信息 - 输出目录: {store_dir}")
    print(f"调试信息 - 预设路径: {preset_path}")
    print(f"调试信息 - 输出格式: {output_format}")
    print(f"调试信息 - 跳过已有文件: {skip_existing_files}")
    
    preset_data = load_configs(preset_path)
    preset_version = preset_data.get("version", "Unknown version")
    if preset_version not in SUPPORTED_PRESET_VERSION:
        logger.error(f"Unsupported preset version: {preset_version}, supported version: {SUPPORTED_PRESET_VERSION}")

    os.makedirs(store_dir, exist_ok=True)

    # 检查最终步骤的结果文件是否已存在
    if skip_existing_files:
        final_step = preset_data["flow"][-1]  # 获取最后一步
        final_outputs = final_step.get("output_to_storage", [])
        
        if final_outputs:  # 如果最后一步有输出到存储的文件
            # 检查所有输入文件夹的所有文件的最终输出是否都存在
            all_final_outputs_exist = True
            for input_folder in input_folders:
                input_files = []
                for file in os.listdir(input_folder):
                    if file.lower().endswith(('.wav', '.flac', '.mp3', '.m4a', '.aac')):
                        input_files.append(file)
                
                if input_files:
                    for input_file in input_files:
                        base_name = os.path.splitext(input_file)[0]
                        for output_stem in final_outputs:
                            output_file = os.path.join(store_dir, f"{base_name}_{output_stem}.{output_format}")
                            if not os.path.exists(output_file):
                                all_final_outputs_exist = False
                                break
                        if not all_final_outputs_exist:
                            break
                
                if not all_final_outputs_exist:
                    break
            
            if all_final_outputs_exist:
                logger.info(f"跳过批量预设处理: 所有最终结果文件已存在")
                print(f"调试信息 - 跳过批量预设处理: 所有最终结果文件已存在")
                return

    # 使用全局缓存目录，为每个批量任务创建唯一的临时目录
    import uuid
    task_id = str(uuid.uuid4())[:8]  # 使用UUID的前8位作为任务ID
    TEMP_PATH = os.path.join(get_cache_dir(), f"batch_task_{task_id}")
    
    print(f"调试信息 - 批量任务临时路径: {TEMP_PATH}")
    
    if os.path.exists(TEMP_PATH):
        shutil.rmtree(TEMP_PATH)
    os.makedirs(TEMP_PATH, exist_ok=True)

    preset = Presets(preset_data, force_cpu=False, use_tta=False, logger=logger)

    logger.info(f"Starting batch preset inference process, use presets: {preset_path}")
    logger.debug(f"presets: {preset.presets}")
    logger.debug(f"total_steps: {preset.total_steps}, store_dir: {store_dir}, output_format: {output_format}")

    if not preset.is_exist_models()[0]:
        logger.error(f"Model {preset.is_exist_models()[1]} not found")

    start_time = time.time()
    current_step = 0
    temp_dirs_to_cleanup = []  # 记录需要清理的临时目录

    for step in range(preset.total_steps):
        data = preset.get_step(step)
        model_type = data["model_type"]
        model_name = data["model_name"]
        input_to_next = data["input_to_next"]
        output_to_storage = data["output_to_storage"]

        logger.info(f"\033[33mStep {current_step + 1}: Running batch inference using {model_name}\033[0m")
        
        # 为每个步骤创建临时目录（在缓存目录中）
        step_temp_dir = os.path.join(TEMP_PATH, f"step_{current_step + 1}_tmp")
        if os.path.exists(step_temp_dir):
            shutil.rmtree(step_temp_dir)
        os.makedirs(step_temp_dir, exist_ok=True)
        temp_dirs_to_cleanup.append(step_temp_dir)  # 记录需要清理的目录
        
        # 为每个输入文件夹创建对应的输出目录
        step_output_dirs = []
        for i, input_folder in enumerate(input_folders):
            folder_name = os.path.basename(input_folder)
            output_dir = os.path.join(step_temp_dir, f"{folder_name}_output")
            os.makedirs(output_dir, exist_ok=True)
            step_output_dirs.append(output_dir)

        if model_type == "UVR_VR_Models":
            # VR模型暂时不支持批量处理，回退到单个处理
            logger.warning("VR模型暂不支持批量处理，回退到单个处理模式")
            for i, input_folder in enumerate(input_folders):
                primary_stem, secondary_stem, _, _ = get_vr_model(model_name)
                storage = {primary_stem: [], secondary_stem: []}
                storage[input_to_next].append(step_output_dirs[i])
                for stem in output_to_storage:
                    storage[stem].append(store_dir)

                logger.debug(f"处理文件夹 {i+1}/{len(input_folders)}: {input_folder}")
                result = preset.vr_infer(model_name, input_folder, storage, output_format, skip_existing_files)
                if result[0] == 0:
                    logger.error(f"Failed to run VR model {model_name} on {input_folder}, error: {result[1]}")
                    continue
        else:
            model_path, config_path, msst_model_type, _ = get_msst_model(model_name)
            stems = load_configs(config_path).training.get("instruments", [])
            
            # 使用批量处理
            storage = {stem: [] for stem in stems}
            storage[input_to_next].extend(step_output_dirs)
            for stem in output_to_storage:
                storage[stem].append(store_dir)

            logger.debug(f"input_to_next: {input_to_next}, output_to_storage: {output_to_storage}, storage: {storage}")
            result = preset.msst_infer_batch(msst_model_type, config_path, model_path, input_folders, storage, output_format, skip_existing_files)
            if result[0] == 0:
                logger.error(f"Failed to run MSST batch model {model_name}, error: {result[1]}")
                return
        
        # 更新输入文件夹列表为当前步骤的输出目录
        input_folders = step_output_dirs
        current_step += 1

    # 清理所有临时目录
    try:
        for temp_dir in temp_dirs_to_cleanup:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                print(f"已清理临时目录: {temp_dir}")
        
        # 清理主临时目录
        if os.path.exists(TEMP_PATH):
            shutil.rmtree(TEMP_PATH)
            print(f"已清理主临时目录: {TEMP_PATH}")
    except Exception as e:
        print(f"清理临时目录时出错: {e}")
    
    # 统计最终处理的文件数量
    processed_files = 0
    try:
        if os.path.exists(store_dir):
            for root, _, files in os.walk(store_dir):
                processed_files += sum(1 for f in files if f.lower().endswith(('.wav', '.flac', '.mp3')))
    except Exception as e:
        logger.error(f"统计最终处理文件数量时出错: {e}")

    logger.info(f"\033[33mBatch preset: {preset_path} inference process completed, results saved to {store_dir}, "
                f"time cost: {round(time.time() - start_time, 2)}s\033[0m")


if __name__ == "__main__":
    import multiprocessing

    multiprocessing.set_start_method('spawn', force=True)

    parser = argparse.ArgumentParser(description="Preset inference Command Line Interface",
                                     formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog,
                                                                                                max_help_position=60))
    parser.add_argument("-p", "--preset_path", type=str,
                        help="Path to the preset file (*.json). To create a preset file, please refer to the documentation or use WebUI to create one.",
                        required=True)
    parser.add_argument("-i", "--input_dir", type=str, action='append', help="Path to the input folder (can be specified multiple times for batch processing)")
    parser.add_argument("-o", "--output_dir", type=str, default="results", help="Path to the output folder")
    parser.add_argument("-f", "--output_format", type=str, default="wav", choices=["wav", "mp3", "flac"],
                        help="Output format of the audio")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--batch", action="store_true", help="Enable batch processing mode")
    args = parser.parse_args()

    print(f"调试信息 - 命令行参数解析完成")
    print(f"调试信息 - 预设路径: {args.preset_path}")
    print(f"调试信息 - 输入目录: {args.input_dir}")
    print(f"调试信息 - 输出目录: {args.output_dir}")
    print(f"调试信息 - 输出格式: {args.output_format}")
    print(f"调试信息 - 调试模式: {args.debug}")
    print(f"调试信息 - 批量处理模式: {args.batch}")

    if not os.path.exists(args.preset_path):
        raise ValueError("Please specify the preset file")

    if not os.path.exists("configs"):
        shutil.copytree("configs_backup", "configs")
    if not os.path.exists("data"):
        shutil.copytree("data_backup", "data")

    setup_webui()  # must be called because we use some functions from webui app
    set_debug(args)

    if args.batch and args.input_dir and len(args.input_dir) > 1:
        # 批量处理模式
        print(f"调试信息 - 使用批量处理模式，处理 {len(args.input_dir)} 个输入目录")
        main_batch(args.input_dir, args.output_dir, args.preset_path, args.output_format)
    else:
        # 单个处理模式
        input_dir = args.input_dir[0] if args.input_dir else "input"
        main(input_dir, args.output_dir, args.preset_path, args.output_format)
