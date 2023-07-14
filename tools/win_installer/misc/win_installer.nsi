; Copyright 2016 Christoph Reiter
;
; This program is free software; you can redistribute it and/or modify
; it under the terms of the GNU General Public License as published by
; the Free Software Foundation; either version 2 of the License, or
; (at your option) any later version.

Unicode true

!define GPO_NAME "gPodder"
!define GPO_ID "gpodder"
!define GPO_DESC "Media aggregator and podcast client"

!define GPO_CMD_NAME "gpo"

!define GPO_WEBSITE "https://gpodder.github.io"

!define GPO_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${GPO_NAME}"
!define GPO_INSTDIR_KEY "Software\${GPO_NAME}"
!define GPO_INSTDIR_VALUENAME "InstDir"

!define MUI_CUSTOMFUNCTION_GUIINIT custom_gui_init
!include "MUI2.nsh"
!include "FileFunc.nsh"

Name "${GPO_NAME} (${VERSION})"
OutFile "gpodder-LATEST.exe"
SetCompressor /SOLID /FINAL lzma
SetCompressorDictSize 32
InstallDir "$PROGRAMFILES\${GPO_NAME}"
RequestExecutionLevel admin

Var GPO_INST_BIN
Var GPO_CMD_INST_BIN
Var UNINST_BIN

!define MUI_ABORTWARNING
!define MUI_ICON "gpodder.ico"

!insertmacro MUI_PAGE_LICENSE "gpodder\COPYING"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "Afrikaans"
!insertmacro MUI_LANGUAGE "Albanian"
!insertmacro MUI_LANGUAGE "Arabic"
!insertmacro MUI_LANGUAGE "Basque"
!insertmacro MUI_LANGUAGE "Belarusian"
!insertmacro MUI_LANGUAGE "Bosnian"
!insertmacro MUI_LANGUAGE "Breton"
!insertmacro MUI_LANGUAGE "Bulgarian"
!insertmacro MUI_LANGUAGE "Catalan"
!insertmacro MUI_LANGUAGE "Croatian"
!insertmacro MUI_LANGUAGE "Czech"
!insertmacro MUI_LANGUAGE "Danish"
!insertmacro MUI_LANGUAGE "Dutch"
!insertmacro MUI_LANGUAGE "Esperanto"
!insertmacro MUI_LANGUAGE "Estonian"
!insertmacro MUI_LANGUAGE "Farsi"
!insertmacro MUI_LANGUAGE "Finnish"
!insertmacro MUI_LANGUAGE "French"
!insertmacro MUI_LANGUAGE "Galician"
!insertmacro MUI_LANGUAGE "German"
!insertmacro MUI_LANGUAGE "Greek"
!insertmacro MUI_LANGUAGE "Hebrew"
!insertmacro MUI_LANGUAGE "Hungarian"
!insertmacro MUI_LANGUAGE "Icelandic"
!insertmacro MUI_LANGUAGE "Indonesian"
!insertmacro MUI_LANGUAGE "Irish"
!insertmacro MUI_LANGUAGE "Italian"
!insertmacro MUI_LANGUAGE "Japanese"
!insertmacro MUI_LANGUAGE "Korean"
!insertmacro MUI_LANGUAGE "Kurdish"
!insertmacro MUI_LANGUAGE "Latvian"
!insertmacro MUI_LANGUAGE "Lithuanian"
!insertmacro MUI_LANGUAGE "Luxembourgish"
!insertmacro MUI_LANGUAGE "Macedonian"
!insertmacro MUI_LANGUAGE "Malay"
!insertmacro MUI_LANGUAGE "Mongolian"
!insertmacro MUI_LANGUAGE "Norwegian"
!insertmacro MUI_LANGUAGE "NorwegianNynorsk"
!insertmacro MUI_LANGUAGE "Polish"
!insertmacro MUI_LANGUAGE "PortugueseBR"
!insertmacro MUI_LANGUAGE "Portuguese"
!insertmacro MUI_LANGUAGE "Romanian"
!insertmacro MUI_LANGUAGE "Russian"
!insertmacro MUI_LANGUAGE "SerbianLatin"
!insertmacro MUI_LANGUAGE "Serbian"
!insertmacro MUI_LANGUAGE "SimpChinese"
!insertmacro MUI_LANGUAGE "Slovak"
!insertmacro MUI_LANGUAGE "Slovenian"
!insertmacro MUI_LANGUAGE "SpanishInternational"
!insertmacro MUI_LANGUAGE "Spanish"
!insertmacro MUI_LANGUAGE "Swedish"
!insertmacro MUI_LANGUAGE "Thai"
!insertmacro MUI_LANGUAGE "TradChinese"
!insertmacro MUI_LANGUAGE "Turkish"
!insertmacro MUI_LANGUAGE "Ukrainian"
!insertmacro MUI_LANGUAGE "Uzbek"
!insertmacro MUI_LANGUAGE "Welsh"


