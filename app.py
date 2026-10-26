"""Streamlit entry point: shared classroom shell and explicit URL routes."""

import streamlit as st

from efreigma.ui.layout import render_footer, render_header


def open_home() -> None:
    """Redirect the root URL to the explicit /home page."""
    st.switch_page("views/home.py")


st.set_page_config(page_title="Efreigma · La classe des secrets", page_icon="✏️", layout="centered")
page = st.navigation([
    st.Page(open_home, title="Bienvenue", default=True),
    st.Page("views/home.py", title="Efreigma · La classe", url_path="home"),
    st.Page("views/image.py", title="Efreigma · Atelier image", url_path="image"),
    st.Page("views/audio.py", title="Efreigma · Atelier audio", url_path="audio"),
    st.Page("views/video.py", title="Efreigma · Atelier vidéo", url_path="video"),
], position="hidden")
if st.session_state.get("_workshop_page") != page.url_path:
    for result_key in ("hidden_png", "hidden_wav", "extracted_message", "extracted_audio_message",
                       "hidden_mkv", "extracted_video_message", "video_hide_info", "video_extract_info",
                       "video_hide_preview", "video_extract_preview", "video_result_preview"):
        st.session_state.pop(result_key, None)
st.session_state["_workshop_page"] = page.url_path
render_header()
page.run()
render_footer(page.url_path)
