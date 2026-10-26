from fractions import Fraction
from io import BytesIO
import os
from pathlib import Path
import subprocess
import sys

import av
from PIL import Image
import pytest

from efreigma import (
    InvalidMessageError, InvalidPayloadError, InvalidVideoError,
    extract_video_message, get_video_capacity, hide_video_message,
)
from efreigma.steganography.video_lsb import get_video_info, get_video_preview
from efreigma.utils import video_validators


def make_video(size=(16, 12), count=6, rate=10, audio=False, mp4=False):
    output = BytesIO()
    with av.open(output, "w", format="mp4" if mp4 else "matroska") as container:
        video = container.add_stream("libx264" if mp4 else "ffv1", rate=rate)
        video.width, video.height = size
        video.pix_fmt = "yuv420p" if mp4 else "bgr0"
        video.time_base = Fraction(1, rate)
        soundtrack = container.add_stream("aac" if mp4 else "pcm_s16le", rate=8000) if audio else None
        if soundtrack:
            soundtrack.layout = "mono"
        for index in range(count):
            image = Image.new("RGB", size)
            image.putdata([((pixel * 13 + index * 3) % 256, (pixel * 7) % 256, (index * 19) % 256)
                           for pixel in range(size[0] * size[1])])
            frame = av.VideoFrame.from_image(image)
            frame.pts, frame.time_base = index, Fraction(1, rate)
            container.mux(video.encode(frame))
            if soundtrack:
                sound = av.AudioFrame(format="s16", layout="mono", samples=8000 // rate)
                sound.sample_rate = 8000
                sound.pts, sound.time_base = index * sound.samples, Fraction(1, 8000)
                sound.planes[0].update(bytes(sound.samples * 2))
                container.mux(soundtrack.encode(sound))
        container.mux(video.encode())
        if soundtrack:
            container.mux(soundtrack.encode())
    return output.getvalue()


@pytest.fixture
def video_factory():
    return make_video


def frame_data(data):
    with av.open(BytesIO(data)) as container:
        return [(frame.to_image().tobytes(), frame.width, frame.height, float(frame.pts * frame.time_base))
                for frame in container.decode(video=0)]


@pytest.mark.parametrize("message", ["Hello!", "Été à Efrei 🔐\nمرحبا", " \t\n\x00 e\u0301"])
def test_round_trip_and_preserved_rgb(message):
    source = make_video()
    encoded = hide_video_message(source, message)
    assert extract_video_message(encoded) == message
    before, after = frame_data(source), frame_data(encoded)
    assert len(before) == len(after) == 6
    for old, new in zip(before, after):
        assert old[1:3] == new[1:3]
        assert abs(old[3] - new[3]) < 0.002
        assert all(abs(a - b) <= 1 for a, b in zip(old[0], new[0]))
    with av.open(BytesIO(encoded)) as container:
        assert container.streams.video[0].codec_context.name == "ffv1"
        assert container.streams.video[0].codec_context.format.name == "bgr0"


def test_header_and_message_span_multiple_frames():
    source = make_video(size=(8, 8), count=8)
    assert get_video_capacity(source) == 8 * 8 * 8 * 3 // 8 - 41
    message = "a" * get_video_capacity(source)
    assert extract_video_message(hide_video_message(source, message)) == message
    with pytest.raises(InvalidMessageError):
        hide_video_message(source, message + "a")


@pytest.mark.parametrize("message", ["", None, "\ud800"])
def test_invalid_text(message):
    with pytest.raises(InvalidMessageError):
        hide_video_message(make_video(), message)


def test_mp4_input_and_browser_preview():
    source = make_video(size=(32, 24), mp4=True)
    encoded = hide_video_message(source, "Texte depuis MP4 🔐")
    assert extract_video_message(encoded) == "Texte depuis MP4 🔐"
    proxy = get_video_preview(encoded)
    with av.open(BytesIO(proxy)) as container:
        assert container.streams.video[0].codec_context.name == "h264"
        assert len(list(container.decode(video=0))) == 6
    with pytest.raises(InvalidPayloadError, match="MKV"):
        extract_video_message(proxy)


@pytest.mark.parametrize("mp4", [False, True])
def test_soundtrack_packet_bytes_preserved(mp4):
    source = make_video(audio=True, mp4=mp4)
    encoded = hide_video_message(source, "avec le son")
    def audio_packets(data):
        with av.open(BytesIO(data)) as container:
            stream = container.streams.audio[0]
            return [(bytes(packet), float(packet.pts * packet.time_base))
                    for packet in container.demux(stream) if packet.pts is not None]
    assert audio_packets(source) == audio_packets(encoded)
    assert [frame[3] for frame in frame_data(encoded)] == pytest.approx(
        [frame[3] for frame in frame_data(source)], abs=0.002
    )
    assert get_video_info(encoded).has_audio
    assert extract_video_message(encoded) == "avec le son"


def test_no_message():
    with pytest.raises(InvalidPayloadError, match="signature"):
        extract_video_message(make_video())


def altered_video(data, offset):
    output = BytesIO()
    with av.open(BytesIO(data)) as source, av.open(output, "w", format="matroska") as target:
        stream = target.add_stream("ffv1", rate=10)
        stream.width, stream.height, stream.pix_fmt = 16, 12, "bgr0"
        for index, frame in enumerate(source.decode(video=0)):
            image = frame.to_image()
            if index == 0:
                pixels = bytearray(image.tobytes())
                pixels[offset] ^= 1
                image.frombytes(bytes(pixels))
            modified = av.VideoFrame.from_image(image)
            modified.pts, modified.time_base = frame.pts, frame.time_base
            target.mux(stream.encode(modified))
        target.mux(stream.encode())
    return output.getvalue()


@pytest.mark.parametrize("offset,match", [(41 * 8, "SHA-256"), (4 * 8 + 6, "version"), (0, "signature")])
def test_altered_packet_detected(offset, match):
    encoded = hide_video_message(make_video(), "secret")
    with pytest.raises(InvalidPayloadError, match=match):
        extract_video_message(altered_video(encoded, offset))


def test_actual_lossless_output_limit(monkeypatch):
    source = make_video()
    monkeypatch.setattr(video_validators, "MAX_VIDEO_BYTES", len(source))
    with pytest.raises(InvalidVideoError):
        hide_video_message(source, "un résultat plus grand")


@pytest.mark.parametrize("data", [b"", None, b"not a video", b"\x1aE\xdf\xa3\x00"])
@pytest.mark.parametrize("operation", [get_video_capacity, extract_video_message, lambda data: hide_video_message(data, "test")])
def test_invalid_files(data, operation):
    with pytest.raises(InvalidVideoError):
        operation(data)


@pytest.mark.parametrize("limit,value", [("MAX_VIDEO_BYTES", 8), ("MAX_FRAME_PIXELS", 10), ("MAX_TOTAL_PIXELS", 200), ("MAX_FRAMES", 2), ("MAX_DURATION", 0.1)])
def test_limits_before_or_during_decode(monkeypatch, limit, value):
    source = make_video()
    monkeypatch.setattr(video_validators, limit, value)
    with pytest.raises(InvalidVideoError):
        get_video_capacity(source)


def test_bounded_output(monkeypatch):
    monkeypatch.setattr(video_validators, "MAX_VIDEO_BYTES", 8)
    output = video_validators.BoundedOutput()
    output.write(b"12345678")
    with pytest.raises(InvalidVideoError, match="résultat"):
        output.write(b"9")


def test_fresh_process_without_streamlit(tmp_path):
    path = tmp_path / "secret.mkv"
    path.write_bytes(hide_video_message(make_video(), "Vidéo persistante 🔐"))
    script = """
import sys
class BlockStreamlit:
    def find_spec(self, fullname, *args):
        if fullname.split('.')[0] == 'streamlit':
            raise AssertionError('Engine must not import Streamlit')
sys.meta_path.insert(0, BlockStreamlit())
from pathlib import Path
from efreigma import extract_video_message
assert extract_video_message(Path(sys.argv[1]).read_bytes()) == 'Vidéo persistante 🔐'
"""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    result = subprocess.run([sys.executable, "-c", script, str(path)], env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
