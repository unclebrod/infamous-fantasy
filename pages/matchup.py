import streamlit as st
import pandas as pd
from helpers import json_from_espn_api
from page import Page
from typing import Optional, List


class MatchupPage(Page):
    def __init__(self):
        super().__init__()

        self.matchup_json: Optional[List[dict]] = None
        self.team_json: Optional[List[dict]] = None

    def run(self):
        st.title("Matchups")
        season = st.selectbox(label="Season", options=self.seasons, index=len(self.seasons)-1)
        self.matchup_json = json_from_espn_api("mMatchup", seasonId=season)
        self.team_json = json_from_espn_api("mTeam", seasonId=season)
        matchup_df = self.build_matchup_df()

    def build_matchup_df(self) -> pd.DataFrame:
        matchup_data = [
            [
                game.get('matchupPeriodId'),
                game.get('home').get('teamId'),
                game.get('home').get('totalPoints'),
                game.get('away').get('teamId'),
                game.get('away').get('totalPoints')
            ] for game in self.matchup_json[0]['schedule']
        ]
        matchup_df = pd.DataFrame(data=matchup_data, columns=['Week', 'HomeTeamId', 'Points', 'AwayTeamId', 'Points'])
        matchup_df['isPlayoff'] = matchup_df['Week'] >= self.playoff_week
        members_data = [
            [
                member.get('id'),
                member.get('firstName'),
                member.get('lastName')
            ] for member in self.team_json[0].get('members')
        ]
        members_df = pd.DataFrame(data=members_data, columns=['OwnerKey', 'FirstName', 'LastName'])
        teams_data = [
            [
                team.get('id'),
                team.get('primaryOwner')
            ] for team in self.team_json[0].get('teams')
        ]
        teams_df = pd.DataFrame(data=teams_data, columns=['TeamId', 'OwnerKey'])
        id_df = members_df.merge(right=teams_df, how='left', on='OwnerKey')
        df = matchup_df.merge(
            right=id_df, left_on='HomeTeamId', right_on='TeamId'
        ).merge(right=id_df, left_on='AwayTeamId', right_on='TeamId')
        return df
