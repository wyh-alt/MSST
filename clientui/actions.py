import json
import shutil
import time

import gradio as gr
import hashlib
from pathlib import Path
import os
from datetime import datetime
from clientui.mission import Mission, manager, write_thread_count
from clientui.task_progress import task_progress
import zipfile

# 从配置文件加载用户目录设置
def get_client_dir():
    """获取客户端用户目录"""
    try:
        with open('client_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        return Path(config.get('user_dir', 'E:/MSSTuser'))
    except (FileNotFoundError, json.JSONDecodeError):
        return Path('E:/MSSTuser')  # 默认目录

client_dir = get_client_dir()

def get_cache_dir():
    """获取缓存目录"""
    try:
        with open('client_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('cache_dir', 'E:/MSSTcache/')
    except (FileNotFoundError, json.JSONDecodeError):
        return "E:/MSSTcache/"  # 默认目录

def switch2user_tab(req: gr.Request):
    from client import is_admin
    admin = is_admin(req.username)
    return gr.Tab(visible=admin)


def change_psw(req: gr.Request, psw, new_psw):
    from client import users, user_lib
    username = req.username

    psw = hashlib.sha256(psw.encode('utf-8')).hexdigest()
    new_psw = hashlib.sha256(new_psw.encode('utf-8')).hexdigest()

    user = users[username]
    if user['psw'] != psw:
        return gr.Warning('旧密码错误')
    user['psw'] = new_psw
    with open(user_lib, mode='w', encoding='utf-8') as f:
        f.write(json.dumps(users, indent=4, ensure_ascii=False))
    return gr.Info('修改密码成功')


def get_user_list():
    from client import users
    names = list(users.keys())
    names.remove('admin')
    return names


def select_remove_user_tab():
    return gr.Radio(choices=get_user_list(),
                    value=None)


def delete_user(req: gr.Request, username):
    from client import users, user_lib
    if username == req.username:
        gr.Warning('不能删除自己')
        return gr.Radio(choices=get_user_list(),
                        value=None)
    users.pop(username, None)

    with open(user_lib, mode='w', encoding='utf-8') as f:
        f.write(json.dumps(users, indent=4, ensure_ascii=False))

    return gr.Radio(choices=get_user_list(),
                    value=None)


def clear_cache():
    cache_dir = os.path.abspath(get_cache_dir())
    shutil.rmtree(cache_dir, ignore_errors=True)
    gr.Info('清空缓存成功')


def add_user(username, password, admin):
    import client
    if not client.add_user(username, password, admin):
        return gr.Warning('用户已存在')

    gr.Info('添加成功')

    return [
        gr.Textbox(value=''),
        gr.Textbox(value=''),
        gr.Checkbox(value=False)
    ]


def get_mission_list(username):
    user_dir = client_dir / username
    if not user_dir.exists():
        return []

    missions = []
    for name in os.listdir(user_dir):
        p = user_dir / name
        if p.is_dir():
            missions.append(name)
    return missions


def switch2mission_tab(req: gr.Request):
    result: list[gr.Radio | gr.Text | gr.Files] = [gr.Radio(choices=get_mission_list(req.username),
                                                            value=None)]
    result.extend(select_mission(req, None))
    return result


def thread_count_change(thread_count):
    if thread_count is None:
        thread_count = 1
    thread_count = min(max(thread_count, 1), 10)
    write_thread_count(thread_count)
    manager.thread_count = thread_count
    print(f"调试信息 - 线程数已更新为: {thread_count}")


def batch_mode_change(batch_mode):
    """切换批量处理模式"""
    manager.set_batch_mode(batch_mode)
    return f"批量处理模式已{'启用' if batch_mode else '禁用'}"


def force_batch_mode_change(force_batch_mode):
    """切换强制批量处理模式"""
    manager.set_force_batch_mode(force_batch_mode)
    return f"强制批量处理模式已{'启用' if force_batch_mode else '禁用'}"


def get_manager_status():
    """获取管理器状态"""
    status = manager.get_status()
    return f"""
    线程数: {status['thread_count']}
    批量处理模式: {'启用' if status['batch_mode'] else '禁用'}
    强制批量模式: {'启用' if status['force_batch_mode'] else '禁用'}
    等待任务: {status['waiting_tasks']}
    运行任务: {status['running_tasks']}
    总任务数: {status['total_tasks']}
    """


def delete_mission(req: gr.Request, mission):
    if mission is None:
        return switch2mission_tab(req)

    mission_dir = client_dir / req.username / mission
    
    # 检查任务是否正在运行，如果是则强制终止
    mission_terminated = False
    
    # 检查running列表中的任务
    for running_mission in manager.running[:]:  # 使用副本避免修改迭代中的列表
        if running_mission.mission_dir == str(mission_dir):
            # 找到正在运行的任务，强制终止
            if running_mission.executor and running_mission.executor.process:
                try:
                    running_mission.executor.kill_command()
                    print(f"已强制终止任务进程: {mission}")
                except Exception as e:
                    print(f"终止任务进程时出错: {e}")
            
            # 从running列表中移除
            manager.running.remove(running_mission)
            mission_terminated = True
            print(f"已从运行队列中移除任务: {mission}")
    
    # 检查missions队列中的任务
    for waiting_mission in manager.missions[:]:  # 使用副本避免修改迭代中的列表
        if waiting_mission.mission_dir == str(mission_dir):
            # 从等待队列中移除
            manager.missions.remove(waiting_mission)
            print(f"已从等待队列中移除任务: {mission}")
    
    # 清理任务进度信息
    try:
        task_progress.clear_progress(str(mission_dir))
        print(f"已清理任务进度信息: {mission}")
    except Exception as e:
        print(f"清理任务进度信息时出错: {e}")
    
    # 清理缓存文件
    try:
        cache_dir = get_cache_dir()
        if os.path.exists(cache_dir):
            # 为避免误删正在使用的临时目录，这里不再删除 preset_task_* 目录
            # 这些目录会在任务结束时自行清理，或通过“清空缓存”功能统一处理
            pass
            
            # 清理tmp开头的临时文件（Gradio缓存）
            for item in os.listdir(cache_dir):
                item_path = os.path.join(cache_dir, item)
                if os.path.isfile(item_path) and item.startswith("tmp"):
                    try:
                        os.remove(item_path)
                        print(f"已清理临时文件: {item}")
                    except Exception as e:
                        print(f"清理临时文件时出错: {e}")
            
            print(f"已清理缓存文件: {mission}")
    except Exception as e:
        print(f"清理缓存文件时出错: {e}")
    
    # 如果强制终止了任务，清理GPU缓存
    if mission_terminated:
        try:
            import torch
            import gc
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                print("已清理GPU缓存")
            elif hasattr(torch, 'mps') and torch.mps.is_available():
                torch.mps.empty_cache()
                print("已清理MPS缓存")
        except Exception as e:
            print(f"清理GPU缓存时出错: {e}")
    
    # 删除任务目录
    shutil.rmtree(mission_dir, ignore_errors=True)
    
    if mission_terminated:
        gr.Info('已强制终止并删除正在运行的任务，已清理GPU缓存')
    else:
        gr.Info('删除任务成功')
    
    return switch2mission_tab(req)


def select_mission(req: gr.Request, mission):
    if mission is None:
        return [
            gr.Files(value=None),
            gr.Files(value=None),
            gr.Textbox(value='')
        ]
    mission_dir = client_dir / req.username / mission
    if not mission_dir.exists():
        gr.Warning('任务已失效')
        return [
            gr.Files(value=None),
            gr.Files(value=None),
            gr.Textbox(value='任务已失效')
        ]

    # 查找并计算输出文件
    output_files = []
    output_file_count = 0
    
    # 检查主输出目录
    output_dir = mission_dir / 'outputs'
    if output_dir.exists():
        for name in os.listdir(output_dir):
            path = output_dir / name
            if path.suffix in [".wav", ".flac", ".mp3"]:
                output_files.append(str(path))
                output_file_count += 1
    
    # 检查批量输出目录（batch_output）
    batch_output_dir = mission_dir / 'batch_output'
    if batch_output_dir.exists():
        for name in os.listdir(batch_output_dir):
            path = batch_output_dir / name
            if path.suffix in [".wav", ".flac", ".mp3"]:
                output_files.append(str(path))
                output_file_count += 1
    
    # 对于上传下载方式，还需要检查子任务的输出目录
    input_dir = mission_dir / 'inputs'
    if input_dir.exists():
        for subdir_name in os.listdir(input_dir):
            subdir_path = input_dir / subdir_name
            if subdir_path.is_dir():
                # 检查子任务的输出目录
                sub_output_dir = subdir_path / 'outputs'
                if sub_output_dir.exists():
                    for name in os.listdir(sub_output_dir):
                        path = sub_output_dir / name
                        if path.suffix in [".wav", ".flac", ".mp3"]:
                            output_files.append(str(path))
                            output_file_count += 1

    state = ''
    
    # 获取进度信息
    progress_info = task_progress.get_progress(str(mission_dir))
    
    # 如果进度信息不存在或已过期，则根据输出文件推断状态
    if not progress_info:
        # 简化处理：直接使用输出文件数作为进度，避免复杂计算
        progress_info = {
            'processed_files': output_file_count,
            'total_files': max(1, output_file_count),
            'status': 'completed' if output_file_count > 0 else 'running'
        }
        # 更新到文件
        if output_file_count > 0:
            task_progress.update_progress(str(mission_dir), progress_info)
    
    # 检查任务是否正在运行
    is_running_now = False
    
    # 检查manager.running中的任务
    for m in manager.running:
        if getattr(m, 'mission_dir', None) == str(mission_dir):
            is_running_now = True
            break
    
    # 检查mission.json文件中的状态
    main_mission_file = mission_dir / 'mission.json'
    if main_mission_file.exists():
        try:
            with open(main_mission_file, 'r', encoding='utf-8') as f:
                main_info = json.load(f)
                if main_info.get('state') == 'running':
                    is_running_now = True
        except:
            pass
    
    # 如果任务正在运行，强制更新状态
    if is_running_now:
        need_update = False
        update_data = {}
        if not progress_info or progress_info.get('status') != 'running':
            update_data['status'] = 'running'
            need_update = True
        if not progress_info or progress_info.get('processing_start_time', 0) == 0:
            try:
                processing_start = os.path.getmtime(main_mission_file) if main_mission_file.exists() else time.time()
            except Exception:
                processing_start = time.time()
            update_data['processing_start_time'] = processing_start
            need_update = True
        if need_update:
            task_progress.update_progress(str(mission_dir), update_data)
            progress_info = task_progress.get_progress(str(mission_dir)) or progress_info
    
    # 根据输出文件检测状态
    if output_file_count > 0 and progress_info.get('status') == 'running':
        # 如果有输出文件但状态仍然是running，检查任务是否实际已完成
        main_mission_file = mission_dir / 'mission.json'
        if main_mission_file.exists():
            try:
                with open(main_mission_file, 'r', encoding='utf-8') as f:
                    main_info = json.load(f)
                
                # 检查是否存在任何还在运行的子任务
                any_running = False
                all_sub_tasks = 0
                completed_sub_tasks = 0
                input_dir = mission_dir / 'inputs'
                if input_dir.exists():
                    for name in os.listdir(input_dir):
                        sub_mission_file = input_dir / name / 'mission.json'
                        if sub_mission_file.exists():
                            all_sub_tasks += 1
                            try:
                                with open(sub_mission_file, 'r', encoding='utf-8') as f:
                                    sub_info = json.load(f)
                                    if sub_info.get('state') == 'running':
                                        any_running = True
                                    elif sub_info.get('state') == 'completed':
                                        completed_sub_tasks += 1
                            except:
                                pass
                
                # 更新子任务完成进度（保持总数锁定）
                if all_sub_tasks > 0:
                    update_data = {
                        'processed_files': completed_sub_tasks,
                        'total_files_locked': True
                    }
                    # 只有在总数未设置时才更新总数
                    current_progress = task_progress.get_progress(str(mission_dir))
                    if not current_progress or current_progress.get('total_files', 0) <= 0:
                        update_data['total_files'] = all_sub_tasks
                    
                    task_progress.update_progress(str(mission_dir), update_data)
                
                # 只有所有子任务都完成，才将主任务标记为完成
                if not any_running and all_sub_tasks > 0 and completed_sub_tasks == all_sub_tasks:
                    progress_info['status'] = 'completed'
                    task_progress.update_progress(str(mission_dir), {'status': 'completed'})
                    
                    # 更新主任务文件状态
                    main_info['state'] = 'completed'
                    with open(main_mission_file, 'w', encoding='utf-8') as f:
                        json.dump(main_info, f, indent=4, ensure_ascii=False)
                else:
                    # 还有子任务正在运行或未完成，确保主任务状态为running
                    progress_info['status'] = 'running'
                    main_info['state'] = 'running'
                    task_progress.update_progress(str(mission_dir), {'status': 'running'})
                    with open(main_mission_file, 'w', encoding='utf-8') as f:
                        json.dump(main_info, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"检查任务状态时出错: {e}")
    
    # 添加总任务进度信息
    processed = progress_info.get('processed_files', output_file_count)
    total = progress_info.get('total_files', max(1, output_file_count))
    status = progress_info.get('status', 'completed' if output_file_count > 0 else 'running')
    
    # 计算总耗时和处理耗时
    total_duration = task_progress.get_total_duration(str(mission_dir))
    processing_duration = task_progress.get_processing_duration(str(mission_dir))
    total_duration_text = task_progress.format_duration(total_duration)
    processing_duration_text = task_progress.format_duration(processing_duration)
    
    # 格式化显示
    # 等待队列状态显示
    try:
        waiting_list = manager.missions[:]
        running_list = manager.running[:]
        # 是否已在运行中
        is_running = any(getattr(m, 'mission_dir', None) == str(mission_dir) for m in running_list)
        # 仅当不在运行且确实在等待队列中时显示
        indices = [i for i, m in enumerate(waiting_list) if getattr(m, 'mission_dir', None) == str(mission_dir)]
        if not is_running and indices:
            first_index = min(indices)
            # 计算总位置：正在运行的任务数 + 等待队列中的位置
            position = len(running_list) + first_index + 1
            preceding_users = []
            # 先添加正在运行的用户
            for m in running_list:
                try:
                    user_name = Path(m.mission_dir).parent.name if getattr(m, 'mission_dir', None) else ''
                    if user_name and user_name not in preceding_users:
                        preceding_users.append(user_name)
                except Exception:
                    pass
            # 再添加等待队列中排在前面的用户
            for m in waiting_list[:first_index]:
                try:
                    user_name = Path(m.mission_dir).parent.name if getattr(m, 'mission_dir', None) else ''
                    if user_name and user_name not in preceding_users:
                        preceding_users.append(user_name)
                except Exception:
                    pass
            users_text = '、'.join(preceding_users) if preceding_users else '无'
            state += f'目前排在处理队列第{position}名（前序用户：{users_text}）\n'
    except Exception:
        pass
    state += f'总任务状态: {status}\n'
    state += f'进度: {processed}/{total}\n'
    # 只在任务完成时显示处理耗时
    if status == 'completed':
        state += f'处理耗时: {processing_duration_text}\n'
    state += '\n'
    
    # 获取子任务状态
    input_dir = mission_dir / 'inputs'
    if input_dir.exists():
        for name in os.listdir(input_dir):
            # 检查mission.json和mission_*.json文件
            mission_files = list((input_dir / name).glob('mission*.json'))
            for mission_file in mission_files:
                if mission_file.exists():
                    with open(mission_file, mode='r', encoding='utf-8') as f:
                        try:
                            mission_info = json.load(f)
                            mission_state = mission_info['state']
                            
                            # 检查输出文件修正状态
                            sub_output_dir = os.path.join(mission_info.get('output_dir', ''), name)
                            if os.path.exists(sub_output_dir) and mission_state == 'running':
                                sub_files = [f for f in os.listdir(sub_output_dir) if f.lower().endswith(('.wav', '.flac', '.mp3'))]
                                if sub_files:  # 有输出文件，说明已经完成
                                    mission_state = 'completed'
                                    mission_info['state'] = 'completed'
                                    with open(mission_file, 'w', encoding='utf-8') as f:
                                        json.dump(mission_info, f, indent=4, ensure_ascii=False)
                            
                            # 添加进度信息
                            progress_text = ""
                            if 'progress' in mission_info:
                                prog = mission_info['progress']
                                proc = prog.get('processed_files', 0)
                                tot = prog.get('total_files', 0)
                                if tot > 0:
                                    progress_text = f" ({proc}/{tot})"
                                    
                            state += f'{name}: {mission_state}{progress_text}\n'
                        except json.JSONDecodeError:
                            state += f'{name}: 数据错误\n'

    return [
        gr.Files(value=output_files),
        gr.Files(value=None),
        gr.Textbox(value=state)
    ]


def make_zip(req: gr.Request, mission):
    if mission is None:
        return gr.Files(value=None)

    mission_dir = client_dir / req.username / mission
    if not mission_dir.exists():
        gr.Warning('任务已失效')
        return gr.Files(value=None)

    output_dir = mission_dir / 'outputs'
    zip_path = None
    if output_dir.exists():
        name = mission_dir / f'{mission}'
        zip_path = mission_dir / f'{mission}.zip'
        try:
            shutil.make_archive(name, 'zip', output_dir)
        except:
            gr.Warning('压缩失败')
            pass

    return gr.Files(value=str(zip_path))


def refresh_mission_status(req: gr.Request, mission):
    """刷新任务状态"""
    if mission is None:
        return select_mission(req, mission)
    
    # 强制刷新任务状态
    mission_dir = client_dir / req.username / mission
    if mission_dir.exists():
        # 检查任务是否正在运行
        is_running = False
        
        # 检查manager.running中的任务
        for m in manager.running:
            if getattr(m, 'mission_dir', None) == str(mission_dir):
                is_running = True
                break
        
        # 检查mission.json文件中的状态
        mission_json = mission_dir / 'mission.json'
        if mission_json.exists():
            try:
                with open(mission_json, 'r', encoding='utf-8') as f:
                    mission_info = json.load(f)
                    if mission_info.get('state') == 'running':
                        is_running = True
            except:
                pass
        
        # 如果任务正在运行，强制更新状态为running
        if is_running:
            task_progress.update_progress(str(mission_dir), {
                'status': 'running',
                'processing_start_time': time.time()
            })
            
            # 更新mission.json文件
            if mission_json.exists():
                try:
                    with open(mission_json, 'r', encoding='utf-8') as f:
                        mission_info = json.load(f)
                    mission_info['state'] = 'running'
                    with open(mission_json, 'w', encoding='utf-8') as f:
                        json.dump(mission_info, f, indent=4, ensure_ascii=False)
                except Exception as e:
                    print(f"刷新任务状态时更新mission.json出错: {e}")
    
    return select_mission(req, mission)


def infer(req: gr.Request,
          preset_name,
          input_audios,
          input_path,
          output_path,
          output_format,
          selected_tab=None,
          skip_existing_files=False):
    if preset_name is None:
        return gr.Warning('请选择预设')
    
    # 根据selected_tab参数来决定使用哪种输入方式
    use_upload_mode = selected_tab == "upload" or (selected_tab is None and input_audios is not None and len(input_audios) > 0)
    
    if use_upload_mode:
        # 上传下载方式：忽略用户指定的路径，使用上传的文件
        if input_audios is None or len(input_audios) == 0:
            return gr.Warning('请上传音频文件')
        
        timestamp = time.time()
        mission_name = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d_%H-%M-%S')
        mission_dir = client_dir / req.username / mission_name
        mission_dir.mkdir(parents=True, exist_ok=True)

        input_dir = mission_dir / 'inputs'
        output_dir = mission_dir / 'outputs'
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 将同一批上传的所有文件直接放入同一个输入目录，作为单个任务处理
        for input_audio in input_audios:
            input_path_obj = Path(input_audio)
            shutil.copyfile(input_path_obj, input_dir / input_path_obj.name)

        mission_json = mission_dir / 'mission.json'
        mission = Mission()
        mission.input_dir = str(input_dir)
        mission.output_dir = str(output_dir)
        mission.preset_name = preset_name
        mission.output_format = output_format
        mission.skip_existing_files = skip_existing_files
        mission.state = 'waiting'
        mission.output_file = mission_json
        mission.write()
        manager.add(mission)

        gr.Info('添加任务成功')
        return gr.Files(value=[])
    
    else:
        # 指定路径方式：使用用户指定的输入和输出路径
        if not input_path or not input_path.strip():
            return gr.Warning('请输入输入路径')
        if not output_path or not output_path.strip():
            return gr.Warning('请输入输出路径')
        
        input_path = input_path.strip()
        output_path = output_path.strip()
        
        # 路径规范化处理
        try:
            # 统一路径分隔符
            input_path = os.path.normpath(input_path)
            output_path = os.path.normpath(output_path)
            
            print(f"调试信息 - 输入路径: {input_path}")
            print(f"调试信息 - 输出路径: {output_path}")
            
            # 处理网络路径（UNC路径）
            if input_path.startswith('\\\\'):
                # 网络路径，尝试访问
                try:
                    if not os.path.exists(input_path):
                        return gr.Warning(f'网络路径不存在或无法访问: {input_path}\n请检查网络连接和路径是否正确')
                except Exception as e:
                    return gr.Warning(f'无法访问网络路径: {input_path}\n错误信息: {str(e)}\n请检查网络连接和权限')
            else:
                # 本地路径
                try:
                    if not os.path.exists(input_path):
                        return gr.Warning(f'输入路径不存在: {input_path}\n请检查路径是否正确')
                except Exception as e:
                    return gr.Warning(f'检查路径时出错: {input_path}\n错误信息: {str(e)}')
            
            # 检查输入路径是否为目录
            try:
                if not os.path.isdir(input_path):
                    return gr.Warning(f'输入路径必须是目录: {input_path}')
            except Exception as e:
                return gr.Warning(f'检查目录类型时出错: {input_path}\n错误信息: {str(e)}')
            
            # 检查输入目录中是否有音频文件
            audio_files = []
            try:
                # 使用os.listdir获取文件列表
                file_list = os.listdir(input_path)
                print(f"调试信息 - 目录中共有 {len(file_list)} 个文件/文件夹")
                
                for file in file_list:
                    file_path = os.path.join(input_path, file)
                    if os.path.isfile(file_path) and file.lower().endswith(('.wav', '.flac', '.mp3', '.m4a', '.aac', '.ogg')):
                        audio_files.append(file_path)
                        print(f"调试信息 - 找到音频文件: {file}")
                
                print(f"调试信息 - 总共找到 {len(audio_files)} 个音频文件")
                
            except PermissionError:
                return gr.Warning(f'没有权限访问目录: {input_path}\n请检查文件权限')
            except Exception as e:
                return gr.Warning(f'读取目录时出错: {input_path}\n错误信息: {str(e)}')
            
            if not audio_files:
                return gr.Warning(f'输入目录中没有找到音频文件: {input_path}\n支持的格式: .wav, .flac, .mp3, .m4a, .aac, .ogg')
            
            # 创建输出目录
            try:
                os.makedirs(output_path, exist_ok=True)
                print(f"调试信息 - 输出目录创建成功: {output_path}")
            except PermissionError:
                return gr.Warning(f'没有权限创建输出目录: {output_path}\n请检查目录权限')
            except Exception as e:
                return gr.Warning(f'创建输出目录时出错: {output_path}\n错误信息: {str(e)}')
            
        except Exception as e:
            return gr.Warning(f'路径处理时出错: {str(e)}\n请检查路径格式是否正确')
        
        timestamp = time.time()
        mission_name = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d_%H-%M-%S')
        mission_dir = client_dir / req.username / mission_name
        mission_dir.mkdir(parents=True, exist_ok=True)

        mission_json = mission_dir / 'mission.json'
        mission = Mission()
        mission.input_dir = input_path
        mission.output_dir = output_path
        mission.preset_name = preset_name
        mission.output_format = output_format
        mission.skip_existing_files = skip_existing_files
        mission.state = 'waiting'
        mission.output_file = mission_json
        mission.write()
        manager.add(mission)

        gr.Info(f'添加任务成功，将处理 {len(audio_files)} 个音频文件')
        return gr.Files(value=[])
