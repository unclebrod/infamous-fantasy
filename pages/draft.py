from typing import *

import pandas as pd
import streamlit as st

from helpers import json_from_espn_api
from pages.page import Page


class DraftPage(Page):
    def __init__(self):
        super().__init__()
        self.player_json: Optional[List[dict]] = None
        self.draft_json: Optional[List[dict]] = None
        self.team_json: Optional[List[dict]] = None

    def run(self):
        st.title("Draft")
        season = st.selectbox(
            label="Season:", options=self.seasons, index=len(self.seasons) - 1
        )
        self.player_json = json_from_espn_api(view="kona_player_info", seasonId=season)
        player_df = pd.json_normalize(self.player_json[0]['players'])
        self.draft_json = json_from_espn_api(view="mDraftDetail", seasonId=season)
        draft_df = pd.json_normalize(self.draft_json[0]['draftDetail']['picks'])
        self.team_json = json_from_espn_api(view="mTeam", seasonId=season)
        team_df = pd.json_normalize(self.team_json[0]['teams'])
        df = draft_df.merge(
            player_df, how='left', left_on='playerId', right_on='id'
        ).merge(team_df, how='left', left_on='teamId', right_on='id')
        st.dataframe(df)
