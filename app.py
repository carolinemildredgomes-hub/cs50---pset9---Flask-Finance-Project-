import os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, lookup, usd
from datetime import datetime

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///finance.db")
app.jinja_env.filters["usd"] = usd

# --------------------------
# INDEX (Portfolio)
# --------------------------


@app.route("/")
@login_required
def index():
    user_id = session["user_id"]
    cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]

    rows = db.execute("""
        SELECT symbol, SUM(shares) AS total_shares
        FROM transactions
        WHERE user_id = ?
        GROUP BY symbol
        HAVING total_shares > 0
    """, user_id)

    holdings = []
    total_value = cash

    for row in rows:
        stock = lookup(row["symbol"])
        value = stock["price"] * row["total_shares"]
        holdings.append({
            "symbol": stock["symbol"],
            "name": stock["name"],
            "shares": row["total_shares"],
            "price": stock["price"],
            "total": value
        })
        total_value += value

    return render_template("index.html", holdings=holdings, cash=cash, total=total_value)

# --------------------------
# REGISTER
# --------------------------


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            return apology("must provide username")
        if not password or not confirmation:
            return apology("must provide password")
        if password != confirmation:
            return apology("passwords do not match")

        hash_pw = generate_password_hash(password)

        try:
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hash_pw)
        except:
            return apology("username already exists")

        user = db.execute("SELECT id FROM users WHERE username = ?", username)
        session["user_id"] = user[0]["id"]
        return redirect("/")
    else:
        return render_template("register.html")

# --------------------------
# LOGIN / LOGOUT
# --------------------------


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if not username:
            return apology("must provide username")
        if not password:
            return apology("must provide password")

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return apology("invalid username and/or password")

        session["user_id"] = rows[0]["id"]
        return redirect("/")
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# --------------------------
# QUOTE
# --------------------------


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("must provide symbol")
        stock = lookup(symbol)
        if not stock:
            return apology("invalid symbol")
        return render_template("quoted.html", stock=stock)
    else:
        return render_template("quote.html")

# --------------------------
# BUY
# --------------------------


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        if not symbol:
            return apology("must provide symbol")
        try:
            shares = int(shares)
            if shares <= 0:
                return apology("shares must be positive")
        except:
            return apology("shares must be a positive integer")

        stock = lookup(symbol)
        if not stock:
            return apology("invalid symbol")

        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
        total_cost = shares * stock["price"]
        if cash < total_cost:
            return apology("can't afford")

        db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", total_cost, session["user_id"])
        db.execute("""
            INSERT INTO transactions (user_id, symbol, shares, price, type, date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, session["user_id"], stock["symbol"], shares, stock["price"], "buy", datetime.now())

        return redirect("/")
    else:
        return render_template("buy.html")

# --------------------------
# SELL
# --------------------------


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    user_id = session["user_id"]
    symbols = db.execute("""
        SELECT symbol, SUM(shares) AS total_shares
        FROM transactions
        WHERE user_id = ?
        GROUP BY symbol
        HAVING total_shares > 0
    """, user_id)

    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        if not symbol:
            return apology("must select symbol")
        try:
            shares = int(shares)
            if shares <= 0:
                return apology("shares must be positive")
        except:
            return apology("shares must be a positive integer")

        owned = db.execute("""
            SELECT SUM(shares) AS total FROM transactions
            WHERE user_id = ? AND symbol = ?
        """, user_id, symbol)[0]["total"]
        if shares > owned:
            return apology("not enough shares")

        stock = lookup(symbol)
        value = shares * stock["price"]
        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", value, user_id)
        db.execute("""
            INSERT INTO transactions (user_id, symbol, shares, price, type, date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, user_id, symbol, -shares, stock["price"], "sell", datetime.now())
        return redirect("/")
    else:
        return render_template("sell.html", symbols=[row["symbol"] for row in symbols])

# --------------------------
# HISTORY
# --------------------------


@app.route("/history")
@login_required
def history():
    user_id = session["user_id"]
    transactions = db.execute("""
        SELECT symbol, shares, price, type, date
        FROM transactions
        WHERE user_id = ?
        ORDER BY date DESC
    """, user_id)
    return render_template("history.html", transactions=transactions)

# --------------------------
# PERSONAL TOUCH: ADD CASH
# --------------------------


@app.route("/add_cash", methods=["GET", "POST"])
@login_required
def add_cash():
    if request.method == "POST":
        amount = request.form.get("amount")
        try:
            amount = float(amount)
            if amount <= 0:
                return apology("amount must be positive")
        except:
            return apology("invalid amount")

        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", amount, session["user_id"])
        flash(f"${amount:.2f} added to your account!")
        return redirect("/")
    else:
        return render_template("add_cash.html")
