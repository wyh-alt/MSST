import _thread
import time
import os
import json
import scripts.preset_infer_cli as cli
from utils.constant import *
from pathlib import Path
from clientui.class_command_executor import CommandExecutor
from clientui.task_progress import task_progress

try:
    import psutil
except ImportError:
    psutil = None


def read_thread_count():
    config_path = Path('./config.json').resolve()
    if not config_path.exists():
        with open(config_path, 'w') as f:
            f.write(json.dumps({'thread_count': 1}))
        return 1
    with open(config_path, 'r') as f:
        thread_config = json.load(f)
        return thread_config['thread_count']


def write_thread_count(thread_count):
    config_path = Path('./config.json').resolve()
    with open(config_path, 'w') as f:
        f.write(json.dumps({'thread_count': thread_count}))


class Mission:
    def __init__(self):
        self.input_dir = ''
        self.input_dirs = []  # 批量处理时的输入目录列表
        self.output_dir = ''
        self.preset_name = ''
        self.output_format = 'wav'
        self.skip_existing_files = False  # 添加跳过已有文件的选项
        self.state = 'waiting'
        self.identity = ''
        self.running = False
        self.debug = False
        self.output_file = None
        self.executor: CommandExecutor | None = None
        self.mission_dir = ''  # 添加任务目录属性

    def cp(self):
        mission = Mission()
        mission.input_dir = self.input_dir
        mission.input_dirs = self.input_dirs.copy() if self.input_dirs else []
        mission.output_dir = self.output_dir
        mission.preset_name = self.preset_name
        mission.output_format = self.output_format
        mission.skip_existing_files = self.skip_existing_files
        mission.state = self.state
        mission.identity = self.identity
        mission.running = self.running
        mission.debug = self.debug
        mission.output_file = self.output_file
        mission.executor = self.executor
        return mission

    def dump(self):
        # 获取进度信息
        progress_data = {}
        if self.mission_dir:
            progress_info = task_progress.get_progress(self.mission_dir)
            if progress_info:
                progress_data = {
                    'processed_files': progress_info.get('processed_files', 0),
                    'total_files': progress_info.get('total_files', 0)
                }
        
        return {
            'input_dir': self.input_dir,
            'output_dir': self.output_dir,
            'preset_name': self.preset_name,
            'output_format': self.output_format,
            'skip_existing_files': self.skip_existing_files,
            'state': self.state,
            'progress': progress_data
        }

    def write(self):
        with open(self.output_file, mode='w', encoding='utf-8') as f:
            f.write(json.dumps(self.dump(), indent=4, ensure_ascii=False))
            
    def update_progress(self, processed_files=None, total_files=None, status=None):
        """更新任务进度"""
        if not self.mission_dir:
            return
            
        update_data = {}
        if processed_files is not None:
            update_data['processed_files'] = processed_files
        if total_files is not None:
            update_data['total_files'] = total_files
        if status is not None:
            update_data['status'] = status
            
        if update_data:
            task_progress.update_progress(self.mission_dir, update_data)


def cli_main(mission: Mission):
    import os
    import shutil
    import multiprocessing
    from webui.setup import setup_webui, set_debug

    multiprocessing.set_start_method("spawn", force=True)

    if not os.path.exists("configs"):
        shutil.copytree("configs_backup", "configs")
    if not os.path.exists("data"):
        shutil.copytree("data_backup", "data")

    setup_webui()  # must be called because we use some functions from webui app
    set_debug(mission)

    preset_path = os.path.join(PRESETS, mission.preset_name)

    mission.running = True
    mission.state = 'running'
    mission.write()

    # 使用clientui目录下的preset_infer_cli.py
    import clientui.preset_infer_cli as cli
    cli.main(mission.input_dir,
             mission.output_dir,
             preset_path,
             mission.output_format,
             mission.skip_existing_files)

    mission.running = False
    mission.state = 'completed'
    mission.write()


