# install-markdown-preview-context-menu.ps1
# Adds a "Preview Markdown" option to Windows Explorer right-click context menu

# Check if running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "This script requires administrator privileges. Restarting as administrator..." -ForegroundColor Yellow
    Start-Process PowerShell -Verb RunAs "-File `"$PSCommandPath`""
    exit
}

Write-Host "Installing Markdown Preview Context Menu..." -ForegroundColor Green

# Create HKCR drive if it doesn't exist
if (!(Get-PSDrive -Name HKCR -ErrorAction SilentlyContinue)) {
    New-PSDrive -Name HKCR -PSProvider Registry -Root HKEY_CLASSES_ROOT | Out-Null
    Write-Host "Created HKCR registry drive" -ForegroundColor Cyan
}

# Registry paths
$mdFileKey = "HKCR:\.md"
$markdownKey = "HKCR:\MarkdownFile"
$shellKey = "$markdownKey\shell"
$previewKey = "$shellKey\preview"
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
Set-ItemProperty -Path $previewKey -Name "(Default)" -Value "Preview Markdown"
Set-ItemProperty -Path $previewKey -Name "Icon" -Value "shell32.dll,70"  # Document icon

# Create command key
if (!(Test-Path $commandKey)) {
    New-Item -Path $commandKey -Force | Out-Null
}

# PowerShell command to preview markdown
$command = 'powershell.exe -WindowStyle Hidden -Command "& { $file = \"%1\"; $content = Get-Content $file -Raw; $html = ConvertFrom-Markdown $content -AsVT100EncodedString; $tempFile = [System.IO.Path]::GetTempFileName() + \".html\"; Set-Content -Path $tempFile -Value @\"\n<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\"><title>$(Split-Path $file -Leaf)</title><style>body{font-family:\"Segoe UI\",Arial,sans-serif;max-width:800px;margin:0 auto;padding:20px;line-height:1.6;}pre{background:#f4f4f4;padding:10px;border-radius:4px;overflow-x:auto;}code{background:#f4f4f4;padding:2px 4px;border-radius:2px;}blockquote{border-left:4px solid #ddd;margin:0;padding-left:20px;font-style:italic;}table{border-collapse:collapse;width:100%;}th,td{border:1px solid #ddd;padding:8px;text-align:left;}th{background-color:#f2f2f2;}</style></head><body>$($content | ConvertFrom-Markdown | Select-Object -ExpandProperty Html)</body></html>\n\"@; Start-Process $tempFile; Start-Sleep 2; Remove-Item $tempFile -ErrorAction SilentlyContinue }"'

Set-ItemProperty -Path $commandKey -Name "(Default)" -Value $command

Write-Host "✅ Markdown Preview context menu installed successfully!" -ForegroundColor Green
Write-Host "Right-click any .md file in Explorer and select 'Preview Markdown'" -ForegroundColor Cyan

# Test if ConvertFrom-Markdown is available
try {
    $null = Get-Command ConvertFrom-Markdown -ErrorAction Stop
    Write-Host "✅ PowerShell Markdown support is available" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Warning: ConvertFrom-Markdown not found. You may need PowerShell 6+ or the Microsoft.PowerShell.Utility module" -ForegroundColor Yellow
    Write-Host "Consider installing a Markdown viewer like Typora or using VS Code instead" -ForegroundColor Yellow
}

Write-Host "`nPress any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
