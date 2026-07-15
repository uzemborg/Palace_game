from flask import Flask, request, jsonify
import random
import traceback

app=Flask(__name__)
games={}

SUITS = ["S", "H", "D", "C"]
RANKS = ["2", "3", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]

RANK_VALUES = {
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "J": 11,
    "Q": 12,
    "K": 13,
    "A": 14
}

def check_winner(game, player):
    pdata = game["players"][player]
    if (len(pdata["hand"]) == 0 and len(pdata["up"]) == 0 and len(pdata["down"]) == 0):
        game["winner"] = player
        
def create_deck():
    deck = []
    for suit in SUITS:
        for rank in RANKS:
            deck.append({"rank": rank,"suit": suit})
    random.shuffle(deck)
    return deck

def can_play(card, pile):
    if not pile:
        return True
    rank = card["rank"]
    if rank in ("2", "10"):
        return True
    top = pile[-1]
    if top["rank"] == "2":       
        return True
    if top["rank"] == "7":
        return (RANK_VALUES[rank]<=RANK_VALUES[top["rank"]])
    return (RANK_VALUES[rank]>=RANK_VALUES[top["rank"]])

@app.post("/create")
def create():
    game_id = str(random.randint(1000,9999))
    games[game_id]={
        "players":[],
        "turn":0,
        "started": False,
        "deck": create_deck(),
        "pile": [],
        "winner": None
        }
    return {"game_id":game_id}

@app.post("/join/<game_id>")
def join(game_id):
    if game_id not in games:
        return {"error": "Game not found"}, 404
    player_id = len(games[game_id]["players"])
    if player_id >= 3:
        return {"error": "Game full"}, 400

    player = {
        "id": player_id, 
        "hand": [], 
        "up": [], 
        "down": [],
        "ready": False
        }

    for d in range(3):
        player["down"].append(games[game_id]["deck"].pop())
    for h in range(6):
        player["hand"].append(games[game_id]["deck"].pop())

    games[game_id]["players"].append(player)
    return {"player_id": player_id}

@app.get("/state/<game_id>")
def state(game_id):
    return jsonify({
        "turn": games[game_id]["turn"],
        "pile": games[game_id]["pile"],
        "players": len(games[game_id]["players"]),
        "started": games[game_id]["started"],
        "deck": len(games[game_id]["deck"]),
        "winner": games[game_id]["winner"],
        "player_data": [
            {
                "id": p["id"],
                "ready": p["ready"],
                "hand_count": len(p["hand"]),
                "up": p["up"],
                "down_count": len(p["down"])
              }
              for p in games[game_id]["players"]
            ]
        })

@app.get("/hand/<game_id>/<int:player_id>")
def hand(game_id, player_id):
    return jsonify(games[game_id]["players"][player_id]["hand"])

@app.post("/play/<game_id>")
def play(game_id):
    game = games[game_id]
    data = request.json
    player = data["player"]

    if "cards" in data:
        cards = data["cards"]
    else:
        cards = [data["card"]]

    if not cards:
        return {"success": False, "error": "No cards given"}

    if player != game["turn"]:
        return {"success": False,"error": "Not your turn"}

    if any(c["rank"] != cards[0]["rank"] for c in cards):
        return {"success": False, "error": "All cards in a group must be the same rank"}

    pdata = game["players"][player]
    if pdata["hand"]:
        source = pdata["hand"]
    else:
        source = pdata["up"]

    found_cards = []
    remaining = source.copy()
    for card in cards:
        match = None
        for c in remaining:
            if c["rank"] == card["rank"] and c["suit"] == card["suit"]:
                match = c
                break
        if match is None:
            return {"success": False,"error": "Card not found"}
        remaining.remove(match)
        found_cards.append(match)

    if not can_play(found_cards[0], game["pile"]):
        return {"success": False,"error": "Illegal move"}

    for c in found_cards:
        source.remove(c)
        game["pile"].append(c)

    check_winner(game, player)

    burned = False
    if found_cards[0]["rank"] == "10":
        game["pile"] = []
        burned = True
    elif len(game["pile"]) >= 4:
        last4 = game["pile"][-4:]
        if all(c["rank"] == last4[0]["rank"] for c in last4):
            game["pile"] = []
            burned = True

    while (source is pdata["hand"] and len(pdata["hand"]) < 3 and game["deck"]):
        pdata["hand"].append(game["deck"].pop())

    if burned:
        return {
            "success": True,
            "burn": True,
            "extra_turn": True
        }

    game["turn"] = (game["turn"] + 1) % len(game["players"])
    return {"success": True}

@app.post("/start/<game_id>")
def start_game(game_id):
    if game_id not in games:
        return {"error": "Game not found"}, 404

    games[game_id]["started"] = True
    return {"success": True}

@app.get("/player/<game_id>/<int:player_id>")
def player_data(game_id, player_id):
    player = games[game_id]["players"][player_id]

    return jsonify({
        "hand": player["hand"],
        "up": player["up"],
        "down_count": len(player["down"]),
        "hand_count": len(player["hand"])
    })

@app.post("/play_down/<game_id>")
def play_down(game_id):
    game = games[game_id]
    data = request.json
    player = data["player"]

    if player != game["turn"]:
        return {"success": False}
    pdata = game["players"][player]
    if not pdata["down"]:
        return {"success": False}
    card = pdata["down"].pop()

    if can_play(card, game["pile"]):
        game["pile"].append(card)
        while (len(pdata["hand"]) < 3 and game["deck"]):
            pdata["hand"].append(game["deck"].pop())
        game["turn"] = (game["turn"] + 1) % len(game["players"])
        check_winner(game, player)
        return {
            "success": True,
            "card": card
        }

    else:
        pdata["hand"].extend(game["pile"])
        pdata["hand"].append(card)
        game["pile"] = []

        return {
            "success": False,
            "pickup": True
        }

@app.post("/setup/<game_id>")
def setup(game_id):
    game = games[game_id]
    data = request.json

    player_id = data["player"]
    chosen = data["cards"]

    player = game["players"][player_id]

    if len(chosen) != 3:
        return {"success": False, "error": "Choose exactly 3 cards"}

    player["hand"].extend(player["up"])
    player["up"] = []

    new_up = []
    for chosen_card in chosen:
        found = None

        for card in player["hand"]:
            if (card["rank"] == chosen_card["rank"] and card["suit"] == chosen_card["suit"]):
                found = card
                break
        if found is None:
            return {"success": False, "error": "Card not found"}

        player["hand"].remove(found)
        new_up.append(found)
    player["up"] = new_up
    player["ready"] = True

    return {"success": True}

@app.post("/pickup/<game_id>")
def pickup(game_id):
    game = games[game_id]
    data = request.json
    player = data["player"]

    if player != game["turn"]:
        return {"success": False, "error": "Not your turn"}

    pdata = game["players"][player]
    pdata["hand"].extend(game["pile"])
    game["pile"] = []
    game["turn"] = (game["turn"] + 1) % len(game["players"])

    return {"success": True}

@app.get("/has_move/<game_id>/<int:player_id>")
def has_move(game_id, player_id):
    game = games[game_id]
    player = game["players"][player_id]

    if player["hand"]:
        cards = player["hand"]
    elif player["up"]:
        cards = player["up"]
    else:
        return {"has_move": True}

    for card in cards:
        if can_play(card, game["pile"]):
            return {"has_move": True}

    return {"has_move": False}

@app.get("/")
def home():
    return "jodjejopwejfopwefjop"
app.run(host="0.0.0.0",port=5000)

