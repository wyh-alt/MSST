; MSST WebUI 配置管理工具 Inno Setup 脚本
; 用于将配置管理工具集成到主安装包中

[Files]
; 配置管理工具exe文件
Source: "MSST配置管理工具.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "MSST配置管理工具.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; 开始菜单快捷方式
Name: "{group}\MSST配置管理工具"; Filename: "{app}\MSST配置管理工具.exe"; WorkingDir: "{app}"
; 桌面快捷方式（可选）
Name: "{commondesktop}\MSST配置管理工具"; Filename: "{app}\MSST配置管理工具.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"

[Run]
; 安装完成后运行配置管理工具（可选）
Filename: "{app}\MSST配置管理工具.exe"; Description: "运行配置管理工具"; Flags: postinstall nowait skipifsilent
