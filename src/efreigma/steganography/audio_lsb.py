"""WAV PCM LSB steganography: one bit per interleaved channel sample."""

from efreigma.exceptions import InvalidMessageError, InvalidPayloadError
from efreigma.steganography.payload import HEADER_SIZE, make_packet, read_message
from efreigma.utils.audio_validators import WavInfo, load_wav
from efreigma.utils.validators import encode_message


def _capacity(info: WavInfo) -> int:
    return max(0, info.data_size // info.sample_width // 8 - HEADER_SIZE)


def get_audio_capacity(audio_bytes: bytes) -> int:
    """Return the maximum UTF-8 payload bytes after the 41-byte EFR1 header."""
    return _capacity(load_wav(audio_bytes))


def hide_audio_message(audio_bytes: bytes, message: str) -> bytes:
    """Return a WAV with one LSB changed per sample; preserve all other bytes.

    Rate, channel count, bit depth, frame count, chunks and metadata stay intact.
    The message is concealed, without encryption or authentication.
    """
    info = load_wav(audio_bytes)
    payload = encode_message(message)
    capacity = _capacity(info)
    if len(payload) > capacity:
        raise InvalidMessageError(
            f"Le message occupe {len(payload)} octets UTF-8 ; capacité : {capacity} octets."
        )
    output = bytearray(audio_bytes)
    position = info.data_offset
    for value in make_packet(payload):
        for shift in range(7, -1, -1):
            output[position] = (output[position] & 0xFE) | ((value >> shift) & 1)
            position += info.sample_width
    return bytes(output)


def extract_audio_message(audio_bytes: bytes) -> str:
    """Extract and validate EFR1 text from the WAV alone, without session state."""
    info = load_wav(audio_bytes)
    if info.data_size // info.sample_width < HEADER_SIZE * 8:
        raise InvalidPayloadError("L’audio est trop court pour contenir un en-tête Efreigma.")
    channels = (audio_bytes[position] for position in range(
        info.data_offset, info.data_offset + info.data_size, info.sample_width
    ))
    return read_message(channels, _capacity(info))
