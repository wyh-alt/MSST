import os
import sys

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

import argparse
import time
import shutil
import json
import threading
from pathlib import Path
from webui.preset import Presets
from webui.utils import load_configs, get_vr_model, get_msst_model
from webui.setup import setup_webui, set_debug
from utils.constant import *
from utils.constant import get_cache_dir
from utils.logger import get_logger

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


def update_step_progress(input_folder, step_index, processed_count):
    """
    更新步骤处理进度
    """
    if not task_progress:
        return
        
    # 尝试查找任务目录
    try:
        # 查找包含mission.json或mission_*.json的父目录
        current_dir = Path(input_folder)
        mission_dir = None
        
        # 向上查找任务目录（最多3层）
        for _ in range(3):
            if not current_dir or current_dir == current_dir.parent:
                break
            
            # 检查当前目录是否有mission.json
            mission_files = list(current_dir.glob('mission*.json'))
            if mission_files:
                mission_dir = str(current_dir)
                break
            
            current_dir = current_dir.parent
        
        if mission_dir:
            # 更新步骤进度
            task_progress.update_step_progress(mission_dir, step_index, processed_count)
            print(f"调试信息 - 更新步骤 {step_index} 进度: {processed_count}")
    except Exception as e:
        print(f"更新步骤进度时出错: {e}")


