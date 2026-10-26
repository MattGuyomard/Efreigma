"""Local byte-stream video validation and bounded frame decoding."""

from contextlib import contextmanager
from dataclasses import dataclass
from io import BytesIO
from fractions import Fraction
from collections.abc import Iterator

import av

from efreigma.exceptions import EfreigmaError, InvalidVideoError

MAX_VIDEO_BYTES = 20 * 1024 * 1024
MAX_FRAME_PIXELS = 2_000_000
MAX_TOTAL_PIXELS = 30_000_000
MAX_FRAMES = 600
MAX_DURATION = 30
AUDIO_CODECS = {"aac", "mp3", "opus", "vorbis", "flac", "pcm_s16le", "pcm_s24le", "pcm_s32le", "pcm_f32le"}


@contextmanager
def open_video(data: bytes) -> Iterator[tuple[av.container.InputContainer, av.video.stream.VideoStream]]:
    if not isinstance(data, bytes) or not data:
        raise InvalidVideoError("Le fichier vidéo est vide ou invalide.")
    if len(data) > MAX_VIDEO_BYTES:
        raise InvalidVideoError("La vidéo dépasse la limite de 20 Mio.")
    try:
        with av.open(BytesIO(data), mode="r") as container:
            if not {"mov", "mp4", "matroska", "webm", "avi"}.intersection(container.format.name.split(",")):
                raise InvalidVideoError("Importez une vidéo MP4, MOV, AVI, WebM ou MKV.")
            if len(container.streams.video) != 1 or len(container.streams.audio) > 1:
                raise InvalidVideoError("Utilisez une vidéo avec une seule piste vidéo et au plus une piste audio.")
            if any(stream.type not in ("video", "audio") for stream in container.streams):
                raise InvalidVideoError("Les sous-titres, pièces jointes et pistes supplémentaires ne sont pas pris en charge.")
            stream = container.streams.video[0]
            if stream.width <= 0 or stream.height <= 0 or stream.width * stream.height > MAX_FRAME_PIXELS:
                raise InvalidVideoError("Chaque image vidéo doit contenir au plus 2 millions de pixels.")
            rate = stream.average_rate or stream.guessed_rate
            if rate is None or not Fraction(1, 10) <= rate <= 60:
                raise InvalidVideoError("La cadence vidéo doit être connue et comprise entre 0,1 et 60 images/s.")
            if container.duration is not None and container.duration / av.time_base > MAX_DURATION + 0.1:
                raise InvalidVideoError("La vidéo dépasse la durée maximale de 30 secondes.")
            if container.streams.audio and container.streams.audio[0].codec_context.name not in AUDIO_CODECS:
                raise InvalidVideoError("La piste audio de cette vidéo ne peut pas être conservée dans le MKV.")
            stream.codec_context.thread_count = 1
            yield container, stream
    except EfreigmaError:
        raise
    except (av.FFmpegError, OSError, ValueError, OverflowError) as error:
        raise InvalidVideoError("La vidéo est corrompue, illisible ou son codec n’est pas pris en charge.") from error


@dataclass
class FrameBudget:
    width: int
    height: int
    rate: Fraction
    count: int = 0
    pixels: int = 0
    first_time: Fraction | None = None
    last_time: Fraction | None = None

    def check(self, frame: av.VideoFrame) -> None:
        if (frame.width, frame.height) != (self.width, self.height):
            raise InvalidVideoError("Les vidéos dont la résolution change ne sont pas prises en charge.")
        self.count += 1
        self.pixels += frame.width * frame.height
        if self.count > MAX_FRAMES or self.pixels > MAX_TOTAL_PIXELS:
            raise InvalidVideoError("La vidéo dépasse 600 images ou 30 millions de pixels au total.")
        if frame.pts is None or frame.time_base is None:
            raise InvalidVideoError("Les horodatages de la vidéo sont absents.")
        time = frame.pts * frame.time_base
        if self.last_time is not None and time <= self.last_time:
            raise InvalidVideoError("Les horodatages de la vidéo sont incohérents.")
        if self.first_time is None:
            self.first_time = time
        self.last_time = time
        if float(time - self.first_time + 1 / self.rate) > MAX_DURATION + 0.1:
            raise InvalidVideoError("La vidéo dépasse la durée maximale de 30 secondes.")

    @property
    def duration(self) -> float:
        if self.first_time is None or self.last_time is None:
            return 0.0
        return float(self.last_time - self.first_time + 1 / self.rate)


class BoundedOutput(BytesIO):
    """Bound FFmpeg output even when the lossless result expands considerably."""

    def write(self, data: bytes) -> int:
        if self.tell() + len(data) > MAX_VIDEO_BYTES:
            raise InvalidVideoError("Le résultat dépasse 20 Mio. Utilisez une vidéo plus courte ou plus petite.")
        return super().write(data)
