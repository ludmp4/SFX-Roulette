param(
    [string]$Repo = "ludmp4/SFX-Roulette",
    [string]$Branch = "main",
    [string]$InstallDir = "$env:LOCALAPPDATA\SFX Roulette",
    [string]$ConfigDir = "$HOME\Documents\SFX Roulette",
    [string]$LauncherDir = "",
    [switch]$PreferGitHub,
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

function Get-ShortSha {
    param([string]$Sha)
    if (-not $Sha) {
        return "unknown"
    }
    if ($Sha.Length -le 7) {
        return $Sha
    }
    return $Sha.Substring(0, 7)
}

function Get-InstalledInfo {
    $versionPath = Join-Path $InstallDir "install.json"
    if (-not (Test-Path $versionPath)) {
        return $null
    }
    try {
        return Get-Content -LiteralPath $versionPath -Raw | ConvertFrom-Json
    } catch {
        return $null
    }
}

function New-VersionInfo {
    param(
        [string]$Source = "unknown",
        [string]$Sha = "",
        [string]$Message = "",
        [string]$Url = ""
    )
    return [pscustomobject]@{
        source = $Source
        sha = $Sha
        message = $Message
        url = $Url
        changes = @()
    }
}

function Get-GitCommandPath {
    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($git) {
        return $git.Source
    }

    $githubDesktopGit = Join-Path $env:LOCALAPPDATA "GitHubDesktop\app-3.5.10\resources\app\git\mingw64\bin\git.exe"
    if (Test-Path $githubDesktopGit) {
        return $githubDesktopGit
    }

    $githubDesktopRoot = Join-Path $env:LOCALAPPDATA "GitHubDesktop"
    if (Test-Path $githubDesktopRoot) {
        $candidate = Get-ChildItem -LiteralPath $githubDesktopRoot -Recurse -Filter git.exe -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -like "*\resources\app\git\mingw64\bin\git.exe" } |
            Select-Object -First 1
        if ($candidate) {
            return $candidate.FullName
        }
    }

    return ""
}

function Get-LocalSourceInfo {
    param([string]$SourceRoot)

    $git = Get-GitCommandPath
    if (-not $git -or -not (Test-Path (Join-Path $SourceRoot ".git"))) {
        return New-VersionInfo -Source "local" -Message "Local source install"
    }

    try {
        $sha = (& $git -c safe.directory="$SourceRoot" -C $SourceRoot rev-parse HEAD 2>$null).Trim()
        $message = (& $git -c safe.directory="$SourceRoot" -C $SourceRoot log -1 --pretty=%s 2>$null).Trim()
        return New-VersionInfo -Source "local-git" -Sha $sha -Message $message
    } catch {
        return New-VersionInfo -Source "local" -Message "Local source install"
    }
}

function Get-GitHubLatestInfo {
    $commitApiUrl = "https://api.github.com/repos/$Repo/commits/$Branch"
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $commit = Invoke-RestMethod -Uri $commitApiUrl -UseBasicParsing
        return New-VersionInfo `
            -Source "github" `
            -Sha ([string]$commit.sha) `
            -Message ([string](([string]$commit.commit.message).Split("`n")[0])) `
            -Url ([string]$commit.html_url)
    } catch {
        Write-Step "GitHub API version check unavailable: $($_.Exception.Message)"
    }

    $git = Get-GitCommandPath
    if ($git) {
        try {
            $remoteUrl = "https://github.com/$Repo.git"
            $line = (& $git ls-remote $remoteUrl "refs/heads/$Branch" 2>$null | Select-Object -First 1)
            if ($line) {
                $sha = ([string]$line).Split("`t")[0].Trim()
                if ($sha) {
                    return New-VersionInfo -Source "github-git" -Sha $sha -Message "Latest GitHub build"
                }
            }
        } catch {
            Write-Step "Git remote version check unavailable: $($_.Exception.Message)"
        }
    }

    Write-Step "Could not determine the latest GitHub commit before install."
    return New-VersionInfo -Source "github"
}

