!1:: {
    SetTitleMatchMode(2) ; allows partial window title match
    if WinExist("Visual Studio Code") {
        WinActivate()
    } else {
        Run "C:\Users\kennethn\AppData\Local\Programs\Microsoft VS Code\Code.exe"
    }
}
