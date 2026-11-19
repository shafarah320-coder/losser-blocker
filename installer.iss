#define MyAppName "Screen Censor 2.0"
#define MyAppVersion "2.0.0"
#define MyAppExeName "ScreenCensor.exe"

[Setup]
AppId={{A2C7B61D-9B63-4BA2-9D6D-6B79A1D5E220}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\Screen Censor
DefaultGroupName=Screen Censor
OutputDir=output
OutputBaseFilename=ScreenCensor_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin

[Tasks]
Name: "desktopicon"; Description: "Buat shortcut di Desktop"; GroupDescription: "Shortcut tambahan:"

[Files]
Source: "dist\ScreenCensor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Screen Censor 2.0"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Screen Censor 2.0"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Jalankan Screen Censor"; Flags: postinstall nowait skipifsilent