def main(input_folder, store_dir, preset_path, output_format, skip_existing_files=False):
    print(f"调试信息 - preset_infer_cli.main: 开始执行")
    print(f"调试信息 - 输入文件夹: {input_folder}")
    print(f"调试信息 - 输出目录: {store_dir}")
    print(f"调试信息 - 预设路径: {preset_path}")
    print(f"调试信息 - 输出格式: {output_format}")
    print(f"调试信息 - 跳过已有文件: {skip_existing_files}")
    
    # 在开始时就确定任务目录，避免后续查找问题
    mission_dir_for_progress = None
    try:
        # 方法1: 从输入目录向上查找
        current_dir = Path(input_folder)
        print(f"调试信息 - 开始查找任务目录，从输入目录: {current_dir}")
        # 向上查找任务目录（最多8层）
        for i in range(8):
            if not current_dir or current_dir == current_dir.parent:
                print(f"调试信息 - 已到达根目录")
                break
            # 查找 mission*.json 或 progress.json
            mission_files = list(current_dir.glob('mission*.json'))
            progress_files = list(current_dir.glob('progress.json'))
            
            if mission_files or progress_files:
                mission_dir_for_progress = str(current_dir)
                print(f"调试信息 - ✅ 找到任务目录: {mission_dir_for_progress}")
                print(f"调试信息 - 找到文件: mission={len(mission_files)}, progress={len(progress_files)}")
                break
            
            print(f"调试信息 - 检查目录 {current_dir}: 未找到任务文件")
            current_dir = current_dir.parent
        
        # 方法2: 如果输入目录查找失败，尝试从输出目录查找
        if not mission_dir_for_progress and store_dir:
            print(f"调试信息 - 尝试从输出目录查找: {store_dir}")
            current_dir = Path(store_dir)
            for i in range(8):
                if not current_dir or current_dir == current_dir.parent:
                    break
                mission_files = list(current_dir.glob('mission*.json'))
                progress_files = list(current_dir.glob('progress.json'))
                
                if mission_files or progress_files:
                    mission_dir_for_progress = str(current_dir)
                    print(f"调试信息 - ✅ 从输出目录找到任务目录: {mission_dir_for_progress}")
                    break
                current_dir = current_dir.parent
        
        # 方法3: 检查输出目录中的 .mission_dir 标记文件（路径方式）
        if not mission_dir_for_progress and store_dir:
            marker_file = os.path.join(store_dir, '.mission_dir')
            if os.path.exists(marker_file):
                try:
                    with open(marker_file, 'r', encoding='utf-8') as f:
                        mission_dir_from_marker = f.read().strip()
                    if os.path.exists(mission_dir_from_marker):
                        mission_dir_for_progress = mission_dir_from_marker
                        print(f"调试信息 - ✅ 从标记文件找到任务目录: {mission_dir_for_progress}")
                except Exception as e:
                    print(f"调试信息 - 读取标记文件时出错: {e}")
        
        # 方法4: 如果还是找不到，尝试在输出目录创建进度文件（路径方式）
        if not mission_dir_for_progress and store_dir:
            print(f"调试信息 - 未找到任务目录，尝试在输出目录创建进度文件（路径方式）")
            try:
                # 检查输出目录是否可写
                test_file = os.path.join(store_dir, '.progress_test')
                try:
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)
                    # 可以写入，使用输出目录作为任务目录
                    mission_dir_for_progress = store_dir
                    print(f"调试信息 - ✅ 使用输出目录作为任务目录: {mission_dir_for_progress}")
                except:
                    print(f"调试信息 - ⚠️  输出目录不可写，无法创建进度文件")
            except Exception as e:
                print(f"调试信息 - 检查输出目录时出错: {e}")
        
        if not mission_dir_for_progress:
            print(f"调试信息 - ⚠️  未找到任务目录！分步骤进度将无法显示")
            print(f"调试信息 - 提示: 请确保输入/输出目录是任务目录的子目录，或任务目录中存在 mission.json 或 progress.json 文件")
    except Exception as e:
        print(f"调试信息 - ❌ 查找任务目录时出错: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"调试信息 - task_progress 是否可用: {task_progress is not None}")
    print(f"调试信息 - mission_dir_for_progress: {mission_dir_for_progress}")
    
    # 如果找到了任务目录，尝试初始化或更新进度追踪
    if mission_dir_for_progress and task_progress:
        try:
            # 提取预设文件名（不含路径）
            preset_filename = os.path.basename(preset_path)
            print(f"调试信息 - 预设文件名: {preset_filename}")
            
            # 检查进度文件是否存在
            progress_file = os.path.join(mission_dir_for_progress, 'progress.json')
            if not os.path.exists(progress_file):
                print(f"调试信息 - progress.json 不存在，初始化进度追踪")
                task_progress.init_progress(mission_dir_for_progress, input_folder, preset_filename)
            else:
                print(f"调试信息 - progress.json 已存在，检查是否需要更新")
                # 确保步骤信息已初始化
                progress_info = task_progress.get_progress(mission_dir_for_progress)
                if not progress_info:
                    print(f"调试信息 - 无法读取进度信息，重新初始化")
                    task_progress.init_progress(mission_dir_for_progress, input_folder, preset_filename)
                elif 'step_progress' not in progress_info or not progress_info.get('step_progress'):
                    print(f"调试信息 - 步骤进度信息缺失，重新初始化")
                    task_progress.init_progress(mission_dir_for_progress, input_folder, preset_filename)
                else:
                    step_keys = list(progress_info.get('step_progress', {}).keys())
                    print(f"调试信息 - ✅ 步骤进度信息已存在: {step_keys}")
                    # 注意: 步骤数量验证将在 preset 对象创建后进行（见下方第343-356行）
        except Exception as e:
            print(f"调试信息 - ❌ 初始化进度追踪时出错: {e}")
            import traceback
            traceback.print_exc()
    
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
    
    # 在创建 preset 后，再次检查并初始化进度（因为现在可以获取 total_steps）
    if mission_dir_for_progress and task_progress:
        try:
            preset_filename = os.path.basename(preset_path)
            progress_info = task_progress.get_progress(mission_dir_for_progress)
            if progress_info:
                step_progress = progress_info.get('step_progress', {})
                expected_steps = preset.total_steps
                actual_steps = len(step_progress) if step_progress else 0
                if actual_steps != expected_steps:
                    print(f"调试信息 - ⚠️  步骤数量不匹配: 预期 {expected_steps} 个，实际 {actual_steps} 个，重新初始化")
                    task_progress.init_progress(mission_dir_for_progress, input_folder, preset_filename)
        except Exception as e:
            print(f"调试信息 - 验证步骤数量时出错: {e}")

    logger.info(f"Starting preset inference process, use presets: {preset_path}")
    logger.debug(f"presets: {preset.presets}")
    logger.debug(f"total_steps: {preset.total_steps}, store_dir: {store_dir}, output_format: {output_format}")
    print(f"调试信息 - 预设总步骤数: {preset.total_steps}")
    print(f"调试信息 - 预设详情: {preset.presets}")

    if not preset.is_exist_models()[0]:
        logger.error(f"Model {preset.is_exist_models()[1]} not found")

    start_time = time.time()
    current_step = 0
    
    # 统计输入文件数量（用于步骤进度报告）
    input_file_count = 0
    try:
        if os.path.exists(input_to_use):
            input_file_count = len([f for f in os.listdir(input_to_use) if f.lower().endswith(('.wav', '.flac', '.mp3', '.m4a', '.aac'))])
    except:
        pass
    print(f"调试信息 - 输入文件数量: {input_file_count}", flush=True)
    logger.info(f"调试信息 - 输入文件数量: {input_file_count}")

    print(f"=== 开始多步骤处理循环，总步骤数: {preset.total_steps} ===", flush=True)
    logger.info(f"=== 开始多步骤处理循环，总步骤数: {preset.total_steps} ===")
    for step in range(preset.total_steps):
        print(f"\n=== 循环迭代: step={step}, current_step={current_step} ===", flush=True)
        logger.info(f"=== 循环迭代: step={step}, current_step={current_step} ===")
        print(f"调试信息 - 步骤处理前: input_to_use={input_to_use}, tmp_store_dir={tmp_store_dir}", flush=True)
        logger.info(f"调试信息 - 步骤处理前: input_to_use={input_to_use}, tmp_store_dir={tmp_store_dir}")
        
        if current_step == 0:
            # 第一步使用已经确定的input_to_use（可能是原始目录或临时目录）
            print(f"调试信息 - 第一步，保持input_to_use和tmp_store_dir不变")
            pass
        if preset.total_steps - 1 > current_step > 0:
            print(f"调试信息 - 中间步骤（current_step={current_step}），更新input和output目录")
            print(f"调试信息 - 条件检查: {preset.total_steps - 1} > {current_step} > 0 = {preset.total_steps - 1 > current_step > 0}")
            if input_to_use != input_folder and input_to_use != os.path.join(TEMP_PATH, "temp_input"):
                print(f"调试信息 - 删除上一步输入目录: {input_to_use}")
                shutil.rmtree(input_to_use)
            input_to_use = tmp_store_dir
            tmp_store_dir = os.path.join(TEMP_PATH, f"step_{current_step + 1}_output")
            print(f"调试信息 - 更新后: input_to_use={input_to_use}, tmp_store_dir={tmp_store_dir}")
        if preset.total_steps == 1:
            # 单步处理：保持原始输入，输出直接到最终目录
            print(f"调试信息 - 单步处理模式")
            tmp_store_dir = store_dir
        elif current_step == preset.total_steps - 1:
            # 多步流程的最后一步：将上一步输出作为输入
            print(f"调试信息 - 最后一步（current_step={current_step}），输出到最终目录")
            print(f"调试信息 - 条件检查: {current_step} == {preset.total_steps - 1} = {current_step == preset.total_steps - 1}")
            input_to_use = tmp_store_dir
            tmp_store_dir = store_dir
            print(f"调试信息 - 更新后: input_to_use={input_to_use}, tmp_store_dir={tmp_store_dir}")

        data = preset.get_step(step)
        model_type = data["model_type"]
        model_name = data["model_name"]
        input_to_next = data["input_to_next"]
        output_to_storage = data["output_to_storage"]

        print(f"调试信息 - 步骤详情: model_type={model_type}, model_name={model_name}")
        print(f"调试信息 - input_to_next={input_to_next}, output_to_storage={output_to_storage}")
        logger.info(f"\033[33mStep {current_step + 1}: Running inference using {model_name}\033[0m")
        
        # 步骤开始前，标记该步骤开始处理（processed = 0）
        if preset.total_steps > 1 and mission_dir_for_progress and task_progress:
            try:
                print(f"调试信息 - 更新步骤 {current_step + 1} 开始进度: processed=0")
                result = task_progress.update_step_progress(mission_dir_for_progress, current_step + 1, 0)
                print(f"调试信息 - 步骤开始进度更新结果: {result}")
            except Exception as e:
                print(f"❌ 更新步骤开始进度时出错: {e}")
                import traceback
                traceback.print_exc()
        
        # 启动进度监控线程，在推理过程中实时更新步骤进度
        progress_monitor_stop = threading.Event()
        progress_monitor_thread = None
        
        # 在步骤开始前记录输出目录中已有的文件数量（用于最后一步时排除之前步骤的输出）
        initial_file_count = 0
        if os.path.exists(tmp_store_dir):
            initial_files = [f for f in os.listdir(tmp_store_dir) 
                           if f.lower().endswith(('.wav', '.flac', '.mp3', '.m4a'))]
            initial_file_count = len(initial_files)
            if initial_file_count > 0:
                print(f"调试信息 - 步骤 {current_step + 1} 输出目录已有 {initial_file_count} 个文件（来自之前步骤）")
        
        if preset.total_steps > 1 and mission_dir_for_progress and task_progress:
            def monitor_progress():
                """后台监控线程，定期检查输出目录文件数并更新进度"""
                last_count = 0
                update_count = 0
                check_count = 0
                print(f"调试信息 - [监控线程] 步骤 {current_step + 1} 监控线程已启动")
                print(f"调试信息 - [监控线程] 监控目录: {tmp_store_dir}")
                print(f"调试信息 - [监控线程] 任务目录: {mission_dir_for_progress}")
                print(f"调试信息 - [监控线程] 初始文件数: {initial_file_count}")
                
                while not progress_monitor_stop.is_set():
                    try:
                        check_count += 1
                        current_count = 0
                        if os.path.exists(tmp_store_dir):
                            files = [f for f in os.listdir(tmp_store_dir) 
                                    if f.lower().endswith(('.wav', '.flac', '.mp3', '.m4a'))]
                            # 减去初始文件数，只统计当前步骤新增的文件
                            current_count = max(0, len(files) - initial_file_count)
                        else:
                            # 目录不存在，可能是第一步刚开始
                            if check_count % 10 == 0:  # 每10秒输出一次
                                print(f"调试信息 - [监控线程] 步骤 {current_step + 1} 输出目录不存在: {tmp_store_dir}")
                        
                        # 只在文件数量变化时更新
                        if current_count != last_count:
                            try:
                                result = task_progress.update_step_progress(mission_dir_for_progress, current_step + 1, current_count)
                                if result:
                                    last_count = current_count
                                    update_count += 1
                                    if update_count <= 5 or update_count % 10 == 1:  # 前5次和每10次更新输出日志
                                        print(f"调试信息 - [监控线程] ✅ 步骤 {current_step + 1} 进度更新: {current_count} 个文件 (更新次数: {update_count})")
                                else:
                                    if update_count == 0:  # 第一次更新失败时输出
                                        print(f"调试信息 - [监控线程] ❌ 步骤 {current_step + 1} 进度更新失败: update_step_progress 返回 False")
                            except Exception as e:
                                print(f"调试信息 - [监控线程] ❌ 更新进度时出错: {e}")
                                import traceback
                                traceback.print_exc()
                    except Exception as e:
                        print(f"调试信息 - [监控线程] ❌ 监控过程中出错: {e}")
                        import traceback
                        traceback.print_exc()
                    
                    # 每秒检查一次
                    progress_monitor_stop.wait(1)
                
                print(f"调试信息 - [监控线程] 步骤 {current_step + 1} 监控线程已停止 (共检查 {check_count} 次, 更新 {update_count} 次)")
            
            print(f"调试信息 - 启动步骤 {current_step + 1} 的进度监控线程")
            print(f"调试信息 - 监控参数: mission_dir={mission_dir_for_progress}, tmp_store_dir={tmp_store_dir}")
            progress_monitor_thread = threading.Thread(target=monitor_progress, daemon=True)
            progress_monitor_thread.start()

        if model_type == "UVR_VR_Models":
            primary_stem, secondary_stem, _, _ = get_vr_model(model_name)
            storage = {primary_stem: [], secondary_stem: []}
            storage[input_to_next].append(tmp_store_dir)
            for stem in output_to_storage:
                # 避免在最后一步时重复添加相同的输出目录
                # 当 tmp_store_dir == direct_output 且 stem == input_to_next 时会发生重复
                if direct_output not in storage[stem]:
                    storage[stem].append(direct_output)

            logger.debug(f"input_to_next: {input_to_next}, output_to_storage: {output_to_storage}, storage: {storage}")
            print(f"调试信息 - 开始执行VR推理: model={model_name}, input={input_to_use}, storage={storage}")
            result = preset.vr_infer(model_name, input_to_use, storage, output_format, skip_existing_files)
            print(f"调试信息 - VR推理完成，返回结果: {result}")
            if result[0] == 0:
                logger.error(f"Failed to run VR model {model_name}, error: {result[1]}")
                print(f"调试信息 - VR推理失败，提前返回")
                # 停止监控线程
                if progress_monitor_thread:
                    progress_monitor_stop.set()
                    progress_monitor_thread.join(timeout=2)
                return
            elif result[0] == -1:
                print(f"调试信息 - VR推理被用户终止，提前返回")
                # 停止监控线程
                if progress_monitor_thread:
                    progress_monitor_stop.set()
                    progress_monitor_thread.join(timeout=2)
                return
            else:
                print(f"调试信息 - VR推理成功，继续下一步")
        else:
            model_path, config_path, msst_model_type, _ = get_msst_model(model_name)
            stems = load_configs(config_path).training.get("instruments", [])
            storage = {stem: [] for stem in stems}
            storage[input_to_next].append(tmp_store_dir)
            for stem in output_to_storage:
                # 避免在最后一步时重复添加相同的输出目录
                # 当 tmp_store_dir == direct_output 且 stem == input_to_next 时会发生重复
                if direct_output not in storage[stem]:
                    storage[stem].append(direct_output)

            logger.debug(f"input_to_next: {input_to_next}, output_to_storage: {output_to_storage}, storage: {storage}")
            print(f"调试信息 - 开始执行MSST推理: model={model_name}, input={input_to_use}, storage={storage}", flush=True)
            logger.info(f"调试信息 - 开始执行MSST推理: model={model_name}, input={input_to_use}")
            try:
                result = preset.msst_infer(msst_model_type, config_path, model_path, input_to_use, storage, output_format, skip_existing_files)
                print(f"调试信息 - MSST推理完成，返回结果: {result}", flush=True)
                logger.info(f"调试信息 - MSST推理完成，返回结果: {result}")
                
                if result is None:
                    logger.error(f"MSST推理返回None，这不应该发生")
                    print(f"调试信息 - MSST推理返回None，提前返回")
                    # 停止监控线程
                    if progress_monitor_thread:
                        progress_monitor_stop.set()
                        progress_monitor_thread.join(timeout=2)
                    return
                
                if result[0] == 0:
                    logger.error(f"Failed to run MSST model {model_name}, error: {result[1]}")
                    print(f"调试信息 - MSST推理失败，提前返回")
                    # 停止监控线程
                    if progress_monitor_thread:
                        progress_monitor_stop.set()
                        progress_monitor_thread.join(timeout=2)
                    return
                elif result[0] == -1:
                    logger.warning(f"MSST推理被用户终止")
                    print(f"调试信息 - MSST推理被用户终止，提前返回")
                    # 停止监控线程
                    if progress_monitor_thread:
                        progress_monitor_stop.set()
                        progress_monitor_thread.join(timeout=2)
                    return
                else:
                    print(f"调试信息 - MSST推理成功，继续下一步")
                    logger.info(f"调试信息 - MSST推理成功，继续下一步，准备执行步骤 {current_step + 2}/{preset.total_steps}")
            except Exception as e:
                logger.error(f"MSST推理过程中发生异常: {str(e)}")
                print(f"调试信息 - MSST推理过程中发生异常: {str(e)}")
                import traceback
                traceback.print_exc()
                logger.error(traceback.format_exc())
                # 停止监控线程
                if progress_monitor_thread:
                    progress_monitor_stop.set()
                    progress_monitor_thread.join(timeout=2)
                return
        
        # 停止监控线程
        if progress_monitor_thread:
            progress_monitor_stop.set()
            progress_monitor_thread.join(timeout=2)
        
        # 步骤完成后，做最终的进度更新
        if preset.total_steps > 1 and mission_dir_for_progress and task_progress:
            # 统计输出目录中的文件数量作为已处理数量（减去初始文件数，只统计当前步骤新增的）
            processed_count = 0
            try:
                if os.path.exists(tmp_store_dir):
                    files = [f for f in os.listdir(tmp_store_dir) 
                            if f.lower().endswith(('.wav', '.flac', '.mp3', '.m4a'))]
                    total_files = len(files)
                    # 减去初始文件数，只统计当前步骤新增的文件
                    processed_count = max(0, total_files - initial_file_count)
                    print(f"调试信息 - 步骤 {current_step + 1} 输出目录包含 {total_files} 个文件（初始: {initial_file_count}, 新增: {processed_count}）")
                else:
                    print(f"调试信息 - ⚠️  步骤 {current_step + 1} 输出目录不存在: {tmp_store_dir}")
            except Exception as e:
                print(f"调试信息 - 统计输出文件失败: {e}")
                processed_count = input_file_count  # 如果无法统计，使用输入文件数
            
            try:
                print(f"调试信息 - 更新步骤 {current_step + 1} 最终进度: processed={processed_count}")
                result = task_progress.update_step_progress(mission_dir_for_progress, current_step + 1, processed_count)
                print(f"调试信息 - 步骤最终进度更新结果: {result}")
            except Exception as e:
                print(f"❌ 更新步骤完成进度时出错: {e}")
                import traceback
                traceback.print_exc()
        
        # 检查输出目录文件情况
        try:
            if os.path.exists(tmp_store_dir):
                output_files = [f for f in os.listdir(tmp_store_dir) 
                              if f.lower().endswith(('.wav', '.flac', '.mp3', '.m4a'))]
                print(f"调试信息 - 步骤 {current_step + 1} 完成，输出目录 {tmp_store_dir} 包含 {len(output_files)} 个文件")
                if len(output_files) > 0:
                    print(f"调试信息 - 前3个输出文件: {output_files[:3]}")
            else:
                print(f"调试信息 - 警告：输出目录 {tmp_store_dir} 不存在！")
        except Exception as e:
            print(f"调试信息 - 检查输出目录时出错: {e}")
        
        current_step += 1
        print(f"调试信息 - 步骤 {step + 1} 完成，current_step 更新为 {current_step}", flush=True)
        logger.info(f"调试信息 - 步骤 {step + 1} 完成，current_step 更新为 {current_step}")
        print(f"=== 循环迭代 {step + 1} 结束 ===", flush=True)
        logger.info(f"=== 循环迭代 {step + 1} 结束，准备执行下一步 ===")
        
        # 检查是否还有更多步骤需要执行
        if current_step < preset.total_steps:
            print(f"调试信息 - 还有 {preset.total_steps - current_step} 个步骤需要执行", flush=True)
            logger.info(f"调试信息 - 还有 {preset.total_steps - current_step} 个步骤需要执行")
        else:
            print(f"调试信息 - 所有步骤已完成", flush=True)
            logger.info(f"调试信息 - 所有步骤已完成")

    print(f"\n=== 所有步骤处理完成 ===", flush=True)
    logger.info(f"=== 所有步骤处理完成 ===")
    print(f"调试信息 - 共完成 {current_step} 个步骤（预期 {preset.total_steps} 个步骤）", flush=True)
    logger.info(f"调试信息 - 共完成 {current_step} 个步骤（预期 {preset.total_steps} 个步骤）")
    
    if os.path.exists(TEMP_PATH):
        print(f"调试信息 - 清理临时目录: {TEMP_PATH}", flush=True)
        logger.info(f"调试信息 - 清理临时目录: {TEMP_PATH}")
        shutil.rmtree(TEMP_PATH)
    
    # 清理输出目录中的 .mission_dir 标记文件（路径方式）
    if store_dir and os.path.exists(store_dir):
        marker_file = os.path.join(store_dir, '.mission_dir')
        if os.path.exists(marker_file):
            try:
                os.remove(marker_file)
                print(f"调试信息 - ✅ 已清理任务目录标记文件: {marker_file}")
            except Exception as e:
                print(f"调试信息 - ⚠️  清理标记文件失败: {e}")
    
    # 更新最终进度（使用输入文件数，因为总进度代表处理了多少首歌曲，而不是输出了多少个文件）
    try:
        if os.path.exists(store_dir):
            output_files_count = 0
            for root, _, files in os.walk(store_dir):
                output_files_count += sum(1 for f in files if f.lower().endswith(('.wav', '.flac', '.mp3')))
            print(f"调试信息 - 最终输出目录 {store_dir} 包含 {output_files_count} 个文件")
        # 更新最终进度（使用输入文件数量，表示成功处理的歌曲数）
        update_progress(input_folder, input_file_count)
        print(f"调试信息 - 更新总进度: {input_file_count} 首歌曲")
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

    print(f"调试信息 - 开始批量处理循环，总步骤数: {preset.total_steps}")
    for step in range(preset.total_steps):
        print(f"\n=== 批量处理循环迭代: step={step}, current_step={current_step} ===")
        data = preset.get_step(step)
        model_type = data["model_type"]
        model_name = data["model_name"]
        input_to_next = data["input_to_next"]
        output_to_storage = data["output_to_storage"]

        logger.info(f"\033[33mStep {current_step + 1}: Running batch inference using {model_name}\033[0m")
        print(f"调试信息 - 步骤 {current_step + 1}: 模型类型={model_type}, 模型名称={model_name}")
        print(f"调试信息 - 步骤 {current_step + 1}: input_to_next={input_to_next}, output_to_storage={output_to_storage}")
        
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
                    # 避免重复添加相同的输出目录
                    if store_dir not in storage[stem]:
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
                # 避免重复添加相同的输出目录
                if store_dir not in storage[stem]:
                    storage[stem].append(store_dir)

            logger.debug(f"input_to_next: {input_to_next}, output_to_storage: {output_to_storage}, storage: {storage}")
            result = preset.msst_infer_batch(msst_model_type, config_path, model_path, input_folders, storage, output_format, skip_existing_files)
            print(f"调试信息 - 步骤 {current_step + 1} MSST批量推理返回结果: {result}")
            if result[0] == 0:
                logger.error(f"Failed to run MSST batch model {model_name}, error: {result[1]}")
                print(f"调试信息 - 步骤 {current_step + 1} 失败，提前返回")
                return
            elif result[0] == -1:
                logger.warning(f"MSST batch model {model_name} was terminated by user")
                print(f"调试信息 - 步骤 {current_step + 1} 被用户终止，提前返回")
                return
            else:
                print(f"调试信息 - 步骤 {current_step + 1} 成功，继续下一步")
        
        # 更新输入文件夹列表为当前步骤的输出目录
        print(f"调试信息 - 步骤 {current_step + 1} 完成，更新输入文件夹列表")
        print(f"调试信息 - 步骤 {current_step + 1} 输出目录数量: {len(step_output_dirs)}")
        if len(step_output_dirs) > 0:
            print(f"调试信息 - 步骤 {current_step + 1} 第一个输出目录: {step_output_dirs[0]}")
            # 检查输出目录是否存在且有文件
            if os.path.exists(step_output_dirs[0]):
                output_files = [f for f in os.listdir(step_output_dirs[0]) 
                              if f.lower().endswith(('.wav', '.flac', '.mp3', '.m4a'))]
                print(f"调试信息 - 步骤 {current_step + 1} 第一个输出目录包含 {len(output_files)} 个文件")
        
        input_folders = step_output_dirs
        current_step += 1
        print(f"调试信息 - 步骤 {step + 1} 完成，current_step 更新为 {current_step}")
        print(f"=== 批量处理循环迭代 {step + 1} 结束 ===")

    print(f"\n=== 所有步骤处理完成 ===")
    print(f"调试信息 - 共完成 {current_step} 个步骤（预期 {preset.total_steps} 个步骤）")
    
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




