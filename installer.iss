; Inno Setup Script for PhotoSorterAI
; https://jrsoftware.org/isinfo.php

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName=PhotoSorterAI
AppVersion=1.0.0
AppVerName=PhotoSorterAI 1.0.0
AppPublisher=PhotoSorterAI
AppPublisherURL=https://github.com/yourusername/photosortai
DefaultDirName={autopf}\PhotoSorterAI
DefaultGroupName=PhotoSorterAI
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=PhotoSorterAI_Setup_1.0.0
SetupIconFile=assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\PhotoSorterAI.exe
LicenseFile=LICENSE
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; PyInstaller로 빌드된 전체 디렉토리
Source: "dist\PhotoSorterAI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\PhotoSorterAI"; Filename: "{app}\PhotoSorterAI.exe"
Name: "{group}\{cm:UninstallProgram,PhotoSorterAI}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\PhotoSorterAI"; Filename: "{app}\PhotoSorterAI.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\PhotoSorterAI.exe"; Description: "{cm:LaunchProgram,PhotoSorterAI}"; Flags: nowait postinstall skipifsilent
