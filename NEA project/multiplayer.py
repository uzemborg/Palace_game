import tkinter as tk
from dict import cards_dict
from network import Net
import __main__ as main
import accounts
from server import state
import random

net = Net()
game_id = None
player_id = None
host_btn = None
back_btn = None

network_card_lookup = {}  # Translate rendered card IDs into rank and suit values for requests

last_hand = None  # Remember server data to avoid unnecessary redraws
last_player_data = None

opponent_texts = []
opponent_up_cards = []
opponent_down_cards = []
opponent_hand = []

opp_base_pos = [(660, 280), (1260, 280)]  # Keep distinct positions for the two possible visible opponents

pile_card_obj = None
pile_image = None
last_pile_size = 0

setup_text = None
setup_button = None

multiplayer_screen = None

join_label = main.canvas.create_text(main.sx(960), main.sy(250), text="", font=("Arial", 20, "bold"), fill="white", state="hidden", tags=("join_label",))
host_label = main.canvas.create_text(main.sx(960), main.sy(250), text="", font=("Arial", 20, "bold"), fill="white", state="hidden", tags=("host_label",))

def pickup_pile(event=None):  # Only the active player may collect the pile, and only without a legal move
    if main.game_mode != "multi":
        return
    if main.turn != "player":
        return

    has_move_result = net.has_move(game_id, player_id)  # Ask the server whether a legal play exists before allowing pickup
    if "has_move" not in has_move_result:
        main.show_game_error(has_move_result.get("error", "Network error. Please try again."))
        return
    if has_move_result["has_move"]:
        return

    result = net.pickup(game_id, player_id)  # Send the collection request to the server before changing local cards
    if not result.get("success"):
        main.show_game_error(result.get("error", "Couldn't pick up the pile. Please try again."))
        return

    state_data = net.state(game_id)  # Fetch the updated pile after the server accepts the pickup
    if "error" in state_data:
        main.show_game_error(state_data["error"])
        return
    update_pile(state_data["pile"])
    sync_player_data()

def clear_network_hand():
    for card in main.canvas.find_withtag("p_hand"):
        main.canvas.delete(card)

def sync_player_data():  # Refresh local cards from the server only when needed
    global last_hand

    if main.dragging_card is not None:  # Avoid replacing canvas cards in the middle of a drag
        return

    player = net.player(game_id, player_id)  # Request the player own cards separately from the public game state
    if player["hand"] == last_hand:  # Skip redrawing if the server hand has not changed
        return
    last_hand = player["hand"].copy()

    clear_network_hand()  # Discard outdated card images before rebuilding the local display
    clear_network_upcards()
    clear_network_downcards()

    render_network_hand(player["hand"])
    render_network_downcards(player["down_count"])
    render_network_upcards(player["up"])

    for card in main.p_up:
        main.canvas.tag_raise(card)

def create_opponent_displays():  # Prepare text elements used to show opponent information
    global opponent_texts
    for i in range(2):
        text = main.canvas.create_text(main.sx(150), main.sy(150 + i * 150), text="", fill="white", font=("Arial", 16))
        opponent_texts.append(text)

def opponent_up_down_slots(base_x, base_y):  # Place an opponent’s three face-up and hidden cards into fixed slots
    top_y = base_y - 150
    return [
        (main.sx(base_x - 150), main.sy(top_y)),
        (main.sx(base_x), main.sy(top_y)),
        (main.sx(base_x + 150), main.sy(top_y)),]

def render_opponent_upcards(state):  # Display opponents’ public face-up cards from shared game state
    global opponent_up_cards
    opponents = []

    for obj in opponent_up_cards:
        main.canvas.delete(obj)
    opponent_up_cards.clear()

    for p in state["player_data"]:  # Exclude the local player when selecting opponents to render
        if p["id"] != player_id:
            opponents.append(p)

    for row, p in enumerate(opponents):  # Use a separate card layout when there are two opponents
        if len(opponents) > 1:
            slots = opponent_up_down_slots(*opp_base_pos[row])
        for col, card in enumerate(p["up"]):
            rank = card["rank"]
            suit = card["suit"]
            img = main.load_card(cards_dict(f"{rank}{suit}"), 5, 5)
            if len(opponents) == 1:
                cid = main.canvas.create_image(main.sx(810 + col * 150), main.sy(150 + row * 150), image=img)
            else:
                if col < len(slots):
                    x, y = slots[col]
                else:
                    x, y = slots[-1]
                cid = main.canvas.create_image(x, y, image=img)
            opponent_up_cards.append(cid)
            main.canvas.tag_raise(cid)

