import os

import _sqlite3
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
import datetime
from helpers import apology, login_required, player_stats, lookup

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure SQLite database
conn = _sqlite3.connect("basketball.db", check_same_thread=False)
db = conn.cursor()


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # Render template to index html
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),)).fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0][2], (request.form.get("password"))):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0][0]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/leagueselect", methods=["GET", "POST"])
@login_required
def leagueselect():

    # Join leagues table and league_user table to select which league to select in
    league = db.execute(
        "SELECT * FROM leagues WHERE id in (SELECT league_id FROM league_user WHERE user_id = ?)", (session["user_id"],))

    # Creating a session for league_id
    if request.method == "POST":
        session["league_id"] = request.form.get('league')

        # Ensure league was selected
        if not session["league_id"]:
            return apology("must select league", 403)

        # Redirect to players
        return redirect("/players")

    # Return leagueselect html
    return render_template("leagueselect.html", league=league)


@app.route("/players", methods=["GET", "POST"])
@login_required
def players():

    exists = db.execute("SELECT * FROM stats").fetchall
    if not exists :

        """Get players stats."""
        players = player_stats()
        name = {}
        for row in players["data"]:
          length = len(row)
          name["player"] = row["first_name"]
    
        for i in range(length):
            name = ['first_name'][i]

        for i in range(len(players)):
            players[i]['data'].append(name[i])
        db.execute("INSERT INTO stats (name, position, team, points, assists, rebounds, steals, blocks, turnovers, salary) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    players[i]['data'][1]['first_name'] + ' ' + players[i]['data'][1]['last_name'], players[i]['data'][1]['position'], players[i]['data'][1]['team'], players[i]['data'][0]['pts'],
                    players[i]['data'][0]['ast'], players[i]['data'][0]['reb'], players[i]['data'][0]['stl'], players[i]['data'][0]['blk'], players[i]['data'][0]['turnover'],
                    players[i]['data'][1]['salary'])
    # for i in range(len(stats)):
    #     print(stats[i]['name'])

    #     

    # Create empty dict for stats to put data into
    stats = []

    # Select relevant data for stats and league to pick players
    stats = db.execute(
        "SELECT * FROM stats WHERE player_id NOT IN (SELECT player_id from user_player WHERE league_id = ?)", (int(session['league_id']),)).fetchall()
    league = db.execute(
        "SELECT * FROM leagues WHERE id in (SELECT league_id FROM league_user WHERE user_id = ?)", (session["user_id"],)).fetchall()

    # SQL command used to add player id into stats
    players = db.execute("SELECT id, first_name, last_name FROM players").fetchall()
    for i in range(len(players)):
        db.execute("UPDATE stats SET player_id = ? WHERE name = ?", (players[i][0], (players[i][1] + ' ' + players[i][2])))
    # Realized we needed team id, so this is sql to copy over team id to stats
    players = db.execute("SELECT id, team_id FROM players").fetchall()
    for i in range(len(players)):
        db.execute("UPDATE stats SET team_id = ? WHERE player_id = ?", (players[i][1], players[i][0]))

    # Sort based on preferences given
    if request.method == "POST":

        if request.form.get('stat') == 'salaryasc':
            stats = db.execute(
                "SELECT * FROM stats WHERE player_id NOT IN (SELECT player_id from user_player WHERE league_id = ?) ORDER BY salary", (int(session['league_id']),)).fetchall()

        if request.form.get('stat') == 'salarydesc':
            stats = db.execute(
                "SELECT * FROM stats WHERE player_id NOT IN (SELECT player_id from user_player WHERE league_id = ?) ORDER BY salary DESC", (int(session['league_id']),)).fetchall()

        if request.form.get('stat') == 'points':
            stats = db.execute(
                "SELECT * FROM stats WHERE player_id NOT IN (SELECT player_id from user_player WHERE league_id = ?) ORDER BY points DESC", (int(session['league_id']),)).fetchall()

    # Query database for user's cash
    rows = db.execute("SELECT cash FROM league_user WHERE user_id = ? AND league_id = ?",
                      (session["user_id"], int(session["league_id"]))).fetchall()
    cash = rows[0][0]

    conn.commit()
    

    # Return players
    return render_template("players.html", stats=stats, league=league, cash=cash)

   


