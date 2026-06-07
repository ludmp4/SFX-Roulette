# Installer And Updates

SFX Roulette is connected to:

```text
https://github.com/ludmp4/SFX-Roulette
```

## User Install

```powershell
irm https://raw.githubusercontent.com/ludmp4/SFX-Roulette/main/scripts/install_windows.ps1 | iex
```

This command downloads the latest `main` branch archive from GitHub, installs the app into `%LOCALAPPDATA%\SFX Roulette`, writes the DaVinci Resolve launcher, and creates an example settings file.

## User Update

Run the same command again:

```powershell
irm https://raw.githubusercontent.com/ludmp4/SFX-Roulette/main/scripts/install_windows.ps1 | iex
```

The installer replaces app files and preserves:

```text
%USERPROFILE%\Documents\SFX Roulette\sfx_roulette_config.json
```

## Developer Install

From a local clone:

```powershell
.\install.ps1
```

The local install path uses the checked-out source instead of downloading from GitHub.

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

From GitHub:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/ludmp4/SFX-Roulette/main/scripts/install_windows.ps1))) -Uninstall
```

The uninstall flow removes installed app files and the Resolve script launcher. User settings are intentionally left in Documents.
