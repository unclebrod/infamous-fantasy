import polars as pl
from pydantic import BaseModel
import requests
import json

FILTERS = {
    "players": {
        "limit": 10000,
        "sortDraftRanks": {"sortPriority": 100, "sortAsc": True, "value": "PPR"},
    }
}
HEADERS = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9",
    "Referrer": "https://fantasy.espn.com/",
    "Origin": "https://fantasy.espn.com/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    "x-fantasy-filter": json.dumps(FILTERS),
}


def main():
    response = requests.get(
        url="https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2025/segments/0/leaguedefaults/3?view=kona_player_info",
        headers=HEADERS,
    )
    jsn = response.json()
    players_list = []
    for players in jsn["players"]:
        player = players["player"]
        ownership = player.get("ownership", {})
        player_data = {
            "player_id": player.get("id"),
            "player_name": player.get("fullName"),
            "position": player.get("defaultPositionId"),
            "average_auction_value": ownership.get("auctionValueAverage"),
            "average_draft_position": ownership.get("averageDraftPosition"),
            "percent_owned": ownership.get("percentOwned"),
            "injured": player.get("injured"),
        }
        players_list.append(player_data)
    df = pl.DataFrame(players_list).sort("average_draft_position")
    df.write_csv("espn_auction_ranks.csv")

    print("ok")


if __name__ == "__main__":
    main()
