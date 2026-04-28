import gradio as gr
from webui.preset import get_presets_list
import clientui.actions as actions
from clientui.mission import read_thread_count


def i18n(i):
    return i


def preset():
    with gr.Tab('创建任务'):
        gr.Markdown(
            value="该模式下的UVR推理参数将直接沿用UVR分离页面的推理参数, 如需修改请前往UVR分离页面。<br>修改完成后, 还需要任意处理一首歌才能保存参数! ")
        with gr.Row():
            preset_dropdown = gr.Dropdown(
                label=i18n("请选择预设"),
                choices=get_presets_list(),
                interactive=True, scale=4
            )
            output_format_flow = gr.Radio(
                label=i18n("输出格式"),
                choices=["wav", "flac", "mp3"],
                value="wav",
                interactive=True,
                scale=1,
            )
        
        # 添加跳过已有文件的选项
        with gr.Row():
            skip_existing_files = gr.Checkbox(
                label=i18n("跳过已有结果文件"),
                value=False,
                interactive=True,
                info=i18n("仅限异常中断再次创建任务，开启将额外消耗匹配及拷贝至临时路径的时间")
            )
        
        # 添加输入方式选择卡片
        with gr.Tabs() as input_tabs:
            with gr.TabItem(label=i18n("上传下载方式")) as upload_tab:
                input_audio = gr.Files(label=i18n("上传一个或多个音频文件"), type="filepath")
            
            with gr.TabItem(label=i18n("指定路径方式")) as path_tab:
                input_path = gr.Textbox(
                    label=i18n("输入路径"), 
                    placeholder="请输入输入文件夹路径，例如: D:/music/input 或 \\\\server\\share\\music", 
                    interactive=True
                )
                output_path = gr.Textbox(
                    label=i18n("输出路径"), 
                    placeholder="请输入输出文件夹路径，例如: D:/music/output 或 \\\\server\\share\\output", 
                    interactive=True
                )
        
        # 添加一个隐藏的组件来跟踪当前选中的标签页
        selected_tab = gr.State(value="upload")
        
        inference_audio = gr.Button(i18n("开始分离"), variant="primary", visible=True)

        # 当标签页切换时更新selected_tab
        def on_tab_change(evt: gr.SelectData):
            if evt.index == 0:
                return "upload"
            else:
                return "path"
        
        input_tabs.select(fn=on_tab_change, outputs=[selected_tab])

        inference_audio.click(fn=actions.infer,
                              inputs=[preset_dropdown,
                                      input_audio,
                                      input_path,
                                      output_path,
                                      output_format_flow,
                                      selected_tab,
                                      skip_existing_files],
                              outputs=[input_audio])


def mission():
    """
    任务管理
    """
    with gr.Tab('任务管理') as mission_tab:
        missions = gr.Radio(label='任务',
                            interactive=True)
        out_files = gr.Files(label='输出文件',
                             interactive=False)
        zip_file = gr.Files(label='zip',
                            interactive=False)
        state = gr.Textbox(label='任务状态',
                           interactive=False)
        with gr.Row():
            delete_mission = gr.Button(value='删除任务',
                                       variant='stop')
            make_zip = gr.Button(value='生成zip文件')
            refresh_mission = gr.Button(value='刷新任务状态',
                                       variant='secondary')

        delete_mission.click(fn=actions.delete_mission,
                             inputs=[missions],
                             outputs=[missions, out_files, zip_file, state])

        missions.change(fn=actions.select_mission,
                        inputs=[missions],
                        outputs=[out_files, zip_file, state])
        
        # 添加点击任务刷新按钮
        refresh_mission.click(fn=actions.refresh_mission_status,
                             inputs=[missions],
                             outputs=[out_files, zip_file, state])

        # 点击任务名称也可以刷新状态
        missions.select(fn=actions.refresh_mission_status,
                        inputs=[missions],
                        outputs=[out_files, zip_file, state])

        make_zip.click(fn=actions.make_zip,
                       inputs=[missions],
                       outputs=zip_file)

    mission_tab.select(fn=actions.switch2mission_tab,
                       outputs=[missions, out_files, zip_file, state])


