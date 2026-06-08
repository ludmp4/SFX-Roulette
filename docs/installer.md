# Installer And Updates

SFX Roulette is connected to:

```text
https://github.com/ludmp4/SFX-Roulette
```

## User Install

Download the repository ZIP from GitHub, extract it, and double-click:

```text
Install SFX Roulette.bat
```

Or run the one-line PowerShell installer:

```powershell
irm https://raw.githubusercontent.com/ludmp4/SFX-Roulette/main/scripts/install_windows.ps1 | iex
```

This command downloads the latest `main` branch archive from GitHub, installs the app into `%LOCALAPPDATA%\SFX Roulette`, writes the DaVinci Resolve launcher, and creates an example settings file.

The installer does not install Python. That is intentional: installation only needs PowerShell, and the plugin itself runs inside DaVinci Resolve Studio's scripting environment. Installing a separate system Python would make the setup more invasive without helping normal Resolve usage.

## User Update

Run the same command again:

```text
Install SFX Roulette.bat
```

Or:

```powershell
irm https://raw.githubusercontent.com/ludmp4/SFX-Roulette/main/scripts/install_windows.ps1 | iex
```

The installer replaces app files and preserves:

```text
%USERPROFILE%\Documents\SFX Roulette\sfx_roulette_config.json
```

The installer stores the installed commit in:

```text
%LOCALAPPDATA%\SFX Roulette\install.json
```

On later runs it compares that commit with the newest GitHub commit and prints one of:

```text
SFX Roulette | Updated SFX Roulette: oldsha -> newsha
SFX Roulette | What's new: Short commit summary
```

```text
SFX Roulette | Already on the newest version (newsha).
```

## Developer Install

From a local clone:

```powershell
.\install.ps1
```

The local install path uses the checked-out source instead of downloading from GitHub.

You can also double-click `Install SFX Roulette.bat`.

## Custom Branch

```powershell
.\install.ps1 -Branch develop
```

From GitHub:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/ludmp4/SFX-Roulette/main/scripts/install_windows.ps1))) -Branch develop
```

## Uninstall

```powershell
.\install.ps1 -Uninstall
```

Or run from Command Prompt:

```bat
"Install SFX Roulette.bat" -Uninstall
```

From GitHub:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/ludmp4/SFX-Roulette/main/scripts/install_windows.ps1))) -Uninstall
```

The uninstall flow removes installed app files and the Resolve script launcher. User settings are intentionally left in Documents.