@app.route("/add", methods=["GET", "POST"])
@login_required
def add():

    # POST
    if request.method == "POST":

        # Query for relevant player information
        player_id = request.form.get('id')
        players = db.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchall()

        # Extract cash of player chosen
        cost = players[0][5]

        # Get user's cash balance
        rows = db.execute("SELECT cash FROM league_user WHERE user_id = ? AND league_id = ?",
                          (session["user_id"], int(session["league_id"]))).fetchall()
        if len(rows) != 1:
            return apology("missing user")
        cash = rows[0][0]

        # Ensure user can afford player
        if cash < cost:
            return apology("can't afford")
        count = db.execute("SELECT COUNT(player_id) FROM user_player WHERE user_id = ? and league_id = ?",
                           (session["user_id"], int(session["league_id"]))).fetchall()

        # Set limit to number of players brought
        if count[0][0] == 7:
            return apology("Too many players")

        # Insert player, user and league information to user_player
        db.execute("INSERT into user_player (user_id, player_id, league_id) VALUES (?,?,?)", (session["user_id"],
                   player_id, int(session['league_id'])))

        # Deduct cash
        db.execute("UPDATE league_user SET cash = cash - ? WHERE user_id = ? and league_id = ?",
                   (cost, session["user_id"], int(session["league_id"])))
        conn.commit()
        # Return myteam
        return redirect("/myteam")


@app.route("/delete", methods=["GET", "POST"])
@login_required
def delete():

    if request.method == "POST":
        player_id = request.form.get('id')

        players = db.execute("SELECT salary FROM players WHERE id = ?", player_id)

        # Get cost of player
        print(players)
        cost = players[0]['salary']

        # Get user's cash balance
        rows = db.execute("SELECT cash FROM league_user WHERE user_id = ? and league_id = ?",
                          session["user_id"], int(session["league_id"]))
        if not rows:
            return apology("missing user")
        cash = rows[0]['cash']

        # Drop players user wants to
        db.execute("DELETE FROM user_player WHERE player_id = ? AND league_id = ?", player_id, int(session["league_id"]))

        # Update the user's cash as a result
        db.execute("UPDATE league_user SET cash = cash + ? WHERE user_id = ? and league_id = ?",
                   cost, session["user_id"], int(session["league_id"]))
        conn.commit()

        return redirect("/myteam")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password") or not request.form.get("confirmation"):
            return apology("must provide password and confirmation", 400)

        # Ensure password matches confirmation
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords do not match", 400)

        elif len(request.form.get("password")) < 8:
            return apology("passwords must be 8 characters long", 400)

        elif request.form.get("password").isalpha():
            return apology("passwords must contain at least 1 number or special character", 400)

        # Ensure username does not exist in database
        name = db.execute("SELECT username FROM users WHERE username = ?", [request.form.get("username")]).fetchall()
        if len(name) == 1:
            return apology("username is already taken", 400)

        # Store username in database
        db.execute("INSERT INTO users (username, hash) VALUES (?,?)",
                   (request.form.get("username"), generate_password_hash(request.form.get("password"))))
        conn.commit()

        # Redirect user to home page
        return redirect("/")

    # Return Register
    return render_template("register.html")


@app.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """Create league"""

    # POST
    if request.method == "POST":

        # Ensure league name was submitted
        if not request.form.get("name"):
            return apology("must provide league name", 400)

        # Check league name conditions
        for i in range(len(request.form.get("name"))):
            print(request.form.get("name")[i])
            if not request.form.get("name")[i].isalpha() and request.form.get("name")[i] != " ":
                return apology("must provide alphabetic league name", 400)

        # Ensure number of teams submitted
        if not request.form.get("teams"):
            return apology("invalid team count")
        elif not request.form.get("teams").isdigit():
            return apology("invalid team count")
        teams = int(request.form.get("teams"))
        if teams < 4 or teams > 10:
            return apology("range of teams go from 4 to 10")

        # Check to see if league name is already taken
        x = db.execute("SELECT league_name FROM leagues WHERE league_name = ?", [request.form.get("name")]).fetchall()
        if len(x) > 0:
            return apology("That league name is already taken, please choose another", 400)

        # Record league information
        db.execute("INSERT INTO leagues (league_name, league_max) VALUES(?, ?)", (request.form.get("name"), teams))
        conn.commit()

        # Display creation success
        return render_template("created.html"), {"Refresh": "2; url=/leagues"}

    # GET
    else:
        return render_template("create.html")


@app.route("/join", methods=["GET", "POST"])
@login_required
def join():
    """Join league"""

    # POST
    if request.method == "POST":

        # league

        # Query for league id's
        l_id = db.execute("""SELECT id FROM leagues WHERE league_name = ?""", (request.form.get('symbol'),)).fetchall()

        # Ensure league was selected
        if len(l_id) == 0:
            return apology("select league", 400)

        # Query for league name
        pID = session["user_id"]
        name = db.execute("SELECT league_name FROM league_user WHERE user_id = ? and league_name = ?",
                          (pID, request.form.get("symbol"))).fetchall()

        # Ensure user is not in league
        if len(name) == 1:
            return apology("aready joined league", 400)

        # Update transaction table as well
        db.execute("INSERT INTO league_user (league_id, user_id, league_name) VALUES (?,?,?)",
                   (l_id[0][0], pID, request.form.get("symbol")))

        conn.commit()

        # Deposit cash
        db.execute("UPDATE leagues SET league_current = league_current + 1 WHERE league_name = ?",
                   (request.form.get("symbol"),))
        conn.commit()
        # Display portfolio
        flash("Joined!")
        return redirect("/")

    # GET
    else:

        # Show available leagues
        league = db.execute("SELECT * FROM leagues WHERE league_current < league_max")

        # Display Join
        return render_template("join.html", league=league)


