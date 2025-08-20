import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

import argparse
import time
import shutil
from webui.preset import Presets
from webui.utils import load_configs, get_vr_model, get_msst_model
from webui.setup import setup_webui, set_debug
from utils.constant import *
from utils.logger import get_logger
logger = get_logger()


def main(input_folder, store_dir, preset_path, output_format):
    preset_data = load_configs(preset_path)
    preset_version = preset_data.get("version", "Unknown version")
    if preset_version not in SUPPORTED_PRESET_VERSION:
        logger.error(f"Unsupported preset version: {preset_version}, supported version: {SUPPORTED_PRESET_VERSION}")

    os.makedirs(store_dir, exist_ok=True)

    direct_output = store_dir

    # 检查最终步骤的结果文件是否已存在，并识别缺失的文件
    missing_input_files = []
    final_step = preset_data["flow"][-1]  # 获取最后一步
    final_outputs = final_step.get("output_to_storage", [])
    
    if final_outputs:  # 如果最后一步有输出到存储的文件
        # 获取输入文件夹中的所有音频文件
        input_files = []
        for file in os.listdir(input_folder):
            if file.lower().endswith(('.wav', '.flac', '.mp3', '.m4a', '.aac')):
                input_files.append(file)
        
        if input_files:
            # 检查所有输入文件的最终输出是否都存在
            # 由于预设处理过程中文件名会被修改，我们需要检查最终的文件名格式
            all_final_outputs_exist = True
            
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
                    missing_input_files.append(input_file)  # 记录对应的输入文件
            
            if all_final_outputs_exist:
                logger.info(f"跳过预设处理: 所有最终结果文件已存在")
                return
            
            if missing_input_files:
                logger.info(f"检测到 {len(missing_input_files)} 个文件缺失，将只处理缺失的文件")

    # 如果有缺失的文件，创建只包含缺失文件的临时目录
    if missing_input_files:
        logger.info(f"创建临时目录，只处理缺失的文件")
        import uuid
        task_id = str(uuid.uuid4())[:8]  # 使用UUID的前8位作为任务ID
        TEMP_PATH = os.path.join("E:/MSSTcache", f"preset_task_{task_id}")
        
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
        
        input_to_use = temp_input_dir
        logger.info(f"临时输入目录包含 {len(missing_input_files)} 个文件")
    else:
        # 如果没有缺失文件，使用原始输入目录
        input_to_use = input_folder
        import uuid
        task_id = str(uuid.uuid4())[:8]  # 使用UUID的前8位作为任务ID
        TEMP_PATH = os.path.join("E:/MSSTcache", f"preset_task_{task_id}")
        
        if os.path.exists(TEMP_PATH):
            shutil.rmtree(TEMP_PATH)
        os.makedirs(TEMP_PATH, exist_ok=True)
    
    tmp_store_dir = os.path.join(TEMP_PATH, "step_1_output")

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
        if current_step == preset.total_steps - 1:
            input_to_use = tmp_store_dir
            tmp_store_dir = store_dir
        if preset.total_steps == 1:
            # 单步处理时，输出直接到最终目录
            tmp_store_dir = store_dir

        data = preset.get_step(step)
        model_type = data["model_type"]
        model_name = data["model_name"]
        input_to_next = data["input_to_next"]
        output_to_storage = data["output_to_storage"]

        logger.info(f"\033[33mStep {current_step + 1}: Running inference using {model_name}\033[0m")

        if model_type == "UVR_VR_Models":
            primary_stem, secondary_stem, _, _= get_vr_model(model_name)
            storage = {primary_stem:[], secondary_stem:[]}
            storage[input_to_next].append(tmp_store_dir)
            for stem in output_to_storage:
                storage[stem].append(direct_output)

            logger.debug(f"input_to_next: {input_to_next}, output_to_storage: {output_to_storage}, storage: {storage}")
            result = preset.vr_infer(model_name, input_to_use, storage, output_format)
            if result[0] == 0:
                logger.error(f"Failed to run VR model {model_name}, error: {result[1]}")
                return
        else:
            model_path, config_path, msst_model_type, _ = get_msst_model(model_name)
            stems = load_configs(config_path).training.get("instruments", [])
            storage = {stem:[] for stem in stems}
            storage[input_to_next].append(tmp_store_dir)
            for stem in output_to_storage:
                storage[stem].append(direct_output)

            logger.debug(f"input_to_next: {input_to_next}, output_to_storage: {output_to_storage}, storage: {storage}")
            result = preset.msst_infer(msst_model_type, config_path, model_path, input_to_use, storage, output_format)
            if result[0] == 0:
                logger.error(f"Failed to run MSST model {model_name}, error: {result[1]}")
                return
        current_step += 1

    if os.path.exists(TEMP_PATH):
        shutil.rmtree(TEMP_PATH)

    logger.info(f"\033[33mPreset: {preset_path} inference process completed, results saved to {store_dir}, "
                f"time cost: {round(time.time() - start_time, 2)}s\033[0m")


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.set_start_method('spawn', force=True)

    parser = argparse.ArgumentParser(description="Preset inference Command Line Interface", formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, max_help_position=60))
    parser.add_argument("-p", "--preset_path", type=str, help="Path to the preset file (*.json). To create a preset file, please refer to the documentation or use WebUI to create one.", required=True)
    parser.add_argument("-i", "--input_dir", type=str, default="input", help="Path to the input folder")
    parser.add_argument("-o", "--output_dir", type=str, default="results", help="Path to the output folder")
    parser.add_argument("-f", "--output_format", type=str, default="wav", choices=["wav", "mp3", "flac"], help="Output format of the audio")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    if not os.path.exists(args.preset_path):
        raise ValueError("Please specify the preset file")

    if not os.path.exists("configs"):
        shutil.copytree("configs_backup", "configs")
    if not os.path.exists("data"):
        shutil.copytree("data_backup", "data")

    setup_webui() # must be called because we use some functions from webui app
    set_debug(args)

    main(args.input_dir, args.output_dir, args.preset_path, args.output_format)
