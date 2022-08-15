import os
from typing import List
import json
import requests
from dotenv import load_dotenv

load_dotenv()

VIEWS = [
    "kona_game_state",
    "kona_league_communication",
    "kona_player_info",
    "mBoxscore",
    "mDraftDetail",
    "mLiveScoring",
    "mMatchup"
    "mMatchupScore",
    "mNav",
    "mPendingTransactions",
    "mPositionalRatings",
    "mPositionalRatingsStats",
    "mProTeamSchedules_wl",
    "mRoster",
    "mSchedule",
    "mSettings",
    "mStatus",
    "mTeam",
    "mTransactions2",
    "modular",
    "players_wl",
]

API_PARAMS = [
    "seasonId",
    "matchupPeriod",
    "scoringPeriod",
]


class ESPNFantasyAPI:
    """Class for pulling data from the ESPN fantasy API"""

    def __init__(self):
        self.cookies = {
            "swid": f"{os.environ.get('SWID')}",
            "espn_s2": f"{os.environ.get('ESPN_S2')}",
        }
        league_id = os.environ.get("LEAGUE_ID")
        self.url = (
            f"https://fantasy.espn.com/apis/v3/games/ffl/leagueHistory/{league_id}"
        )
        self.views = VIEWS
        self.api_params = API_PARAMS
        self.response = None

    def get(self, view: str, **kwargs) -> List[dict]:
        """
        Return a list of jsons for the specified ESPN fantasy football endpoint
        """
        filters = {
            "players": {
                "limit": 5000,
                "sortDraftRanks": {
                    "sortPriority": 100,
                    "sortAsc": True,
                    "value": "STANDARD"
                }
            }
        }
        headers = {'x-fantasy-filter': json.dumps(filters)}
        params = {"view": view}
        if kwargs:
            params.update(**kwargs)
        self.response = requests.get(url=self.url, cookies=self.cookies, headers=headers, params=params)
        return self.response.json()
