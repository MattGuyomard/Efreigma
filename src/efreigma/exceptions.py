"""Public, user-readable errors. Never include secret payloads in errors."""


class EfreigmaError(ValueError):
    """Base class for expected validation and extraction failures."""


class InvalidImageError(EfreigmaError):
    """The input is not a supported, bounded PNG image."""


class InvalidAudioError(EfreigmaError):
    """The input is not a supported, bounded PCM WAV file."""


class InvalidVideoError(EfreigmaError):
    """The video cannot be decoded or exceeds the supported limits."""


class InvalidMessageError(EfreigmaError):
    """The text cannot be embedded in the carrier."""


class InvalidPayloadError(EfreigmaError):
    """The carrier does not contain a valid supported Efreigma payload."""
