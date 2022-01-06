import os
import requests
import urllib.parse
import json
import datetime
from flask import redirect, render_template, request, session
from functools import wraps
import _sqlite3

conn = _sqlite3.connect("basketball.db")
db = conn.cursor()

# Apology helper function


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def player_stats():
    """Look up stats for player."""

    # Contact API
    text = []
    player_ids = []
    ids = []
    try:
        # this is how we got the initial players for our database
        player_ids = db.execute("SELECT id FROM players")
        # print(len(player_ids))
        for i in range(len(player_ids.fetchall())):
            ids.append(player_ids[i][0])
            # print(ids)
        # player_ids = db.execute("SELECT id FROM players SORT BY ?",  )
        # print(ids[0])
        # print(len(ids))
        for i in range(len(ids)):
            url = f"https://www.balldontlie.io/api/v1/season_averages?season=2019&player_ids[]={ids[i]}"
            response = requests.get(url)
            response.raise_for_status()
            text.append(response.json())
            # print(text)
    except requests.RequestException:
        return None

    hi = json.dumps(text, indent=4)
    data = json.loads(hi)
    # print(text)

    return data


def lookup():
    ids = []
    try:
        player_ids = db.execute("SELECT id FROM players").fetchall()
        # print(player_ids)
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        # this was used for our demo and the model we left in
        #Since we used a free API just be careful spamming update-only get a limited
        #number of calls per minute
        # string = 'per_page=100&start_date=2019-12-07&end_date=2019-12-12'
        # this commented line is what should update the games daily if you click update
        string = f'per_page=100&start_date={yesterday}&end_date={today}'
        # API call getting all player stats in our db;
        for i in range(len(player_ids)):
            string += f"&player_ids[]={player_ids[i][0]}"
            query = 'https://www.balldontlie.io/api/v1/stats?' + string
            url = f"{query}"
            # print(url)
        response = requests.get(url).json()
        page = 1
        # loop used to iterate through each page that the API brought back
        while True:
            url = f'https://www.balldontlie.io/api/v1/stats?page={page}' + '&' + string
            # if requests.get(url) != None:
            #     print(requests.get(url).json())
            response = requests.get(url).json()
            if response:
                ids.append(response)
                if type(response['meta']['next_page']) != int:
                    last_page = response['meta']['total_count'] - ((response['meta']['current_page'] - 1) * 100)
                    break
            page += 1
        # print(ids)
    except requests.RequestException:
        return None
    # iterate through every page before last page, see documentation for retrieving data from API calls
    # insert data into fantasy_points
    for i in range(len(ids) - 1):
        for j in range(100):
            # if response:
            # print(ids[i]['data'][j]['player']['id'])
            db.execute("INSERT INTO fantasy_points (player_id, total_points, game_id) VALUES (?,?,?)",
                       (ids[i]['data'][j]['player']['id'], (ids[i]['data'][j]['pts'] + (2 * ids[i]['data'][j]['ast']) +
                       (2 * ids[i]['data'][j]['reb']) + (2 * ids[i]['data'][j]['stl']) + (2 * ids[i]['data'][j]['blk'])
                       - (2 * ids[i]['data'][j]['turnover'])), ids[i]['data'][j]['game']['id']))
    # print(last_page)
    # iterate through last page of data
    # insert data into fantasy points
    last = response['meta']['current_page'] - 1
    for i in range(last_page):
        # if response:
        # print(ids[last]['data'][i]['pts'])
        db.execute("INSERT INTO fantasy_points (player_id, total_points, game_id) VALUES (?,?,?)",
                   (ids[last]['data'][i]['player']['id'], (ids[last]['data'][i]['pts'] + (2 * ids[last]['data'][i]['ast']) +
                   (2 * ids[last]['data'][i]['reb']) + (2 * ids[last]['data'][i]['stl']) + (2 * ids[last]['data'][i]['blk'])
                   - (2 * ids[last]['data'][i]['turnover'])), ids[last]['data'][i]['game']['id']))
        conn.commit()

    return
