#define MyAppName "OneKey DIMP"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "OneKey Payments"
#define MyAppExeName "OneKey DIMP.exe"
#define MyAppURL "https://www.onekeypayments.com"
#define MyAppCopyright "Copyright (C) 2026 OneKey Payments. Todos os direitos reservados."
#define BuildOutput "release_build\output\OneKey DIMP"

[Setup]
AppId={{B2C3D4E5-F6A7-8901-BCDE-FA2345678901}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppCopyright={#MyAppCopyright}
VersionInfoVersion=1.1.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Processador DIMP - OneKey Payments
VersionInfoCopyright={#MyAppCopyright}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
DefaultDirName={commonpf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=release_build\installer
OutputBaseFilename=OneKeyDIMP_Setup_v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
DisableWelcomePage=no
ShowLanguageDialog=no
MinVersion=10.0
CloseApplications=force
RestartApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Area de Trabalho"; GroupDescription: "Atalhos:"

[Files]
Source: "{#BuildOutput}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Flags: nowait postinstall

[UninstallDelete]
Type: filesandordirs; Name: "{app}\__pycache__"
