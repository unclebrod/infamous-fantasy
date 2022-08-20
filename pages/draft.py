from typing import *

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.linear_model import LinearRegression

from enumerations import POSITIONS, TEAMS
from helpers import json_from_espn_api
from pages.page import Page


def get_season_avg(row, year: int):
    avg = None
    for stat_dict in row["player.stats"]:
        if stat_dict.get("id") == f"00{str(year)}":
            avg = stat_dict.get(f"appliedAverage")
    return avg


def get_unique_vals(vals, add_all: bool = True):
    all_list = ["all"] if add_all else []
    return vals.unique().tolist() + all_list


class DraftPage(Page):
    def __init__(self):
        super().__init__()
        self.season: Optional[int] = None
        self.player_json: Optional[List[dict]] = None
        self.draft_json: Optional[List[dict]] = None
        self.team_json: Optional[List[dict]] = None
        self.df: Optional[pd.DataFrame] = None
        self.positions: Optional[List[str]] = None
        self.teams: Optional[List[str]] = None
        self.drafters: Optional[List[str]] = None
        self.keepers: Optional[List[bool]] = None
        self.season_avg: Optional[Tuple[float]] = None
        self.bid_amount: Optional[Tuple[int]] = None

    def run(self):
        st.title("Draft")
        self.season = st.selectbox(
            label="Season:", options=self.seasons, index=len(self.seasons) - 1
        )
        self.player_json = json_from_espn_api(
            view="kona_player_info", seasonId=self.season
        )
        player_df = pd.json_normalize(self.player_json[0]["players"])
        self.draft_json = json_from_espn_api(view="mDraftDetail", seasonId=self.season)
        draft_df = pd.json_normalize(self.draft_json[0]["draftDetail"]["picks"])
        self.team_json = json_from_espn_api(view="mTeam", seasonId=self.season)
        team_df = pd.json_normalize(self.team_json[0]["teams"])
        self.df = draft_df.merge(
            player_df, how="left", left_on="playerId", right_on="id"
        ).merge(team_df, how="left", left_on="teamId", right_on="id")
        self._add_columns()
        st.dataframe(self.df)
        st.dataframe(player_df)
        st.dataframe(draft_df)
        st.dataframe(team_df)
        st.subheader("Filter Options")
        st.caption(
            "Use the menus below to change which points appear on the plot. "
            "By default, all drafted players are selected."
        )
        filter_col, plot_col = st.columns([1, 3])
        with filter_col:
            positions_vals = get_unique_vals(self.df["Position"])
            self.positions = st.multiselect(
                "Positions:",
                options=positions_vals,
                default=["all"],
                help="Player position.",
            )
            self.positions = (
                positions_vals if "all" in self.positions else self.positions
            )
            teams_vals = get_unique_vals(self.df["Team"])
            self.teams = st.multiselect(
                "Teams:",
                options=teams_vals,
                default=["all"],
                help="NFL team (at end of season).",
            )
            self.teams = teams_vals if "all" in self.teams else self.teams
            drafters_vals = get_unique_vals(self.df["Drafter"])
            self.drafters = st.multiselect(
                "Drafters:",
                options=drafters_vals,
                default=["all"],
                help="League member who originally drafted the player.",
            )
            self.drafters = drafters_vals if "all" in self.drafters else self.drafters
            self.keepers = st.multiselect(
                "Keepers:",
                options=[True, False],
                default=[True, False],
                help="Indicates if player was kept from previous season.",
            )
            self.season_avg = st.slider(
                "Season Averages", value=(0.0, float(self.df["seasonAverage"].max()))
            )
            self.bid_amount = st.slider(
                "Bid Amount", value=(0, int(self.df["bidAmount"].max()))
            )
        self._filter_df()
        with plot_col:
            self._plot_value_scatter()

    def _add_columns(self):
        self.df["seasonAverage"] = self.df.apply(
            lambda x: get_season_avg(x, self.season), axis=1
        )
        self.df["Drafter"] = self.df["location"] + " " + self.df["nickname"]
        self.df["Position"] = self.df["player.defaultPositionId"].map(POSITIONS)
        self.df["Team"] = self.df["player.proTeamId"].map(TEAMS)

    def _filter_df(self):
        return self.df.loc[
            (self.df["Position"].isin(self.positions))
            & (self.df["Team"].isin(self.teams))
            & (self.df["Drafter"].isin(self.drafters))
            & (self.df["keeper"].isin(self.keepers))
            & (self.df["seasonAverage"].between(*self.season_avg))
            & (self.df["bidAmount"].between(*self.bid_amount))
        ]

    def _plot_value_scatter(self):
        lr = LinearRegression(fit_intercept=False)
        lr.fit(self.df[["bidAmount"]], self.df[["seasonAverage"]])
        reg_x = np.linspace(-5, self.df["bidAmount"].max() + 5).reshape(-1, 1)
        reg_y = lr.predict(reg_x)
        plot_df = self._filter_df()
        reg_df = pd.DataFrame({"x": reg_x.reshape(-1), "y": reg_y.reshape(-1)})
        fig1 = px.scatter(
            plot_df,
            x="bidAmount",
            y="seasonAverage",
            hover_data=["player.fullName", "Drafter"],
            color="keeper",
            color_discrete_map={True: "red", False: "blue"},
        )
        fig2 = px.line(reg_df, x="x", y="y")
        fig2.update_traces(
            line=dict(color="black", dash="dash"), hoverinfo="skip", hovertemplate=None
        )
        fig = go.Figure(data=fig2.data + fig1.data)
        fig.update_xaxes(
            dict(
                range=[self.df["bidAmount"].min() - 2, self.df["bidAmount"].max() + 2],
                zeroline=True,
                zerolinewidth=1,
                zerolinecolor="black",
            )
        )
        fig.update_yaxes(
            dict(
                range=[
                    self.df["seasonAverage"].min() - 2,
                    self.df["seasonAverage"].max() + 2,
                ],
                zeroline=True,
                zerolinewidth=1,
                zerolinecolor="black",
            )
        )
        fig.update_traces(marker=dict(size=8, line=dict(width=1, color="black")))
        fig.update_layout(
            title_text="Season Averages vs. Auction Amount",
            title_x=0.5,
            xaxis_title="Bid Amount",
            yaxis_title="Season Scoring Average",
        )
        st.plotly_chart(fig, use_container_width=True)
