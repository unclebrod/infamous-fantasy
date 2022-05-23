import streamlit as st
from espn_api import ESPNFantasyAPI
from typing import List


@st.experimental_memo
def json_from_espn_api(view: str, **kwargs) -> List[dict]:
    """Wrapper to load cached json data from ESPN's fantasy API"""
    espn = ESPNFantasyAPI()
    espn_json = espn.get(view=view, **kwargs)
    return espn_json