def render_opponent_downcards(state):  # Opponents’ hidden cards are shown as backs, never revealed
    global opponent_down_cards
    opponents = []

    for obj in opponent_down_cards:
        main.canvas.delete(obj)
    opponent_down_cards.clear()

    for p in state["player_data"]:
        if p["id"] != player_id:
            opponents.append(p)

    for row, p in enumerate(opponents):
        if len(opponents) > 1:
            slots = opponent_up_down_slots(*opp_base_pos[row])
        for col in range(p["down_count"]):  # Only the number of hidden cards is sent for an opponent
            img = main.load_card(cards_dict("back"), 22, 22)
            if len(opponents) == 1:
                cid = main.canvas.create_image(main.sx(810 + col * 150), main.sy(150 + row * 150), image=img)
            else:
                if col < len(slots):
                    x, y = slots[col]
                else:
                    x, y = slots[-1]
                cid = main.canvas.create_image(x, y, image=img)
            opponent_down_cards.append(cid)

def render_opponent_hand(state):  # Use only card counts to represent opponents’ private hands
    global opponent_hand
    opponents = []

    for obj in opponent_hand:
        main.canvas.delete(obj)
    opponent_hand.clear()

    for p in state["player_data"]:
        if p["id"] != player_id:
            opponents.append(p)

    for row, p in enumerate(opponents):
        if len(opponents) > 1:
            base_x, base_y = opp_base_pos[row]  # Position multiple opponent hand backs around their centre
            start = base_x - (p["hand_count"] - 1) * 20
        for col in range(p["hand_count"]):
            img = main.load_card(cards_dict("back"), 22, 22)
            if len(opponents) == 1:
                cid = main.canvas.create_image(main.sx(750 + col * 60), main.sy(300 + row * 150), image=img)
            else:
                cid = main.canvas.create_image(main.sx(start + col * 40), main.sy(base_y), image=img)
            opponent_hand.append(cid)

def show_setup_phase():  # Show the three selection slots before multiplayer play begins
    global setup_text, setup_button
    canvas = main.canvas
    setup_text = canvas.create_text(main.sx(170), main.sy(140), text="Choose 3 up-cards", fill="white", font=("Arial", 24, "bold"))
    setup_button = tk.Button(main.root, text="Confirm Selection", font=("Arial", 16, "bold"), bg="green", fg="white", command=finish_setup)
    canvas.create_window(main.sx(130), main.sy(190), window=setup_button)
    for box in main.upcard_slot_boxes:
        canvas.itemconfigure(box, state="normal")

def update_pile(pile):  # Only redraw the central pile when its card count changes
    global last_pile_size, pile_image, pile_card_obj

    if len(pile) == last_pile_size:  # The previous pile size acts as a simple redraw cache
        return
    last_pile_size = len(pile)

    if not pile:  # Remove the displayed pile image when the server pile becomes empty
        if pile_card_obj:
            main.canvas.delete(pile_card_obj)
            pile_card_obj = None
        last_pile_size = 0
        return

    top = pile[-1]  # Use the last server pile record as the top visible card
    rank = top["rank"]
    suit = top["suit"]

    pile_image = main.load_card(cards_dict(f"{rank}{suit}"), 5, 5)
    if pile_card_obj:
        main.canvas.delete(pile_card_obj)

    pile_card_obj = main.canvas.create_image(main.pile_pos[0], main.pile_pos[1], image=pile_image)
    main.canvas.tag_bind(pile_card_obj, "<Button-1>", pickup_pile)

