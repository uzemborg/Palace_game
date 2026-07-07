login_file = "logins.txt"
start_elo = 1000
 
def load_accounts():
    accounts_list = []
    try:
        with open(login_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = [p.strip().strip('"') for p in line.split(",")]
                if len(parts) < 2:
                    continue
 
                user, passw = parts[0], parts[1]
                if len(parts) >= 3 and parts[2].lstrip("-").isdigit():
                    elo = int(parts[2])
                else:
                    elo = start_elo
 
                accounts_list.append({"user": user, "pass": passw, "elo": elo})
    except FileNotFoundError:
        pass
    return accounts_list
 
def save_accounts(accounts_list):
    with open(login_file, "w") as f:
        for acc in accounts_list:
            f.write(f'"{acc["user"]}", "{acc["pass"]}", "{acc["elo"]}"\n')
 
def create_account(username, password, elo=start_elo):
    with open(login_file, "a") as f:
        f.write(f'"{username}", "{password}", "{elo}"\n')
 
def check_login(username, password):
    for acc in load_accounts():
        if acc["user"] == username and acc["pass"] == password:
            return True
    return False
 
def get_elo(username):
    for acc in load_accounts():
        if acc["user"] == username:
            return acc["elo"]
    return None
 
def apply_elo_change(username, delta):
    if not username:
        return None
 
    accounts_list = load_accounts()
    for acc in accounts_list:
        if acc["user"] == username:
            acc["elo"] += delta
            save_accounts(accounts_list)
            return acc["elo"]
    return None
 
def get_leaderboard():
    accounts_list = load_accounts()
    ranked = sorted(accounts_list, key=lambda a: a["elo"], reverse=True)
    return [(acc["user"], acc["elo"]) for acc in ranked]