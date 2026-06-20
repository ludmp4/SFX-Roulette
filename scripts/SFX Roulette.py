import os
import sys
import traceback
from pathlib import Path


LOG_PATH = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Documents" / "SFX Roulette" / "sfx_roulette_launch.log"


def _candidate_package_roots():
    program_data = Path(os.environ.get("ProgramData", "C:/ProgramData"))
    app_data = Path(os.environ.get("APPDATA", ""))
    yield program_data / "Blackmagic Design" / "DaVinci Resolve" / "Fusion" / "Modules" / "Python" / "SFX Roulette"
    if str(app_data):
        yield app_data / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Fusion" / "Modules" / "Python" / "SFX Roulette"
    yield Path.cwd()


def main():
    try:
        for package_root in _candidate_package_roots():
            src_dir = package_root / "src"
            if src_dir.is_dir():
                sys.path.insert(0, str(src_dir))
                break

        resolve = bmd.scriptapp("Resolve")  # type: ignore[name-defined]
        if resolve is None:
            raise RuntimeError("DaVinci Resolve scripting is unavailable.")

        from sfx_roulette.resolve_ui import show_ui

        show_ui(resolve, bmd)  # type: ignore[name-defined]
    except Exception as exc:
        try:
            LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            LOG_PATH.write_text(
                "SFX Roulette failed to start.\n\n" + "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
                encoding="utf-8",
            )
        except Exception:
            pass
        print("SFX Roulette failed to start. See:", LOG_PATH)


if __name__ == "__main__":
    main()