def render_network_hand(cards):  # Convert server card objects into draggable local canvas items
    canvas = main.canvas
    for i, card in enumerate(cards):
        rank = card["rank"]
        suit = card["suit"]
        face = main.load_card(cards_dict(f"{rank}{suit}"), 5, 5)
        if main.card_width == 0:  # Measure one loaded card image to size the pile drop area
            main.card_width = face.width()
            main.card_height = face.height()
        cid = canvas.create_image(main.sx(750 + i * 60), main.sy(760), image=face, tags=("p_hand",))

        main.card_ranks[cid] = rank  # Associate every local canvas card with its rank and image
        main.card_values[cid] = main.rank_values[rank]
        main.card_faces[cid] = face
        main.card_suits[cid] = suit
        network_card_lookup[cid] = {"rank": rank, "suit": suit}
    main.reposition_p_hand()

def render_network_upcards(cards):  # Show the player’s face-up cards using the latest server data
    canvas = main.canvas
    main.p_up.clear()
    for i, card in enumerate(cards):
        rank = card["rank"]
        suit = card["suit"]
        face = main.load_card(cards_dict(f"{rank}{suit}"), 5, 5)
        cid = canvas.create_image(main.sx(810 + i * 150), main.sy(920), image=face, tags=("p_up",))

        main.card_ranks[cid] = rank
        main.card_values[cid] = main.rank_values[rank]
        main.card_faces[cid] = face
        main.card_suits[cid] = suit
        network_card_lookup[cid] = {"rank": rank, "suit": suit}
        main.p_up.append(cid)

def render_network_deck(deck_count):  # Keep the remaining deck count in sync with the server
    canvas = main.canvas
    img = main.load_card(cards_dict("back"), 22, 22)
    cid = canvas.create_image(main.sx(1150), main.sy(540), image=img, tags=("deck",))

    if deck_count == 0:  # A deck count of zero means no draw-pile image should remain
        canvas.delete(cid)
        return
    canvas.itemconfigure(main.deck_label, text=f"{deck_count}")
    canvas.tag_raise(main.deck_label)

def clear_network_upcards():
    for card in main.canvas.find_withtag("p_up"):
        main.canvas.delete(card)

def render_network_downcards(count):  # Draw only card backs because face-down identities must stay hidden
    canvas = main.canvas
    back = main.load_card(cards_dict("back"), 22, 22)
    for i in range(count):
        canvas.create_image(main.sx(810 + i * 150), main.sy(920), image=back, tags=("p_down",))

def clear_network_downcards():
    for card in main.canvas.find_withtag("p_down"):
        main.canvas.delete(card)
        
