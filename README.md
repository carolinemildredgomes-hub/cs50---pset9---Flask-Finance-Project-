# CS50 PSet 9 — Finance

## Description
This is a Flask web application that simulates a simple stock trading platform. Users can register and log in, look up stock quotes, buy and sell shares using a mock market data provider, view their portfolio and transaction history, and add additional cash to their account.

This project is part of Harvard's **CS50x Problem Set 9**.

---

## Files
- `app.py` — Flask application with routes for register, login, quote, buy, sell, history, add cash, and portfolio.
- `helpers.py` — helper functions (provided by distribution): `lookup`, `usd`, `apology`, `login_required`.
- `finance.db` — SQLite database (includes `users` table and `transactions` table).
- `templates/` — HTML templates (Jinja2) for pages.
- `static/styles.css` — styles.

---

## Database
`transactions` table schema (created automatically if missing):

```sql
CREATE TABLE transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  symbol TEXT NOT NULL,
  shares INTEGER NOT NULL,
  price REAL NOT NULL,
  created_at TEXT NOT NULL
);


