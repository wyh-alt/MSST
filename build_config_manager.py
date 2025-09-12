#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理工具打包脚本
使用PyInstaller将config_manager.py打包为exe文件
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_dependencies():
    """检查依赖项"""
    print("检查依赖项...")
    
    # 检查PyInstaller
    try:
        import PyInstaller
        print(f"✅ PyInstaller版本: {PyInstaller.__version__}")
    except ImportError:
        print("❌ PyInstaller未安装，请运行: pip install pyinstaller")
        return False
    
    # 检查源文件
    if not os.path.exists("config_manager.py"):
        print("❌ 找不到config_manager.py文件")
        return False
    print("✅ 找到config_manager.py文件")
    
    # 检查图标文件
    if os.path.exists("docs/logo.ico"):
        print("✅ 找到图标文件: docs/logo.ico")
    else:
        print("⚠️ 未找到图标文件，将使用默认图标")
    
    return True

def create_spec_file():
    """创建PyInstaller spec文件"""
    print("\n创建PyInstaller spec文件...")
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['config_manager.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('docs/logo.ico', 'docs') if os.path.exists('docs/logo.ico') else None,
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'json',
        'os',
        'sys',
        'shutil',
        'pathlib',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MSST_Config_Manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='docs/logo.ico' if os.path.exists('docs/logo.ico') else None,
)
'''
    
    # 清理spec文件中的None值
    spec_content = '\n'.join([line for line in spec_content.split('\n') if 'None,' not in line])
    
    with open('config_manager.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("✅ 已创建config_manager.spec文件")
    return True

def build_exe():
    """构建exe文件"""
    print("\n开始构建exe文件...")
    
    try:
        # 使用spec文件构建
        cmd = [sys.executable, '-m', 'PyInstaller', '--clean', 'config_manager.spec']
        
        print(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            print("✅ exe文件构建成功")
            return True
        else:
            print(f"❌ 构建失败:")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 构建过程中出错: {e}")
        return False

def check_build_result():
    """检查构建结果"""
    print("\n检查构建结果...")
    
    exe_path = "dist/MSST_Config_Manager.exe"
    if os.path.exists(exe_path):
        file_size = os.path.getsize(exe_path)
        print(f"✅ exe文件已生成: {exe_path}")
        print(f"   文件大小: {file_size / 1024 / 1024:.2f} MB")
        return True
    else:
        print(f"❌ exe文件未找到: {exe_path}")
        return False

def create_installer_script():
    """创建安装包集成脚本"""
    print("\n创建安装包集成脚本...")
    
    installer_script = '''@echo off
REM MSST WebUI 配置管理工具安装脚本
REM 将配置管理工具复制到安装目录

echo 正在安装配置管理工具...

REM 检查exe文件是否存在
if not exist "MSST_Config_Manager.exe" (
    echo 错误: 找不到MSST_Config_Manager.exe文件
    pause
    exit /b 1
)

REM 复制exe文件到目标目录
copy "MSST_Config_Manager.exe" "%INSTALL_DIR%\\" >nul
if %errorlevel% neq 0 (
    echo 错误: 复制配置管理工具失败
    pause
    exit /b 1
)

echo 配置管理工具安装完成
echo 文件位置: %INSTALL_DIR%\\MSST_Config_Manager.exe

REM 创建桌面快捷方式（可选）
set /p create_shortcut="是否创建桌面快捷方式? (y/n): "
if /i "%create_shortcut%"=="y" (
    powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\\Desktop\\MSST配置管理工具.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\\MSST_Config_Manager.exe'; $Shortcut.Save()"
    echo 桌面快捷方式已创建
)

pause
'''
    
    with open('install_config_manager.bat', 'w', encoding='utf-8') as f:
        f.write(installer_script)
    
    print("✅ 已创建install_config_manager.bat安装脚本")
    
    # 创建Inno Setup脚本
    inno_script = '''; MSST WebUI 配置管理工具 Inno Setup 脚本
; 用于将配置管理工具集成到主安装包中

[Files]
; 配置管理工具exe文件
Source: "MSST_Config_Manager.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "MSST_Config_Manager.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; 开始菜单快捷方式
Name: "{group}\\MSST配置管理工具"; Filename: "{app}\\MSST_Config_Manager.exe"; WorkingDir: "{app}"
; 桌面快捷方式（可选）
Name: "{commondesktop}\\MSST配置管理工具"; Filename: "{app}\\MSST_Config_Manager.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"

[Run]
; 安装完成后运行配置管理工具（可选）
Filename: "{app}\\MSST_Config_Manager.exe"; Description: "运行配置管理工具"; Flags: postinstall nowait skipifsilent
'''
    
    with open('config_manager_inno.iss', 'w', encoding='utf-8') as f:
        f.write(inno_script)
    
    print("✅ 已创建config_manager_inno.iss Inno Setup脚本")

def cleanup():
    """清理临时文件"""
    print("\n清理临时文件...")
    
    temp_dirs = ['build', '__pycache__']
    temp_files = ['config_manager.spec']
    
    for temp_dir in temp_dirs:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"✅ 已删除临时目录: {temp_dir}")
    
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            os.remove(temp_file)
            print(f"✅ 已删除临时文件: {temp_file}")

def main():
    """主函数"""
    print("=" * 60)
    print("MSST WebUI 配置管理工具打包脚本")
    print("=" * 60)
    
    # 检查依赖项
    if not check_dependencies():
        return False
    
    # 创建spec文件
    if not create_spec_file():
        return False
    
    # 构建exe文件
    if not build_exe():
        return False
    
    # 检查构建结果
    if not check_build_result():
        return False
    
    # 创建安装包集成脚本
    create_installer_script()
    
    # 清理临时文件
    cleanup()
    
    print("\n" + "=" * 60)
    print("打包完成!")
    print("=" * 60)
    print("生成的文件:")
    print("  - dist/MSST_Config_Manager.exe (主程序)")
    print("  - install_config_manager.bat (安装脚本)")
    print("  - config_manager_inno.iss (Inno Setup脚本)")
    print("\n使用方法:")
    print("  1. 直接运行: dist/MSST_Config_Manager.exe")
    print("  2. 集成到安装包: 使用config_manager_inno.iss")
    print("  3. 手动安装: 运行install_config_manager.bat")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n发生错误: {e}")
        sys.exit(1)
