"""Sequential RGB LSB over video frames; lossless FFV1/Matroska output."""

from fractions import Fraction
from collections.abc import Iterator
from typing import NamedTuple

import av

from efreigma.exceptions import InvalidMessageError, InvalidPayloadError, InvalidVideoError
from efreigma.steganography.payload import HEADER_SIZE, make_packet, read_message
from efreigma.utils.validators import encode_message
from efreigma.utils.video_validators import BoundedOutput, FrameBudget, open_video


class VideoInfo(NamedTuple):
    width: int
    height: int
    frames: int
    frame_rate: Fraction
    duration: float
    has_audio: bool

    @property
    def capacity(self) -> int:
        return max(0, self.width * self.height * self.frames * 3 // 8 - HEADER_SIZE)


def get_video_info(video_bytes: bytes) -> VideoInfo:
    """Fully decode a bounded clip to count actual frames rather than trust metadata."""
    with open_video(video_bytes) as (container, stream):
        budget = FrameBudget(stream.width, stream.height, stream.average_rate or stream.guessed_rate)
        for frame in container.decode(stream):
            budget.check(frame)
        if budget.count == 0:
            raise InvalidVideoError("La vidéo ne contient aucune image lisible.")
        return VideoInfo(budget.width, budget.height, budget.count, budget.rate, budget.duration, bool(container.streams.audio))


def get_video_capacity(video_bytes: bytes) -> int:
    """Maximum UTF-8 bytes across all RGB frames after the 41-byte header."""
    return get_video_info(video_bytes).capacity


def hide_video_message(video_bytes: bytes, message: str) -> bytes:
    """Return FFV1 RGB MKV, preserving frames, timing and supported audio packets.

    The input is decoded to RGB8. Only its RGB LSBs are modified. The resulting
    pixels are encoded losslessly; do not convert this MKV to a lossy format.
    """
    payload = encode_message(message)
    info = get_video_info(video_bytes)
    if len(payload) > info.capacity:
        raise InvalidMessageError(f"Le message occupe {len(payload)} octets UTF-8 ; capacité : {info.capacity} octets.")
    packet = make_packet(payload)
    bit_index = 0
    output = BoundedOutput()
    with open_video(video_bytes) as (source, video), av.open(
        output, "w", format="matroska", options={"avoid_negative_ts": "disabled"}
    ) as target:
        encoded = target.add_stream("ffv1", rate=info.frame_rate)
        encoded.width, encoded.height = info.width, info.height
        encoded.pix_fmt = "bgr0"
        encoded.time_base = video.time_base
        encoded.codec_context.thread_count = 1
        encoded.options = {"level": "3", "slicecrc": "1"}
        audio = source.streams.audio[0] if source.streams.audio else None
        copied_audio = target.add_stream_from_template(audio) if audio else None
        budget = FrameBudget(info.width, info.height, info.frame_rate)
        for demuxed in source.demux():
            if demuxed.stream == video:
                for frame in demuxed.decode():
                    budget.check(frame)
                    image = frame.to_image()
                    pixels = bytearray(image.tobytes())
                    count = min(len(pixels), len(packet) * 8 - bit_index)
                    for index in range(count):
                        bit = (packet[bit_index // 8] >> (7 - bit_index % 8)) & 1
                        pixels[index] = (pixels[index] & 0xFE) | bit
                        bit_index += 1
                    image.frombytes(bytes(pixels))
                    modified = av.VideoFrame.from_image(image)
                    modified.pts, modified.time_base = frame.pts, frame.time_base
                    for coded in encoded.encode(modified):
                        target.mux(coded)
            elif audio is not None and demuxed.stream == audio and demuxed.dts is not None:
                demuxed.stream = copied_audio
                target.mux(demuxed)
        for coded in encoded.encode():
            target.mux(coded)
    if bit_index != len(packet) * 8:
        raise InvalidVideoError("La vidéo ne contient pas assez d’images pour terminer l’insertion.")
    return output.getvalue()


def extract_video_message(video_bytes: bytes) -> str:
    """Recover EFR1 from a lossless FFV1 RGB MKV, independent of the session."""
    info = get_video_info(video_bytes)
    if info.width * info.height * info.frames * 3 < HEADER_SIZE * 8:
        raise InvalidPayloadError("La vidéo est trop petite pour contenir un en-tête Efreigma.")
    with open_video(video_bytes) as (container, stream):
        if stream.codec_context.name != "ffv1" or stream.codec_context.format.name not in ("bgr0", "bgra", "rgb24"):
            raise InvalidPayloadError("Réimportez le MKV FFV1 téléchargé depuis Efreigma pour extraire le message.")

        def channels() -> Iterator[int]:
            for frame in container.decode(stream):
                yield from frame.to_image().tobytes()

        return read_message(channels(), info.capacity)


def get_video_preview(video_bytes: bytes) -> bytes:
    """Return a silent H.264 MP4 proxy for browsers; never use it for extraction."""
    info = get_video_info(video_bytes)
    output = BoundedOutput()
    with open_video(video_bytes) as (source, video), av.open(output, "w", format="mp4") as target:
        stream = target.add_stream("libx264", rate=info.frame_rate)
        # H.264 yuv420p requires even dimensions. Resize only this display proxy.
        stream.width = max(2, info.width // 2 * 2)
        stream.height = max(2, info.height // 2 * 2)
        stream.pix_fmt = "yuv420p"
        stream.time_base = video.time_base
        stream.options = {"preset": "ultrafast", "crf": "26"}
        for frame in source.decode(video):
            proxy = frame.reformat(width=stream.width, height=stream.height, format="yuv420p")
            proxy.pts, proxy.time_base = frame.pts, frame.time_base
            for packet in stream.encode(proxy):
                target.mux(packet)
        for packet in stream.encode():
            target.mux(packet)
    return output.getvalue()
