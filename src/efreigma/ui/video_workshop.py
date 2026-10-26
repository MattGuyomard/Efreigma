"""Video workshop with a distinct lossless download and browser preview."""

from hashlib import sha256

import streamlit as st

from efreigma import EfreigmaError, extract_video_message, hide_video_message
from efreigma.steganography.video_lsb import VideoInfo, get_video_info, get_video_preview


def clear_video_result() -> None:
    for key in ("hidden_mkv", "video_result_preview"):
        st.session_state.pop(key, None)


def clear_video_source() -> None:
    clear_video_result()
    for key in ("video_hide_info", "video_hide_preview"):
        st.session_state.pop(key, None)


def clear_video_extraction() -> None:
    for key in ("extracted_video_message", "video_extract_info", "video_extract_preview"):
        st.session_state.pop(key, None)


def scan(data: bytes, key: str) -> VideoInfo:
    fingerprint = sha256(data).digest()
    stored = st.session_state.get(key)
    if stored is None or stored[0] != fingerprint:
        with st.spinner("Lecture et vérification du clip…"):
            stored = (fingerprint, get_video_info(data))
        st.session_state[key] = stored
    return stored[1]


def preview(data: bytes, key: str) -> None:
    if st.button("Lire l’aperçu vidéo (muet)", key=key + "_button"):
        st.session_state.pop(key, None)
        try:
            with st.spinner("Préparation de l’aperçu…"):
                st.session_state[key] = get_video_preview(data)
        except EfreigmaError as error:
            st.error(str(error))
    if key in st.session_state:
        st.video(st.session_state[key], format="video/mp4")
        st.caption("Aperçu MP4 muet pour la lecture. Le message se récupère uniquement dans le MKV téléchargé.")


def render_video_workshop() -> None:
    hide_tab, extract_tab = st.tabs(["Cacher un message", "Extraire un message"])
    with hide_tab:
        st.subheader("01. Ton petit mot fait son cinéma ✉️")
        st.caption("Importe un clip, écris ton texte, puis télécharge le MKV qui garde le secret.")
        source = st.file_uploader("Vidéo originale", type=["mp4", "mov", "avi", "webm", "mkv"],
                                  key="video_hide_upload", on_change=clear_video_source)
        message = st.text_area("Message secret", placeholder="Écris ton message ici…", height=150,
                               key="video_secret_text", on_change=clear_video_result)
        data = None
        capacity = 0
        valid_source = False
        if source is not None:
            data = source.getvalue()
            try:
                info = scan(data, "video_hide_info")
                capacity = info.capacity
                valid_source = True
                st.caption(f"{info.width} × {info.height} · {info.frames} images · {float(info.frame_rate):.2f} images/s · {info.duration:.2f} s · {'avec son' if info.has_audio else 'sans son'}")
                preview(data, "video_hide_preview")
            except EfreigmaError as error:
                st.error(str(error))
        try:
            used = len(message.encode("utf-8"))
            valid_text = True
        except UnicodeEncodeError:
            used, valid_text = 0, False
            st.error("Le message contient des caractères Unicode invalides.")
        if valid_source:
            left, right = st.columns(2)
            left.metric("Espace disponible", f"{capacity:,} octets")
            right.metric("Taille du message", f"{used:,} octets")
            st.progress(min(used / capacity, 1.0) if capacity else 0.0)
            if capacity == 0:
                st.warning("Le clip est trop petit pour contenir un message Efreigma.")
            elif used > capacity:
                st.error("Le message dépasse la capacité du clip. Réduisez le texte ou choisissez un autre support.")
        if st.button("Cacher le message", key="video_hide_button", type="primary",
                     disabled=not (valid_source and valid_text and 0 < used <= capacity)):
            clear_video_result()
            try:
                with st.spinner("Insertion du message et encodage sans perte…"):
                    st.session_state.hidden_mkv = hide_video_message(data, message)
            except EfreigmaError as error:
                st.error(str(error))
        if "hidden_mkv" in st.session_state:
            st.success("Message dissimulé. Téléchargez le MKV pour conserver le secret.")
            st.download_button("Télécharger le MKV", data=st.session_state.hidden_mkv, file_name="efreigma-secret.mkv",
                               mime="video/x-matroska", key="video_download_carrier")
            preview(st.session_state.hidden_mkv, "video_result_preview")
    with extract_tab:
        st.subheader("02. Retrouve le secret après le générique 🔎")
        st.caption("Réimporte le MKV sans perte téléchargé depuis Efreigma.")
        carrier = st.file_uploader("MKV contenant un message", type=["mkv"], key="video_extract_upload",
                                   on_change=clear_video_extraction)
        data = None
        valid_carrier = False
        if carrier is not None:
            data = carrier.getvalue()
            try:
                scan(data, "video_extract_info")
                valid_carrier = True
                preview(data, "video_extract_preview")
            except EfreigmaError as error:
                st.error(str(error))
        if st.button("Extraire", key="video_extract_button", type="primary", disabled=not valid_carrier):
            st.session_state.pop("extracted_video_message", None)
            try:
                with st.spinner("Lecture des pixels et vérification du message…"):
                    st.session_state.extracted_video_message = extract_video_message(data)
            except EfreigmaError as error:
                st.error(str(error))
        if "extracted_video_message" in st.session_state:
            st.success("Message extrait et intégrité vérifiée.")
            st.caption("Utilisez l’icône de copie du bloc ci-dessous pour copier le message.")
            st.code(st.session_state.extracted_video_message, language=None, wrap_lines=True)
            st.download_button("Télécharger le texte", data=st.session_state.extracted_video_message.encode("utf-8"),
                               file_name="efreigma-message.txt", mime="text/plain; charset=utf-8", key="video_download_text")
    with st.expander("📎 Le petit rappel du prof"):
        st.caption("20 Mio en entrée et sortie · 30 s · 600 images · 2 millions de pixels/image · 30 millions de pixels au total · 60 images/s maximum")
        st.write("La sortie MKV FFV1 préserve les pixels RGB et la piste audio prise en charge. Le navigateur lit un aperçu MP4 muet séparé.")
        st.info("Le LSB ne chiffre pas le message. SHA-256 vérifie l’intégrité. Conversion MP4, montage, redimensionnement ou recompression peuvent effacer le secret.")
