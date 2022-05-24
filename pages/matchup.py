import streamlit as st
import pandas as pd
from helpers import json_from_espn_api
from pages.page import Page
from typing import Optional, List
import plotly.express as px
import numpy as np


class MatchupPage(Page):
    def __init__(self):
        super().__init__()

        self.matchup_json: Optional[List[dict]] = None
        self.team_json: Optional[List[dict]] = None
        self.matchup_df: Optional[pd.DataFrame] = None
        self.long_matchup_df: Optional[pd.DataFrame] = None

    def run(self):
        st.title("Matchups")
        season = st.selectbox(label="Season", options=self.seasons, index=len(self.seasons)-1)
        self.matchup_json = json_from_espn_api(view="mMatchup", seasonId=season)
        self.team_json = json_from_espn_api(view="mTeam", seasonId=season)
        self.build_matchup_df()
        self.build_long_matchup_df()
        st.dataframe(self.matchup_df)
        self.plot_margin_boxplot()
        team = st.selectbox(label="Team", options=self.long_matchup_df['Team'].unique())
        self.plot_margin_lineplot(team=team)
        # self.plot_points_lineplot(team=team)

    def build_matchup_df(self):
        matchup_data = [
            [
                game.get('matchupPeriodId'),
                game.get('home').get('teamId') if 'home' in game else None,
                game.get('home').get('totalPoints') if 'home' in game else None,
                game.get('away').get('teamId') if 'away' in game else None,
                game.get('away').get('totalPoints') if 'away' in game else None
            ] for game in self.matchup_json[0]['schedule']
        ]
        matchup_df = pd.DataFrame(
            data=matchup_data, columns=['Week', 'HomeTeamId', 'HomePoints', 'AwayTeamId', 'AwayPoints']
        )
        matchup_df['Type'] = np.where(matchup_df['Week'] >= self.playoff_week, 'Regular', 'Playoff')
        teams_data = [
            [
                team.get('id'),  # integer id
                team.get('location'),  # first part of nickname
                team.get('nickname')  # second part of nickname
            ] for team in self.team_json[0].get('teams')
        ]
        teams_df = pd.DataFrame(data=teams_data, columns=['TeamId', 'Location', 'Nickname'])
        df = matchup_df.merge(
            right=teams_df, left_on='HomeTeamId', right_on='TeamId', how='left'
        ).merge(
            right=teams_df, left_on='AwayTeamId', right_on='TeamId', how='left', suffixes=('Home', 'Away')
        )
        df['HomeTeam'] = df['LocationHome'] + ' ' + df['NicknameHome']
        df['AwayTeam'] = df['LocationAway'] + ' ' + df['NicknameAway']
        df['HomeMargin'] = df['HomePoints'] - df['AwayPoints']
        df['AwayMargin'] = -1 * df['HomeMargin']
        self.matchup_df = df[df['HomeMargin'].notna()]

    def build_long_matchup_df(self):
        df = self.matchup_df[
            ['Week', 'HomeTeam', 'HomeMargin', 'HomePoints', 'Type']
        ].rename(
            columns={'HomeTeam': 'Team', 'HomePoints': 'Points', 'HomeMargin': 'Margin'}
        ).append(
            self.matchup_df[
                ['Week', 'AwayTeam', 'AwayMargin', 'AwayPoints', 'Type']
            ].rename(
                columns={'AwayTeam': 'Team', 'AwayPoints': 'Points', 'AwayMargin': 'Margin'}
            )
        )
        self.long_matchup_df = df

    def plot_margin_boxplot(self):
        fig = px.box(self.long_matchup_df, x='Team', y='Margin', color='Type')
        fig.update_layout(title_text="Scoring Margin Quantiles", title_x=0.5)
        fig.update_xaxes(categoryorder="total ascending")
        st.plotly_chart(fig, use_container_width=True)

    def plot_margin_lineplot(self, team):
        df = self.long_matchup_df[self.long_matchup_df['Team'] == team].sort_values('Week')
        fig = px.line(df, x='Week', y=['Margin', 'Points'], color='Team', markers=True)
        fig.update_layout(title_text="Scoring Margins over Time", title_x=0.5)
        st.plotly_chart(fig, use_container_width=True)
