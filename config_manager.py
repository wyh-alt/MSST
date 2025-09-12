#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MSST WebUI 客户端配置管理工具
专门针对客户端（client.py）进行配置管理
"""

import os
import sys
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import shutil
from pathlib import Path

class ClientConfigManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MSST WebUI 客户端配置管理工具")
        self.root.geometry("750x800")
        self.root.resizable(True, True)
        self.root.minsize(700, 700)
        
        # 设置图标
        try:
            if os.path.exists("docs/logo.ico"):
                self.root.iconbitmap("docs/logo.ico")
        except:
            pass
        
        # 自动检测配置文件路径
        self.config_file = self._find_config_file("data/webui_config.json")
        self.user_file = self._find_config_file("user.json")
        self.client_config_file = self._find_config_file("client_config.json")
        
        self.load_configs()
        self.create_widgets()
        
    def _find_config_file(self, relative_path):
        """自动查找配置文件路径"""
        # 首先尝试当前目录
        if os.path.exists(relative_path):
            return relative_path
            
        # 尝试脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, relative_path)
        if os.path.exists(script_path):
            return script_path
            
        # 尝试上级目录
        parent_path = os.path.join(os.path.dirname(script_dir), relative_path)
        if os.path.exists(parent_path):
            return parent_path
            
        # 如果都找不到，返回原始路径（让后续错误处理）
        return relative_path
        
    def load_configs(self):
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.webui_config = json.load(f)
        except FileNotFoundError:
            messagebox.showerror("错误", f"找不到配置文件: {self.config_file}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            # 回退到备份配置
            fallback = None
            try:
                # 备份路径优先与项目内一致
                backup_candidate = self._find_config_file("data_backup/webui_config.json")
                with open(backup_candidate, 'r', encoding='utf-8') as f:
                    self.webui_config = json.load(f)
                fallback = backup_candidate
            except Exception as e2:
                messagebox.showerror(
                    "错误",
                    f"配置文件格式错误:\n{self.config_file}\n\n详细: {e}\n\n且无法从备份恢复: {e2}"
                )
                sys.exit(1)

            messagebox.showwarning(
                "警告",
                f"配置文件格式错误，已使用备份文件:\n原文件: {self.config_file}\n备份: {fallback}\n\n详细: {e}"
            )
            
        try:
            with open(self.user_file, 'r', encoding='utf-8') as f:
                self.user_config = json.load(f)
        except FileNotFoundError:
            self.user_config = {}
            
        # 加载客户端专用配置
        try:
            with open(self.client_config_file, 'r', encoding='utf-8') as f:
                self.client_config = json.load(f)
        except FileNotFoundError:
            # 创建默认客户端配置，使用程序中的目录设置
            default_user_dir = "E:/MSSTuser"  # 与clientui/actions.py中的设置保持一致
            self.client_config = {
                "client_port": 7861,
                "server_port": 7860,
                "server_address": "localhost",
                "user_dir": default_user_dir,  # 合并的上传下载目录
                "cache_dir": (os.path.join(os.path.expanduser("~"), "AppData", "Local", "MSST_WebUI", "cache")).replace('\\', '/'),
                "temp_dir": (os.path.join(os.path.expanduser("~"), "AppData", "Local", "MSST_WebUI", "temp")).replace('\\', '/'),
                "auto_clean_temp": True,
                "max_file_size": 100,  # MB
                "allowed_formats": ["wav", "mp3", "flac", "m4a", "ogg"]
            }
            self.save_client_config()
    
    def save_client_config(self):
        """保存客户端配置"""
        try:
            with open(self.client_config_file, 'w', encoding='utf-8') as f:
                json.dump(self.client_config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("错误", f"保存客户端配置失败: {str(e)}")
    
    def create_widgets(self):
        """创建界面组件"""
        # 创建主框架和滚动条
        canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 创建主框架
        main_frame = ttk.Frame(scrollable_frame, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置滚动
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except tk.TclError:
                pass  # 窗口已销毁，忽略错误
        
        # 保存canvas引用
        self.canvas = canvas
        
        # 绑定鼠标滚轮事件到canvas和root
        canvas.bind("<MouseWheel>", _on_mousewheel)
        self.root.bind("<MouseWheel>", _on_mousewheel)
        
        # 标题
        title_label = ttk.Label(main_frame, text="MSST WebUI 客户端配置管理工具", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # 当前配置状态显示
        status_frame = ttk.LabelFrame(main_frame, text="当前配置状态", padding="10")
        status_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 显示当前配置信息
        current_client_port = self.client_config.get('client_port', 7861)
        current_server_port = self.client_config.get('server_port', 7860)
        current_user_dir = self.client_config.get('user_dir', '未设置')
        current_cache = self.client_config.get('cache_dir', '未设置')
        current_temp = self.client_config.get('temp_dir', '未设置')
        
        
        # 创建配置信息显示区域
        config_info_frame = ttk.Frame(status_frame)
        config_info_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # 端口信息
        ttk.Label(config_info_frame, text=f"客户端端口: {current_client_port}", font=("Arial", 9)).grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        ttk.Label(config_info_frame, text=f"服务器端口: {current_server_port}", font=("Arial", 9)).grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # 目录信息 - 显示完整路径
        ttk.Label(config_info_frame, text=f"用户目录: {current_user_dir}", font=("Arial", 9)).grid(row=1, column=0, sticky=tk.W, padx=(0, 20))
        ttk.Label(config_info_frame, text=f"缓存目录: {current_cache}", font=("Arial", 9)).grid(row=1, column=1, sticky=tk.W, padx=(0, 20))
        ttk.Label(config_info_frame, text=f"临时目录: {current_temp}", font=("Arial", 9)).grid(row=2, column=0, sticky=tk.W, padx=(0, 20))
        
        # 添加刷新状态按钮
        ttk.Button(status_frame, text="刷新状态", command=self.refresh_status).grid(row=1, column=0, columnspan=2, pady=(5, 0))
        
        # 客户端端口设置
        port_frame = ttk.LabelFrame(main_frame, text="客户端端口设置", padding="10")
        port_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(port_frame, text="客户端端口:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.client_port_var = tk.StringVar(value=str(self.client_config.get('client_port', 7861)))
        client_port_entry = ttk.Entry(port_frame, textvariable=self.client_port_var, width=20)
        client_port_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        ttk.Label(port_frame, text="服务器端口:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.server_port_var = tk.StringVar(value=str(self.client_config.get('server_port', 7860)))
        server_port_entry = ttk.Entry(port_frame, textvariable=self.server_port_var, width=20)
        server_port_entry.grid(row=1, column=1, sticky=(tk.W, tk.E))
        
        ttk.Label(port_frame, text="服务器地址:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
        self.server_address_var = tk.StringVar(value=self.client_config.get('server_address', 'localhost'))
        server_address_entry = ttk.Entry(port_frame, textvariable=self.server_address_var, width=20)
        server_address_entry.grid(row=2, column=1, sticky=(tk.W, tk.E))
        
        # 目录设置
        dir_frame = ttk.LabelFrame(main_frame, text="目录设置", padding="10")
        dir_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 用户目录（合并上传下载目录）
        ttk.Label(dir_frame, text="用户目录 (上传/下载):").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=(0, 5))
        self.user_dir_var = tk.StringVar(value=self.client_config.get('user_dir', ''))
        user_dir_frame = ttk.Frame(dir_frame)
        user_dir_frame.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        user_dir_entry = ttk.Entry(user_dir_frame, textvariable=self.user_dir_var, width=40)
        user_dir_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(user_dir_frame, text="浏览", command=self.browse_user_dir).grid(row=0, column=1, padx=(5, 0))
        
        # 缓存目录
        ttk.Label(dir_frame, text="缓存目录:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(0, 5))
        self.cache_dir_var = tk.StringVar(value=self.client_config.get('cache_dir', ''))
        cache_dir_frame = ttk.Frame(dir_frame)
        cache_dir_frame.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        cache_dir_entry = ttk.Entry(cache_dir_frame, textvariable=self.cache_dir_var, width=40)
        cache_dir_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(cache_dir_frame, text="浏览", command=self.browse_cache_dir).grid(row=0, column=1, padx=(5, 0))
        
        # 临时目录
        ttk.Label(dir_frame, text="临时目录:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=(0, 5))
        self.temp_dir_var = tk.StringVar(value=self.client_config.get('temp_dir', ''))
        temp_dir_frame = ttk.Frame(dir_frame)
        temp_dir_frame.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        temp_dir_entry = ttk.Entry(temp_dir_frame, textvariable=self.temp_dir_var, width=40)
        temp_dir_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(temp_dir_frame, text="浏览", command=self.browse_temp_dir).grid(row=0, column=1, padx=(5, 0))
        
        # 其他设置
        other_frame = ttk.LabelFrame(main_frame, text="其他设置", padding="10")
        other_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 自动清理临时文件
        self.auto_clean_var = tk.BooleanVar(value=self.client_config.get('auto_clean_temp', True))
        ttk.Checkbutton(other_frame, text="自动清理临时文件", variable=self.auto_clean_var).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # 最大文件大小
        ttk.Label(other_frame, text="最大文件大小(MB):").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(0, 5))
        self.max_file_size_var = tk.StringVar(value=str(self.client_config.get('max_file_size', 100)))
        max_file_size_entry = ttk.Entry(other_frame, textvariable=self.max_file_size_var, width=10)
        max_file_size_entry.grid(row=1, column=1, sticky=tk.W, pady=(0, 5))
        
        # 用户管理
        user_frame = ttk.LabelFrame(main_frame, text="用户管理", padding="10")
        user_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 显示当前用户
        ttk.Label(user_frame, text="当前用户:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        user_list = ttk.Frame(user_frame)
        user_list.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E))
        
        self.user_listbox = tk.Listbox(user_list, height=3)
        self.user_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E))
        scrollbar = ttk.Scrollbar(user_list, orient=tk.VERTICAL, command=self.user_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.user_listbox.config(yscrollcommand=scrollbar.set)
        
        # 刷新用户列表
        self.refresh_user_list()
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=3, pady=(20, 10), sticky=(tk.W, tk.E))
        
        # 第一行按钮
        ttk.Button(button_frame, text="保存配置", command=self.save_config, width=12).grid(row=0, column=0, padx=(0, 10), pady=(0, 5))
        ttk.Button(button_frame, text="重置配置", command=self.reset_config, width=12).grid(row=0, column=1, padx=(0, 10), pady=(0, 5))
        ttk.Button(button_frame, text="创建目录", command=self.create_directories, width=12).grid(row=0, column=2, padx=(0, 10), pady=(0, 5))
        
        # 第二行按钮
        ttk.Button(button_frame, text="测试连接", command=self.test_connection, width=12).grid(row=1, column=0, padx=(0, 10), pady=(0, 5))
        ttk.Button(button_frame, text="退出", command=self.root.quit, width=12).grid(row=1, column=1, padx=(0, 10), pady=(0, 5))
        
        # 配置列权重
        main_frame.columnconfigure(1, weight=1)
        dir_frame.columnconfigure(1, weight=1)
        user_dir_frame.columnconfigure(0, weight=1)
        cache_dir_frame.columnconfigure(0, weight=1)
        temp_dir_frame.columnconfigure(0, weight=1)
        user_list.columnconfigure(0, weight=1)
    
    def browse_user_dir(self):
        """浏览用户目录"""
        directory = filedialog.askdirectory(title="选择用户目录 (上传/下载)")
        if directory:
            # 统一转换为正斜杠格式
            normalized_directory = directory.replace('\\', '/')
            self.user_dir_var.set(normalized_directory)
    
    def browse_cache_dir(self):
        """浏览缓存目录"""
        directory = filedialog.askdirectory(title="选择缓存目录")
        if directory:
            # 统一转换为正斜杠格式
            normalized_directory = directory.replace('\\', '/')
            self.cache_dir_var.set(normalized_directory)
    
    def browse_temp_dir(self):
        """浏览临时目录"""
        directory = filedialog.askdirectory(title="选择临时目录")
        if directory:
            # 统一转换为正斜杠格式
            normalized_directory = directory.replace('\\', '/')
            self.temp_dir_var.set(normalized_directory)
    
    def refresh_user_list(self):
        """刷新用户列表"""
        self.user_listbox.delete(0, tk.END)
        for username, user_info in self.user_config.items():
            admin_status = "管理员" if user_info.get('is_admin', False) else "普通用户"
            self.user_listbox.insert(tk.END, f"{username} ({admin_status})")
    
    def refresh_status(self):
        """刷新当前配置状态显示"""
        try:
            # 重新加载配置文件
            self.load_configs()
            
            # 更新输入框的值
            self.client_port_var.set(str(self.client_config.get('client_port', 7861)))
            self.server_port_var.set(str(self.client_config.get('server_port', 7860)))
            self.server_address_var.set(self.client_config.get('server_address', 'localhost'))
            self.user_dir_var.set(self.client_config.get('user_dir', ''))
            self.cache_dir_var.set(self.client_config.get('cache_dir', ''))
            self.temp_dir_var.set(self.client_config.get('temp_dir', ''))
            self.auto_clean_var.set(self.client_config.get('auto_clean_temp', True))
            self.max_file_size_var.set(str(self.client_config.get('max_file_size', 100)))
            
            # 刷新用户列表
            self.refresh_user_list()
            
            messagebox.showinfo("成功", "配置状态已刷新")
            
        except Exception as e:
            messagebox.showerror("错误", f"刷新状态失败: {str(e)}")
    
    def save_config(self):
        """保存配置"""
        try:
            # 验证端口号
            client_port = int(self.client_port_var.get())
            server_port = int(self.server_port_var.get())
            if client_port < 1 or client_port > 65535:
                messagebox.showerror("错误", "客户端端口号必须在1-65535之间")
                return
            if server_port < 1 or server_port > 65535:
                messagebox.showerror("错误", "服务器端口号必须在1-65535之间")
                return
            
            # 验证文件大小
            max_file_size = int(self.max_file_size_var.get())
            if max_file_size < 1 or max_file_size > 1000:
                messagebox.showerror("错误", "最大文件大小必须在1-1000MB之间")
                return
            
            # 统一路径分隔符为正斜杠
            def _normalize(p: str) -> str:
                return p.replace('\\', '/') if isinstance(p, str) else p

            # 更新客户端配置
            self.client_config['client_port'] = client_port
            self.client_config['server_port'] = server_port
            self.client_config['server_address'] = self.server_address_var.get()
            self.client_config['user_dir'] = _normalize(self.user_dir_var.get())
            self.client_config['cache_dir'] = _normalize(self.cache_dir_var.get())
            self.client_config['temp_dir'] = _normalize(self.temp_dir_var.get())
            self.client_config['auto_clean_temp'] = self.auto_clean_var.get()
            self.client_config['max_file_size'] = max_file_size
            
            # 保存客户端配置文件
            self.save_client_config()
            
            messagebox.showinfo("成功", "客户端配置已保存！\n请重启客户端以应用新配置。")
            
        except ValueError:
            messagebox.showerror("错误", "端口号和文件大小必须是数字")
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {str(e)}")
    
    def reset_config(self):
        """重置配置"""
        if messagebox.askyesno("确认", "确定要重置所有客户端配置到默认值吗？"):
            try:
                # 重置为默认值
                self.client_port_var.set("7861")
                self.server_port_var.set("7860")
                self.server_address_var.set("localhost")
                self.user_dir_var.set("E:/MSSTuser")  # 与程序中的设置保持一致
                self.cache_dir_var.set((os.path.join(os.path.expanduser("~"), "AppData", "Local", "MSST_WebUI", "cache")).replace('\\','/'))
                self.temp_dir_var.set((os.path.join(os.path.expanduser("~"), "AppData", "Local", "MSST_WebUI", "temp")).replace('\\','/'))
                self.auto_clean_var.set(True)
                self.max_file_size_var.set("100")
                
                messagebox.showinfo("成功", "配置已重置为默认值")
            except Exception as e:
                messagebox.showerror("错误", f"重置配置失败: {str(e)}")
    
    def create_directories(self):
        """创建配置的目录"""
        try:
            directories = [
                self.user_dir_var.get(),
                self.cache_dir_var.get(),
                self.temp_dir_var.get()
            ]
            
            created_dirs = []
            for directory in directories:
                if directory:
                    os.makedirs(directory, exist_ok=True)
                    created_dirs.append(directory)
            
            if created_dirs:
                messagebox.showinfo("成功", f"已创建以下目录:\n" + "\n".join(created_dirs))
            else:
                messagebox.showinfo("提示", "没有需要创建的目录")
        except Exception as e:
            messagebox.showerror("错误", f"创建目录失败: {str(e)}")
    
    def test_connection(self):
        """测试服务器连接"""
        try:
            import socket
            server_address = self.server_address_var.get()
            server_port = int(self.server_port_var.get())
            
            # 测试连接
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((server_address, server_port))
            sock.close()
            
            if result == 0:
                messagebox.showinfo("连接测试", f"成功连接到服务器 {server_address}:{server_port}")
            else:
                messagebox.showwarning("连接测试", f"无法连接到服务器 {server_address}:{server_port}\n请检查服务器是否正在运行")
                
        except Exception as e:
            messagebox.showerror("连接测试", f"连接测试失败: {str(e)}")
    
    def run(self):
        """运行配置管理器"""
        try:
            self.root.mainloop()
        except Exception as e:
            print(f"程序运行出错: {e}")
        finally:
            # 清理事件绑定
            try:
                if hasattr(self, 'canvas'):
                    self.canvas.unbind("<MouseWheel>")
                if hasattr(self, 'root'):
                    self.root.unbind("<MouseWheel>")
            except tk.TclError:
                pass  # 窗口已销毁，忽略错误

if __name__ == "__main__":
    try:
        app = ClientConfigManager()
        app.run()
    except Exception as e:
        messagebox.showerror("错误", f"启动配置管理器失败: {str(e)}")
        sys.exit(1)