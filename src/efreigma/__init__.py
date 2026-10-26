"""Public Efreigma API for PNG and PCM WAV, independent of Streamlit."""

from efreigma.exceptions import EfreigmaError, InvalidImageError, InvalidMessageError, InvalidPayloadError
from efreigma.steganography.image_lsb import extract_message, get_capacity, hide_message
from efreigma.exceptions import InvalidAudioError
from efreigma.steganography.audio_lsb import extract_audio_message, get_audio_capacity, hide_audio_message
from efreigma.exceptions import InvalidVideoError
from efreigma.steganography.video_lsb import extract_video_message, get_video_capacity, hide_video_message

__all__ = [
    "hide_message", "extract_message", "get_capacity", "EfreigmaError",
    "InvalidImageError", "InvalidMessageError", "InvalidPayloadError",
    "hide_audio_message", "extract_audio_message", "get_audio_capacity", "InvalidAudioError",
    "hide_video_message", "extract_video_message", "get_video_capacity", "InvalidVideoError",
]
