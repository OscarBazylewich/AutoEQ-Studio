; AutoEQ Studio's installer (Inno Setup 6), built by make_installer.py ("Make installer.bat" in the main folder),
; which passes AppVersion (paths.VERSION), Stage (the program, its Python and the first-start files, staged) and OutDir.
;
; Installed for the current Windows user only, without an administrator prompt (the user's choice, 2026-10-11:
; Equalizer APO lets every user change its config folder, so nothing needs more): the program in
; %LOCALAPPDATA%\Programs\AutoEQ Studio, a Start menu shortcut (a desktop one if ticked), listed in Windows' Installed
; apps with its version and an uninstaller. Your files aren't in the program's folder (app\paths.py): an update
; replaces the program and keeps them. Uninstalling takes AutoEQ Studio out of Equalizer APO and Start with Windows
; (start.py --uninstall), and asks before deleting the settings, History and downloaded curves; your targets,
; measurements and saved EQs in Documents\AutoEQ Studio always stay.

#ifndef AppVersion
  #error Build it with make_installer.py (it passes AppVersion, Stage and OutDir)
#endif

; (TestBuild, make_installer.py --test-build: another app id and name, so installing and uninstalling it to try it
; never touches the user's own installation: its Installed apps entry, shortcuts and folder are the test's own)
#ifdef TestBuild
  #define AppName "AutoEQ Studio (test)"
  #define AppGuid "7E2B9A41-5C3D-4F80-9B16-2D4E8A6C1F35"
#else
  #define AppName "AutoEQ Studio"
  #define AppGuid "0D3FC27C-1B63-4214-80B6-48E182589F07"
