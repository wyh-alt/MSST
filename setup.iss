; MSST WebUI Installation Script - Minimal Version
; Compatible with Inno Setup 6

#define MyAppName "MSST WebUI"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "SUC-DriverOld"
#define MyAppURL "https://github.com/SUC-DriverOld/MSST-WebUI"
#define MyAppExeName "webUI.py"
#define MyAppExeNameBat "go-webui.bat"

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

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "full"; Description: "Full Installation"
Name: "custom"; Description: "Custom Installation"; Flags: iscustom

[Components]
Name: "main"; Description: "MSST WebUI Main Program"; Types: full custom; Flags: fixed
Name: "python"; Description: "Python Runtime Environment"; Types: full custom; Flags: fixed
Name: "models"; Description: "Model Configuration Files"; Types: full custom
Name: "tools"; Description: "Additional Tools"; Types: full custom
Name: "presets"; Description: "Preset Configurations"; Types: full custom
Name: "desktop"; Description: "Desktop Shortcut"; Types: full custom

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

[Dirs]
Name: "{localappdata}\MSST_WebUI\cache"; Permissions: everyone-full
Name: "{app}\logs"; Permissions: everyone-full
Name: "{app}\cache"; Permissions: everyone-full
Name: "{app}\tmpdir"; Permissions: everyone-full
Name: "{app}\input"; Permissions: everyone-full
Name: "{app}\results"; Permissions: everyone-full

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeNameBat}"; WorkingDir: "{app}"; IconFilename: "{app}\docs\logo.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeNameBat}"; WorkingDir: "{app}"; IconFilename: "{app}\docs\logo.ico"; Components: desktop

[Run]
Filename: "{app}\{#MyAppExeNameBat}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\cache"
Type: filesandordirs; Name: "{app}\tmpdir"
Type: filesandordirs; Name: "{localappdata}\MSST_WebUI"

[CustomMessages]
english.LaunchProgram=Launch %1