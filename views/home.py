import streamlit as st

from efreigma.ui.layout import artwork, render_hero

render_hero("home")
left, middle, right = st.columns(3)
with left, st.container(border=True, key="home_image"):
    st.markdown('<div class="workshop-number">ATELIER Nº 01 · LES PIXELS</div>' + artwork("image"), unsafe_allow_html=True)
    st.subheader("Le coin des images")
    st.write("Un dessin, une photo, un PNG… Glisse ton texte dans les pixels ou retrouve un mot caché.")
    st.page_link("views/image.py", label="Ouvrir l’atelier image", icon="🎨")
with middle, st.container(border=True, key="home_audio"):
    st.markdown('<div class="workshop-number">ATELIER Nº 02 · LES SONS</div>' + artwork("audio"), unsafe_allow_html=True)
    st.subheader("Le coin des sons")
    st.write("Passe ton petit mot sur cassette ! Cache un texte dans un WAV ou récupère son secret.")
    st.page_link("views/audio.py", label="Ouvrir l’atelier audio", icon="🎵")
with right, st.container(border=True, key="home_video"):
    st.markdown('<div class="workshop-number">ATELIER Nº 03 · LES FILMS</div>' + artwork("video"), unsafe_allow_html=True)
    st.subheader("Le coin du cinéma")
    st.write("Un secret au casting ! Cache ton texte dans un petit film et récupère son MKV sans perte.")
    st.page_link("views/video.py", label="Ouvrir l’atelier vidéo", icon="🎬")
