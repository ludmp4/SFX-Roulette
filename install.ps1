param(
    [string]$Repo = "ludmp4/SFX-Roulette",
    [string]$Branch = "main",
    [string]$InstallDir = "$env:APPDATA\Blackmagic Design\DaVinci Resolve\Support\Fusion\Modules\Python\SFX Roulette",
    [string]$ConfigDir = "$HOME\Documents\SFX Roulette",
    [string]$LauncherDir = "",
    [switch]$PreferGitHub,
    [switch]$Update,
    [switch]$Uninstall,
    [switch]$DryRun
)

$script = Join-Path $PSScriptRoot "scripts\install_windows.ps1"
& $script -Repo $Repo -Branch $Branch -InstallDir $InstallDir -ConfigDir $ConfigDir -LauncherDir $LauncherDir -PreferGitHub:$PreferGitHub -Update:$Update -Uninstall:$Uninstall -DryRun:$DryRun
