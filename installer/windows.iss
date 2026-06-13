[Setup]
AppName=pdf-tool
AppVersion=0.1.0
DefaultDirName={autopf}\pdf-tool
DefaultGroupName=pdf-tool
OutputBaseFilename=pdf-tool-setup
Compression=lzma
SolidCompression=yes
; Actualiza en sitio: instala sobre la versión previa en el mismo AppId.
AppId={{B5E1C0DE-PDF0-4F00-9000-PDFTOOL00001}}

[Files]
Source: "..\build\windows\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\pdf-tool"; Filename: "{app}\pdf-tool.exe"
Name: "{commondesktop}\pdf-tool"; Filename: "{app}\pdf-tool.exe"

[Run]
Filename: "{app}\pdf-tool.exe"; Description: "Abrir pdf-tool"; Flags: nowait postinstall skipifsilent
