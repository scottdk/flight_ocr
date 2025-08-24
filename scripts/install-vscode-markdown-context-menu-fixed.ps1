# install-vscode-markdown-context-menu-fixed.ps1
# Adds "Open with VS Code (Markdown Preview)" to right-click context menu
# Uses direct registry paths instead of PowerShell drives

# Check if running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "This script requires administrator privileges. Restarting as administrator..." -ForegroundColor Yellow
    Start-Process PowerShell -Verb RunAs "-File `"$PSCommandPath`""
    exit
}

Write-Host "Installing VS Code Markdown Preview Context Menu (Fixed)..." -ForegroundColor Green

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

# Direct registry paths (not using PowerShell drives)
$mdFileKey = "Registry::HKEY_CLASSES_ROOT\.md"
$markdownKey = "Registry::HKEY_CLASSES_ROOT\MarkdownFile"
$shellKey = "$markdownKey\shell"
$previewKey = "$shellKey\vscode_preview"
$commandKey = "$previewKey\command"

try {
    # Create .md file association if it doesn't exist
    if (!(Test-Path $mdFileKey)) {
        New-Item -Path $mdFileKey -Force | Out-Null
        Set-ItemProperty -Path $mdFileKey -Name "(Default)" -Value "MarkdownFile"
        Write-Host "✓ Created .md file association" -ForegroundColor Green
    }

    # Create MarkdownFile class if it doesn't exist
    if (!(Test-Path $markdownKey)) {
        New-Item -Path $markdownKey -Force | Out-Null
        Set-ItemProperty -Path $markdownKey -Name "(Default)" -Value "Markdown Document"
        Write-Host "✓ Created MarkdownFile class" -ForegroundColor Green
    }

    # Create shell key
    if (!(Test-Path $shellKey)) {
        New-Item -Path $shellKey -Force | Out-Null
        Write-Host "✓ Created shell key" -ForegroundColor Green
    }

    # Create preview key
    if (!(Test-Path $previewKey)) {
        New-Item -Path $previewKey -Force | Out-Null
        Write-Host "✓ Created preview key" -ForegroundColor Green
    }

    # Set the display name for the context menu item
    Set-ItemProperty -Path $previewKey -Name "(Default)" -Value "Preview in VS Code"
    Set-ItemProperty -Path $previewKey -Name "Icon" -Value "`"$vscodeCmd`",0"
    Write-Host "✓ Set menu display name and icon" -ForegroundColor Green

    # Create command key
    if (!(Test-Path $commandKey)) {
        New-Item -Path $commandKey -Force | Out-Null
        Write-Host "✓ Created command key" -ForegroundColor Green
    }

    # Command to open in VS Code with markdown preview
    $command = "`"$vscodeCmd`" `"%1`" --command `"markdown.showPreviewToSide`""
    Set-ItemProperty -Path $commandKey -Name "(Default)" -Value $command
    Write-Host "✓ Set preview command" -ForegroundColor Green

    Write-Host "`n✅ VS Code Markdown Preview context menu installed successfully!" -ForegroundColor Green
    Write-Host "Right-click any .md file in Explorer and select 'Preview in VS Code'" -ForegroundColor Cyan
    
} catch {
    Write-Host "❌ Error installing context menu: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Make sure you're running as Administrator" -ForegroundColor Yellow
    exit 1
}

Write-Host "`nPress any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
