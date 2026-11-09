import sqlite3

DB_FILE = "accounts.db"
OLD_LOGINS_FILE = "logins.txt"
DEFAULT_ELO = 1000

def _get_connection():  # Create the SQLite table automatically on first connection
    conn = sqlite3.connect(DB_FILE)  # Persist accounts in a local SQLite file rather than a temporary list
    conn.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            elo INTEGER NOT NULL DEFAULT 1000,
            email TEXT,
            email_opt_in INTEGER NOT NULL DEFAULT 0
        )
    """)

    columns = []
    for row in conn.execute("PRAGMA table_info(accounts)"):
        columns.append(row[1])

    if "email" not in columns:
        conn.execute("ALTER TABLE accounts ADD COLUMN email TEXT")
    if "email_opt_in" not in columns:
        conn.execute("ALTER TABLE accounts ADD COLUMN email_opt_in INTEGER NOT NULL DEFAULT 0")

    conn.commit()
    return conn

def load_accounts():  # Convert database rows into account dictionaries
    conn = _get_connection()
    try:
        rows = conn.execute("SELECT username, password, elo, email, email_opt_in FROM accounts").fetchall()  # Read existing usernames, passwords, emails, and ratings from persistent storage
    finally:
        conn.close()
    accounts = []
    for row in rows:
        account = {
            "user": row[0],
            "pass": row[1],
            "elo": row[2],
            "email": row[3],
            "email_opt_in": bool(row[4])
        }
        accounts.append(account)
    return accounts

def save_accounts(accounts_list):  # Replace all existing rows with the supplied account collection
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM accounts")  # Remove old rows before replacing the complete account collection
        account_rows = []
        for account in accounts_list:
            account_rows.append((account["user"], account["pass"], account["elo"], account.get("email"), int(account.get("email_opt_in", False))))

        conn.executemany(
            "INSERT INTO accounts (username, password, elo, email, email_opt_in) VALUES (?, ?, ?, ?, ?)",
            account_rows,  # Insert all account rows efficiently instead of one query per account
        )
        conn.commit()
    finally:
        conn.close()

def create_account(username, password, elo=DEFAULT_ELO, email=None, email_opt_in=False):
    # Keep the email address for the account, but only subscribe when the user explicitly opts in.
    if email_opt_in and not email:
        raise ValueError("An email address is required to receive updates")

    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO accounts (username, password, elo, email, email_opt_in) VALUES (?, ?, ?, ?, ?)",
            (username, password, elo, email, int(email_opt_in)),
        )
        conn.commit()
    finally:
        conn.close()

def check_login(username, password):
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM accounts WHERE username = ? AND password = ?",  # Parameters keep user-entered credentials separate from SQL syntax
            (username, password),
        ).fetchone()
    finally:
        conn.close()
    return row is not None

def get_elo(username):  # Look up a player current rating without loading the whole leaderboard
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT elo FROM accounts WHERE username = ?",
            (username,),
        ).fetchone()
    finally:
        conn.close()
    if row:
        return row[0]
    else:
        return None

def apply_elo_change(username, delta):  # Apply a signed ELO change to the stored rating
    if not username:
        return None

    conn = _get_connection()
    try:
        row = conn.execute("SELECT elo FROM accounts WHERE username = ?", (username,)).fetchone()  # Check that a player exists before changing their stored rating
        if row is None:
            return None
        new_elo = row[0] + delta
        conn.execute("UPDATE accounts SET elo = ? WHERE username = ?", (new_elo, username))
        conn.commit()
        return new_elo
    finally:
        conn.close()

def get_leaderboard():  # Return player ratings in descending order for the leaderboard
    conn = _get_connection()
    try:
        rows = conn.execute("SELECT username, elo FROM accounts ORDER BY elo DESC").fetchall()
    finally:
        conn.close()
    leaderboard = []
    for row in rows:
        leaderboard.append((row[0], row[1]))
    return leaderboard

def get_email_addresses():
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT email FROM accounts "
            "WHERE email_opt_in = 1 AND email IS NOT NULL AND TRIM(email) != ''"
        ).fetchall()
    finally:
        conn.close()

    emails = []
    for row in rows:
        emails.append(row[0])
    return emails