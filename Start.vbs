Dim WshShell, FSO, folder, msg, ret

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

folder = FSO.GetParentFolderName(WScript.ScriptFullName)

msg = "DISCLAIMER" & vbCrLf & vbCrLf & _
      "This project is open-source and provided for learning, research, and reference only." & vbCrLf & _
      "Do NOT use it for any illegal activity, infringement, rule evasion, or other improper purpose." & vbCrLf & vbCrLf & _
      "All risks, responsibilities, disputes, and consequences caused by using this project shall be borne by the user." & vbCrLf & _
      "The author and contributors are not responsible for any misuse." & vbCrLf & vbCrLf & _
      "Click OK to continue, or Cancel to exit."

ret = MsgBox(msg, vbOKCancel + vbExclamation + vbSystemModal, "DISCLAIMER")

If ret = vbOK Then
    WshShell.CurrentDirectory = folder
    WshShell.Run Chr(34) & folder & "\Start.bat" & Chr(34), 0, False
End If
