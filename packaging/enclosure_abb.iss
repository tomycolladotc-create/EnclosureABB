; Instalador de Windows por usuario para EnclosureABB (no requiere permisos de Administrador)
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{8D6B4F3E-4A7C-4D31-9B19-3A7E5E4F01A2}
AppName=EnclosureABB
AppVersion={#AppVersion}
AppVerName=EnclosureABB {#AppVersion}
AppPublisher=EnclosureABB
DefaultDirName={localappdata}\Programs\EnclosureABB
DefaultGroupName=EnclosureABB
AllowNoIcons=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\salida\instalador
OutputBaseFilename=EnclosureABB-Setup
SetupIconFile=..\datos\icon.ico
UninstallDisplayIcon={app}\EnclosureABB.exe
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
CloseApplications=force

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "..\salida\dist\EnclosureABB\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\EnclosureABB"; Filename: "{app}\EnclosureABB.exe"; IconFilename: "{app}\EnclosureABB.exe"
Name: "{autodesktop}\EnclosureABB"; Filename: "{app}\EnclosureABB.exe"; IconFilename: "{app}\EnclosureABB.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\EnclosureABB.exe"; Description: "Abrir EnclosureABB ahora"; Flags: nowait postinstall skipifsilent
