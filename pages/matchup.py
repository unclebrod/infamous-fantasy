from typing import List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from helpers import json_from_espn_api
from pages.page import Page


class MatchupPage(Page):
    def __init__(self):
        super().__init__()

        self.matchup_json: Optional[List[dict]] = None
        self.team_json: Optional[List[dict]] = None
        self.matchup_df: Optional[pd.DataFrame] = None
        self.long_matchup_df: Optional[pd.DataFrame] = None

    def run(self):
        st.title("Matchups")
        season = st.selectbox(
            label="Season:", options=self.seasons, index=len(self.seasons) - 1
        )
        self.matchup_json = json_from_espn_api(view="mMatchup", seasonId=season)
        self.team_json = json_from_espn_api(view="mTeam", seasonId=season)
        self.build_matchup_df()
        self.build_long_matchup_df()
        st.header("League Trends")
        stat1 = st.radio("Statistic:", ["Points", "Margin"])
        self.plot_league_boxplot(stat=stat1)
        st.header("Team Comparisons")
        team_values = self.long_matchup_df["Team"].unique()
        teams = st.multiselect(label="Teams:", options=team_values, default="Average")
        stat2 = st.radio("Statistic: ", ["Points", "Margin"])
        self.plot_team_lineplot(teams=teams, stat=stat2)
        self.plot_team_barplot(teams=teams, stat=stat2)
        st.header("Single Team Drilldown")
        team = st.selectbox(
            label="Team:", options=[x for x in team_values if x != "Average"]
        )
        st.markdown(
            """
            #### Lucky Win? Unlucky Loss?
            
            * Each point is a game centered with respect to the league's average points scored that week.
            * A win could be considered __lucky__ if a player scored higher than a particularly high scoring opponent.
            * Alternatively, a poor scoring team could get __lucky__ and win by having an even lower scoring opponent.
            * It follows suit that __unlucky__ losses would be inverses of the above.
            * Points below the dashed line are wins; above, losses.
            """
        )
        self.plot_luck_scatter(team=team)

    def build_matchup_df(self) -> None:
        matchup_data = [
            [
                game.get("matchupPeriodId"),
                game.get("home").get("teamId") if "home" in game else None,
                game.get("home").get("totalPoints") if "home" in game else None,
                game.get("away").get("teamId") if "away" in game else None,
                game.get("away").get("totalPoints") if "away" in game else None,
            ]
            for game in self.matchup_json[0]["schedule"]
        ]
        matchup_df = pd.DataFrame(
            data=matchup_data,
            columns=["Week", "HomeTeamId", "HomePoints", "AwayTeamId", "AwayPoints"],
        )
        matchup_df["Type"] = np.where(
            matchup_df["Week"] >= self.playoff_week, "Playoff", "Regular"
        )
        teams_data = [
            [
                team.get("id"),  # integer id
                team.get("location"),  # first part of nickname
                team.get("nickname"),  # second part of nickname
            ]
            for team in self.team_json[0].get("teams")
        ]
        teams_df = pd.DataFrame(
            data=teams_data, columns=["TeamId", "Location", "Nickname"]
        )
        df = matchup_df.merge(
            right=teams_df, left_on="HomeTeamId", right_on="TeamId", how="left"
        ).merge(
            right=teams_df,
            left_on="AwayTeamId",
            right_on="TeamId",
            how="left",
            suffixes=("Home", "Away"),
        )
        df["HomeTeam"] = df["LocationHome"] + " " + df["NicknameHome"]
        df["AwayTeam"] = df["LocationAway"] + " " + df["NicknameAway"]
        df["HomeMargin"] = df["HomePoints"] - df["AwayPoints"]
        df["AwayMargin"] = -1 * df["HomeMargin"]
        self.matchup_df = df[df["HomeMargin"].notna()]

    def build_long_matchup_df(self) -> None:
        df_list = []
        for loc in ["Home", "Away"]:
            df = self.matchup_df[
                ["Week", f"{loc}Team", f"{loc}Margin", f"{loc}Points", "Type"]
            ].rename(
                columns={f"{loc}Team": "Team", f"{loc}Points": "Points", f"{loc}Margin": "Margin"}
            )
            df_list.append(df)
        df = pd.concat(df_list, axis=0, ignore_index=True)
        avg_df = df.groupby("Week", as_index=False).mean()
        avg_df["Team"] = "Average"
        avg_df["Type"] = np.where(
            avg_df["Week"] >= self.playoff_week, "Playoff", "Regular"
        )
        df = pd.concat([df, avg_df], axis=0, ignore_index=True)
        self.long_matchup_df = df

    def plot_league_boxplot(self, stat) -> None:
        fig = px.box(self.long_matchup_df, x="Team", y=stat, color="Type")
        fig.update_layout(title_text=f"Scoring {stat} Quantiles", title_x=0.5)
        fig.update_xaxes(categoryorder="total ascending")
        st.plotly_chart(fig, use_container_width=True)

    def plot_team_lineplot(self, teams, stat) -> None:
        df = self.long_matchup_df[self.long_matchup_df["Team"].isin(teams)].sort_values(
            "Week"
        )
        fig = px.line(df, x="Week", y=stat, color="Team", markers=True)
        fig.update_layout(
            title_text=f"Scoring {stat} over the Season",
            title_x=0.5,
            hovermode="x unified",
        )
        fig.update_yaxes(rangemode="tozero")
        st.plotly_chart(fig, use_container_width=True)

    def plot_team_barplot(self, teams, stat) -> None:
        df = (
            self.long_matchup_df[self.long_matchup_df["Team"].isin(teams)]
            .sort_values(stat)
            .reset_index(drop=True)
        )
        fig = px.bar(df, y=stat, color="Team", hover_data=["Type", "Week"])
        fig.update_layout(title_text=f"Scoring {stat} Distribution", title_x=0.5)
        fig.update_layout(xaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)

    def plot_luck_scatter(self, team) -> None:
        avg_df = (
            self.matchup_df[["Week", "HomePoints", "AwayPoints"]]
            .melt(id_vars=["Week"], value_name="Points")
            .groupby("Week", as_index=False)
            .mean()
        )
        df = self.matchup_df[
            (self.matchup_df["HomeTeam"] == team)
            | (self.matchup_df["AwayTeam"] == team)
        ]
        idx = df["AwayTeam"] == team  # swap columns to make Home for the team of choice
        df.loc[idx, ["HomeTeam", "HomePoints", "AwayTeam", "AwayPoints"]] = df.loc[
            idx, ["AwayTeam", "AwayPoints", "HomeTeam", "HomePoints"]
        ].values
        df = df.merge(right=avg_df, on="Week")
        df["PointsFor"] = df["HomePoints"] - df["Points"]
        df["PointsAgainst"] = df["AwayPoints"] - df["Points"]
        df["Win"] = np.where(df["HomePoints"] > df["AwayPoints"], "Win", "Loss")
        fig = px.scatter(
            df,
            x="PointsFor",
            y="PointsAgainst",
            color="Type",
            symbol="Win",
            symbol_map=dict(Win="circle", Loss="x"),
            hover_data=["AwayTeam", "Week"],
        )
        fig.update_traces(
            marker=dict(size=15, line=dict(width=2, color="DarkSlateGrey"))
        )
        fig.add_shape(
            type="line",
            x0=0,
            y0=0,
            x1=1,
            y1=1,
            yref="paper",
            xref="paper",
            line=dict(dash="dash"),
        )
        ax_max = df[["PointsFor", "PointsAgainst"]].abs().max().max() + 5
        fig.add_trace(
            go.Scatter(
                x=[0, ax_max, ax_max, -ax_max, 0, 0],
                y=[0, 0, ax_max, -ax_max, -ax_max, 0],
                fill="toself",
                fillcolor="azure",
                line=dict(color="azure", width=0),
                hoverinfo="skip",
                name="Lucky Win",
            ),
        )
        fig.add_trace(
            go.Scatter(
                x=[0, -ax_max, -ax_max, ax_max, 0, 0],
                y=[0, 0, -ax_max, ax_max, ax_max, 0],
                fill="toself",
                fillcolor="mistyrose",
                line=dict(color="mistyrose", width=0),
                hoverinfo="skip",
                name="Unlucky Loss",
            )
        )
        fig.data = fig.data[::-1]
        axes_kwargs = dict(
            range=[-ax_max, ax_max],
            showgrid=False,
            zeroline=True,
            zerolinewidth=3,
            zerolinecolor="black",
        )
        fig.update_xaxes(**axes_kwargs)
        fig.update_yaxes(**axes_kwargs)
        fig.update_layout(
            title_text="Weekly Scores, Centered at League Average", title_x=0.5
        )
        st.plotly_chart(fig, use_container_width=True)