def refresh_game():  # Repeatedly poll the server for turn and card changes
    global last_player_data

    if not main.session_active:
        return

    canvas = main.canvas
    state_data = net.state(game_id)  # Retrieve the latest turn, cards and ready status from the server

    if main.game_mode != "multi":
        return

    if state_data["winner"] is not None:  # A winner response ends polling and opens the result screen
        main.session_active = False
        show_winner(state_data["winner"], state_data["match_type"])
        return

    if main.state == "waiting_setup":  # The game starts when every joined player has confirmed setup
        ready_count = 0
        for player in state_data["player_data"]:
            if player["ready"]:
                ready_count += 1

        if ready_count == state_data["players"]:  # Do not enter normal play until every registered player is ready
            main.state = "play"
            sync_player_data()

        main.root.after(500, refresh_game)
        return

    if state_data["player_data"] != last_player_data:  # Redraw opponents only when their published data changes
        render_opponent_downcards(state_data)
        render_opponent_upcards(state_data)
        render_opponent_hand(state_data)
        render_network_deck(state_data["deck"])

        last_player_data = []  # Store a snapshot so unchanged opponent cards do not need redrawing
        for player in state_data["player_data"]:
            player_snapshot = {
                "id": player["id"],
                "hand_count": player["hand_count"],
                "down_count": player["down_count"],
                "up": player["up"][:]
            }
            last_player_data.append(player_snapshot)

    update_pile(state_data["pile"])  # Update the pile independently from the opponent hand displays

    if main.turn == "player" and not net.has_move(game_id, player_id)["has_move"]:  # Highlight the pile when the server reports no legal moves
        canvas.itemconfigure(main.slot_box_pile, outline="red", width=4)
    else:
        canvas.itemconfigure(main.slot_box_pile, outline="white", width=2)

    sync_player_data()  # Refresh the local hand after processing the shared game data

    if state_data["turn"] == player_id:  # The server turn index determines who may act locally
        main.turn = "player"
        main.canvas.coords(main.turn_indicator, main.sx(580), main.sy(820), main.sx(600), main.sy(840))
        main.canvas.itemconfigure(main.turn_indicator, state="normal")
    else:
        main.turn = "waiting"
        opponents = []
        for player in state_data["player_data"]:
            if player["id"] != player_id:
                opponents.append(player)  # Find opponents for positioning the turn indicator
        for row, p in enumerate(opponents):
            if p["id"] == state_data["turn"]:
                if len(opponents) == 1:
                    main.canvas.coords(main.turn_indicator, main.sx(580), main.sy(240), main.sx(600), main.sy(260))
                elif row == 0:
                    main.canvas.coords(main.turn_indicator, main.sx(180), main.sy(240), main.sx(200), main.sy(260))
                else:
                    main.canvas.coords(main.turn_indicator, main.sx(1380), main.sy(240), main.sx(1400), main.sy(260))
                main.canvas.itemconfigure(main.turn_indicator, state="normal")
                

    canvas.itemconfigure(main.deck_label, text=f"{state_data['deck']}")  # Display the remaining deck size reported by the server
    main.root.after(500, refresh_game)  # Poll every 500ms without blocking the Tkinter event loop

def show_winner(winner, match_type):  # Apply the multiplayer result and local rating change
    if match_type == "competitive" and main.user_var:  # Apply the multiplayer result to the signed-in local account rating. They must be in competitive mode.
        if winner == player_id:
            accounts.apply_elo_change(main.user_var, 50)
        else:
            accounts.apply_elo_change(main.user_var, -50)

    main.hide_home_button()
    canvas = main.canvas
    text = f"Player {winner + 1} Wins!"
    canvas.create_rectangle(main.sx(500), main.sy(350), main.sx(1400), main.sy(700), fill="black", tags=("win_overlay",))
    canvas.create_text(main.sx(950), main.sy(470), text=text, fill="white", font=("Arial", 40, "bold"), tags=("win_overlay",))

    home_btn = tk.Button(
        main.root, text="Home", font=("Arial", 20, "bold"),
        bg="white", fg="black", relief="flat", padx=20, pady=8,
        command=lambda: go_home_from_winner(home_btn),
    )
    canvas.create_window(main.sx(950), main.sy(600), window=home_btn, tags=("win_overlay",))

def go_home_from_winner(home_btn):
    main.canvas.delete("win_overlay")
    home_btn.destroy()
    main.go_home()

def finish_setup():  # Submit exactly three chosen face-up cards to the server
    global setup_button, setup_text
    cards = []

    if len(main.p_up) != 3:  # Block setup confirmation until exactly three face-up cards are chosen
        print("Choose 3 up cards first")
        return

    for cid in main.p_up:  # Map the selected canvas cards back to their server card records
        if cid not in network_card_lookup:
            print("Card missing from lookup:", cid)
            return
        cards.append(network_card_lookup[cid])

    result = net.setup(game_id, player_id, cards)  # Ask the server to verify and record those three chosen cards
    if not result["success"]:
        print(result)
        return

    main.state = "waiting_setup"  # Keep setup locked until every player has finished

    for box in main.upcard_slot_boxes:
        main.canvas.itemconfigure(box, state="hidden")
    if setup_button:
        setup_button.destroy()
    if setup_text:
        main.canvas.delete(setup_text)

