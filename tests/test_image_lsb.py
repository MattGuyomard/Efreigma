from hashlib import sha256
from io import BytesIO
import os
from pathlib import Path
import subprocess
import sys

from PIL import Image
import pytest

from efreigma import InvalidMessageError, InvalidPayloadError, extract_message, get_capacity, hide_message
from efreigma.steganography.image_lsb import HEADER, HEADER_SIZE, MAGIC, VERSION


def overwrite_packet(carrier: bytes, packet: bytes) -> bytes:
    """Independent fixture encoder to exercise malformed packet handling."""
    with Image.open(BytesIO(carrier)) as image:
        values = [image.getpixel((x, y)) for y in range(image.height) for x in range(image.width)]
        bits = [(value >> shift) & 1 for value in packet for shift in range(7, -1, -1)]
        for offset, bit in enumerate(bits):
            pixel, channel = divmod(offset, 3)
            channels = list(values[pixel])
            channels[channel] = (channels[channel] & 254) | bit
            values[pixel] = tuple(channels)
        image.putdata(values)
        output = BytesIO()
        image.save(output, "PNG")
        return output.getvalue()


@pytest.mark.parametrize("mode", ["RGB", "RGBA"])
@pytest.mark.parametrize("message", ["Hello, world!", "Été à Efrei — déjà prêt ?", "🔐🦊🚀", " \n\t", "nul\x00\nfin", "e\u0301 et é"])
def test_round_trip(png_factory, mode, message):
    original = png_factory(mode)
    assert extract_message(hide_message(original, message)) == message


@pytest.mark.parametrize("mode", ["RGB", "RGBA"])
def test_pixels_dimensions_alpha_and_serialization(png_factory, mode):
    source = png_factory(mode, (35, 27))
    result = hide_message(source, "Message de démonstration 🔐")
    with Image.open(BytesIO(source)) as before, Image.open(BytesIO(result)) as after:
        assert after.format == "PNG"
        assert before.size == after.size
        assert before.mode == after.mode
        for y in range(before.height):
            for x in range(before.width):
                old, new = before.getpixel((x, y)), after.getpixel((x, y))
                assert all(abs(a - b) <= 1 for a, b in zip(old[:3], new[:3]))
                if mode == "RGBA":
                    assert old[3] == new[3]
        serialized = BytesIO()
        after.save(serialized, "PNG")
    assert extract_message(serialized.getvalue()) == "Message de démonstration 🔐"


@pytest.mark.parametrize("size", [(1, 1), (10, 10), (11, 10), (12, 10), (32, 32)])
def test_capacity(png_factory, size):
    source = png_factory(size=size)
    expected = max(0, size[0] * size[1] * 3 // 8 - 41)
    assert get_capacity(source) == expected
    if expected:
        assert extract_message(hide_message(source, "a" * expected)) == "a" * expected
    with pytest.raises(InvalidMessageError):
        hide_message(source, "a" * (expected + 1))


def test_capacity_counts_utf8_bytes(png_factory):
    source = png_factory(size=(12, 10))  # 4 payload bytes
    assert extract_message(hide_message(source, "🔐")) == "🔐"
    with pytest.raises(InvalidMessageError):
        hide_message(source, "🔐a")


@pytest.mark.parametrize("message", ["", None, 123, "\ud800"])
def test_invalid_message(png_factory, message):
    with pytest.raises(InvalidMessageError):
        hide_message(png_factory(), message)


@pytest.mark.parametrize("size", [(1, 1), (32, 32)])
def test_no_message(png_factory, size):
    with pytest.raises(InvalidPayloadError):
        extract_message(png_factory(size=size))


@pytest.mark.parametrize("magic, version, length, match", [
    (b"NOPE", VERSION, 1, "signature"),
    (MAGIC, 2, 1, "version"),
    (MAGIC, VERSION, 0, "longueur"),
    (MAGIC, VERSION, 2**32 - 1, "longueur"),
])
def test_bad_header(png_factory, magic, version, length, match):
    packet = HEADER.pack(magic, version, length, sha256(b"a").digest()) + b"a"
    with pytest.raises(InvalidPayloadError, match=match):
        extract_message(overwrite_packet(png_factory(), packet))


def test_detect_altered_payload(png_factory):
    packet = HEADER.pack(MAGIC, VERSION, 5, sha256(b"hello").digest()) + b"jello"
    with pytest.raises(InvalidPayloadError, match="SHA-256"):
        extract_message(overwrite_packet(png_factory(), packet))


def test_reject_utf8_even_with_valid_digest(png_factory):
    packet = HEADER.pack(MAGIC, VERSION, 1, sha256(b"\xff").digest()) + b"\xff"
    with pytest.raises(InvalidPayloadError, match="UTF-8"):
        extract_message(overwrite_packet(png_factory(), packet))


def test_explicit_header_and_bit_order(png_factory):
    result = hide_message(png_factory(), "é")
    with Image.open(BytesIO(result)) as image:
        channels = [value for y in range(image.height) for x in range(image.width)
                    for value in image.getpixel((x, y))[:3]]
    decoded = bytes(sum((channels[i * 8 + bit] & 1) << (7 - bit) for bit in range(8))
                    for i in range(HEADER_SIZE + 2))
    assert decoded == HEADER.pack(b"EFR1", 1, 2, sha256("é".encode()).digest()) + "é".encode()


def test_fresh_process_without_streamlit(png_factory, tmp_path):
    carrier = tmp_path / "carrier.png"
    carrier.write_bytes(hide_message(png_factory("RGBA"), "Persistant 🔐"))
    script = """
import sys
class BlockStreamlit:
    def find_spec(self, fullname, *args):
        if fullname.split('.')[0] == 'streamlit':
            raise AssertionError('Engine must not import Streamlit')
sys.meta_path.insert(0, BlockStreamlit())
from pathlib import Path
from efreigma import extract_message, get_capacity, hide_message
data = Path(sys.argv[1]).read_bytes()
assert extract_message(data) == 'Persistant 🔐'
assert get_capacity(data) > 0
assert extract_message(hide_message(data, 'fresh process')) == 'fresh process'
"""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    result = subprocess.run([sys.executable, "-c", script, str(carrier)],
                            env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
