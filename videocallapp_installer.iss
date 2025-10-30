; Script de Inno Setup para VideoCall App
; Descarga Inno Setup de: https://jrsoftware.org/isdl.php

#define MyAppName "VideoCall App"
#define MyAppVersion "1.0"
#define MyAppPublisher "Tu Nombre"
#define MyAppExeName "VideoCallApp.exe"

[Setup]
; Información básica
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; LicenseFile=LICENSE.txt
; Descomenta la línea anterior si tienes LICENSE.txt
OutputDir=installer_output
OutputBaseFilename=VideoCallApp_Setup_v{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Imagen del instalador (opcional)
; WizardImageFile=installer_image.bmp
; WizardSmallImageFile=installer_small.bmp

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Ejecutable principal
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; Archivo de usuarios (se crea si no existe)
Source: "usuarios.json"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist; AfterInstall: CreateEmptyUsersFile
; Documentación (opcional)
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme; Check: FileExists(ExpandConstant('{tmp}\README.md'))
Source: "SOLUCION_PROBLEMAS.md"; DestDir: "{app}"; Flags: ignoreversion; Check: FileExists(ExpandConstant('{tmp}\SOLUCION_PROBLEMAS.md'))

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CreateEmptyUsersFile();
var
  UsersFile: string;
begin
  UsersFile := ExpandConstant('{app}\usuarios.json');
  if not FileExists(UsersFile) then
  begin
    SaveStringToFile(UsersFile, '{}', False);
  end;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  if not IsWin64 then
  begin
    MsgBox('Este programa requiere Windows de 64 bits.', mbError, MB_OK);
    Result := False;
  end;
end;