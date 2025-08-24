# install-vscode-markdown-context-menu.ps1
# Adds "Open with VS Code (Markdown Preview)" to right-click context menu

# Check if running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "This script requires administrator privileges. Restarting as administrator..." -ForegroundColor Yellow
    Start-Process PowerShell -Verb RunAs "-File `"$PSCommandPath`""
    exit
}

Write-Host "Installing VS Code Markdown Preview Context Menu..." -ForegroundColor Green

# Create HKCR drive if it doesn't exist
if (!(Get-PSDrive -Name HKCR -ErrorAction SilentlyContinue)) {
    New-PSDrive -Name HKCR -PSProvider Registry -Root HKEY_CLASSES_ROOT | Out-Null
    Write-Host "Created HKCR registry drive" -ForegroundColor Cyan
}

# Find VS Code installation
$vscodeCmd = Get-Command code -ErrorAction SilentlyContinue
if (-not $vscodeCmd) {
    # Try common installation paths
    $possiblePaths = @(
        "${env:LOCALAPPDATA}\Programs\Microsoft VS Code\Code.exe",
        "${env:PROGRAMFILES}\Microsoft VS Code\Code.exe",
        "${env:PROGRAMFILES(x86)}\Microsoft VS Code\Code.exe"
    )
    
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $vscodeCmd = $path
            break
        }
    }
    
    if (-not $vscodeCmd) {
        Write-Host "❌ VS Code not found. Please install VS Code first." -ForegroundColor Red
        Write-Host "Download from: https://code.visualstudio.com/" -ForegroundColor Cyan
        exit 1
    }
} else {
    $vscodeCmd = $vscodeCmd.Source
}

Write-Host "Found VS Code at: $vscodeCmd" -ForegroundColor Cyan

# Registry paths
$mdFileKey = "HKCR:\.md"
$markdownKey = "HKCR:\MarkdownFile"
$shellKey = "$markdownKey\shell"
$previewKey = "$shellKey\vscode_preview"
$commandKey = "$previewKey\command"

# Create .md file association if it doesn't exist
if (!(Test-Path $mdFileKey)) {
    New-Item -Path $mdFileKey -Force | Out-Null
    Set-ItemProperty -Path $mdFileKey -Name "(Default)" -Value "MarkdownFile"
}

# Create MarkdownFile class if it doesn't exist
if (!(Test-Path $markdownKey)) {
    New-Item -Path $markdownKey -Force | Out-Null
    Set-ItemProperty -Path $markdownKey -Name "(Default)" -Value "Markdown Document"
}

# Create shell key
if (!(Test-Path $shellKey)) {
    New-Item -Path $shellKey -Force | Out-Null
}

# Create preview key
if (!(Test-Path $previewKey)) {
    New-Item -Path $previewKey -Force | Out-Null
}

# Set the display name for the context menu item
Set-ItemProperty -Path $previewKey -Name "(Default)" -Value "Preview in VS Code"
Set-ItemProperty -Path $previewKey -Name "Icon" -Value "`"$vscodeCmd`",0"

# Create command key
if (!(Test-Path $commandKey)) {
    New-Item -Path $commandKey -Force | Out-Null
}

# Command to open in VS Code with markdown preview
$command = "`"$vscodeCmd`" `"%1`" --command `"markdown.showPreviewToSide`""
Set-ItemProperty -Path $commandKey -Name "(Default)" -Value $command

Write-Host "✅ VS Code Markdown Preview context menu installed successfully!" -ForegroundColor Green
Write-Host "Right-click any .md file in Explorer and select 'Preview in VS Code'" -ForegroundColor Cyan

Write-Host "`nPress any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
