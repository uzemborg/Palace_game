from flask import Flask, request, jsonify
import random

app=Flask(__name__)
games={}  # Store active matches in memory until the Flask server restarts

suits_game = ["S", "H", "D", "C"]
ranks_game = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]

rank_values = {
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

def check_winner(game, player):  # Winning requires the player to have no cards in any area
    pdata = game["players"][player]
    if (len(pdata["hand"]) == 0 and len(pdata["up"]) == 0 and len(pdata["down"]) == 0):
        game["winner"] = player
        
def create_deck():  # Create a shuffled deck of card records for multiplayer
    deck = []
    for suit in suits_game:
        for rank in ranks_game:
            deck.append({"rank": rank,"suit": suit})
    random.shuffle(deck)
    return deck

def can_play(card, pile):  # Enforce card rank rules on the server, not only in the GUI
    if not pile:
        return True
    rank = card["rank"]
    if rank in ("2", "10"):  # Twos and tens may always be played
        return True
    top = pile[-1]
    if top["rank"] == "2":  # A two resets the rank restriction on the next play
        return True
    if top["rank"] == "7":  # After a seven, only equal or lower ranks are legal
        return (rank_values[rank]<=rank_values[top["rank"]])
    return (rank_values[rank]>=rank_values[top["rank"]])  # Otherwise the next rank must be equal or greater

@app.post("/create")
def create():  # Generate a lobby ID and its initial game state
    data = request.get_json(silent=True) or {}
    match_type = data.get("match_type")  # Requests the match type of the game chosen previously
    if match_type not in ("casual", "competitive"):  # 400 error for a non-existent match type
        return {"error": "Invalid match type"}, 400

    game_id = str(random.randint(1000,9999))  # The four-digit code is random and currently has no collision check

    games[game_id]={  # A lobby keeps its own match type, deck, pile, players, turn, and winner state
        "match_type": match_type,
        "players":[],
        "turn":0,
        "started": False,
        "deck": create_deck(),
        "pile": [],
        "winner": None
        }
    return {"game_id":game_id}

@app.post("/join/<game_id>")
def join(game_id):  # Reject invalid and full-lobby requests before dealing cards
    if game_id not in games:
        return {"error": "Game not found"}, 404
    player_id = len(games[game_id]["players"])  # Player IDs are assigned in the order they join the lobby
    if player_id >= 3:
        return {"error": "Game full"}, 400

    player = {  # Store each player collections separately to track card ownership
        "id": player_id,
        "hand": [],
        "up": [],
        "down": [],
        "ready": False
        }

    for d in range(3):  # Three hidden cards are dealt before each player receives a hand
        player["down"].append(games[game_id]["deck"].pop())
    for h in range(6):  # Give the player six hand cards for selecting three face-up cards
        player["hand"].append(games[game_id]["deck"].pop())

    games[game_id]["players"].append(player)
    return {"player_id": player_id}

@app.get("/state/<game_id>")
def state(game_id):  # Send public state and opponent counts without exposing hidden cards
    public_players = []  # Return public card counts without exposing hidden card identities
    for player in games[game_id]["players"]:
        public_player = {
            "id": player["id"],
            "ready": player["ready"],
            "hand_count": len(player["hand"]),
            "up": player["up"],
            "down_count": len(player["down"])
        }
        public_players.append(public_player)

    return jsonify({
        "match_type": games[game_id]["match_type"],
        "turn": games[game_id]["turn"],
        "pile": games[game_id]["pile"],
        "players": len(games[game_id]["players"]),
        "started": games[game_id]["started"],
        "deck": len(games[game_id]["deck"]),
        "winner": games[game_id]["winner"],
        "player_data": public_players
    })

@app.get("/hand/<game_id>/<int:player_id>")
def hand(game_id, player_id):  # Return the requested hand so its owner can render their cards
    return jsonify(games[game_id]["players"][player_id]["hand"])

@app.post("/play/<game_id>")
def play(game_id):  # Validate selected cards and update the authoritative game state
    game = games[game_id]
    data = request.json
    player = data["player"]

    if "cards" in data:  # Accept either a group of cards or one individually submitted card
        cards = data["cards"]
    else:
        cards = [data["card"]]

    if not cards:  # Do not attempt rank comparisons when no cards were submitted
        return {"success": False, "error": "No cards given"}

    if player != game["turn"]:  # Reject attempts to play outside the assigned turn
        return {"success": False,"error": "Not your turn"}

    mixed_ranks = False
    for card in cards:
        if card["rank"] != cards[0]["rank"]:
            mixed_ranks = True
            break

    if mixed_ranks:  # A group move may contain only cards of one rank
        return {"success": False, "error": "All cards in a group must be the same rank"}

    pdata = game["players"][player]  # Choose the card collection allowed for this player current phase
    if pdata["hand"]:  # A player must finish their hand before using face-up cards
        source = pdata["hand"]
    else:
        source = pdata["up"]

    found_cards = []  # Keep the validated card records separate until all checks pass
    remaining = source.copy()  # Work on a copy so the same card cannot be submitted twice
    for card in cards:
        match = None
        for c in remaining:
            if c["rank"] == card["rank"] and c["suit"] == card["suit"]:  # Match cards using both rank and suit
                match = c
                break
        if match is None:
            return {"success": False,"error": "Card not found"}
        remaining.remove(match)
        found_cards.append(match)

    if not can_play(found_cards[0], game["pile"]):  # Reject moves that break the pile rank rules
        return {"success": False,"error": "Illegal move"}

    for c in found_cards:  # Transfer ownership only after all submitted cards have been validated
        source.remove(c)
        game["pile"].append(c)

    check_winner(game, player)  # Determine whether this move emptied every card area for the player

    burned = False  # Track whether a special card causes the pile to be cleared
    if found_cards[0]["rank"] == "10":  # Playing a ten clears the pile and grants an extra turn
        game["pile"] = []
        burned = True
    elif len(game["pile"]) >= 4:
        last4 = game["pile"][-4:]
        matching_ranks = True
        for card in last4:
            if card["rank"] != last4[0]["rank"]:
                matching_ranks = False
                break
        if matching_ranks:  # Four identical ranks at the top also clear the pile
            game["pile"] = []
            burned = True

    while (source is pdata["hand"] and len(pdata["hand"]) < 3 and game["deck"]):  # Draw replacement cards until the hand has three or the deck is empty
        pdata["hand"].append(game["deck"].pop())

    if burned:  # Burning the pile leaves the current player’s turn unchanged
        return {
            "success": True,
            "burn": True,
            "extra_turn": True
        }

    game["turn"] = (game["turn"] + 1) % len(game["players"])  # Use modulo to wrap the turn index back to the first player
    return {"success": True}

@app.post("/start/<game_id>")
def start_game(game_id):  # Let the lobby begin once the host sends a start request
    if game_id not in games:
        return {"error": "Game not found"}, 404

    games[game_id]["started"] = True
    return {"success": True}

@app.get("/player/<game_id>/<int:player_id>")
def player_data(game_id, player_id):  # Send the local player hand and face-up cards for client rendering
    player = games[game_id]["players"][player_id]

    return jsonify({
        "hand": player["hand"],
        "up": player["up"],
        "down_count": len(player["down"]),
        "hand_count": len(player["hand"])
    })

@app.post("/play_down/<game_id>")
def play_down(game_id):  # A face-down card is played without being seen beforehand
    game = games[game_id]
    data = request.json
    player = data["player"]

    if player != game["turn"]:  # Only the current player may request a hidden play
        return {"success": False}
    pdata = game["players"][player]
    if not pdata["down"]:
        return {"success": False}
    card = pdata["down"].pop()  # Remove a hidden card before revealing whether it is playable

    if can_play(card, game["pile"]):  # The server checks whether the blind card can be played
        game["pile"].append(card)
        while (len(pdata["hand"]) < 3 and game["deck"]):
            pdata["hand"].append(game["deck"].pop())
        game["turn"] = (game["turn"] + 1) % len(game["players"])
        check_winner(game, player)
        return {
            "success": True,
            "card": card
        }

    else:  # An invalid blind play sends the pile and played card to the hand
        pdata["hand"].extend(game["pile"])
        pdata["hand"].append(card)
        game["pile"] = []

        return {
            "success": False,
            "pickup": True
        }

@app.post("/setup/<game_id>")
def setup(game_id):  # Save the three face-up cards chosen during setup
    game = games[game_id]
    data = request.json

    player_id = data["player"]
    chosen = data["cards"]

    player = game["players"][player_id]

    if len(chosen) != 3:  # Exactly three upcards must be selected
        return {"success": False, "error": "Choose exactly 3 cards"}

    player["hand"].extend(player["up"])  # Return old upcards to the hand before processing the selection
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

        player["hand"].remove(found)  # Removing each chosen card prevents choosing it more than once
        new_up.append(found)
    player["up"] = new_up  # Record that this player has completed face-up card setup
    player["ready"] = True

    return {"success": True}

@app.post("/pickup/<game_id>")
def pickup(game_id):  # Picking up transfers the entire pile and advances the turn
    game = games[game_id]
    data = request.json
    player = data["player"]

    if player != game["turn"]:  # Prevent players from picking up out of turn
        return {"success": False, "error": "Not your turn"}

    pdata = game["players"][player]
    pdata["hand"].extend(game["pile"])  # Add all pile cards to the current player hand on pickup
    game["pile"] = []
    game["turn"] = (game["turn"] + 1) % len(game["players"])

    return {"success": True}

@app.get("/has_move/<game_id>/<int:player_id>")
def has_move(game_id, player_id):  # Check whether the player has at least one legal move
    game = games[game_id]
    player = game["players"][player_id]

    if player["hand"]:
        cards = player["hand"]
    elif player["up"]:
        cards = player["up"]
    else:  # Once only hidden cards remain, a blind attempt is still allowed
        return {"has_move": True}

    for card in cards:  # Stop searching as soon as a legal card is found
        if can_play(card, game["pile"]):
            return {"has_move": True}

    return {"has_move": False}

@app.get("/")
def home():
    return "jodjejopwejfopwefjop"
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