#endif
#define Exe "{app}\runtime\AutoEQ Studio.exe"
; (start.py's path in quotes, written for inside a quoted parameter: "" is one ")
#define Start '""{app}\app\start.py""'

[Setup]
; (the app's id for Windows: never changed, or an update would install a second copy)
AppId={{{#AppGuid}}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppName}
AppComments=Makes EQs for headphones and IEMs, and gives each playback device its own EQ through Equalizer APO
VersionInfoVersion={#AppVersion}.0
VersionInfoDescription={#AppName} Setup
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=auto
UsePreviousAppDir=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
WizardStyle=modern dynamic
SetupIconFile={#Stage}\AutoEQ Studio.ico
UninstallDisplayIcon={app}\AutoEQ Studio.ico
UninstallDisplayName={#AppName}
OutputDir={#OutDir}
OutputBaseFilename={#AppName} Setup {#AppVersion}
Compression=lzma2/max
SolidCompression=yes
; (a running copy is asked to quit by the [Code] below, not by Windows' Restart Manager)
CloseApplications=no
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
; (an update: the old program goes first, so no module of the old version is left behind)
Type: filesandordirs; Name: "{app}\app"
Type: filesandordirs; Name: "{app}\runtime"
Type: filesandordirs; Name: "{app}\samples"
Type: filesandordirs; Name: "{app}\first-start"

[Files]
Source: "{#Stage}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{#Exe}"; Parameters: "{#Start}"; WorkingDir: "{app}"; \
  IconFilename: "{app}\AutoEQ Studio.ico"; AppUserModelID: "AutoEQStudio.AutoEQStudio"; \
  Comment: "Make EQs for headphones and IEMs; an EQ for each playback device"
Name: "{autodesktop}\{#AppName}"; Filename: "{#Exe}"; Parameters: "{#Start}"; WorkingDir: "{app}"; \
  IconFilename: "{app}\AutoEQ Studio.ico"; AppUserModelID: "AutoEQStudio.AutoEQStudio"; Tasks: desktopicon

[Run]
Filename: "{#Exe}"; Parameters: "{#Start}"; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,{#AppName}}"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
; (quits a running copy, takes AutoEQ Studio out of Equalizer APO's config.txt and this copy's Start with Windows)
Filename: "{#Exe}"; Parameters: "{#Start} --uninstall"; WorkingDir: "{app}"; Flags: waituntilterminated runhidden; \
  RunOnceId: "TakeOutOfApo"

[UninstallDelete]
; (what the program wrote in its own folder while it ran: Python's compiled files)
Type: filesandordirs; Name: "{app}\app"
Type: filesandordirs; Name: "{app}\runtime"
Type: dirifempty; Name: "{app}"

[Code]
const
#ifdef TestBuild
  Mutex = 'AutoEQStudioRunning-test';  { (a test build: the user's running app is none of its business) }
#else
  Mutex = 'AutoEQStudioRunning';  { (start.py holds it while the app runs) }
#endif

{ Ask the installed copy to quit (start.py --quit waits until it has). False when it isn't there to ask. }
function QuitInstalled(Dir: String): Boolean;
var
  Code: Integer;
begin
  Result := FileExists(Dir + '\runtime\AutoEQ Studio.exe') and FileExists(Dir + '\app\start.py');
  if Result then
    Exec(Dir + '\runtime\AutoEQ Studio.exe', AddQuotes(Dir + '\app\start.py') + ' --quit', Dir, SW_HIDE,
         ewWaitUntilTerminated, Code);
end;

{ AutoEQ Studio running: close it (the installed copy is asked to quit; another copy, e.g. one run from its own
  folder, is quit by you from its tray icon), or stop. }
function CloseRunning(Dir: String; Silent: Boolean): Boolean;
begin
  Result := True;
  while CheckForMutexes(Mutex) do
  begin
    if Silent then
      QuitInstalled(Dir)
    else if MsgBox('AutoEQ Studio is running. Close it and continue?' + #13#10#13#10 +
                   '(If it doesn''t close, quit it from its icon by the clock: right-click it, Quit.)',
                   mbConfirmation, MB_OKCANCEL) = IDOK then
      QuitInstalled(Dir)
    else
    begin
      Result := False;
      Exit;
    end;
    if Silent and CheckForMutexes(Mutex) then
    begin
      Result := False;
      Exit;
    end;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if not CloseRunning(ExpandConstant('{app}'), WizardSilent) then
    Result := 'AutoEQ Studio is still running: quit it from its icon by the clock, then run Setup again.';
end;

{ Windows' 260-character limit on paths: the program's deepest file is 122 characters below its folder. }
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = wpSelectDir) and (Length(WizardDirValue) > 130) then
  begin
    MsgBox('This folder''s path is too long for AutoEQ Studio''s files (Windows allows 260 characters). ' +
           'Choose a shorter one.', mbError, MB_OK);
    Result := False;
  end;
end;

function InitializeUninstall(): Boolean;
begin
  Result := CloseRunning(ExpandConstant('{app}'), UninstallSilent);
end;

function EnvDir(Name, Fallback: String): String;
{ (APPDATA or LOCALAPPDATA as app\paths.py reads them, so the folders deleted are the ones the app used) }
begin
  Result := GetEnv(Name);
  if Result = '' then
    Result := ExpandConstant(Fallback);
  Result := AddBackslash(Result) + '{#AppName}';
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and not UninstallSilent then
    if MsgBox('Also delete your AutoEQ Studio settings, History and downloaded curves?' + #13#10#13#10 +
              'Your targets, measurements and saved EQs in Documents\AutoEQ Studio are kept either way.',
              mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
    begin
      DelTree(EnvDir('APPDATA', '{userappdata}'), True, True, True);
      { (only the installed app's own parts of it: a copy run from a long folder keeps its Python environment in
        AutoEQ Studio\venv there, app\setup.bat) }
      DelTree(EnvDir('LOCALAPPDATA', '{localappdata}') + '\cache', True, True, True);
      DelTree(EnvDir('LOCALAPPDATA', '{localappdata}') + '\downloads', True, True, True);
      RemoveDir(EnvDir('LOCALAPPDATA', '{localappdata}'));
    end;
end;
