from datetime import datetime


class Page:
    def __init__(self):

        self.min_season = 2014
        self.max_season = 2022
        self.seasons = [season for season in range(self.min_season, self.max_season+1)]
        self.current_year = datetime.today().year
        self.playoff_week = 14

    def run(self):
        raise NotImplementedError
