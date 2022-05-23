import streamlit as st
from pages.matchup import MatchupPage

PAGES = {
    "Matchups": MatchupPage
}

st.set_page_config(layout="wide")
st.sidebar.title('Navigation')
page = st.sidebar.radio("Pages", list(PAGES.keys()))
PAGES[page].run()
