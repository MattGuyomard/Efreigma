from hashlib import sha256
from io import BytesIO
import os
from pathlib import Path
import struct
import subprocess
import sys
import wave

import pytest

from efreigma import (
    InvalidAudioError, InvalidMessageError, InvalidPayloadError,
    extract_audio_message, get_audio_capacity, hide_audio_message,
)
from efreigma.steganography.payload import HEADER, HEADER_SIZE, MAGIC, VERSION
from efreigma.utils import audio_validators
from efreigma.utils.audio_validators import load_wav


@pytest.mark.parametrize("channels", [1, 2])
@pytest.mark.parametrize("width", [1, 2, 3, 4])
@pytest.mark.parametrize("message", ["Hello!", "Été à Efrei 🔐\nمرحبا", " \t\n\x00 e\u0301"])
def test_audio_round_trip_preserves_samples_and_parameters(wav_factory, channels, width, message):
    source = wav_factory(channels, width)
    result = hide_audio_message(source, message)
    assert extract_audio_message(result) == message
    info = load_wav(source)
    assert len(source) == len(result)
    assert load_wav(result) == info
    used = (HEADER_SIZE + len(message.encode())) * 8
    for offset, (old, new) in enumerate(zip(source, result)):
        if info.data_offset <= offset < info.data_offset + used * width and (offset - info.data_offset) % width == 0:
            assert (old & 0xFE) == (new & 0xFE)
            assert abs(old - new) <= 1
        else:
            assert old == new
    with wave.open(BytesIO(source), "rb") as before, wave.open(BytesIO(result), "rb") as after:
        assert before.getparams() == after.getparams()
        old_samples, new_samples = before.readframes(info.frames), after.readframes(info.frames)
        for index in range(0, len(old_samples), width):
            old = int.from_bytes(old_samples[index:index + width], "little", signed=width > 1)
            new = int.from_bytes(new_samples[index:index + width], "little", signed=width > 1)
            assert abs(old - new) <= 1


@pytest.mark.parametrize("width", [1, 2, 3, 4])
def test_exact_capacity(wav_factory, width):
    source = wav_factory(2, width, frames=1000)
    assert get_audio_capacity(source) == 2 * 1000 // 8 - 41
    message = "a" * get_audio_capacity(source)
    assert extract_audio_message(hide_audio_message(source, message)) == message
    with pytest.raises(InvalidMessageError):
        hide_audio_message(source, message + "a")


@pytest.mark.parametrize("frames", [1, 327, 328, 335])
def test_short_audio(wav_factory, frames):
    source = wav_factory(frames=frames)
    assert get_audio_capacity(source) == 0
    with pytest.raises(InvalidMessageError):
        hide_audio_message(source, "a")
    with pytest.raises(InvalidPayloadError):
        extract_audio_message(source)


def test_utf8_capacity_and_empty_message(wav_factory):
    source = wav_factory(frames=360)  # 4 UTF-8 bytes
    assert extract_audio_message(hide_audio_message(source, "🔐")) == "🔐"
    for message in ("🔐a", "", None, "\ud800"):
        with pytest.raises(InvalidMessageError):
            hide_audio_message(source, message)


def test_missing_and_altered_message(wav_factory):
    source = wav_factory()
    with pytest.raises(InvalidPayloadError, match="signature"):
        extract_audio_message(source)
    result = bytearray(hide_audio_message(source, "secret"))
    info = load_wav(source)
    result[info.data_offset + HEADER_SIZE * 8 * info.sample_width] ^= 1
    with pytest.raises(InvalidPayloadError, match="SHA-256"):
        extract_audio_message(bytes(result))


@pytest.mark.parametrize("version,length,payload,match", [
    (2, 1, b"a", "version"), (VERSION, 0, b"a", "longueur"),
    (VERSION, 2**32 - 1, b"a", "longueur"), (VERSION, 1, b"\xff", "UTF-8"),
])
def test_bad_audio_packet(wav_factory, version, length, payload, match):
    source = bytearray(wav_factory())
    info = load_wav(bytes(source))
    packet = HEADER.pack(MAGIC, version, length, sha256(payload).digest()) + payload
    for index, bit in enumerate((value >> shift) & 1 for value in packet for shift in range(7, -1, -1)):
        offset = info.data_offset + index * info.sample_width
        source[offset] = (source[offset] & 0xFE) | bit
    with pytest.raises(InvalidPayloadError, match=match):
        extract_audio_message(bytes(source))


def test_chunks_and_odd_padding_preserved(wav_factory):
    source = wav_factory()
    metadata = b"JUNK" + struct.pack("<I", 3) + b"abc\x00"
    result = source[:36] + metadata + source[36:]
    result = result[:4] + struct.pack("<I", len(result) - 8) + result[8:]
    encoded = hide_audio_message(result, "metadata intacte")
    assert metadata in encoded
    assert extract_audio_message(encoded) == "metadata intacte"
    # Python's wave writer omits terminal padding for odd 8-bit data.
    assert extract_audio_message(hide_audio_message(wav_factory(width=1, frames=1001), "odd")) == "odd"


@pytest.mark.parametrize("data", [b"", None, b"ID3 mp3", b"RIFF\x00\x00\x00\x00WAVE"])
@pytest.mark.parametrize("operation", [get_audio_capacity, extract_audio_message, lambda data: hide_audio_message(data, "a")])
def test_invalid_audio_files(data, operation):
    with pytest.raises(InvalidAudioError):
        operation(data)


def test_truncated_and_inconsistent_files(wav_factory):
    source = wav_factory()
    for data in (source[:-1], source[:30], source + b"trailing"):
        with pytest.raises(InvalidAudioError):
            get_audio_capacity(data)
    # Update RIFF length but leave data length announcing missing samples.
    truncated = source[:-1]
    truncated = truncated[:4] + struct.pack("<I", len(truncated) - 8) + truncated[8:]
    with pytest.raises(InvalidAudioError):
        get_audio_capacity(truncated)


@pytest.mark.parametrize("offset,format,value", [
    (20, "<H", 3), (20, "<H", 0xFFFE), (22, "<H", 3),
    (24, "<I", 0), (24, "<I", 384000), (28, "<I", 1),
    (32, "<H", 8), (34, "<H", 12),
])
def test_unsupported_and_inconsistent_formats(wav_factory, offset, format, value):
    source = bytearray(wav_factory())
    struct.pack_into(format, source, offset, value)
    with pytest.raises(InvalidAudioError):
        get_audio_capacity(bytes(source))


def test_empty_audio_and_file_limit(wav_factory, monkeypatch):
    with pytest.raises(InvalidAudioError):
        get_audio_capacity(wav_factory(frames=0))
    monkeypatch.setattr(audio_validators, "MAX_FILE_BYTES", 100)
    with pytest.raises(InvalidAudioError, match="20 Mio"):
        get_audio_capacity(wav_factory())


def test_reopen_in_new_process_without_streamlit(wav_factory, tmp_path):
    path = tmp_path / "secret.wav"
    path.write_bytes(hide_audio_message(wav_factory(), "Audio persistant 🔐"))
    script = """
import sys
class BlockStreamlit:
    def find_spec(self, fullname, *args):
        if fullname.split('.')[0] == 'streamlit':
            raise AssertionError('Engine must not import Streamlit')
sys.meta_path.insert(0, BlockStreamlit())
from pathlib import Path
from efreigma import extract_audio_message
assert extract_audio_message(Path(sys.argv[1]).read_bytes()) == 'Audio persistant 🔐'
"""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    result = subprocess.run([sys.executable, "-c", script, str(path)], env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
