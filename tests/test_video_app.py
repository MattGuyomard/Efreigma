from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from efreigma import extract_video_message
from test_video_lsb import make_video

APP = Path(__file__).resolve().parents[1] / "app.py"


def video_app():
    return AppTest.from_file(str(APP)).run().switch_page("views/video.py").run()


def test_video_starts_disabled():
    app = video_app()
    assert not app.exception
    assert app.button(key="video_hide_button").disabled
    assert app.button(key="video_extract_button").disabled


def test_video_round_trip_new_session_and_preview():
    source = make_video(mp4=True, size=(32, 24))
    message = "Un secret dans le film 🔐\nÉté à Efrei."
    with patch("streamlit.file_uploader", side_effect=lambda label, **kwargs:
               BytesIO(source) if kwargs["key"] == "video_hide_upload" else None):
        app = video_app()
        app.button(key="video_hide_preview_button").click().run()
        assert not app.exception
        assert app.get("video")
        app.text_area(key="video_secret_text").input(message).run()
        app.button(key="video_hide_button").click().run()
        assert not app.exception
        result = app.session_state["hidden_mkv"]
        assert extract_video_message(result) == message
        assert app.get("download_button")
        app.text_area(key="video_secret_text").input("nouveau").run()
        assert "hidden_mkv" not in app.session_state
        app.switch_page("views/home.py").run()
        assert "video_hide_preview" not in app.session_state
    with patch("streamlit.file_uploader", side_effect=lambda label, **kwargs:
               BytesIO(result) if kwargs["key"] == "video_extract_upload" else None):
        fresh = video_app()
        fresh.button(key="video_extract_button").click().run()
        assert not fresh.exception
        assert fresh.code[0].value == message


def test_invalid_video_uploads():
    with patch("streamlit.file_uploader", return_value=BytesIO(b"broken video")):
        app = video_app()
        assert not app.exception
        assert len(app.error) == 2
        assert app.button(key="video_hide_button").disabled
        assert app.button(key="video_extract_button").disabled


def test_invalid_extraction_clears_old_message():
    from efreigma import hide_video_message
    current = hide_video_message(make_video(), "ancien message")
    with patch("streamlit.file_uploader", side_effect=lambda label, **kwargs:
               BytesIO(current) if kwargs["key"] == "video_extract_upload" else None):
        app = video_app()
        app.button(key="video_extract_button").click().run()
        assert app.code[0].value == "ancien message"
        current = make_video()
        app.button(key="video_extract_button").click().run()
        assert not app.exception
        assert app.error
        assert not app.code
