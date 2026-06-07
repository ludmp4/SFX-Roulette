param(
    [string]$Repo = "ludmp4/SFX-Roulette",
    [string]$Branch = "main",
    [string]$InstallDir = "$env:LOCALAPPDATA\SFX Roulette",
    [string]$ConfigDir = "$HOME\Documents\SFX Roulette",
    [string]$LauncherDir = "",
    [switch]$Update,
    [switch]$Uninstall,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Step {
    param([string]$Message)
    Write-Host "SFX Roulette | $Message"
}

function Invoke-Step {
    param(
        [string]$Message,
        [scriptblock]$Action
    )
    Write-Step $Message
    if (-not $DryRun) {
        & $Action
    }
}

function Get-ResolveLauncherDir {
    if ($LauncherDir) {
        return $LauncherDir
    }
    return Join-Path $env:APPDATA "Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"
}

function Get-LocalSourceRoot {
    if (-not $PSScriptRoot) {
        return $null
    }
    $candidate = Split-Path -Parent $PSScriptRoot
    if (Test-Path (Join-Path $candidate "src\sfx_roulette\__init__.py")) {
        return $candidate
    }
    return $null
}

function Get-GitHubSourceRoot {
    $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("sfx-roulette-" + [guid]::NewGuid().ToString("N"))
    $zipPath = Join-Path $tempRoot "source.zip"
    $archiveUrl = "https://github.com/$Repo/archive/refs/heads/$Branch.zip"

    Invoke-Step "Downloading latest source from $archiveUrl" {
        New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $archiveUrl -OutFile $zipPath -UseBasicParsing
        Expand-Archive -LiteralPath $zipPath -DestinationPath $tempRoot -Force
    }

    if ($DryRun) {
        return $null
    }

    $sourceRoot = Get-ChildItem -LiteralPath $tempRoot -Directory | Select-Object -First 1
    if (-not $sourceRoot -or -not (Test-Path (Join-Path $sourceRoot.FullName "src\sfx_roulette\__init__.py"))) {
        throw "Downloaded archive did not contain the expected SFX Roulette source layout."
    }
    return $sourceRoot.FullName
}

function Copy-AppFiles {
    param([string]$SourceRoot)

    $items = @("src", "config", "docs", "scripts", "tests", "main.py", "README.md")

    Invoke-Step "Creating install directory: $InstallDir" {
        New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    }

    foreach ($item in $items) {
        $source = Join-Path $SourceRoot $item
        if (-not (Test-Path $source)) {
            continue
        }
        $destination = Join-Path $InstallDir $item
        Invoke-Step "Installing $item" {
            if (Test-Path $destination) {
                Remove-Item -LiteralPath $destination -Recurse -Force
            }
            Copy-Item -LiteralPath $source -Destination $destination -Recurse -Force
        }
    }
}

function Write-ResolveLauncher {
    $launcherDir = Get-ResolveLauncherDir
    $launcherPath = Join-Path $launcherDir "SFX Roulette.py"
    $escapedInstallDir = $InstallDir.Replace("\", "\\")
    $launcher = @"
import sys
from pathlib import Path

install_dir = Path(r"$escapedInstallDir")
src_dir = install_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from sfx_roulette.ui import SFXRouletteUI
SFXRouletteUI().run()
"@

    Invoke-Step "Writing Resolve launcher: $launcherPath" {
        New-Item -ItemType Directory -Force -Path $launcherDir | Out-Null
        Set-Content -LiteralPath $launcherPath -Value $launcher -Encoding UTF8
    }
}

function Initialize-Config {
    $exampleSource = Join-Path $InstallDir "config\example_config.json"
    $configPath = Join-Path $ConfigDir "sfx_roulette_config.json"
    $exampleDestination = Join-Path $ConfigDir "sfx_roulette_config.example.json"

    Invoke-Step "Preparing settings directory: $ConfigDir" {
        New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null
        if (Test-Path $exampleSource) {
            Copy-Item -LiteralPath $exampleSource -Destination $exampleDestination -Force
            if (-not (Test-Path $configPath)) {
                Copy-Item -LiteralPath $exampleSource -Destination $configPath -Force
            }
        }
    }
}

function Write-VersionInfo {
    $versionPath = Join-Path $InstallDir "install.json"
    $payload = [ordered]@{
        repo = $Repo
        branch = $Branch
        installed_at = (Get-Date).ToUniversalTime().ToString("o")
        install_dir = $InstallDir
        config_dir = $ConfigDir
    }

    Invoke-Step "Recording install metadata" {
        $payload | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $versionPath -Encoding UTF8
    }
}

function Remove-Install {
    $launcherPath = Join-Path (Get-ResolveLauncherDir) "SFX Roulette.py"
    Invoke-Step "Removing Resolve launcher" {
        if (Test-Path $launcherPath) {
            Remove-Item -LiteralPath $launcherPath -Force
        }
    }
    Invoke-Step "Removing installed app files" {
        if (Test-Path $InstallDir) {
            Remove-Item -LiteralPath $InstallDir -Recurse -Force
        }
    }
    Write-Step "User settings were kept in $ConfigDir"
}

if ($Uninstall) {
    Remove-Install
    exit 0
}

$sourceRoot = Get-LocalSourceRoot
if ($sourceRoot) {
    Write-Step "Using local source: $sourceRoot"
} else {
    $sourceRoot = Get-GitHubSourceRoot
}

if ($DryRun) {
    Write-Step "Dry run complete."
    exit 0
}

if (-not $sourceRoot) {
    throw "Could not locate or download SFX Roulette source."
}

Copy-AppFiles -SourceRoot $sourceRoot
Initialize-Config
Write-ResolveLauncher
Write-VersionInfo

Write-Host ""
Write-Step "Installed successfully."
Write-Step "Open Resolve, then choose Workspace > Scripts > Utility > SFX Roulette."
Write-Step "Run this installer again any time to update from https://github.com/$Repo"
