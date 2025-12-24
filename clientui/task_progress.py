import os
import json
import time
from pathlib import Path
import threading

class TaskProgress:
    def __init__(self):
        self._lock = threading.Lock()
        self._progress_cache = {}  # 缓存任务进度，避免频繁读取文件
        self._last_update = {}     # 记录上次更新时间，避免过于频繁的文件访问
        self._verifying = set()    # 正在验证的任务目录集合，防止递归调用
    
    def get_progress_file_path(self, mission_dir):
        """获取进度文件路径"""
        return os.path.join(mission_dir, 'progress.json')
    
    def init_progress(self, mission_dir, input_dir, preset_name=None):
        """初始化任务进度文件
        
        Args:
            mission_dir: 任务目录
            input_dir: 输入目录
            preset_name: 预设名称（可选），用于初始化步骤进度
        """
        try:
            # 初始化时先使用基本的文件统计
            total_files = 0
            processed_files = 0
            
            # 统计输入目录中的音频文件
            if os.path.isdir(input_dir):
                # 检查是否直接包含音频文件
                direct_files = []
                for file in os.listdir(input_dir):
                    file_path = os.path.join(input_dir, file)
                    if os.path.isfile(file_path) and file.lower().endswith(('.wav', '.flac', '.mp3', '.m4a', '.aac', '.ogg')):
                        direct_files.append(file_path)
                
                if direct_files:
                    # 直接包含音频文件
                    total_files = len(direct_files)
                    print(f"调试信息 - 初始化进度: 直接包含音频文件，总数 {total_files}")
                else:
                    # 包含子目录，每个子目录一首歌
                    subdirs = []
                    for item in os.listdir(input_dir):
                        item_path = os.path.join(input_dir, item)
                        if os.path.isdir(item_path):
                            subdirs.append(item_path)
                    total_files = len(subdirs)
                    print(f"调试信息 - 初始化进度: 包含子目录，总数 {total_files}")
            
            # 确保至少为1
            if total_files <= 0:
                total_files = 1
                print(f"调试信息 - 初始化进度: 未找到文件，设置为默认值 {total_files}")
            
            # 创建初始进度数据
            progress_data = {
                'total_files': total_files,
                'processed_files': processed_files,
                'last_update': time.time(),
                'start_time': time.time(),  # 记录任务开始时间
                'status': 'waiting',
                'details': [],  # 可以存储每个文件的处理状态
                'total_files_locked': False  # 允许后续更新总数
            }
            
            # 如果提供了预设名称，初始化步骤进度
            if preset_name:
                step_progress = self._init_step_progress(preset_name, total_files)
                if step_progress:
                    progress_data['step_progress'] = step_progress
                    progress_data['total_steps'] = len(step_progress)
                    print(f"调试信息 - 初始化步骤进度: {len(step_progress)} 个步骤")
            
            # 保存到文件
            progress_file = self.get_progress_file_path(mission_dir)
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=4, ensure_ascii=False)
                
            # 更新缓存
            with self._lock:
                self._progress_cache[mission_dir] = progress_data
                self._last_update[mission_dir] = time.time()
                
            print(f"调试信息 - 进度初始化完成: {total_files} 个文件")
            return progress_data
        except Exception as e:
            print(f"初始化任务进度时出错: {e}")
            return {
                'total_files': 0,
                'processed_files': 0,
                'status': 'error',
                'error_message': str(e)
            }
    
    def update_progress(self, mission_dir, progress_update):
        """更新任务进度
        
        Args:
            mission_dir: 任务目录
            progress_update: 要更新的进度数据，可以是部分数据
        """
        try:
            # 获取当前进度数据
            current_progress = self.get_progress(mission_dir)
            if not current_progress:
                return False
            
            # 检查总数是否已锁定
            is_locked = current_progress.get('total_files_locked', False)
            
            # 如果总数已锁定，不允许更新total_files
            if is_locked and 'total_files' in progress_update:
                # 保留原有的总数和锁定状态
                original_total = current_progress.get('total_files', 0)
                progress_update_copy = progress_update.copy()
                progress_update_copy['total_files'] = original_total
                progress_update_copy['total_files_locked'] = True
                current_progress.update(progress_update_copy)
                print(f"调试信息 - 总数已锁定，保持原有总数: {original_total}")
            else:
                # 正常更新
                if 'total_files' in progress_update:
                    print(f"调试信息 - 更新文件总数: {current_progress.get('total_files', 0)} -> {progress_update['total_files']}")
                current_progress.update(progress_update)
                
            current_progress['last_update'] = time.time()
            
            # 保存到文件
            progress_file = self.get_progress_file_path(mission_dir)
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(current_progress, f, indent=4, ensure_ascii=False)
                
            # 更新缓存
            with self._lock:
                self._progress_cache[mission_dir] = current_progress
                self._last_update[mission_dir] = time.time()
                
            return True
        except Exception as e:
            print(f"更新任务进度时出错: {e}")
            return False
    
    def get_progress(self, mission_dir):
        """获取任务进度"""
        try:
            progress_file = self.get_progress_file_path(mission_dir)
            
            # 检查缓存是否有效
            # 1. 缓存必须在30秒内
            # 2. 文件修改时间不能比缓存更新（防止其他进程修改了文件）
            current_time = time.time()
            cache_valid = False
            with self._lock:
                if mission_dir in self._progress_cache and current_time - self._last_update.get(mission_dir, 0) < 30:
                    # 检查文件是否被修改
                    if os.path.exists(progress_file):
                        try:
                            file_mtime = os.path.getmtime(progress_file)
                            cache_time = self._last_update.get(mission_dir, 0)
                            # 如果文件修改时间比缓存时间晚，说明文件被其他进程更新了，需要重新读取
                            if file_mtime <= cache_time:
                                cache_valid = True
                        except:
                            pass
                    else:
                        # 文件不存在，使用缓存
                        cache_valid = True
            
            if cache_valid:
                return self._progress_cache[mission_dir]
            
            # 从文件读取
            if os.path.exists(progress_file):
                try:
                    with open(progress_file, 'r', encoding='utf-8') as f:
                        progress_data = json.load(f)
                except (json.JSONDecodeError, RecursionError) as e:
                    print(f"JSON文件损坏或格式错误: {progress_file}, 错误: {e}")
                    # 删除损坏的文件，返回None让系统重新初始化
                    try:
                        os.remove(progress_file)
                    except:
                        pass
                    return None
                
                # 检查状态是否需要更新 - 如果有输出文件但状态仍为running
                # 只有在不在验证过程中时才调用，防止递归
                with self._lock:
                    should_verify = mission_dir not in self._verifying
                
                if should_verify:
                    self._verify_status(mission_dir, progress_data)
                    
                # 更新缓存
                with self._lock:
                    self._progress_cache[mission_dir] = progress_data
                    self._last_update[mission_dir] = current_time
                    
                return progress_data
            else:
                return None
        except Exception as e:
            print(f"获取任务进度时出错: {e}")
            return None
            
    def _verify_status(self, mission_dir, progress_data):
        """验证任务状态的正确性"""
        # 防止递归调用：如果正在验证此任务，直接返回
        with self._lock:
            if mission_dir in self._verifying:
                return
            self._verifying.add(mission_dir)
        
        try:
            # 注意：此方法中不再调用 update_progress，而是直接修改 progress_data 并调用 _save_progress_directly
            # 这样可以避免递归调用：update_progress -> get_progress -> _verify_status -> update_progress
            # 如果状态为running，但任务目录中有mission.json标记为completed，则更新状态
            if progress_data.get('status') == 'running':
                mission_json = os.path.join(mission_dir, 'mission.json')
                if os.path.exists(mission_json):
                    try:
                        with open(mission_json, 'r', encoding='utf-8') as f:
                            mission_data = json.load(f)
                            if mission_data.get('state') == 'completed':
                                progress_data['status'] = 'completed'
                                # 直接更新文件，避免调用 update_progress 导致递归
                                self._save_progress_directly(mission_dir, progress_data)
                    except:
                        pass
                        
                # 检查输出目录中是否有文件但未标记为完成
                # 只有在状态为running时才进行复杂的计算
                if progress_data.get('status') == 'running':
                    output_files = []
                    
                    # 检查主输出目录
                    outputs_dir = os.path.join(mission_dir, 'outputs')
                    if os.path.exists(outputs_dir):
                        output_files.extend([f for f in os.listdir(outputs_dir) if f.lower().endswith(('.wav', '.flac', '.mp3'))])
                    
                    # 检查批量输出目录（batch_output）
                    batch_outputs_dir = os.path.join(mission_dir, 'batch_output')
                    if os.path.exists(batch_outputs_dir):
                        output_files.extend([f for f in os.listdir(batch_outputs_dir) if f.lower().endswith(('.wav', '.flac', '.mp3'))])
                    
                    # 对于上传下载方式，还需要检查子任务的输出目录
                    inputs_dir = os.path.join(mission_dir, 'inputs')
                    if os.path.exists(inputs_dir):
                        for subdir_name in os.listdir(inputs_dir):
                            subdir_path = os.path.join(inputs_dir, subdir_name)
                            if os.path.isdir(subdir_path):
                                sub_outputs_dir = os.path.join(subdir_path, 'outputs')
                                if os.path.exists(sub_outputs_dir):
                                    output_files.extend([f for f in os.listdir(sub_outputs_dir) if f.lower().endswith(('.wav', '.flac', '.mp3'))])
                        
                        # 计算每首歌生成的输出文件数量
                        outputs_per_song = self._get_outputs_per_song(mission_dir)
                        
                        # 根据输出文件数计算已处理的歌曲数
                        if outputs_per_song > 0:
                            processed_songs = len(output_files) // outputs_per_song
                            # 确保已处理歌曲数不超过总歌曲数
                            total_songs = progress_data.get('total_files', 0)
                            if total_songs > 0:
                                processed_songs = min(processed_songs, total_songs)
                            
                            # 检查总数是否已锁定
                            is_locked = progress_data.get('total_files_locked', False)
                            current_total = progress_data.get('total_files', 0)
                            
                            if is_locked and current_total > 0:
                                # 总数已锁定，使用已有的总数
                                total_songs = current_total
                                # print(f"调试信息 - 使用已锁定的总歌曲数: {total_songs}")  # 注释掉调试信息
                            else:
                                # 总数未锁定，重新计算并锁定
                                total_songs = self._count_input_songs(mission_dir)
                                progress_data['total_files_locked'] = True
                                # print(f"调试信息 - 重新计算并锁定总歌曲数: {total_songs}")  # 注释掉调试信息
                            
                            # print(f"调试信息 - 输出文件数: {len(output_files)}, 每首歌输出数: {outputs_per_song}, 已处理歌曲数: {processed_songs}, 总歌曲数: {total_songs}")  # 注释掉调试信息
                            
                            # 更新进度信息（只更新已处理数量，总数已锁定）
                            if processed_songs != progress_data.get('processed_files', 0):
                                progress_data['processed_files'] = processed_songs
                                
                            # 只在第一次设置总数或总数为0时更新总数
                            if not is_locked or current_total <= 0:
                                progress_data['total_files'] = total_songs
                                progress_data['total_files_locked'] = True
                                
                            # 检查是否所有歌曲都处理完成
                            if processed_songs >= total_songs and total_songs > 0:
                                progress_data['status'] = 'completed'
                                # 只有在还没有结束时间时才设置
                                if not progress_data.get('end_time', 0):
                                    progress_data['end_time'] = time.time()  # 记录任务结束时间
                                
                                update_data = {
                                    'processed_files': processed_songs,
                                    'status': 'completed',
                                    'total_files_locked': True
                                }
                                # 只在总数未锁定时更新总数
                                if not is_locked or current_total <= 0:
                                    update_data['total_files'] = total_songs
                                # 只在还没有结束时间时才添加结束时间
                                if not progress_data.get('end_time', 0):
                                    update_data['end_time'] = progress_data['end_time']
                                # 直接更新数据并保存，避免调用 update_progress 导致递归
                                progress_data.update(update_data)
                                self._save_progress_directly(mission_dir, progress_data)
                            else:
                                # 否则确保状态为running
                                progress_data['status'] = 'running'
                                update_data = {
                                    'processed_files': processed_songs,
                                    'status': 'running',
                                    'total_files_locked': True
                                }
                                # 只在总数未锁定时更新总数
                                if not is_locked or current_total <= 0:
                                    update_data['total_files'] = total_songs
                                # 直接更新数据并保存，避免调用 update_progress 导致递归
                                progress_data.update(update_data)
                                self._save_progress_directly(mission_dir, progress_data)
        except Exception as e:
            print(f"验证任务状态时出错: {e}")
        finally:
            # 移除验证标志
            with self._lock:
                self._verifying.discard(mission_dir)
            
    def _save_progress_directly(self, mission_dir, progress_data):
        """直接保存进度数据到文件，不触发验证，避免递归"""
        try:
            progress_data['last_update'] = time.time()
            progress_file = self.get_progress_file_path(mission_dir)
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=4, ensure_ascii=False)
            
            # 更新缓存
            with self._lock:
                self._progress_cache[mission_dir] = progress_data
                self._last_update[mission_dir] = time.time()
        except Exception as e:
            print(f"直接保存进度数据时出错: {e}")
    
    def _init_step_progress(self, preset_name, total_files):
        """初始化步骤进度
        
        Args:
            preset_name: 预设名称
            total_files: 总文件数
            
        Returns:
            dict: 步骤进度字典，格式为 {'step1': {'name': '模型名', 'processed': 0, 'total': total_files}, ...}
        """
        try:
            preset_path = os.path.join('presets', preset_name)
            if not os.path.exists(preset_path):
                return None
            
            with open(preset_path, 'r', encoding='utf-8') as f:
                preset_data = json.load(f)
            
            flow = preset_data.get('flow', preset_data.get('steps', []))
            if not flow or len(flow) <= 1:
                # 单步骤或无步骤，不需要步骤进度
                return None
            
            step_progress = {}
            for i, step in enumerate(flow, 1):
                step_key = f'step{i}'
                model_name = step.get('model_name', f'步骤 {i}')
                step_progress[step_key] = {
                    'name': model_name,
                    'processed': 0,
                    'total': total_files
                }
            
            return step_progress
        except Exception as e:
            print(f"初始化步骤进度时出错: {e}")
            return None
    
    def update_step_progress(self, mission_dir, step_index, processed_files):
        """更新单个步骤的进度
        
        Args:
            mission_dir: 任务目录
            step_index: 步骤索引（从1开始）
            processed_files: 已处理文件数
        """
        try:
            current_progress = self.get_progress(mission_dir)
            if not current_progress:
                return False
            
            step_progress = current_progress.get('step_progress', {})
            if not step_progress:
                return False
            
            step_key = f'step{step_index}'
            if step_key in step_progress:
                step_progress[step_key]['processed'] = processed_files
                
                # 直接保存，避免递归
                current_progress['step_progress'] = step_progress
                self._save_progress_directly(mission_dir, current_progress)
                return True
            
            return False
        except Exception as e:
            print(f"更新步骤进度时出错: {e}")
            return False
    
    def _get_outputs_per_song(self, mission_dir):
        """获取每首歌生成的输出文件数量"""
        try:
            # 读取mission.json获取预设名称
            mission_json = os.path.join(mission_dir, 'mission.json')
            if os.path.exists(mission_json):
                with open(mission_json, 'r', encoding='utf-8') as f:
                    mission_data = json.load(f)
                    preset_name = mission_data.get('preset_name', '')
                    
                    if preset_name:
                        preset_path = os.path.join('presets', preset_name)
                        if os.path.exists(preset_path):
                            try:
                                with open(preset_path, 'r', encoding='utf-8') as f:
                                    preset_data = json.load(f)
                                
                                # 检查是否有steps字段（新格式）
                                steps = preset_data.get('steps', [])
                                if steps:
                                    # 新格式：使用steps
                                    total_outputs = 0
                                    for step in steps:
                                        outputs = step.get('output_to_storage', [])
                                        total_outputs += len(outputs)
                                else:
                                    # 旧格式：使用flow
                                    flow = preset_data.get('flow', [])
                                    total_outputs = 0
                                    for step in flow:
                                        outputs = step.get('output_to_storage', [])
                                        total_outputs += len(outputs)
                                
                                # print(f"调试信息 - 预设 {preset_name}: 每首歌输出 {total_outputs} 个文件")  # 注释掉调试信息
                                # 返回每首歌的输出文件数，至少为1
                                return max(1, total_outputs)
                            except (json.JSONDecodeError, RecursionError) as e:
                                print(f"预设文件损坏或格式错误: {preset_path}, 错误: {e}")
                                return 1  # 返回默认值
        except Exception as e:
            print(f"获取每首歌输出文件数时出错: {e}")
            
        # 默认每首歌生成1个输出文件
        return 1
        
    def _count_input_songs(self, mission_dir):
        """统计输入目录中的歌曲数量"""
        try:
            # 首先尝试从任务目录的inputs子目录统计（上传方式）
            inputs_dir = os.path.join(mission_dir, 'inputs')
            if os.path.exists(inputs_dir):
                # 先检查inputs目录下是否直接包含音频文件（单步骤处理多文件的情况）
                audio_files = []
                subdirs = []
                for item in os.listdir(inputs_dir):
                    item_path = os.path.join(inputs_dir, item)
                    if os.path.isdir(item_path):
                        subdirs.append(item_path)
                    elif os.path.isfile(item_path) and item.lower().endswith(('.wav', '.flac', '.mp3', '.m4a', '.aac', '.ogg')):
                        audio_files.append(item_path)
                
                # 如果直接包含音频文件，返回音频文件数量
                if audio_files:
                    # print(f"调试信息 - 从inputs目录统计到 {len(audio_files)} 首歌（直接音频文件）")  # 注释掉调试信息
                    return len(audio_files)
                
                # 否则统计子目录数量（每个子目录代表一首上传的歌）
                if subdirs:
                    # print(f"调试信息 - 从inputs目录统计到 {len(subdirs)} 首歌")  # 注释掉调试信息
                    return len(subdirs)
            
            # 如果没有inputs目录，则读取mission.json获取原始输入目录（路径方式）
            mission_json = os.path.join(mission_dir, 'mission.json')
            if os.path.exists(mission_json):
                try:
                    with open(mission_json, 'r', encoding='utf-8') as f:
                        mission_data = json.load(f)
                        input_dir = mission_data.get('input_dir', '')
                except (json.JSONDecodeError, RecursionError) as e:
                    print(f"mission.json文件损坏或格式错误: {mission_json}, 错误: {e}")
                    return 1  # 返回默认值
                    
                    if input_dir and os.path.exists(input_dir):
                        # 检查输入目录是否直接包含音频文件
                        direct_audio_files = []
                        for file in os.listdir(input_dir):
                            file_path = os.path.join(input_dir, file)
                            if os.path.isfile(file_path) and file.lower().endswith(('.wav', '.flac', '.mp3', '.m4a', '.aac', '.ogg')):
                                direct_audio_files.append(file_path)
                        
                        if direct_audio_files:
                            # 如果输入目录直接包含音频文件，返回文件数量
                            # print(f"调试信息 - 从原始输入目录统计到 {len(direct_audio_files)} 首歌")  # 注释掉调试信息
                            return len(direct_audio_files)
                        else:
                            # 如果输入目录包含子目录，统计子目录数量（每个子目录代表一首歌）
                            subdirs = []
                            for item in os.listdir(input_dir):
                                item_path = os.path.join(input_dir, item)
                                if os.path.isdir(item_path):
                                    subdirs.append(item_path)
                            # print(f"调试信息 - 从原始输入目录的子目录统计到 {len(subdirs)} 首歌")  # 注释掉调试信息
                            return len(subdirs)
        except Exception as e:
            print(f"统计输入歌曲数量时出错: {e}")
            
        # 如果无法获取，返回默认值1
        # print("调试信息 - 无法统计歌曲数量，返回默认值1")  # 注释掉调试信息
        return 1
        
    def get_total_duration(self, mission_dir):
        """获取任务总耗时（秒），包括排队等待时间"""
        try:
            progress_data = self.get_progress(mission_dir)
            if not progress_data:
                return 0
                
            start_time = progress_data.get('start_time', 0)
            if start_time == 0:
                return 0
                
            end_time = progress_data.get('end_time', 0)
            status = progress_data.get('status', '')
            
            if end_time > 0 and status in ['completed', 'stopped']:
                # 任务已完成或已停止，使用固定的结束时间
                return end_time - start_time
            elif status == 'running':
                # 任务正在运行，计算当前耗时
                return time.time() - start_time
            else:
                # 其他状态，返回0
                return 0
        except Exception as e:
            print(f"计算任务耗时时出错: {e}")
            return 0
            
    def get_processing_duration(self, mission_dir):
        """获取任务纯处理耗时（秒），不包括排队等待时间"""
        try:
            # 首先尝试从日志中提取处理耗时（最准确）
            log_duration = self.get_processing_duration_from_logs(mission_dir)
            if log_duration > 0:
                return log_duration
                
            # 如果日志中没有，则从进度文件中计算
            progress_data = self.get_progress(mission_dir)
            if not progress_data:
                return 0
                
            # 检查是否有处理开始时间记录
            processing_start = progress_data.get('processing_start_time', 0)
            
            # 如果没有处理开始时间，则尝试从mission.json中获取
            if processing_start == 0:
                mission_json = os.path.join(mission_dir, 'mission.json')
                if os.path.exists(mission_json):
                    try:
                        with open(mission_json, 'r', encoding='utf-8') as f:
                            mission_data = json.load(f)
                            # 如果任务状态为running或completed，则认为处理已开始
                            if mission_data.get('state') in ['running', 'completed']:
                                # 如果没有记录处理开始时间，使用文件修改时间作为近似值
                                processing_start = os.path.getmtime(mission_json)
                                # 更新到进度文件中
                                self.update_progress(mission_dir, {'processing_start_time': processing_start})
                    except:
                        pass
            
            # 如果仍然没有处理开始时间，则无法计算处理耗时
            if processing_start == 0:
                return 0
                
            end_time = progress_data.get('end_time', 0)
            status = progress_data.get('status', '')
            
            if end_time > 0 and status in ['completed', 'stopped']:
                # 任务已完成或已停止，使用固定的结束时间
                return end_time - processing_start
            elif status == 'running':
                # 任务正在运行，计算当前耗时
                return time.time() - processing_start
            else:
                # 其他状态，返回0
                return 0
        except Exception as e:
            print(f"计算任务处理耗时时出错: {e}")
            return 0
    
    def get_processing_duration_from_logs(self, mission_dir):
        """从日志中解析本任务的处理耗时（秒）。优先匹配包含该任务输出目录的 time cost 行。"""
        try:
            # 获取输出目录
            store_dir = None
            mission_json = os.path.join(mission_dir, 'mission.json')
            if os.path.exists(mission_json):
                try:
                    with open(mission_json, 'r', encoding='utf-8') as f:
                        mission_data = json.load(f)
                        store_dir = mission_data.get('output_dir')
                except Exception:
                    pass
            if not store_dir:
                default_outputs = os.path.join(mission_dir, 'outputs')
                if os.path.exists(default_outputs):
                    store_dir = default_outputs
            if not store_dir:
                return 0
            # 扫描日志目录
            logs_dir = 'logs'
            if not os.path.exists(logs_dir):
                return 0
            log_files = [os.path.join(logs_dir, f) for f in os.listdir(logs_dir) if f.endswith('.log')]
            if not log_files:
                return 0
            # 按修改时间倒序，限制最近20个
            log_files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            for fp in log_files[:20]:
                try:
                    with open(fp, 'r', encoding='utf-8', errors='ignore') as lf:
                        # 只读末尾最多1000行，提高性能
                        lines = lf.readlines()
                        for line in reversed(lines[-1000:]):
                            if 'time cost' in line and store_dir in line:
                                import re as _re
                                m = _re.search(r'time cost:\s*([0-9.]+)s', line)
                                if m:
                                    return float(m.group(1))
                except Exception:
                    continue
            return 0
        except Exception as e:
            print(f"从日志提取处理耗时出错: {e}")
            return 0
            
    def format_duration(self, seconds):
        """格式化耗时显示"""
        if seconds < 60:
            return f"{seconds:.1f}秒"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}分钟"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}小时"
    
    def update_file_progress(self, mission_dir, file_path, status='completed'):
        """更新单个文件的处理状态"""
        try:
            progress = self.get_progress(mission_dir)
            if not progress:
                return False
            
            # 更新已处理文件数
            if status == 'completed':
                progress['processed_files'] += 1
            
            # 更新文件状态
            file_name = os.path.basename(file_path)
            file_found = False
            
            for detail in progress.get('details', []):
                if detail.get('file_name') == file_name:
                    detail['status'] = status
                    file_found = True
                    break
            
            if not file_found:
                if 'details' not in progress:
                    progress['details'] = []
                progress['details'].append({
                    'file_name': file_name,
                    'status': status,
                    'update_time': time.time()
                })
            
            # 保存更新
            return self.update_progress(mission_dir, progress)
        except Exception as e:
            print(f"更新文件进度时出错: {e}")
            return False
    
    def clear_progress(self, mission_dir):
        """清理任务进度信息"""
        try:
            # 删除进度文件
            progress_file = self.get_progress_file_path(mission_dir)
            if os.path.exists(progress_file):
                os.remove(progress_file)
                print(f"已删除进度文件: {progress_file}")
            
            # 从缓存中移除
            with self._lock:
                if mission_dir in self._progress_cache:
                    del self._progress_cache[mission_dir]
                if mission_dir in self._last_update:
                    del self._last_update[mission_dir]
            
            return True
        except Exception as e:
            print(f"清理任务进度时出错: {e}")
            return False

# 创建全局实例
task_progress = TaskProgress()
