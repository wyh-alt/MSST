; MSST WebUI Enhanced Installation Script
; 支持自定义安装路径、临时目录、端口和账户设置
; 兼容 Inno Setup 6

#define MyAppName "MSST WebUI"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "SUC-DriverOld"
#define MyAppURL "https://github.com/SUC-DriverOld/MSST-WebUI"
#define MyAppExeName "MSST.bat"

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

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "full"; Description: "完整安装"
Name: "custom"; Description: "自定义安装"; Flags: iscustom

[Components]
Name: "main"; Description: "MSST WebUI 主程序"; Types: full custom; Flags: fixed
Name: "python"; Description: "Python 运行环境"; Types: full custom; Flags: fixed
Name: "models"; Description: "模型配置文件"; Types: full custom
Name: "tools"; Description: "附加工具"; Types: full custom
Name: "presets"; Description: "预设配置"; Types: full custom
Name: "desktop"; Description: "桌面快捷方式"; Types: full custom

[Files]
Source: "workenv\*"; DestDir: "{app}\workenv"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: python
Source: "*.py"; DestDir: "{app}"; Flags: ignoreversion; Components: main
Source: "*.bat"; DestDir: "{app}"; Flags: ignoreversion; Components: main
Source: "*.json"; DestDir: "{app}"; Flags: ignoreversion; Components: main
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion; Components: main
Source: "clientui\*"; DestDir: "{app}\clientui"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
Source: "inference\*"; DestDir: "{app}\inference"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
Source: "modules\*"; DestDir: "{app}\modules"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
Source: "scripts\*"; DestDir: "{app}\scripts"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
Source: "utils\*"; DestDir: "{app}\utils"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
Source: "webui\*"; DestDir: "{app}\webui"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
Source: "train\*"; DestDir: "{app}\train"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
Source: "configs\*"; DestDir: "{app}\configs"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: models
Source: "configs_backup\*"; DestDir: "{app}\configs_backup"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: models
Source: "config_unofficial\*"; DestDir: "{app}\config_unofficial"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: models
Source: "data\*"; DestDir: "{app}\data"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: models
Source: "data_backup\*"; DestDir: "{app}\data_backup"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: models
Source: "tools\*"; DestDir: "{app}\tools"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: tools
Source: "presets\*"; DestDir: "{app}\presets"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: presets
Source: "docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
Source: "config_manager.py"; DestDir: "{app}"; Flags: ignoreversion; Components: main

[Dirs]
Name: "{localappdata}\MSST_WebUI\cache"; Permissions: everyone-full
Name: "{app}\logs"; Permissions: everyone-full
Name: "{app}\cache"; Permissions: everyone-full
Name: "{app}\tmpdir"; Permissions: everyone-full
Name: "{app}\input"; Permissions: everyone-full
Name: "{app}\results"; Permissions: everyone-full

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\docs\logo.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\docs\logo.ico"; Components: desktop
Name: "{autoprograms}\{#MyAppName}\配置管理工具"; Filename: "{app}\workenv\python.exe"; Parameters: "config_manager.py"; WorkingDir: "{app}"; IconFilename: "{app}\docs\logo.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\cache"
Type: filesandordirs; Name: "{app}\tmpdir"
Type: filesandordirs; Name: "{localappdata}\MSST_WebUI"

[Code]
var
  CustomPage: TInputQueryWizardPage;
  PortPage: TInputQueryWizardPage;
  AccountPage: TInputQueryWizardPage;
  InputDirPage: TInputQueryWizardPage;
  OutputDirPage: TInputQueryWizardPage;
  CacheDirPage: TInputQueryWizardPage;

function InitializeSetup(): Boolean;
begin
  Result := True;
end;

