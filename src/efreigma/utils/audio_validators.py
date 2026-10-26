"""Bounded RIFF/WAVE validation, with offsets to preserve the original file."""

import struct
from typing import NamedTuple

from efreigma.exceptions import InvalidAudioError
from efreigma.utils.validators import MAX_FILE_BYTES


class WavInfo(NamedTuple):
    channels: int
    sample_width: int
    sample_rate: int
    frames: int
    data_offset: int
    data_size: int


def load_wav(audio_bytes: bytes) -> WavInfo:
    """Accept little-endian RIFF WAV, integer PCM, mono/stereo, 8–32 bits.

    Strictly validate chunk boundaries, padding, frame alignment and format
    parameters before exposing sample offsets. No sample conversion is done.
    """
    if not isinstance(audio_bytes, bytes) or not audio_bytes:
        raise InvalidAudioError("Le fichier audio est vide ou invalide.")
    if len(audio_bytes) > MAX_FILE_BYTES:
        raise InvalidAudioError("Le fichier audio dépasse la limite de 20 Mio.")
    if len(audio_bytes) < 12 or audio_bytes[:4] != b"RIFF" or audio_bytes[8:12] != b"WAVE":
        raise InvalidAudioError("Importez un véritable fichier WAV PCM non compressé.")
    if struct.unpack_from("<I", audio_bytes, 4)[0] + 8 != len(audio_bytes):
        raise InvalidAudioError("Le fichier WAV est tronqué ou sa taille est incohérente.")
    fmt = None
    data = None
    position = 12
    while position < len(audio_bytes):
        if position + 8 > len(audio_bytes):
            raise InvalidAudioError("Le fichier WAV contient un bloc tronqué.")
        chunk_id, size = struct.unpack_from("<4sI", audio_bytes, position)
        start = position + 8
        end = start + size
        padded_end = end + (size % 2)
        # Some WAV writers omit padding for the final odd-sized data chunk.
        if chunk_id == b"data" and end == len(audio_bytes):
            padded_end = end
        if padded_end > len(audio_bytes):
            raise InvalidAudioError("Le fichier WAV contient un bloc tronqué.")
        if chunk_id == b"fmt ":
            if fmt is not None or size < 16:
                raise InvalidAudioError("Le format du fichier WAV est invalide.")
            fmt = struct.unpack_from("<HHIIHH", audio_bytes, start)
        elif chunk_id == b"data":
            if fmt is None:
                raise InvalidAudioError("Le bloc fmt doit précéder les échantillons audio.")
            if data is not None:
                raise InvalidAudioError("Les WAV contenant plusieurs blocs audio ne sont pas pris en charge.")
            data = (start, size)
        position = padded_end
    if fmt is None or data is None:
        raise InvalidAudioError("Le fichier WAV doit contenir des blocs fmt et data.")
    encoding, channels, rate, byte_rate, alignment, bits = fmt
    if encoding != 1:
        raise InvalidAudioError("Seul le WAV PCM entier est pris en charge (pas de compression ni de flottants).")
    if channels not in (1, 2) or bits not in (8, 16, 24, 32):
        raise InvalidAudioError("Utilisez un WAV mono ou stéréo en PCM 8, 16, 24 ou 32 bits.")
    width = bits // 8
    if not 1 <= rate <= 192_000 or alignment != channels * width or byte_rate != rate * alignment:
        raise InvalidAudioError("Les paramètres audio du WAV sont incohérents ou non pris en charge.")
    offset, size = data
    if size == 0 or size % alignment:
        raise InvalidAudioError("Les échantillons audio sont vides ou tronqués.")
    return WavInfo(channels, width, rate, size // alignment, offset, size)
