import streamlit as st

from PIL import Image

icon = Image.open('images/KeeperDAO_Logo_Icon_White.png')
st.set_page_config(
    page_title="ROOK Tokenomics",
    page_icon=icon
)

with open('markdown/Home.md') as homepage:
    st.markdown(homepage.read())
