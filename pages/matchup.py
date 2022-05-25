import streamlit as st
import pandas as pd
from helpers import json_from_espn_api
from pages.page import Page
from typing import Optional, List
import plotly.express as px
import numpy as np
import plotly.graph_objects as go


class MatchupPage(Page):
    def __init__(self):
        super().__init__()

        self.matchup_json: Optional[List[dict]] = None
        self.team_json: Optional[List[dict]] = None
        self.matchup_df: Optional[pd.DataFrame] = None
        self.long_matchup_df: Optional[pd.DataFrame] = None

    def run(self):
        st.title("Matchups")
        season = st.selectbox(label="Season:", options=self.seasons, index=len(self.seasons)-1)
        self.matchup_json = json_from_espn_api(view="mMatchup", seasonId=season)
        self.team_json = json_from_espn_api(view="mTeam", seasonId=season)
        self.build_matchup_df()
        self.build_long_matchup_df()
        st.subheader('League Trends')
        self.plot_margin_boxplot()
        st.subheader('Team Comparisons')
        team_values = self.long_matchup_df['Team'].unique()
        teams = st.multiselect(
            label="Teams:", options=team_values, default='Average'
        )
        self.plot_margin_lineplot(teams=teams)
        st.subheader('Single Team Drilldown')
        team = st.selectbox(label="Team:", options=[x for x in team_values if x != 'Average'])
        self.plot_luck_scatter(team=team)

    def build_matchup_df(self) -> None:
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
        matchup_df['Type'] = np.where(matchup_df['Week'] >= self.playoff_week, 'Playoff', 'Regular')
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

    def build_long_matchup_df(self) -> None:
        home_df = self.matchup_df[
            ['Week', 'HomeTeam', 'HomeMargin', 'HomePoints', 'Type']
        ].rename(
            columns={'HomeTeam': 'Team', 'HomePoints': 'Points', 'HomeMargin': 'Margin'}
        )
        away_df = self.matchup_df[
            ['Week', 'AwayTeam', 'AwayMargin', 'AwayPoints', 'Type']
        ].rename(
            columns={'AwayTeam': 'Team', 'AwayPoints': 'Points', 'AwayMargin': 'Margin'}
        )
        df = pd.concat([home_df, away_df], axis=0, ignore_index=True)
        avg_df = df.groupby('Week', as_index=False).mean()
        avg_df['Team'] = 'Average'
        avg_df['Type'] = np.where(avg_df['Week'] >= self.playoff_week, 'Playoff', 'Regular')
        df = pd.concat([df, avg_df], axis=0, ignore_index=True)
        self.long_matchup_df = df

    def plot_margin_boxplot(self) -> None:
        fig = px.box(self.long_matchup_df, x='Team', y='Margin', color='Type')
        fig.update_layout(title_text="Scoring Margin Quantiles", title_x=0.5)
        fig.update_xaxes(categoryorder="total ascending")
        st.plotly_chart(fig, use_container_width=True)
        fig2 = px.box(self.long_matchup_df, x='Team', y='Points', color='Type')
        fig2.update_layout(title_text="Points Quantiles", title_x=0.5)
        fig2.update_xaxes(categoryorder="total ascending")
        st.plotly_chart(fig2, use_container_width=True)

    def plot_margin_lineplot(self, teams) -> None:
        df = self.long_matchup_df[self.long_matchup_df['Team'].isin(teams)].sort_values('Week')
        fig1 = px.line(df, x='Week', y='Margin', color='Team', markers=True)
        fig1.update_layout(title_text="Scoring Margins over Time", title_x=0.5)
        fig2 = px.line(df, x='Week', y='Points', color='Team', markers=True)
        fig2.update_layout(title_text="Total Points over Time", title_x=0.5)
        st.plotly_chart(fig1, use_container_width=True)
        st.plotly_chart(fig2, use_container_width=True)

    def plot_luck_scatter(self, team) -> None:
        avg_df = self.matchup_df[['Week', 'HomePoints', 'AwayPoints']].melt(
            id_vars=['Week'], value_name='Points'
        ).groupby('Week', as_index=False).mean()
        df = self.matchup_df[(self.matchup_df['HomeTeam'] == team) | (self.matchup_df['AwayTeam'] == team)]
        idx = df['AwayTeam'] == team
        df.loc[idx, ['HomeTeam', 'HomePoints', 'AwayTeam', 'AwayPoints']] = df.loc[
            idx, ['AwayTeam', 'AwayPoints', 'HomeTeam', 'HomePoints']
        ].values
        df = df.merge(right=avg_df, on='Week')
        df['PointsFor'] = df['HomePoints'] - df['Points']
        df['PointsAgainst'] = df['AwayPoints'] - df['Points']
        df['Win'] = np.where(df['HomePoints'] > df['AwayPoints'], 'Win', 'Loss')
        fig = px.scatter(
            df, x='PointsFor', y='PointsAgainst', color='Type', symbol='Win', symbol_map={'Win': 'circle', 'Loss': 'x'}
        )
        fig.update_traces(marker={'size': 15, 'line': {'width': 2, 'color': 'DarkSlateGrey'}})
        fig.add_shape(
            type='line', x0=0, y0=0, x1=1, y1=1, yref='paper', xref='paper', line={'dash': 'dash'},
        )
        ax_max = df[['PointsFor', 'PointsAgainst']].abs().max().max() + 5
        fig.add_trace(
            go.Scatter(
                x=[0, ax_max, ax_max, -ax_max, 0, 0],
                y=[0, 0, ax_max, -ax_max, -ax_max, 0],
                fill='toself', fillcolor='azure', line={'color': 'azure', 'width': 0},
                showlegend=False, hoverinfo='skip'
            ),
        )
        fig.add_trace(
            go.Scatter(
                x=[0, -ax_max, -ax_max, ax_max, 0, 0],
                y=[0, 0, -ax_max, ax_max, ax_max, 0],
                fill='toself', fillcolor='mistyrose', line={'color': 'mistyrose', 'width': 0},
                showlegend=False, hoverinfo='skip'
            )
        )
        fig.data = fig.data[::-1]
        # TODO: Figure out annotations
        fig.update_annotations(
            {'font': {'color': 'black', 'size': 100}, 'x': 0.25, 'y': 0.75, 'xref': 'paper', 'yref': 'paper'}
        )
        fig.update_xaxes(
            range=[-ax_max, ax_max], showgrid=False, zeroline=True, zerolinewidth=3, zerolinecolor='black'
        )
        fig.update_yaxes(
            range=[-ax_max, ax_max], showgrid=False, zeroline=True, zerolinewidth=3, zerolinecolor='black'
        )
        st.plotly_chart(fig, use_container_width=True)
