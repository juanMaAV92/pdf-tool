[Setup]
AppName=pdf-tool
AppVersion=0.1.0
DefaultDirName={autopf}\pdf-tool
; Explícito: instala para todos los usuarios en Archivos de programa (pide UAC).
; Cambiarlo movería la ruta de instalación y rompería la actualización en sitio.
PrivilegesRequired=admin
DefaultGroupName=pdf-tool
OutputBaseFilename=pdf-tool-setup
Compression=lzma
SolidCompression=yes
; Actualiza en sitio: instala sobre la versión previa en el mismo AppId.
AppId={{B5E1C0DE-PDF0-4F00-9000-PDFTOOL00001}}
; Idioma según el del sistema, como la app; solo pregunta si no hay coincidencia.
ShowLanguageDialog=auto

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[CustomMessages]
english.OpenApp=Open pdf-tool
spanish.OpenApp=Abrir pdf-tool

[Files]
Source: "..\build\windows\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\pdf-tool"; Filename: "{app}\pdf_tool.exe"
Name: "{commondesktop}\pdf-tool"; Filename: "{app}\pdf_tool.exe"

[Run]
Filename: "{app}\pdf_tool.exe"; Description: "{cm:OpenApp}"; Flags: nowait postinstall skipifsilent