Section "Install"
    SetShellVarContext all

    ; Use this to make things faster for testing installer changes
    ;~ SetOutPath "$INSTDIR\bin"
    ;~ File /r "mingw32\bin\*.exe"

    SetOutPath "$INSTDIR"
    File /r "mingw32\*.*"

    StrCpy $GPO_CMD_INST_BIN "$INSTDIR\bin\gpo.exe"
    StrCpy $GPO_INST_BIN "$INSTDIR\bin\gpodder.exe"
    StrCpy $UNINST_BIN "$INSTDIR\uninstall.exe"

    ; Store installation folder
    WriteRegStr HKLM "${GPO_INSTDIR_KEY}" "${GPO_INSTDIR_VALUENAME}" $INSTDIR

    ; Set up an entry for the uninstaller
    WriteRegStr HKLM "${GPO_UNINST_KEY}" \
        "DisplayName" "${GPO_NAME} - ${GPO_DESC}"
    WriteRegStr HKLM "${GPO_UNINST_KEY}" "DisplayIcon" "$\"$GPO_INST_BIN$\""
    WriteRegStr HKLM "${GPO_UNINST_KEY}" "UninstallString" \
        "$\"$UNINST_BIN$\""
    WriteRegStr HKLM "${GPO_UNINST_KEY}" "QuietUninstallString" \
    "$\"$UNINST_BIN$\" /S"
    WriteRegStr HKLM "${GPO_UNINST_KEY}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "${GPO_UNINST_KEY}" "HelpLink" "${GPO_WEBSITE}"
    WriteRegStr HKLM "${GPO_UNINST_KEY}" "Publisher" "The gPodder Team"
    WriteRegStr HKLM "${GPO_UNINST_KEY}" "DisplayVersion" "${VERSION}"
    WriteRegDWORD HKLM "${GPO_UNINST_KEY}" "NoModify" 0x1
    WriteRegDWORD HKLM "${GPO_UNINST_KEY}" "NoRepair" 0x1
    ; Installation size
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "${GPO_UNINST_KEY}" "EstimatedSize" "$0"

    ; Add application entry
    WriteRegStr HKLM "Software\${GPO_NAME}\${GPO_ID}\Capabilities" "ApplicationDescription" "${GPO_DESC}"
    WriteRegStr HKLM "Software\${GPO_NAME}\${GPO_ID}\Capabilities" "ApplicationName" "${GPO_NAME}"

    ; Register application entry
    WriteRegStr HKLM "Software\RegisteredApplications" "${GPO_NAME}" "Software\${GPO_NAME}\${GPO_ID}\Capabilities"

    ; Register app paths
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\gpodder.exe" "" "$GPO_INST_BIN"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\gpo.exe" "" "$GPO_CMD_INST_BIN"

    ; Create uninstaller
    WriteUninstaller "$UNINST_BIN"

    ; Create start menu shortcuts
    CreateDirectory "$SMPROGRAMS\${GPO_NAME}"
    CreateShortCut "$SMPROGRAMS\${GPO_NAME}\${GPO_NAME}.lnk" "$GPO_INST_BIN"
    CreateShortCut "$SMPROGRAMS\${GPO_NAME}\${GPO_CMD_NAME}.lnk" "$GPO_CMD_INST_BIN"
SectionEnd

Function custom_gui_init
    BringToFront

    ; Read the install dir and set it
    Var /GLOBAL instdir_temp
    Var /GLOBAL uninst_bin_temp

    SetRegView 32
    ReadRegStr $instdir_temp HKLM "${GPO_INSTDIR_KEY}" "${GPO_INSTDIR_VALUENAME}"
    SetRegView lastused
    StrCmp $instdir_temp "" skip 0
        StrCpy $INSTDIR $instdir_temp
    skip:

    SetRegView 64
    ReadRegStr $instdir_temp HKLM "${GPO_INSTDIR_KEY}" "${GPO_INSTDIR_VALUENAME}"
    SetRegView lastused
    StrCmp $instdir_temp "" skip2 0
        StrCpy $INSTDIR $instdir_temp
    skip2:

    StrCpy $uninst_bin_temp "$INSTDIR\uninstall.exe"

    ; try to un-install existing installations first
    IfFileExists "$INSTDIR" do_uninst do_continue
    do_uninst:
        ; instdir exists
        IfFileExists "$uninst_bin_temp" exec_uninst rm_instdir
        exec_uninst:
            ; uninstall.exe exists, execute it and
            ; if it returns success proceed, otherwise abort the
            ; installer (uninstall aborted by user for example)
            ExecWait '"$uninst_bin_temp" _?=$INSTDIR' $R1
            ; uninstall succeeded, since the uninstall.exe is still there
            ; goto rm_instdir as well
            StrCmp $R1 0 rm_instdir
            ; uninstall failed
            Abort
        rm_instdir:
            ; either the uninstaller was successful or
            ; the uninstaller.exe wasn't found
            RMDir /r "$INSTDIR"
    do_continue:
        ; the instdir shouldn't exist from here on

    BringToFront
FunctionEnd

Section "Uninstall"
    SetShellVarContext all
    SetAutoClose true

    ; Remove start menu entries
    Delete "$SMPROGRAMS\${GPO_NAME}\${GPO_NAME}.lnk"
    Delete "$SMPROGRAMS\${GPO_NAME}\${GPO_CMD_NAME}.lnk"
    RMDir "$SMPROGRAMS\${GPO_NAME}"

    ; Remove application registration and file assocs
    DeleteRegKey HKLM "Software\${GPO_NAME}"
    DeleteRegValue HKLM "Software\RegisteredApplications" "${GPO_NAME}"

    ; Remove app paths
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\gpodder.exe"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\gpo.exe"

    ; Delete installation related keys
    DeleteRegKey HKLM "${GPO_UNINST_KEY}"
    DeleteRegKey HKLM "${GPO_INSTDIR_KEY}"

    ; Delete files
    RMDir /r "$INSTDIR"
SectionEnd