def refresh_lobby():  # Poll for player count and host start confirmation
    if not main.session_active:
        return
    if not game_id:
        return

    state = net.state(game_id)
    if "error" in state or "players" not in state:
        main.root.after(1000, refresh_lobby)  # Retry the lobby poll after a failed or incomplete response
        return

    num_players = state["players"]
    if state["started"]:  # Move from the lobby to the match when the host has started it
        start_multiplayer_game()
        return

    match_type = state.get("match_type", "Unkown")
    main.canvas.itemconfigure("lobby_text", state="hidden")
    main.root.after(1000, refresh_lobby)  # Recheck the lobby in one second
    main.canvas.create_text(main.sx(960), main.sy(200), text=f"{match_type.title()} Match\nPlayers in lobby: {num_players}/3", fill="white", font=("Arial", 24, "bold"), tags="lobby_text")

def start_multiplayer_game():  # Build the multiplayer board and begin synchronisation
    global multiplayer_screen

    if multiplayer_screen:
        multiplayer_screen.destroy()
        multiplayer_screen = None

    create_opponent_displays()

    main.state = "select_up"
    main.p_phase = "hand"
    main.turn = "waiting"

    canvas = main.canvas
    canvas.coords(
        main.slot_box_pile,
        main.pile_pos[0] - 80, main.pile_pos[1] - 120,
        main.pile_pos[0] + 80, main.pile_pos[1] + 120,
    )
    canvas.itemconfigure(main.slot_box_pile, state="normal")
    canvas.itemconfigure(main.deck_label, state="normal")

    canvas.bind("<ButtonPress-1>", main.start_drag)
    canvas.bind("<B1-Motion>", main.do_drag)
    canvas.bind("<ButtonRelease-1>", main.end_drag)
    canvas.tag_bind("pile", "<Button-1>", pickup_pile)

    player = net.player(game_id, player_id)  # Load the local player cards before showing the setup controls
    render_network_hand(player["hand"])

    show_setup_phase()
    refresh_game()
    main.show_home_button()

class MultiplayerScreen:
    def __init__(self, root, canvas):
        self.root = root
        self.canvas = canvas
        self.frame = tk.Frame(root, bg="green")
        self.canvas_window = canvas.create_window(main.sx(960), main.sy(540), window=self.frame)

        tk.Button(self.frame, text="Host Game", font=("Arial", 30, "bold"), bg="white", fg="green", relief="flat", padx=30, pady=10, command=self.open_hostgame).pack()
        tk.Button(self.frame, text="Join Game", font=("Arial", 30, "bold"), bg="white", fg="green", relief="flat", padx=30, pady=10, command=self.open_joingame).pack(pady=20)
        tk.Button(self.frame, text="Back", font=("Arial", 16, "bold"), bg="white", fg="green", relief="flat", padx=20, pady=6, command=self.back).pack(pady=(10, 0))

    def destroy(self):
        self.canvas.delete(self.canvas_window)
        self.frame.destroy()
        self.canvas.itemconfigure("lobby_text", state="hidden")

    def open_hostgame(self):
        self.destroy()
        open_game_type_screen(self.root, self.canvas)

    def open_joingame(self):
        self.destroy()
        open_joingame(self.root, self.canvas)

    def back(self):
        main.go_home()

class GameTypeScreen:
    def __init__(self, root, canvas):
        self.root = root
        self.canvas = canvas

        self.frame = tk.Frame(root, bg="green")
        self.canvas_window = canvas.create_window(main.sx(960), main.sy(540), window=self.frame)

        tk.Label(self.frame, text="Select Match Type", font=("Arial", 32, "bold"), bg="green", fg="white" ).pack(pady=15)
        tk.Button(self.frame, text="Casual", font=("Arial", 26, "bold"), bg="white", fg="green", command=lambda: self.choose("casual")).pack(pady=10)
        tk.Button(self.frame, text="Competitive", font=("Arial", 26, "bold"), bg="white", fg="green", command=lambda: self.choose("competitive")).pack(pady=10)
        tk.Button(self.frame, text="Back", font=("Arial", 16), command=self.back).pack(pady=10)

    def choose(self, match_type):
        self.destroy()
        open_hostgame(self.root, self.canvas, match_type)

    def back(self):
        self.destroy()
        open_multiplayer_screen(self.root, self.canvas)

    def destroy(self):
        self.canvas.delete(self.canvas_window)
        self.frame.destroy()