class Manager:
    def __init__(self):
        self.missions: list[Mission] = []
        self.running: list[Mission] = []
        self.thread_count = read_thread_count()
        self.batch_mode = False  # 默认关闭批量处理模式，启用真正的多线程
        self.force_batch_mode = False  # 添加强制批量模式选项

        _thread.start_new_thread(self.loop, ())

    def add(self, mission: Mission):
        print(f"调试信息 - Manager.add: 开始处理任务")
        print(f"调试信息 - 输入目录: {mission.input_dir}")
        print(f"调试信息 - 输出目录: {mission.output_dir}")
        print(f"调试信息 - 当前线程数设置: {self.thread_count}")
        print(f"调试信息 - 批量处理模式: {self.batch_mode}")
        
        # 设置任务目录
        if not mission.mission_dir and mission.output_file:
            mission_dir = os.path.dirname(mission.output_file)
            mission.mission_dir = mission_dir
            
            # 初始化进度追踪，传入预设名称以支持多步骤进度
            task_progress.init_progress(mission.mission_dir, mission.input_dir, mission.preset_name)
        
        # 检查输入目录是否直接包含音频文件
        has_audio_files = False
        total_audio_files = 0
        audio_files_to_process = []
        try:
            file_list = os.listdir(mission.input_dir)
            print(f"调试信息 - 目录中共有 {len(file_list)} 个文件/文件夹")
            
            for name in file_list:
                full_path = os.path.join(mission.input_dir, name)
                if os.path.isfile(full_path) and name.lower().endswith(('.wav', '.flac', '.mp3', '.m4a', '.aac', '.ogg')):
                    has_audio_files = True
                    total_audio_files += 1
                    print(f"调试信息 - 找到音频文件: {name}")
                    
                    # 检查输出文件是否已存在
                    if mission.output_dir and os.path.exists(mission.output_dir):
                        # 这里需要根据具体的预设来检查输出文件
                        # 由于预设信息不在mission对象中，我们暂时跳过这个检查
                        # 实际的检查将在推理过程中进行
                        audio_files_to_process.append(name)
                    else:
                        audio_files_to_process.append(name)
            
            print(f"调试信息 - 是否包含音频文件: {has_audio_files}")
            print(f"调试信息 - 音频文件总数: {total_audio_files}")
            print(f"调试信息 - 需要处理的文件数: {len(audio_files_to_process)}")
            
            # 更新总文件数 - 使用实际需要处理的文件数
            if mission.mission_dir and has_audio_files:
                files_to_process = len(audio_files_to_process) if audio_files_to_process else total_audio_files
                print(f"调试信息 - 更新进度文件总数: {files_to_process}")
                task_progress.update_progress(mission.mission_dir, {
                    'total_files': files_to_process,
                    'total_files_locked': True  # 锁定总数，防止后续被覆盖
                })
            
        except Exception as e:
            print(f"调试信息 - 检查目录时出错: {e}")
            return
        
        if has_audio_files:
            # 输入目录直接包含音频文件，直接添加任务
            print(f"调试信息 - 直接添加任务")
            self.missions.append(mission)
            print(f"调试信息 - 任务已添加到队列，当前队列长度: {len(self.missions)}")
        else:
            # 输入目录包含子目录，为每个子目录创建子任务
            print(f"调试信息 - 创建子任务")
            sub_mission_count = 0
            for name in file_list:
                full_path = os.path.join(mission.input_dir, name)
                if os.path.isdir(full_path):
                    sub_mission = mission.cp()
                    sub_mission.input_dir = full_path
                    sub_mission.output_file = os.path.join(mission.input_dir, f'mission_{name}.json')
                    sub_mission.mission_dir = mission.mission_dir
                    self.missions.append(sub_mission)
                    sub_mission_count += 1
                    print(f"调试信息 - 添加子任务: {name}")
                    
            # 更新总任务数
            if mission.mission_dir:
                task_progress.update_progress(mission.mission_dir, {'total_files': sub_mission_count})

    def loop(self):
        while True:
            start = time.time()
            self.check()
            current = time.time()
            interval = 2 + start - current
            if interval > 0:
                time.sleep(interval)

    def check(self):
        if len(self.missions) == 0 and len(self.running) == 0:
            return

        running = self.running[:]
        for mission in running:
            # 检查进程是否已结束
            process_ended = False
            process_exists = False
            
            # 检查 executor 和 process 是否存在
            if mission.executor is not None and mission.executor.process is not None:
                try:
                    exit_code = mission.executor.process.poll()
                    if exit_code is not None:  # 进程已结束
                        process_ended = True
                        print(f"调试信息 - 任务进程已结束: {mission.input_dir}, exit_code={exit_code}")
                    else:
                        process_exists = True  # 进程还在运行
                except (ProcessLookupError, OSError):
                    # 进程不存在（可能被强制终止）
                    process_ended = True
                    print(f"调试信息 - 任务进程不存在（可能已被终止）: {mission.input_dir}")
                except Exception as e:
                    # 其他异常，也认为进程已结束
                    process_ended = True
                    print(f"调试信息 - 检查进程状态时出错，标记为已结束: {mission.input_dir}, 错误: {e}")
            else:
                # executor 或 process 为 None，说明任务可能被强制删除
                # 检查任务目录是否还存在，如果不存在，说明任务已被删除
                if mission.mission_dir and not os.path.exists(mission.mission_dir):
                    process_ended = True
                    print(f"调试信息 - 任务目录不存在，任务可能已被删除: {mission.input_dir}")
                elif mission.executor is None:
                    # executor 为 None 但任务还在 running 列表中，可能是异常状态
                    print(f"调试信息 - ⚠️  警告：任务 executor 为 None 但仍在运行列表: {mission.input_dir}")
                    # 检查进程是否真的在运行（通过检查输出目录是否有新文件）
                    if not process_exists:
                        # 如果超过一定时间没有新文件产生，认为任务已停止
                        process_ended = True
                        print(f"调试信息 - 任务 executor 为 None，标记为已结束: {mission.input_dir}")
            
            # 检查是否为批量任务
            is_batch_task = False
            expected_file_count = 1
            
            # 对于上传下载方式，检查inputs目录中的子目录数量
            if mission.mission_dir:
                inputs_dir = os.path.join(mission.mission_dir, 'inputs')
                if os.path.exists(inputs_dir):
                    subdirs = [d for d in os.listdir(inputs_dir) 
                              if os.path.isdir(os.path.join(inputs_dir, d))]
                    if len(subdirs) > 1:
                        is_batch_task = True
                        expected_file_count = len(subdirs)
            
            # 如果不是上传下载方式，检查原始输入目录
            if not is_batch_task and mission.input_dir and os.path.exists(mission.input_dir):
                audio_files = [f for f in os.listdir(mission.input_dir) 
                             if os.path.isfile(os.path.join(mission.input_dir, f)) and 
                             f.lower().endswith(('.wav', '.flac', '.mp3', '.m4a', '.aac', '.ogg'))]
                if len(audio_files) > 1:
                    is_batch_task = True
                    expected_file_count = len(audio_files)
            
            # 检查输出目录中是否有文件 - 用于跟踪进度
            processed_files = 0
            processed_songs = 0
            output_files = []
            
            # 检查主输出目录
            if mission.output_dir and os.path.exists(mission.output_dir):
                output_files.extend([f for f in os.listdir(mission.output_dir) 
                                   if f.lower().endswith(('.wav', '.flac', '.mp3'))])
            
            # 检查批量输出目录（batch_output）
            if mission.mission_dir:
                batch_output_dir = os.path.join(mission.mission_dir, 'batch_output')
                if os.path.exists(batch_output_dir):
                    batch_files = [f for f in os.listdir(batch_output_dir) 
                                 if f.lower().endswith(('.wav', '.flac', '.mp3'))]
                    output_files.extend(batch_files)
                    print(f"调试信息 - 检测到批量输出文件: {batch_output_dir}, 文件数: {len(batch_files)}")
            
            # 对于上传下载方式，还需要检查子任务的输出目录
            if mission.mission_dir:
                inputs_dir = os.path.join(mission.mission_dir, 'inputs')
                if os.path.exists(inputs_dir):
                    for subdir_name in os.listdir(inputs_dir):
                        subdir_path = os.path.join(inputs_dir, subdir_name)
                        if os.path.isdir(subdir_path):
                            sub_outputs_dir = os.path.join(subdir_path, 'outputs')
                            if os.path.exists(sub_outputs_dir):
                                sub_files = [f for f in os.listdir(sub_outputs_dir) 
                                           if f.lower().endswith(('.wav', '.flac', '.mp3'))]
                                output_files.extend(sub_files)
                                if sub_files:
                                    print(f"调试信息 - 检测到子任务输出文件: {sub_outputs_dir}, 文件数: {len(sub_files)}")
            
            processed_files = len(output_files)
            
            # 计算每首歌生成的输出文件数量
            outputs_per_song = 1
            if mission.mission_dir:
                try:
                    from clientui.task_progress import task_progress
                    outputs_per_song = task_progress._get_outputs_per_song(mission.mission_dir)
                except:
                    pass
            
            # 根据输出文件数计算已处理的歌曲数
            if outputs_per_song > 0:
                processed_songs = processed_files // outputs_per_song
                # 确保已处理歌曲数不超过总歌曲数
                processed_songs = min(processed_songs, expected_file_count)
            
            if output_files:
                # 有输出文件，说明任务已经完成部分或全部
                print(f"调试信息 - 检测到输出文件: {mission.output_dir}, 文件数: {len(output_files)}, 处理歌曲数: {processed_songs}, 预期: {expected_file_count}")
                
                # 检查是否所有文件都已处理完成
                all_files_processed = processed_songs >= expected_file_count
                
                # 更新进度信息
                if mission.mission_dir:
                    status = 'running'
                    # 如果所有文件都已处理完成，即使进程还没结束，也标记为完成
                    # 或者进程已结束且所有歌曲处理完成
                    if all_files_processed or (process_ended and (not is_batch_task or processed_songs >= expected_file_count)):
                        status = 'completed'
                        # 记录任务结束时间
                        end_time = time.time()
                        print(f"调试信息 - ✅ 任务已完成: 已处理 {processed_songs}/{expected_file_count} 首歌曲, process_ended={process_ended}, all_files_processed={all_files_processed}")
                    else:
                        end_time = None
                        if not process_ended:
                            print(f"调试信息 - ⏳ 任务进行中: 已处理 {processed_songs}/{expected_file_count} 首歌曲, 等待进程结束...")
                    
                    update_data = {
                        'processed_files': processed_songs,  # 使用歌曲数而不是文件数
                        'total_files': expected_file_count,  # 总歌曲数
                        'status': status
                    }
                    
                    # 如果任务完成，添加结束时间
                    if end_time:
                        update_data['end_time'] = end_time
                        
                    task_progress.update_progress(mission.mission_dir, update_data)
                    
                    # 同时更新mission.json文件中的状态
                    try:
                        mission_json = os.path.join(mission.mission_dir, 'mission.json')
                        if os.path.exists(mission_json):
                            with open(mission_json, 'r', encoding='utf-8') as f:
                                mission_info = json.load(f)
                            mission_info['state'] = status
                            with open(mission_json, 'w', encoding='utf-8') as f:
                                json.dump(mission_info, f, indent=4, ensure_ascii=False)
                    except Exception as e:
                        print(f"更新mission.json状态时出错: {e}")
            
            # 如果所有文件都已处理完成，即使进程还没结束，也结束任务
            # 或者进程已结束时，结束任务
            should_end_task = False
            
            # 检查是否所有文件都已处理完成
            if processed_songs >= expected_file_count and expected_file_count > 0:
                # 所有文件都已处理完成
                should_end_task = True
                print(f"调试信息 - ✅ 所有文件已处理完成 ({processed_songs}/{expected_file_count})，准备结束任务")
            elif process_ended:
                # 进程已结束
                should_end_task = True
                print(f"调试信息 - ✅ 进程已结束，准备结束任务")
                # 如果进程结束但没有输出文件，也结束任务（可能是所有文件都被跳过）
                if not output_files and expected_file_count > 0:
                    print(f"调试信息 - ⚠️  进程已结束但没有输出文件，可能是所有文件都被跳过，结束任务")
            
            if should_end_task:
                # 获取进程退出码
                exit_code = 0
                if mission.executor and mission.executor.process:
                    try:
                        exit_code = mission.executor.process.poll()
                        if exit_code is None:
                            # 进程还在运行，但所有文件已处理完成，强制结束
                            print(f"调试信息 - ⚠️  进程还在运行，但所有文件已处理完成，强制结束任务")
                            exit_code = 0  # 视为正常完成
                    except:
                        exit_code = 0
                
                if exit_code == 0 or processed_songs >= expected_file_count:
                    # 正常完成（退出码为0或所有文件已处理）
                    print(f"调试信息 - ✅ 任务正常完成: 已处理 {processed_songs}/{expected_file_count} 首歌曲, exit_code={exit_code}")
                    mission.state = 'completed'
                    mission.update_progress(status='completed', processed_files=processed_songs, total_files=expected_file_count)
                else:
                    # 异常退出
                    print(f"调试信息 - ❌ 任务异常退出: exit_code={exit_code}, 已处理 {processed_songs}/{expected_file_count} 首歌曲")
                    mission.state = 'failed'
                    mission.update_progress(status='failed', processed_files=processed_songs, total_files=expected_file_count)
                
                mission.running = False
                try:
                    mission.write()
                except:
                    pass  # 如果任务目录已删除，写入可能失败
                self.running.remove(mission)
                print(f"调试信息 - ✅ 任务已从运行队列移除: {mission.input_dir}")

        # 清理无效任务（僵尸任务）
        self._cleanup_invalid_tasks()
        
        # 多线程处理逻辑 - 启动尽可能多的任务
        goon = True
        while len(self.running) < self.thread_count and goon:
            goon = self.start_nxt_if_available()

    def _cleanup_invalid_tasks(self):
        """清理无效任务（僵尸任务）"""
        invalid_tasks = []
        for mission in self.running[:]:
            is_invalid = False
            
            # 检查 executor 是否存在
            if mission.executor is None:
                is_invalid = True
                print(f"调试信息 - 发现无效任务（executor 为 None）: {mission.input_dir}")
            elif mission.executor.process is None:
                is_invalid = True
                print(f"调试信息 - 发现无效任务（process 为 None）: {mission.input_dir}")
            else:
                # 检查进程是否真的在运行
                try:
                    exit_code = mission.executor.process.poll()
                    if exit_code is not None:
                        # 进程已结束但还在 running 列表中
                        is_invalid = True
                        print(f"调试信息 - 发现无效任务（进程已结束但未清理）: {mission.input_dir}, exit_code={exit_code}")
                except (ProcessLookupError, OSError):
                    # 进程不存在
                    is_invalid = True
                    print(f"调试信息 - 发现无效任务（进程不存在）: {mission.input_dir}")
            
            # 检查任务目录是否存在
            if mission.mission_dir and not os.path.exists(mission.mission_dir):
                is_invalid = True
                print(f"调试信息 - 发现无效任务（任务目录不存在）: {mission.input_dir}")
            
            if is_invalid:
                invalid_tasks.append(mission)
        
        # 清理无效任务
        for mission in invalid_tasks:
            try:
                mission.running = False
                mission.state = 'terminated'
                self.running.remove(mission)
                print(f"调试信息 - ✅ 已清理无效任务: {mission.input_dir}")
            except Exception as e:
                print(f"调试信息 - ❌ 清理无效任务时出错: {mission.input_dir}, 错误: {e}")
        
        if invalid_tasks:
            print(f"调试信息 - 共清理了 {len(invalid_tasks)} 个无效任务")

    def start_nxt_if_available(self):
        if len(self.missions) == 0:
            return False

        # 根据配置决定使用批量处理还是多线程处理
        if self.batch_mode and self.force_batch_mode:
            return self._start_batch_if_available()
        else:
            return self._start_single_if_available()

    def _start_single_if_available(self):
        """单个任务处理模式 - 真正的多线程并行处理"""
        if len(self.missions) == 0:
            return False
            
        first: Mission = self.missions[0]
        print(f"调试信息 - 🚀 开始处理单个任务: {first.input_dir}")
        print(f"调试信息 - 当前运行任务数: {len(self.running)}/{self.thread_count}")
        print(f"调试信息 - 等待队列任务数: {len(self.missions)}")
        
        self.running.append(first)
        self.missions.remove(first)
        
        # 初始化executor
        if first.executor is None:
            first.executor = CommandExecutor()
        
        # 修复Python路径，使用绝对路径
        current_dir = Path.cwd()
        python = current_dir / "workenv" / "python.exe"
        script = current_dir / "clientui" / "preset_infer_cli.py"
        preset_path = current_dir / "presets" / first.preset_name
        
        # 构建命令，修复--debug参数
        cmd_parts = [
            f'"{python}"',
            f'"{script}"',
            '-p', f'"{preset_path}"',
            '-i', f'"{first.input_dir}"',
            '-o', f'"{first.output_dir}"',
            '-f', first.output_format
        ]
        
        # 只在debug为True时添加--debug标志
        if first.debug:
            cmd_parts.append('--debug')
        
        cmd = ' '.join(cmd_parts)
        
        print(f"调试信息 - 执行命令: {cmd}")
        print(f"调试信息 - Python路径: {python}")
        print(f"调试信息 - 脚本路径: {script}")
        print(f"调试信息 - 预设路径: {preset_path}")
        
        try:
            first.executor.execute_command(cmd)
            first.running = True
            first.state = 'running'
            # 记录处理开始时间
            first.update_progress(status='running')
            first.write()
            print(f"调试信息 - ✅ 命令执行成功，任务已启动")
            print(f"调试信息 - 进程 PID: {first.executor.process.pid if first.executor.process else 'N/A'}")
            return True
        except Exception as e:
            print(f"调试信息 - ❌ 命令执行失败: {e}")
            # 如果启动失败，从 running 列表中移除
            if first in self.running:
                self.running.remove(first)
            import traceback
            traceback.print_exc()
            return False

    def _start_batch_if_available(self):
        """批量任务处理模式"""
        if len(self.missions) == 0:
            return False

        # 查找相同预设的任务进行批量处理
        batch_missions = []
        first_mission = self.missions[0]
        
        # 收集相同预设的任务
        for mission in self.missions[:]:  # 使用切片避免修改迭代中的列表
            if (mission.preset_name == first_mission.preset_name and 
                mission.output_format == first_mission.output_format and
                mission.debug == first_mission.debug):
                batch_missions.append(mission)
        
        if len(batch_missions) == 1:
            # 只有一个任务，使用单个处理模式
            return self._start_single_if_available()
        
        print(f"调试信息 - 开始批量处理 {len(batch_missions)} 个任务")
        
        # 创建批量任务
        batch_mission = first_mission.cp()
        batch_mission.input_dirs = [m.input_dir for m in batch_missions]
        batch_mission.output_dir = os.path.join(os.path.dirname(first_mission.output_dir), "batch_output")
        batch_mission.mission_dir = os.path.dirname(first_mission.output_file)
        
        # 从队列中移除已收集的任务
        for mission in batch_missions:
            self.missions.remove(mission)
        
        self.running.append(batch_mission)
        
        # 初始化executor
        if batch_mission.executor is None:
            batch_mission.executor = CommandExecutor()
        
        # 修复Python路径，使用绝对路径
        current_dir = Path.cwd()
        python = current_dir / "workenv" / "python.exe"
        script = current_dir / "clientui" / "preset_infer_cli.py"
        preset_path = current_dir / "presets" / batch_mission.preset_name
        
        # 构建批量处理命令
        cmd_parts = [
            f'"{python}"',
            f'"{script}"',
            '--batch',  # 添加批量处理标志
            '-p', f'"{preset_path}"',
            '-o', f'"{batch_mission.output_dir}"',
            '-f', batch_mission.output_format
        ]
        
        # 添加输入目录列表
        for input_dir in batch_mission.input_dirs:
            cmd_parts.extend(['-i', f'"{input_dir}"'])
        
        # 只在debug为True时添加--debug标志
        if batch_mission.debug:
            cmd_parts.append('--debug')
        
        cmd = ' '.join(cmd_parts)
        
        print(f"调试信息 - 执行批量命令: {cmd}")
        print(f"调试信息 - 批量处理 {len(batch_mission.input_dirs)} 个目录")
        
        try:
            batch_mission.executor.execute_command(cmd)
            batch_mission.running = True
            batch_mission.state = 'running'
            # 记录处理开始时间
            batch_mission.update_progress(status='running')
            batch_mission.write()
            print(f"调试信息 - 批量命令执行成功")
            return True
        except Exception as e:
            print(f"调试信息 - 批量命令执行失败: {e}")
            return False

    def set_batch_mode(self, enabled: bool):
        """设置批量处理模式"""
        self.batch_mode = enabled
        print(f"调试信息 - 批量处理模式已设置为: {enabled}")

    def set_force_batch_mode(self, enabled: bool):
        """设置强制批量处理模式"""
        self.force_batch_mode = enabled
        print(f"调试信息 - 强制批量处理模式已设置为: {enabled}")

    def get_status(self):
        """获取管理器状态信息"""
        return {
            'thread_count': self.thread_count,
            'batch_mode': self.batch_mode,
            'force_batch_mode': self.force_batch_mode,
            'waiting_tasks': len(self.missions),
            'running_tasks': len(self.running),
            'total_tasks': len(self.missions) + len(self.running)
        }


manager = Manager()