@app.route("/leagues")
@login_required
def leagues():
    """pathway to creating or joining league"""

    # Display leagues
    return render_template("leagues.html")


# Same leagueselect design as before but for myteam
@app.route("/leagueselect2", methods=["GET", "POST"])
@login_required
def leagueselect2():

    league = db.execute(
        "SELECT * FROM leagues WHERE id in (SELECT league_id FROM league_user WHERE user_id = ?)", (session["user_id"],))

    if request.method == "POST":
        session["league_id"] = request.form.get('league')

        # Ensure league was selected
        if not session["league_id"]:
            return apology("must select league", 403)

        return redirect("/myteam")

    return render_template("leagueselect2.html", league=league)


@app.route("/myteam", methods=["GET", "POST"])
@login_required
def myteam():
    """shows user's team for each league"""

    # Create empty dict for points and select relevant info for leagues
    points = {}
    league = db.execute(
        "SELECT * FROM leagues WHERE id in (SELECT league_id FROM league_user WHERE user_id = ?)", (session["user_id"],))

    # SQL query to keep track of plyer's fantasy points and total fantasy points by team
    myteam = db.execute("SELECT DISTINCT game_id, name, player_id, position FROM fantasy_points WHERE player_id IN (SELECT player_id FROM user_player WHERE user_id = ? AND league_id = ?) GROUP BY player_id",
                        (session["user_id"], int(session["league_id"]))).fetchall()
    point = db.execute("SELECT DISTINCT game_id, name, total_points FROM fantasy_points WHERE player_id IN (SELECT player_id FROM user_player WHERE user_id = ? AND league_id = ?)",
                       (session["user_id"], int(session["league_id"]))).fetchall()

    # Iterate through point to extract player fantasy points
    for i in range(len(point)):
        player = point[i][1]
        if player in points:
            points[player] += point[i][2]
        else:
            points[player] = point[i][2]

    # Calculate total fantasy points for user
    total = sum(points.values())

    # Query database for user's cash
    rows = db.execute("SELECT cash FROM league_user WHERE user_id = ? AND league_id = ?",
                      (session["user_id"], int(session["league_id"]))).fetchall()
    cash = rows[0][0]

    # Record fantasy_points in league_user
    db.execute("UPDATE league_user SET fantasy_points = ? WHERE user_id = ? AND league_id = ?",
               (total, session["user_id"], int(session["league_id"])))

    conn.commit()

    # Return myteam
    return render_template("myteam.html", league=league, myteam=myteam, points=points, total=total, cash=cash)


@app.route("/update", methods=["GET", "POST"])
@login_required
def update():
    if request.method == "POST":

        # Used lookup helper function to extract stats
        lookup()

        # Iterate through each player to update stats accordingly
        stats = db.execute("SELECT name, player_id, position FROM stats").fetchall()
        for i in range(len(stats)):
            db.execute("UPDATE fantasy_points set name = ? WHERE player_id = ?", (stats[i][0], stats[i][1]))
            db.execute("UPDATE fantasy_points set position = ? WHERE player_id = ?", (stats[i][2], stats[i][1]))

        conn.commit()
        return redirect("/myteam")

# Same league select design as before


@app.route("/leagueselect3", methods=["GET", "POST"])
@login_required
def leagueselect3():

    league = db.execute(
        "SELECT * FROM leagues WHERE id IN (SELECT league_id FROM league_user WHERE user_id = ?)", (session["user_id"],))

    if request.method == "POST":
        session["league_id"] = request.form.get('league')

        # Ensure league was selected
        if not session["league_id"]:
            return apology("must select league", 403)

        return redirect("/leaderboards")

    return render_template("leagueselect3.html", league=league)


@app.route("/leaderboards")
@login_required
def leaderboards():
    """shows leaderboards for each league user is in"""

    # Select relevant league information
    league = db.execute(
        "SELECT * FROM leagues WHERE id in (SELECT league_id FROM league_user WHERE user_id = ?)", (session["user_id"],))

    # Query database for league rankings based on league
    standings = db.execute(
        "SELECT username,fantasy_points FROM users JOIN league_user ON users.id = league_user.user_id WHERE league_id = ? ORDER BY fantasy_points DESC", (int(session["league_id"]),))

    # Return leaderboards
    return render_template("leaderboards.html", league=league, standings=standings)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