class HostScreen:
    def __init__(self, root, canvas, match_type):
        global host_btn, back_btn
        self.root = root
        self.canvas = canvas
        self.frame = tk.Frame(root, bg="green")
        self.canvas_window = canvas.create_window(main.sx(960), main.sy(540), window=self.frame)
        self.match_type = match_type

        self.status_label = tk.Label(self.frame, text="", font=("Arial", 20, "bold"), bg="green", fg="white")
        self.status_label.pack(pady=(0, 10))

        host_btn = tk.Button(self.frame, text="Retry hosting", font=("Arial", 25, "bold"), bg="white", fg="green", relief="flat", command=self.host_game)
        back_btn = tk.Button(self.frame, text="Home", font=("Arial", 10, "bold"), bg="white", fg="green", relief="flat", padx=20, pady=6, command=self.back)
        back_btn.pack(pady=10)
        self.error_label = main.make_error_label(self.frame)
        self.host_game()
         
    def host_game(self):  # Create a server lobby and share its code with other players
        global game_id, player_id, host_btn, back_btn

        game = net.create(self.match_type)
        if "error" in game or "game_id" not in game:
            main.show_error(self.error_label, game.get("error", "Could not create a game. Please try again."))
            host_btn.pack(pady=10)
            return

        player = net.join(game["game_id"])  # The host joins their own lobby as its first registered player
        if "error" in player or "player_id" not in player:
            main.show_error(self.error_label, player.get("error", "Could not join the game you just created. Please try again."))
            host_btn.pack(pady=10)
            return

        main.clear_error(self.error_label)
        main.game_mode = "multi"
        main.session_active = True
        game_id = game["game_id"]
        player_id = player["player_id"]
        self.status_label.configure(text=f"{self.match_type.title()} match - Hosting at: {game_id}")
        host_btn.pack_forget()
        back_btn.pack_forget()

        self.card_label = tk.Label(self.frame, bg="green")
        self.card_label.pack(pady=10)
        self.cycling = True
        self.cycle_card()

        tk.Button(self.frame, text="Start Game", font=("Arial", 30, "bold"), bg="white", fg="green", relief="flat", command=self.start_game).pack(pady=10)
        tk.Button(self.frame, text="Home", font=("Arial", 10, "bold"), bg="white", fg="green", relief="flat", padx=20, pady=6, command=self.back).pack(pady=(10, 0))
        refresh_lobby()

    def cycle_card(self):
        if not self.cycling:
            return
        if not self.card_label.winfo_exists():
            self.cycling = False
            return
        rank = random.choice(main.ranks)  # Choose random display cards without changing the actual game deck
        suit = random.choice(main.suits)
        card_img = main.load_card(cards_dict(f"{rank}{suit}"), 2, 2)
        self.card_label.configure(image=card_img)
        self.card_label.image = card_img
        main.root.after(1000, self.cycle_card)
    
    def start_game(self):  # Only the host sends the request to start the shared game
        net.start(game_id)

    def destroy(self):
        self.cycling = False
        self.canvas.delete(self.canvas_window)
        self.frame.destroy()
        self.canvas.itemconfigure("lobby_text", state="hidden")

    def back(self):
        main.go_home()

