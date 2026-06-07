class SFXRouletteError(RuntimeError):
    """Base class for user-facing SFX Roulette errors."""


class ResolveUnavailableError(SFXRouletteError):
    pass


class ProjectUnavailableError(SFXRouletteError):
    pass


class TimelineUnavailableError(SFXRouletteError):
    pass


class BinUnavailableError(SFXRouletteError):
    pass


class ClipUnavailableError(SFXRouletteError):
    pass


class TrackUnavailableError(SFXRouletteError):
    pass


class InsertError(SFXRouletteError):
    pass
