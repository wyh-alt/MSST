; MSST WebUI 增强安装脚本 - 最终版本
; 支持自定义安装路径、临时目录、端口和账户设置
; 兼容 Inno Setup 6
; 创建桌面快捷方式指向 MSST.bat 和配置管理工具

#define MyAppName "MSST WebUI"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "SUC-DriverOld"
#define MyAppURL "https://github.com/SUC-DriverOld/MSST-WebUI"
#define MyAppExeName "MSST.bat"
#define MyConfigManager "config_manager.py"

[Setup]
AppId={{8B2F5D3C-4A7E-4F9B-8C1D-2E6A5B8F9C0E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=MSST_WebUI_Setup_{#MyAppVersion}
SetupIconFile=docs\logo.ico
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\docs\logo.ico
LicenseFile=LICENSE
InfoBeforeFile=installer_readme.md
WizardStyle=modern
DisableWelcomePage=no
DisableDirPage=no
DisableReadyPage=no
DisableFinishedPage=no
DiskSpanning=yes
SlicesPerDisk=1


[Languages]
#if FileExists(AddBackslash(GetEnv('ProgramFiles(x86)')) + 'Inno Setup 6\\Languages\\ChineseSimplified.isl') || FileExists(AddBackslash(GetEnv('ProgramFiles')) + 'Inno Setup 6\\Languages\\ChineseSimplified.isl')
Name: "chinesesimp"; MessagesFile: "compiler:Languages\\ChineseSimplified.isl"
#endif
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "full"; Description: "完整安装 (推荐)"
Name: "custom"; Description: "自定义安装"; Flags: iscustom

[Components]
Name: "main"; Description: "MSST WebUI 主程序"; Types: full custom; Flags: fixed
Name: "python"; Description: "Python 运行环境"; Types: full custom; Flags: fixed
Name: "models"; Description: "模型配置文件"; Types: full custom
Name: "tools"; Description: "附加工具"; Types: full custom
Name: "presets"; Description: "预设配置"; Types: full custom
; 使用 Tasks 控制桌面快捷方式，不再作为组件

[Files]
; Python 环境
Source: "workenv\*"; DestDir: "{app}\workenv"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: python

; 主程序文件
Source: "*.py"; DestDir: "{app}"; Flags: ignoreversion; Components: main
Source: "*.bat"; DestDir: "{app}"; Flags: ignoreversion; Components: main
Source: "*.json"; DestDir: "{app}"; Flags: ignoreversion; Components: main
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion; Components: main

; 程序模块
Source: "clientui\*"; DestDir: "{app}\clientui"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
Source: "inference\*"; DestDir: "{app}\inference"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
Source: "modules\*"; DestDir: "{app}\modules"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
Source: "scripts\*"; DestDir: "{app}\scripts"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
Source: "utils\*"; DestDir: "{app}\utils"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
Source: "webui\*"; DestDir: "{app}\webui"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
Source: "train\*"; DestDir: "{app}\train"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main

; 模型和配置文件
Source: "configs\*"; DestDir: "{app}\configs"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: models
Source: "configs_backup\*"; DestDir: "{app}\configs_backup"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: models
Source: "config_unofficial\*"; DestDir: "{app}\config_unofficial"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: models
Source: "data\*"; DestDir: "{app}\data"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: models
Source: "data_backup\*"; DestDir: "{app}\data_backup"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: models

; 预训练模型文件
Source: "pretrain\*"; DestDir: "{app}\pretrain"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: models

; 工具和预设
Source: "tools\*"; DestDir: "{app}\tools"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: tools
Source: "presets\*"; DestDir: "{app}\presets"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: presets

; 文档和资源
Source: "docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main

; 配置管理工具
Source: "config_manager.py"; DestDir: "{app}"; Flags: ignoreversion; Components: main
Source: "verify_installation.py"; DestDir: "{app}"; Flags: ignoreversion; Components: main
Source: "fix_model_paths.py"; DestDir: "{app}"; Flags: ignoreversion; Components: main

; FFmpeg 工具
Source: "ffmpeg\*"; DestDir: "{app}\ffmpeg"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: tools

[Dirs]
; 创建必要的目录
Name: "{localappdata}\MSST_WebUI\cache"; Permissions: everyone-full
Name: "{app}\logs"; Permissions: everyone-full
Name: "{app}\cache"; Permissions: everyone-full
Name: "{app}\tmpdir"; Permissions: everyone-full
Name: "{app}\input"; Permissions: everyone-full
Name: "{app}\results"; Permissions: everyone-full
Name: "{app}\pretrain"; Permissions: everyone-full

[Tasks]
Name: desktopicon; Description: "创建桌面快捷方式 (MSST.bat)"; Flags: checkedonce
Name: desktopconfig; Description: "创建桌面快捷方式 (配置管理工具)"

[Icons]
; 开始菜单快捷方式
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\docs\logo.ico"
Name: "{autoprograms}\{#MyAppName}\配置管理工具"; Filename: "{app}\workenv\python.exe"; Parameters: "config_manager.py"; WorkingDir: "{app}"; IconFilename: "{app}\docs\logo.ico"
Name: "{autoprograms}\{#MyAppName}\安装验证工具"; Filename: "{app}\workenv\python.exe"; Parameters: "verify_installation.py"; WorkingDir: "{app}"; IconFilename: "{app}\docs\logo.ico"
Name: "{autoprograms}\{#MyAppName}\卸载程序"; Filename: "{uninstallexe}"; IconFilename: "{app}\docs\logo.ico"

; 桌面快捷方式（根据用户选择）
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\docs\logo.ico"; Tasks: desktopicon
Name: "{autodesktop}\{#MyAppName} 配置管理工具"; Filename: "{app}\workenv\python.exe"; Parameters: "config_manager.py"; WorkingDir: "{app}"; IconFilename: "{app}\docs\logo.ico"; Tasks: desktopconfig

[Run]
; 安装完成后运行选项
Filename: "{app}\workenv\python.exe"; Parameters: "fix_model_paths.py --silent"; WorkingDir: "{app}"; Flags: runhidden; StatusMsg: "正在修复模型目录配置..."; Description: "修复模型目录配置"
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent unchecked
Filename: "{app}\workenv\python.exe"; Parameters: "config_manager.py"; WorkingDir: "{app}"; Description: "打开配置管理工具"; Flags: nowait postinstall skipifsilent unchecked

[UninstallDelete]
; 卸载时删除的目录和文件
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\cache"
Type: filesandordirs; Name: "{app}\tmpdir"
Type: filesandordirs; Name: "{localappdata}\MSST_WebUI"
Type: files; Name: "{app}\user.json"
Type: files; Name: "{app}\client_config.json"
Type: files; Name: "{app}\install_config.json"

[Code]
var
  // 自定义页面变量
  PortPage: TInputQueryWizardPage;
  AccountPage: TInputQueryWizardPage;
  UserDirPage: TInputQueryWizardPage;
  CacheDirPage: TInputQueryWizardPage;
  // 目录browse按钮变量
  UserDirBrowseButton: TNewButton;
  CacheDirBrowseButton: TNewButton;
  // 桌面快捷方式由 [Tasks] 控制，不在此创建页面

// 自定义字符串替换函数
function CustomStringReplace(S, OldPattern, NewPattern: string): string;
var
  SearchStr, Patt, NewStr: string;
  Offset: Integer;
begin
  SearchStr := S;
  Patt := OldPattern;
  NewStr := NewPattern;

  Result := '';
  while SearchStr <> '' do
  begin
    Offset := Pos(Patt, SearchStr);
    if Offset = 0 then
    begin
      Result := Result + SearchStr;
      Break;
    end;
    Result := Result + Copy(SearchStr, 1, Offset - 1) + NewStr;
    SearchStr := Copy(SearchStr, Offset + Length(Patt), Length(SearchStr));
  end;
end;

// 用户目录browse按钮点击事件
procedure UserDirBrowseButtonClick(Sender: TObject);
var
  SelectedDir: String;
begin
  SelectedDir := UserDirPage.Values[0];
  if BrowseForFolder('选择用户目录 (上传/下载)', SelectedDir, False) then
  begin
    // 转换为正斜杠格式
    SelectedDir := CustomStringReplace(SelectedDir, '\', '/');
    UserDirPage.Values[0] := SelectedDir;
  end;
end;

// 缓存目录browse按钮点击事件
procedure CacheDirBrowseButtonClick(Sender: TObject);
var
  SelectedDir: String;
begin
  SelectedDir := CacheDirPage.Values[0];
  if BrowseForFolder('选择缓存目录', SelectedDir, False) then
  begin
    // 转换为正斜杠格式
    SelectedDir := CustomStringReplace(SelectedDir, '\', '/');
    CacheDirPage.Values[0] := SelectedDir;
  end;
end;

// 自定义函数：转义JSON路径并转换为正斜杠格式
function EscapeJsonPath(Path: String): String;
var
  i: Integer;
  EscapedPath: String;
begin
  EscapedPath := '';
  for i := 1 to Length(Path) do
  begin
    if Path[i] = '\' then
      EscapedPath := EscapedPath + '/'
    else
      EscapedPath := EscapedPath + Path[i];
  end;
  Result := EscapedPath;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
end;

procedure CreateCustomPages;
begin
  // 创建客户端端口设置页面
  PortPage := CreateInputQueryPage(wpSelectComponents,
    '客户端端口设置', '请设置客户端端口',
    '请输入客户端端口号 (默认: 7861):');
  PortPage.Add('客户端端口号:', False);
  PortPage.Values[0] := '7861';

  // 创建账户设置页面
  AccountPage := CreateInputQueryPage(PortPage.ID,
    '管理员账户设置', '请设置初始管理员账户信息',
    '请输入管理员用户名和密码:');
  AccountPage.Add('用户名:', False);
  AccountPage.Add('密码:', True);
  AccountPage.Values[0] := 'admin';
  AccountPage.Values[1] := 'admin123';

  // 创建用户目录设置页面（合并输入/输出目录为一个用户目录）
  UserDirPage := CreateInputQueryPage(AccountPage.ID,
    '用户目录设置', '请设置用户目录（用于上传/下载，替代输入/输出目录）',
    '请输入用户目录路径(推荐使用正斜杠"/"格式):');
  UserDirPage.Add('用户目录:', False);
  UserDirPage.Values[0] := CustomStringReplace(ExpandConstant('{localappdata}\MSST_WebUI\user'), '\', '/');
  
  // 为用户目录添加browse按钮
  UserDirBrowseButton := TNewButton.Create(UserDirPage);
  UserDirBrowseButton.Parent := UserDirPage.Surface;
  UserDirBrowseButton.Left := UserDirPage.Edits[0].Left + UserDirPage.Edits[0].Width + 10;
  UserDirBrowseButton.Top := UserDirPage.Edits[0].Top;
  UserDirBrowseButton.Width := 75;
  UserDirBrowseButton.Height := UserDirPage.Edits[0].Height;
  UserDirBrowseButton.Caption := '浏览...';
  UserDirBrowseButton.OnClick := @UserDirBrowseButtonClick;

  // 创建缓存目录设置页面
  CacheDirPage := CreateInputQueryPage(UserDirPage.ID,
    '缓存目录设置', '请设置缓存文件目录',
    '请输入缓存文件目录路径(推荐使用正斜杠"/"格式):');
  CacheDirPage.Add('缓存目录:', False);
  CacheDirPage.Values[0] := CustomStringReplace(ExpandConstant('{localappdata}\MSST_WebUI\cache'), '\', '/');
  
  // 为缓存目录添加browse按钮
  CacheDirBrowseButton := TNewButton.Create(CacheDirPage);
  CacheDirBrowseButton.Parent := CacheDirPage.Surface;
  CacheDirBrowseButton.Left := CacheDirPage.Edits[0].Left + CacheDirPage.Edits[0].Width + 10;
  CacheDirBrowseButton.Top := CacheDirPage.Edits[0].Top;
  CacheDirBrowseButton.Width := 75;
  CacheDirBrowseButton.Height := CacheDirPage.Edits[0].Height;
  CacheDirBrowseButton.Caption := '浏览...';
  CacheDirBrowseButton.OnClick := @CacheDirBrowseButtonClick;

  // 桌面快捷方式在 Tasks 页处理，无需自定义页面
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ClientPortStr: String;
  ClientPort: Integer;
  UserDir, CacheDir: String;
begin
  Result := True;
  
  if CurPageID = PortPage.ID then
  begin
    ClientPortStr := PortPage.Values[0];
    ClientPort := StrToIntDef(ClientPortStr, -1);
    if (ClientPort < 1) or (ClientPort > 65535) then
    begin
      MsgBox('请输入有效的客户端端口号 (1-65535)', mbError, MB_OK);
      Result := False;
    end;
  end
  else if CurPageID = AccountPage.ID then
  begin
    if Trim(AccountPage.Values[0]) = '' then
    begin
      MsgBox('用户名不能为空', mbError, MB_OK);
      Result := False;
    end
    else if Trim(AccountPage.Values[1]) = '' then
    begin
      MsgBox('密码不能为空', mbError, MB_OK);
      Result := False;
    end;
  end
  else if CurPageID = UserDirPage.ID then
  begin
    UserDir := UserDirPage.Values[0];
    if UserDir = '' then
    begin
      MsgBox('请输入有效的用户目录路径', mbError, MB_OK);
      Result := False;
    end;
  end
  else if CurPageID = CacheDirPage.ID then
  begin
    CacheDir := CacheDirPage.Values[0];
    if CacheDir = '' then
    begin
      MsgBox('请输入有效的缓存目录路径', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigFile: String;
  ConfigContent: String;
  UserFile: String;
  UserContent: String;
  ClientConfigFile: String;
  ClientConfigContent: String;
  ClientPortStr, Username, Password: String;
  UserDir, CacheDir, TempDir: String;
  InstallConfigFile: String;
  InstallConfigContent: String;
begin
  if CurStep = ssPostInstall then
  begin
    // 获取用户输入的值
    ClientPortStr := PortPage.Values[0];
    Username := AccountPage.Values[0];
    Password := AccountPage.Values[1];
    UserDir := UserDirPage.Values[0];
    CacheDir := CacheDirPage.Values[0];
    TempDir := AddBackslash(CacheDir) + 'temp';

    // 创建目录
    ForceDirectories(UserDir);
    ForceDirectories(CacheDir);
    ForceDirectories(TempDir);

    // 更新webui_config.json
    ConfigFile := ExpandConstant('{app}\data\webui_config.json');
    ConfigContent := 
      '{' + #13#10 +
      '    "version": "1.7.0 v2",' + #13#10 +
      '    "inference": {' + #13#10 +
      '        "model_type": "multi_stem_models",' + #13#10 +
      '        "selected_model": null,' + #13#10 +
      '        "input_dir": "' + UserDir + '",' + #13#10 +
      '        "store_dir": "' + UserDir + '",' + #13#10 +
      '        "device": null,' + #13#10 +
      '        "output_format": "wav",' + #13#10 +
      '        "force_cpu": false,' + #13#10 +
      '        "instrumental": null,' + #13#10 +
      '        "use_tta": false,' + #13#10 +
      '        "preset": "test_preset.json",' + #13#10 +
      '        "preset_use_tta": false,' + #13#10 +
      '        "extra_output_dir": false,' + #13#10 +
      '        "vr_select_model": null,' + #13#10 +
      '        "vr_window_size": 512,' + #13#10 +
      '        "vr_aggression": 5,' + #13#10 +
      '        "vr_batch_size": 2,' + #13#10 +
      '        "vr_primary_stem_only": false,' + #13#10 +
      '        "vr_secondary_stem_only": false,' + #13#10 +
      '        "vr_post_process_threshold": 0.2,' + #13#10 +
      '        "vr_invert_spect": false,' + #13#10 +
      '        "vr_enable_tta": false,' + #13#10 +
      '        "vr_high_end_process": false,' + #13#10 +
      '        "vr_enable_post_process": false,' + #13#10 +
      '        "ensemble_type": null,' + #13#10 +
      '        "ensemble_use_tta": false,' + #13#10 +
      '        "ensemble_extract_inst": false,' + #13#10 +
      '        "ensemble_preset": null' + #13#10 +
      '    },' + #13#10 +
      '    "tools": {' + #13#10 +
      '        "store_dir": null,' + #13#10 +
      '        "output_format": "wav",' + #13#10 +
      '        "sample_rate": 44100,' + #13#10 +
      '        "channels": 2,' + #13#10 +
      '        "wav_bit_depth": "PCM_16",' + #13#10 +
      '        "flac_bit_depth": "16-bit",' + #13#10 +
      '        "mp3_bit_rate": "320k",' + #13#10 +
      '        "ogg_bit_rate": "320k",' + #13#10 +
      '        "merge_audio_input": null' + #13#10 +
      '    },' + #13#10 +
      '    "training": {' + #13#10 +
      '        "model_type": null,' + #13#10 +
      '        "config_path": null,' + #13#10 +
      '        "dataset_type": null,' + #13#10 +
      '        "dataset_path": null,' + #13#10 +
      '        "valid_path": null,' + #13#10 +
      '        "num_workers": 0,' + #13#10 +
      '        "device": null,' + #13#10 +
      '        "seed": 0,' + #13#10 +
      '        "pin_memory": false,' + #13#10 +
      '        "use_multistft_loss": false,' + #13#10 +
      '        "use_mse_loss": false,' + #13#10 +
      '        "use_l1_loss": false,' + #13#10 +
      '        "accelerate": false,' + #13#10 +
      '        "pre_valid": false,' + #13#10 +
      '        "metrics": null,' + #13#10 +
      '        "metrics_scheduler": null,' + #13#10 +
      '        "results_path": null' + #13#10 +
      '    },' + #13#10 +
      '    "settings": {' + #13#10 +
      '        "uvr_model_dir": "' + EscapeJsonPath(ExpandConstant('{app}\\pretrain\\VR_Models')) + '",' + #13#10 +
      '        "port": 7860,' + #13#10 +
      '        "language": "Auto",' + #13#10 +
      '        "download_link": "Auto",' + #13#10 +
      '        "local_link": false,' + #13#10 +
      '        "share_link": false,' + #13#10 +
      '        "auto_clean_cache": true,' + #13#10 +
      '        "debug": false,' + #13#10 +
      '        "theme": "theme_blue.json",' + #13#10 +
      '        "wav_bit_depth": "PCM_16",' + #13#10 +
      '        "flac_bit_depth": "PCM_24",' + #13#10 +
      '        "mp3_bit_rate": "320k",' + #13#10 +
      '        "input_dir": "' + EscapeJsonPath(UserDir) + '",' + #13#10 +
      '        "output_dir": "' + EscapeJsonPath(UserDir) + '",' + #13#10 +
      '        "cache_dir": "' + EscapeJsonPath(CacheDir) + '",' + #13#10 +
      '        "user_dir": "' + EscapeJsonPath(UserDir) + '"' + #13#10 +
      '    }' + #13#10 +
      '}';
    
    SaveStringToFile(ConfigFile, ConfigContent, False);

    // 创建用户配置文件
    UserFile := ExpandConstant('{app}\user.json');
    UserContent := 
      '{' + #13#10 +
      '    "' + Username + '": {' + #13#10 +
      '        "psw": "TEMP_' + Password + '",' + #13#10 +
      '        "is_admin": true' + #13#10 +
      '    }' + #13#10 +
      '}';
    
    SaveStringToFile(UserFile, UserContent, False);

    // 创建客户端配置文件
    ClientConfigFile := ExpandConstant('{app}\client_config.json');
    ClientConfigContent := 
      '{' + #13#10 +
      '    "client_port": ' + ClientPortStr + ',' + #13#10 +
      '    "server_port": 7860,' + #13#10 +
      '    "server_address": "localhost",' + #13#10 +
      '    "user_dir": "' + EscapeJsonPath(UserDir) + '",' + #13#10 +
      '    "cache_dir": "' + EscapeJsonPath(CacheDir) + '",' + #13#10 +
      '    "temp_dir": "' + EscapeJsonPath(TempDir) + '",' + #13#10 +
      '    "auto_clean_temp": true,' + #13#10 +
      '    "max_file_size": 100,' + #13#10 +
      '    "allowed_formats": [' + #13#10 +
      '        "wav",' + #13#10 +
      '        "mp3",' + #13#10 +
      '        "flac",' + #13#10 +
      '        "m4a",' + #13#10 +
      '        "ogg"' + #13#10 +
      '    ]' + #13#10 +
      '}';
    
    SaveStringToFile(ClientConfigFile, ClientConfigContent, False);

    // 创建安装配置记录文件
    InstallConfigFile := ExpandConstant('{app}\install_config.json');
    InstallConfigContent := 
      '{' + #13#10 +
      '    "install_path": "' + EscapeJsonPath(ExpandConstant('{app}')) + '",' + #13#10 +
      '    "client_port": ' + ClientPortStr + ',' + #13#10 +
      '    "server_port": 7860,' + #13#10 +
      '    "username": "' + Username + '",' + #13#10 +
      '    "user_dir": "' + EscapeJsonPath(UserDir) + '",' + #13#10 +
      '    "cache_dir": "' + EscapeJsonPath(CacheDir) + '",' + #13#10 +
      '    "install_date": "' + GetDateTimeString('yyyy-mm-dd hh:nn:ss', #0, #0) + '",' + #13#10 +
      '    "version": "{#MyAppVersion}"' + #13#10 +
      '}';
    
    SaveStringToFile(InstallConfigFile, InstallConfigContent, False);
  end;
end;

procedure InitializeWizard;
begin
  CreateCustomPages;
end;

// 根据用户选择创建桌面快捷方式
// 不再使用 Code 处理桌面快捷方式，由 [Tasks] + [Icons] 处理

[CustomMessages]
english.LaunchProgram=Launch %1
english.LaunchConfigManager=Open Configuration Manager