class JoinScreen:
    def __init__(self, root, canvas):
        self.root = root
        self.canvas = canvas
        self.frame = tk.Frame(root, bg="green")
        self.canvas_window = canvas.create_window(main.sx(960), main.sy(540), window=self.frame)
        self.status_label = tk.Label(self.frame, text="", font=("Arial", 20, "bold"), bg="green", fg="white")
        self.status_label.pack(pady=(0, 10))

        self.title_label = tk.Label(self.frame, text="Join Code", font=("Arial", 25, "bold"), bg="green", fg="white")
        self.title_label.pack()
        self.code_entry = tk.Entry(self.frame, font=("Arial", 25, "bold"))
        self.code_entry.pack()
        self.join_btn = tk.Button(self.frame, text="Join Game", font=("Arial", 30, "bold"), bg="white", fg="green", relief="flat", command=self.join_game)
        self.join_btn.pack(pady=10)
        self.back_btn = tk.Button(self.frame, text="Back", font=("Arial", 10, "bold"), bg="white", fg="green", relief="flat", padx=20, pady=6, command=self.back)
        self.back_btn.pack(pady=(10, 0))
        self.error_label = main.make_error_label(self.frame)

    def join_game(self):  # Join the lobby identified by the entered four-digit code
        global game_id, player_id

        code = self.code_entry.get().strip()
        if not code:
            main.show_error(self.error_label, "Enter a game code first.")
            return
        player = net.join(code)

        if "error" in player:
            main.show_error(self.error_label, player["error"])
            return
        if "player_id" not in player:
            main.show_error(self.error_label, "Unexpected response from server. Please try again.")
            return
        main.clear_error(self.error_label)

        main.game_mode = "multi"
        main.session_active = True
        code = self.code_entry.get()
        game_id = code
        player_id = player["player_id"]
        self.status_label.configure(text=f"Joined: {game_id}")

        self.title_label.pack_forget()
        self.code_entry.pack_forget()
        self.join_btn.pack_forget()
        self.back_btn.pack_forget()
        self.error_label.pack_forget()

        self.card_label = tk.Label(self.frame, bg="green")
        self.card_label.pack(pady=10)
        self.cycling = True
        self.cycle_card()

        tk.Button(self.frame, text="Home", font=("Arial", 10, "bold"), bg="white", fg="green", relief="flat", padx=20, pady=6, command=self.back).pack(pady=(10, 0))

        refresh_lobby()

    def cycle_card(self):
        if not self.cycling:
            return
        if not self.card_label.winfo_exists():
            self.cycling = False
            return
        rank = random.choice(main.ranks)
        suit = random.choice(main.suits)
        card_img = main.load_card(cards_dict(f"{rank}{suit}"), 2, 2)
        self.card_label.configure(image=card_img)
        self.card_label.image = card_img
        main.root.after(1000, self.cycle_card)

    def destroy(self):
        self.cycling = False
        self.canvas.delete(self.canvas_window)
        self.frame.destroy()
        self.canvas.itemconfigure("lobby_text", state="hidden")

    def back(self):
        main.go_home()
        self.canvas.itemconfigure("enter_code", state="hidden")

def open_multiplayer_screen(root, canvas):
    global multiplayer_screen
    multiplayer_screen = MultiplayerScreen(root, canvas)

def open_game_type_screen(root, canvas):
    global multiplayer_screen
    multiplayer_screen = GameTypeScreen(root, canvas)

def open_hostgame(root, canvas, match_type):
    global multiplayer_screen
    multiplayer_screen = HostScreen(root, canvas, match_type)

def open_joingame(root, canvas):
    global multiplayer_screen
    multiplayer_screen = JoinScreen(root, canvas)

def reset():  # Clear network card caches and controls after leaving a match
    global game_id, player_id, network_card_lookup, last_hand, last_player_data
    global opponent_texts, opponent_up_cards, opponent_down_cards, opponent_hand
    global pile_card_obj, pile_image, last_pile_size, setup_text, setup_button
    global multiplayer_screen

    for cid in opponent_texts + opponent_up_cards + opponent_down_cards + opponent_hand:
        main.canvas.delete(cid)
    if pile_card_obj is not None:
        main.canvas.delete(pile_card_obj)
    if setup_text is not None:
        main.canvas.delete(setup_text)
    if setup_button is not None:
        setup_button.destroy()
    if multiplayer_screen is not None:
        multiplayer_screen.destroy()
    
    game_id = None
    player_id = None
    network_card_lookup = {}
    last_hand = None
    last_player_data = None
    opponent_texts = []
    opponent_up_cards = []
    opponent_down_cards = []
    opponent_hand = []
    pile_card_obj = None
    pile_image = None
    last_pile_size = 0
    setup_text = None
    setup_button = None
    multiplayer_screen = None