procedure CreateCustomPages;
begin
  // 创建端口设置页面
  PortPage := CreateInputQueryPage(wpSelectComponents,
    '服务器端口设置', '请设置WebUI服务器端口',
    '请输入服务器端口号 (默认: 7860):');
  PortPage.Add('端口号:', False);
  PortPage.Values[0] := '7860';

  // 创建账户设置页面
  AccountPage := CreateInputQueryPage(PortPage.ID,
    '管理员账户设置', '请设置初始管理员账户信息',
    '请输入管理员用户名和密码:');
  AccountPage.Add('用户名:', False);
  AccountPage.Add('密码:', True);
  AccountPage.Values[0] := 'admin';
  AccountPage.Values[1] := 'admin123';

  // 创建输入目录设置页面
  InputDirPage := CreateInputQueryPage(AccountPage.ID,
    '输入目录设置', '请设置临时输入文件目录',
    '请输入输入文件目录路径:');
  InputDirPage.Add('输入目录:', False);
  InputDirPage.Values[0] := ExpandConstant('{localappdata}\MSST_WebUI\input');

  // 创建输出目录设置页面
  OutputDirPage := CreateInputQueryPage(InputDirPage.ID,
    '输出目录设置', '请设置临时输出文件目录',
    '请输入输出文件目录路径:');
  OutputDirPage.Add('输出目录:', False);
  OutputDirPage.Values[0] := ExpandConstant('{localappdata}\MSST_WebUI\output');

  // 创建缓存目录设置页面
  CacheDirPage := CreateInputQueryPage(OutputDirPage.ID,
    '缓存目录设置', '请设置缓存文件目录',
    '请输入缓存文件目录路径:');
  CacheDirPage.Add('缓存目录:', False);
  CacheDirPage.Values[0] := ExpandConstant('{localappdata}\MSST_WebUI\cache');
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  PortStr: String;
  Port: Integer;
  InputDir, OutputDir, CacheDir: String;
begin
  Result := True;
  
  if CurPageID = PortPage.ID then
  begin
    PortStr := PortPage.Values[0];
    if not TryStrToInt(PortStr, Port) or (Port < 1) or (Port > 65535) then
    begin
      MsgBox('请输入有效的端口号 (1-65535)', mbError, MB_OK);
      Result := False;
    end;
  end
  else if CurPageID = InputDirPage.ID then
  begin
    InputDir := InputDirPage.Values[0];
    if InputDir = '' then
    begin
      MsgBox('请输入有效的输入目录路径', mbError, MB_OK);
      Result := False;
    end;
  end
  else if CurPageID = OutputDirPage.ID then
  begin
    OutputDir := OutputDirPage.Values[0];
    if OutputDir = '' then
    begin
      MsgBox('请输入有效的输出目录路径', mbError, MB_OK);
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
  PortStr, Username, Password: String;
  InputDir, OutputDir, CacheDir: String;
begin
  if CurStep = ssPostInstall then
  begin
    // 获取用户输入的值
    PortStr := PortPage.Values[0];
    Username := AccountPage.Values[0];
    Password := AccountPage.Values[1];
    InputDir := InputDirPage.Values[0];
    OutputDir := OutputDirPage.Values[0];
    CacheDir := CacheDirPage.Values[0];

    // 创建目录
    ForceDirectories(InputDir);
    ForceDirectories(OutputDir);
    ForceDirectories(CacheDir);

    // 更新webui_config.json
    ConfigFile := ExpandConstant('{app}\data\webui_config.json');
    ConfigContent := 
      '{' + #13#10 +
      '    "version": "1.7.0 v2",' + #13#10 +
      '    "inference": {' + #13#10 +
      '        "model_type": "multi_stem_models",' + #13#10 +
      '        "selected_model": null,' + #13#10 +
      '        "input_dir": "' + InputDir + '",' + #13#10 +
      '        "store_dir": "' + OutputDir + '",' + #13#10 +
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
      '        "wav_bit_depth": "PCM-16",' + #13#10 +
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
      '        "uvr_model_dir": "' + ExpandConstant('{app}\pretrain\VR_Models') + '",' + #13#10 +
      '        "port": ' + PortStr + ',' + #13#10 +
      '        "language": "Auto",' + #13#10 +
      '        "download_link": "Auto",' + #13#10 +
      '        "local_link": false,' + #13#10 +
      '        "share_link": false,' + #13#10 +
      '        "auto_clean_cache": true,' + #13#10 +
      '        "debug": false,' + #13#10 +
      '        "theme": "theme_blue.json",' + #13#10 +
      '        "wav_bit_depth": "FLOAT",' + #13#10 +
      '        "flac_bit_depth": "PCM_24",' + #13#10 +
      '        "mp3_bit_rate": "320k",' + #13#10 +
      '        "input_dir": "' + InputDir + '",' + #13#10 +
      '        "output_dir": "' + OutputDir + '",' + #13#10 +
      '        "cache_dir": "' + CacheDir + '"' + #13#10 +
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

    // 创建安装配置记录文件
    SaveStringToFile(ExpandConstant('{app}\install_config.json'), 
      '{"install_path": "' + ExpandConstant('{app}') + '", "port": ' + PortStr + ', "input_dir": "' + InputDir + '", "output_dir": "' + OutputDir + '", "cache_dir": "' + CacheDir + '"}', False);
  end;
end;

function InitializeWizard(): Boolean;
begin
  CreateCustomPages;
  Result := True;
end;

[CustomMessages]
chinesesimp.LaunchProgram=启动 %1
english.LaunchProgram=Launch %1
