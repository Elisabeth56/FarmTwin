; Before files are replaced, stop a running FarmTwin's background processes, then remove the old
; sidecar folders so a reinstall can't keep stale binaries (tauri-apps/tauri#15134).
!macro NSIS_HOOK_PREINSTALL
  nsExec::Exec 'taskkill /F /T /IM farmtwin-api.exe'
  nsExec::Exec 'taskkill /F /T /IM llama-server.exe'
  RMDir /r "$INSTDIR\api"
  RMDir /r "$INSTDIR\llama"
!macroend