def users():
    """
    用户管理
    """
    with gr.Tab('管理员') as user_tab:
        with gr.Tab('添加/删除') as manager:
            gr.Markdown(value='管理员可增加/删除用户/清空缓存')
            with gr.Row():
                thread_count = gr.Number(label='多线程数量',
                                         value=read_thread_count(),
                                         minimum=1,
                                         maximum=10,
                                         step=1)
                thread_count.change(fn=actions.thread_count_change,
                                    inputs=[thread_count])
                clear_cache = gr.Button(value='清空缓存',
                                        variant='stop')
                clear_cache.click(fn=actions.clear_cache)
            
            # 添加任务处理模式控制
            gr.Markdown(value='### 任务处理模式设置')
            with gr.Row():
                batch_mode = gr.Checkbox(label='启用批量处理模式',
                                         value=False,
                                         info='启用后会将相同预设的任务合并为批量任务处理')
                batch_mode.change(fn=actions.batch_mode_change,
                                  inputs=[batch_mode])
                
                force_batch_mode = gr.Checkbox(label='强制批量处理模式',
                                               value=False,
                                               info='启用后会强制使用批量处理，即使只有一个任务')
                force_batch_mode.change(fn=actions.force_batch_mode_change,
                                        inputs=[force_batch_mode])
            
            # 添加状态显示
            with gr.Row():
                status_display = gr.Textbox(label='任务管理器状态',
                                            value=actions.get_manager_status(),
                                            lines=8,
                                            interactive=False)
                refresh_status = gr.Button(value='刷新状态',
                                           variant='secondary')
                refresh_status.click(fn=actions.get_manager_status,
                                     outputs=[status_display])
            
            gr.Markdown(value='**说明**: 默认情况下系统使用多线程并行处理，每个任务独立运行。启用批量处理模式后，相同预设的任务会被合并处理以提高效率。')
            
            with gr.Tab('删除') as remove:
                choice_user = gr.Radio(label='选择用户',
                                       choices=actions.get_user_list(),
                                       interactive=True,
                                       scale=4)
                delete_user = gr.Button(value='删除',
                                        variant='stop')
                delete_user.click(fn=actions.delete_user,
                                  inputs=[choice_user],
                                  outputs=choice_user)
                remove.select(fn=actions.select_remove_user_tab,
                              outputs=choice_user)
            with gr.Tab('添加'):
                username = gr.Textbox(label='username',
                                      lines=1,
                                      max_lines=1)
                password = gr.Textbox(label='password',
                                      lines=1,
                                      max_lines=1)
                admin = gr.Checkbox(label='管理员',
                                    value=False,
                                    interactive=True)
                add_user = gr.Button(value='添加',
                                     variant='primary')
                add_user.click(fn=actions.add_user,
                               inputs=[username, password, admin],
                               outputs=[username, password, admin])
        with gr.Tab('修改密码'):
            psw = gr.Textbox(label='旧密码',
                             lines=1,
                             max_lines=1)
            new_psw = gr.Textbox(label='新密码',
                                 lines=1,
                                 max_lines=1)
            change_psw = gr.Button('修改密码',
                                   variant="primary",
                                   visible=True)
            change_psw.click(fn=actions.change_psw,
                             inputs=[psw, new_psw])

    user_tab.select(fn=actions.switch2user_tab,
                    outputs=manager)


def create_ui():
    # 添加自动刷新脚本
    auto_refresh_js = """
    <script>
    // 任务状态自动刷新脚本
    let autoRefreshInterval = null;
    
    // 开始自动刷新任务状态
    function startAutoRefresh() {
      if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
      }
      
      // 每30秒刷新一次任务状态
      autoRefreshInterval = setInterval(() => {
        const refreshButton = document.querySelector('button[aria-label="刷新任务状态"]');
        if (refreshButton) {
          refreshButton.click();
        }
      }, 30000);
    }
    
    // 停止自动刷新
    function stopAutoRefresh() {
      if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
      }
    }
    
    // 在任务管理标签页激活时启动自动刷新
    document.addEventListener("DOMContentLoaded", function() {
      const tabObserver = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
          if (mutation.type === 'childList') {
            const tabs = document.querySelectorAll('button[role="tab"]');
            for (const tab of tabs) {
              if (tab.textContent.includes('任务管理') && tab.getAttribute('aria-selected') === 'true') {
                startAutoRefresh();
                return;
              }
            }
          }
        }
      });
      
      // 监听DOM变化以检测标签页切换
      setTimeout(() => {
        const tabsContainer = document.querySelector('.tabs');
        if (tabsContainer) {
          tabObserver.observe(tabsContainer, { childList: true, subtree: true, attributes: true });
        }
        
        // 检查初始状态
        const missionTab = document.querySelector('button[role="tab"]:nth-child(2)');
        if (missionTab && missionTab.getAttribute('aria-selected') === 'true') {
          startAutoRefresh();
        }
      }, 2000); // 给页面加载一些时间
    });
    
    // 在页面卸载时清理
    window.addEventListener('beforeunload', () => {
      stopAutoRefresh();
    });
    </script>
    """
    
    gr.HTML(auto_refresh_js)  # 添加自动刷新脚本
    preset()
    mission()
    users()