function Add-GitHubChangeSummary {
    param(
        [object]$InstalledInfo,
        [object]$LatestInfo
    )

    if (-not $InstalledInfo -or -not $InstalledInfo.commit_sha -or -not $LatestInfo.sha) {
        return $LatestInfo
    }

    $compareUrl = "https://api.github.com/repos/$Repo/compare/$($InstalledInfo.commit_sha)...$($LatestInfo.sha)"
    try {
        $compare = Invoke-RestMethod -Uri $compareUrl -UseBasicParsing
        $LatestInfo.changes = @(
            $compare.commits |
                Select-Object -Last 3 |
                ForEach-Object { [string](([string]$_.commit.message).Split("`n")[0]) }
        )
    } catch {
        $LatestInfo.changes = @()
    }
    return $LatestInfo
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
    param([object]$LatestInfo)

    $versionPath = Join-Path $InstallDir "install.json"
    $payload = [ordered]@{
        repo = $Repo
        branch = $Branch
        commit_sha = $LatestInfo.sha
        commit_message = $LatestInfo.message
        commit_url = $LatestInfo.url
        source = $LatestInfo.source
        installed_at = (Get-Date).ToUniversalTime().ToString("o")
        install_dir = $InstallDir
        config_dir = $ConfigDir
    }

    Invoke-Step "Recording install metadata" {
        $payload | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $versionPath -Encoding UTF8
    }
}

function Write-UpdateResult {
    param(
        [object]$InstalledInfo,
        [object]$LatestInfo
    )

    $oldSha = ""
    if ($InstalledInfo -and $InstalledInfo.commit_sha) {
        $oldSha = [string]$InstalledInfo.commit_sha
    }
    $newSha = [string]$LatestInfo.sha

    Write-Host ""
    if ($oldSha -and $newSha -and $oldSha -eq $newSha) {
        Write-Step "Already on the newest version ($(Get-ShortSha $newSha))."
        if ($LatestInfo.message) {
            Write-Step "Current update: $($LatestInfo.message)"
        }
        return
    }

    if ($oldSha -and $newSha) {
        Write-Step "Updated SFX Roulette: $(Get-ShortSha $oldSha) -> $(Get-ShortSha $newSha)"
    } elseif ($newSha) {
        Write-Step "Installed SFX Roulette version $(Get-ShortSha $newSha)."
    } else {
        Write-Step "Installed SFX Roulette."
    }

    if ($LatestInfo.changes -and $LatestInfo.changes.Count -gt 0) {
        Write-Step "What's new:"
        foreach ($change in $LatestInfo.changes) {
            Write-Host "  - $change"
        }
    } elseif ($LatestInfo.message) {
        Write-Step "What's new: $($LatestInfo.message)"
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

$installedInfo = Get-InstalledInfo
$localFallbackSourceRoot = Get-LocalSourceRoot
$sourceRoot = $null
if (-not $PreferGitHub) {
    $sourceRoot = $localFallbackSourceRoot
}
if ($sourceRoot) {
    Write-Step "Using local source: $sourceRoot"
    $latestInfo = Get-LocalSourceInfo -SourceRoot $sourceRoot
} else {
    if ($PreferGitHub) {
        Write-Step "Checking GitHub for the newest version."
    }
    $latestInfo = Get-GitHubLatestInfo
    $latestInfo = Add-GitHubChangeSummary -InstalledInfo $installedInfo -LatestInfo $latestInfo
    if ($latestInfo.sha) {
        Write-Step "Newest GitHub version: $(Get-ShortSha $latestInfo.sha)"
    }
    try {
        $sourceRoot = Get-GitHubSourceRoot
    } catch {
        Write-Step "GitHub download unavailable: $($_.Exception.Message)"
        if ($localFallbackSourceRoot) {
            Write-Step "Installing bundled files from this extracted folder instead."
            $sourceRoot = $localFallbackSourceRoot
            if (-not $latestInfo.sha) {
                $latestInfo = Get-LocalSourceInfo -SourceRoot $sourceRoot
            }
        } else {
            throw
        }
    }
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
Write-VersionInfo -LatestInfo $latestInfo

Write-UpdateResult -InstalledInfo $installedInfo -LatestInfo $latestInfo
Write-Step "Open Resolve, then choose Workspace > Scripts > Utility > SFX Roulette."
Write-Step "Run this installer again any time to update from https://github.com/$Repo"
