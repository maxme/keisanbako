; Keisanbako Windows Installer Script (NSIS)
; Install NSIS from: https://nsis.sourceforge.io

!include "MUI2.nsh"

; App Info
; DISTDIR is passed by the release workflow (absolute path to the dist folder)
!ifndef DISTDIR
  !define DISTDIR "..\dist"
!endif
Name "Keisanbako 0.1.0"
OutFile "${DISTDIR}\Keisanbako-0.1.0-installer.exe"
InstallDir "$PROGRAMFILES\Keisanbako"
RequestExecutionLevel admin

; MUI Settings
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

; Installer Section
Section "Install"
    SetOutPath "$INSTDIR"
    File /r "${DISTDIR}\Keisanbako\*.*"

    ; Create Start Menu shortcuts
    CreateDirectory "$SMPROGRAMS\Keisanbako"
    CreateShortCut "$SMPROGRAMS\Keisanbako\Keisanbako.lnk" "$INSTDIR\Keisanbako.exe"
    CreateShortCut "$SMPROGRAMS\Keisanbako\Uninstall.lnk" "$INSTDIR\uninstall.exe"

    ; Create uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

; Uninstaller Section
Section "Uninstall"
    RMDir /r "$INSTDIR"
    RMDir /r "$SMPROGRAMS\Keisanbako"
SectionEnd
