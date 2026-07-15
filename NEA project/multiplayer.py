import tkinter as tk
from dict import cards_dict
from network import Net
import __main__ as main
import accounts
from server import state

net = Net()
game_id = None    
player_id = None

network_card_lookup = {}

last_hand = None
last_player_data = None

opponent_texts = []
opponent_up_cards = []
opponent_down_cards = []
opponent_hand = []

opp_base_pos = [(660, 280), (1260, 280)]

pile_card_obj = None
pile_image = None
last_pile_size = 0

setup_text = None
setup_button = None

multiplayer_screen = None

join_label = main.canvas.create_text(main.sx(960), main.sy(1060), text="", font=("Arial", 20, "bold"), fill="white", state="hidden", tags=("join_label",))
host_label = main.canvas.create_text(main.sx(960), main.sy(1060), text="", font=("Arial", 20, "bold"), fill="white", state="hidden", tags=("host_label",))

def pickup_pile(event=None):
    if main.game_mode != "multi":
        return
    if main.turn != "player":
        return
    if net.has_move(game_id, player_id)["has_move"]:
        return

    result = net.pickup(game_id, player_id)
    if result["success"]:
        state_data = net.state(game_id)
        update_pile(state_data["pile"])
        sync_player_data()

def clear_network_hand():
    for card in main.canvas.find_withtag("p_hand"):
        main.canvas.delete(card)

def sync_player_data():
    global last_hand

    if main.dragging_card is not None:
        return

    player = net.player(game_id, player_id)
    if player["hand"] == last_hand:
        return
    last_hand = player["hand"].copy()

    clear_network_hand()
    clear_network_upcards()
    clear_network_downcards()

    render_network_hand(player["hand"])
    render_network_downcards(player["down_count"])
    render_network_upcards(player["up"])

    for card in main.p_up:
        main.canvas.tag_raise(card)

def create_opponent_displays():
    global opponent_texts
    for i in range(2):
        text = main.canvas.create_text(main.sx(150), main.sy(150 + i * 150), text="", fill="white", font=("Arial", 16))
        opponent_texts.append(text)

def opponent_up_down_slots(base_x, base_y):
    top_y = base_y - 150
    return [
        (main.sx(base_x - 150), main.sy(top_y)),
        (main.sx(base_x), main.sy(top_y)),
        (main.sx(base_x + 150), main.sy(top_y)),]

def render_opponent_upcards(state):
    global opponent_up_cards
    opponents = []

    for obj in opponent_up_cards:
        main.canvas.delete(obj)
    opponent_up_cards.clear()

    for p in state["player_data"]:
        if p["id"] != player_id:
            opponents.append(p)

    for row, p in enumerate(opponents):
        if len(opponents) > 1:
            slots = opponent_up_down_slots(*opp_base_pos[row])
        for col, card in enumerate(p["up"]):
            rank = card["rank"]
            suit = card["suit"]
            img = main.load_card(cards_dict(f"{rank}{suit}"), 5, 5)
            if len(opponents) == 1:
                cid = main.canvas.create_image(main.sx(810 + col * 150), main.sy(150 + row * 150), image=img)
            else:
                x, y = slots[col] if col < len(slots) else slots[-1]
                cid = main.canvas.create_image(x, y, image=img)
            opponent_up_cards.append(cid)
            main.canvas.tag_raise(cid)

def render_opponent_downcards(state):
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
        for col in range(p["down_count"]):
            img = main.load_card(cards_dict("back"), 22, 22)
            if len(opponents) == 1:
                cid = main.canvas.create_image(main.sx(810 + col * 150), main.sy(150 + row * 150), image=img)
            else:
                x, y = slots[col] if col < len(slots) else slots[-1]
                cid = main.canvas.create_image(x, y, image=img)
            opponent_down_cards.append(cid)

def render_opponent_hand(state):
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
            base_x, base_y = opp_base_pos[row]
            start = base_x - (p["hand_count"] - 1) * 20
        for col in range(p["hand_count"]):
            img = main.load_card(cards_dict("back"), 22, 22)
            if len(opponents) == 1:
                cid = main.canvas.create_image(main.sx(750 + col * 60), main.sy(300 + row * 150), image=img)
            else:
                cid = main.canvas.create_image(main.sx(start + col * 40), main.sy(base_y), image=img)
            opponent_hand.append(cid)

def show_setup_phase():
    global setup_text, setup_button
    canvas = main.canvas
    setup_text = canvas.create_text(main.sx(170), main.sy(40), text="Choose 3 up-cards", fill="white", font=("Arial", 24, "bold"))
    setup_button = tk.Button(main.root, text="Confirm Selection", font=("Arial", 16, "bold"), bg="green", fg="white", command=finish_setup)
    canvas.create_window(main.sx(130), main.sy(90), window=setup_button)
    for box in main.upcard_slot_boxes:
        canvas.itemconfigure(box, state="normal")

def update_pile(pile):
    global last_pile_size, pile_image, pile_card_obj

    if len(pile) == last_pile_size:
        return
    last_pile_size = len(pile)

    if not pile:
        if pile_card_obj:
            main.canvas.delete(pile_card_obj)
            pile_card_obj = None
        last_pile_size = 0
        return

    top = pile[-1]
    rank = top["rank"]
    suit = top["suit"]

    pile_image = main.load_card(cards_dict(f"{rank}{suit}"), 5, 5)
    if pile_card_obj:
        main.canvas.delete(pile_card_obj)

    pile_card_obj = main.canvas.create_image(main.pile_pos[0], main.pile_pos[1], image=pile_image)
    main.canvas.tag_bind(pile_card_obj, "<Button-1>", pickup_pile)

def render_network_hand(cards):
    canvas = main.canvas
    for i, card in enumerate(cards):
        rank = card["rank"]
        suit = card["suit"]
        face = main.load_card(cards_dict(f"{rank}{suit}"), 5, 5)
        if main.card_width == 0:
            main.card_width = face.width()
            main.card_height = face.height()
        cid = canvas.create_image(main.sx(750 + i * 60), main.sy(760), image=face, tags=("p_hand",))

        main.card_ranks[cid] = rank
        main.card_values[cid] = main.rank_values[rank]
        main.card_faces[cid] = face
        main.card_suits[cid] = suit
        network_card_lookup[cid] = {"rank": rank, "suit": suit}
    main.reposition_p_hand()

def render_network_upcards(cards):
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

def render_network_deck(deck_count):
    canvas = main.canvas
    img = main.load_card(cards_dict("back"), 22, 22)
    cid = canvas.create_image(main.sx(1150), main.sy(540), image=img, tags=("deck",))

    if deck_count == 0:                             
        canvas.delete(cid)
        return
    canvas.itemconfigure(main.deck_label, text=f"{deck_count}")
    canvas.tag_raise(main.deck_label)

def clear_network_upcards():
    for card in main.canvas.find_withtag("p_up"):
        main.canvas.delete(card)

def render_network_downcards(count):
    canvas = main.canvas
    back = main.load_card(cards_dict("back"), 22, 22)
    for i in range(count):
        canvas.create_image(main.sx(810 + i * 150), main.sy(920), image=back, tags=("p_down",))

def clear_network_downcards():
    for card in main.canvas.find_withtag("p_down"):
        main.canvas.delete(card)
        
def refresh_game():
    global last_player_data

    if not main.session_active:
        return

    canvas = main.canvas
    state_data = net.state(game_id)

    if main.game_mode != "multi":
        return

    if state_data["winner"] is not None:
        main.session_active = False
        show_winner(state_data["winner"])
        return

    if main.state == "waiting_setup":
        ready_count = sum(1 for p in state_data["player_data"] if p["ready"])

        if ready_count == state_data["players"]:
            main.state = "play"
            sync_player_data()

        main.root.after(500, refresh_game)
        return

    if state_data["player_data"] != last_player_data:
        render_opponent_downcards(state_data)
        render_opponent_upcards(state_data)
        render_opponent_hand(state_data)
        render_network_deck(state_data["deck"])

        last_player_data = [
            {
                "id": p["id"],
                "hand_count": p["hand_count"],
                "down_count": p["down_count"],
                "up": p["up"][:]
            }
            for p in state_data["player_data"]
        ]

    update_pile(state_data["pile"])

    if main.turn == "player" and not net.has_move(game_id, player_id)["has_move"]:
        canvas.itemconfigure(main.slot_box_pile, outline="red", width=4)
    else:
        canvas.itemconfigure(main.slot_box_pile, outline="white", width=2)

    sync_player_data()

    if state_data["turn"] == player_id:
        main.turn = "player"
        main.canvas.coords(main.turn_indicator, main.sx(580), main.sy(820), main.sx(600), main.sy(840))
        main.canvas.itemconfigure(main.turn_indicator, state="normal")
    else:
        main.turn = "waiting"
        opponents = [p for p in state_data["player_data"] if p["id"] != player_id]
        for row, p in enumerate(opponents):
            if p["id"] == state_data["turn"]:
                if len(opponents) == 1:
                    main.canvas.coords(main.turn_indicator, main.sx(700), main.sy(240), main.sx(720), main.sy(260))
                elif row == 0:
                    main.canvas.coords(main.turn_indicator, main.sx(180), main.sy(240), main.sx(200), main.sy(260))
                else:
                    main.canvas.coords(main.turn_indicator, main.sx(1380), main.sy(240), main.sx(1400), main.sy(260))
                main.canvas.itemconfigure(main.turn_indicator, state="normal")
                break

    canvas.itemconfigure(main.deck_label, text=f"{state_data['deck']}")
    main.root.after(500, refresh_game)

def show_winner(winner):
    if main.user_var:
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

def finish_setup():
    global setup_button, setup_text
    cards = []

    if len(main.p_up) != 3:
        print("Choose 3 up cards first")
        return

    for cid in main.p_up:
        if cid not in network_card_lookup:
            print("Card missing from lookup:", cid)
            return
        cards.append(network_card_lookup[cid])

    result = net.setup(game_id, player_id, cards)
    if not result["success"]:
        print(result)
        return

    main.state = "waiting_setup"

    for box in main.upcard_slot_boxes:
        main.canvas.itemconfigure(box, state="hidden")
    if setup_button:
        setup_button.destroy()
    if setup_text:
        main.canvas.delete(setup_text)

def refresh_lobby():
    if not main.session_active:
        return
    if not game_id:
        return
    state = net.state(game_id)
    num_players = state["players"]
    if state["started"]:
        start_multiplayer_game()
        return
    main.canvas.itemconfigure("lobby_text", state="hidden")
    main.root.after(1000, refresh_lobby)
    main.canvas.create_text(main.sx(960), main.sy(200), text=f"Players in lobby: {num_players}/3", fill="white", font=("Arial", 24, "bold"), tags="lobby_text")

def start_multiplayer_game():
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

    player = net.player(game_id, player_id)
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
        open_hostgame(self.root, self.canvas)

    def open_joingame(self):
        self.destroy()
        open_joingame(self.root, self.canvas)

    def back(self):
        main.go_home()

class HostScreen:
    def __init__(self, root, canvas):
        self.root = root
        self.canvas = canvas
        self.frame = tk.Frame(root, bg="green")
        self.canvas_window = canvas.create_window(main.sx(960), main.sy(540), window=self.frame)

        tk.Button(self.frame, text="Host Game", font=("Arial", 30, "bold"), bg="white", fg="green", relief="flat", command=self.host_game).pack(pady=10)
        tk.Button(self.frame, text="Start Game",  font=("Arial", 20, "bold"), bg="white", fg="green", relief="flat", command=self.start_game).pack(pady=10)
        tk.Button(self.frame, text="Back", font=("Arial", 10, "bold"), bg="white", fg="green", relief="flat", padx=20, pady=6, command=self.back).pack(pady=(10, 0))

    def host_game(self):
        global game_id, player_id
        main.game_mode = "multi"
        main.session_active = True
        game = net.create()
        game_id = game["game_id"]
        player = net.join(game_id)
        player_id = player["player_id"]
        main.canvas.itemconfigure("host_label", state="normal", text=f"Hosting at: {game_id}")
        refresh_lobby()

    def start_game(self):
        net.start(game_id)
        self.destroy()

    def destroy(self):
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

        tk.Label(self.frame, text="Join Code", font=("Arial", 25, "bold"), bg="green", fg="white").pack()
        entry = self.code_entry = tk.Entry(self.frame, font=("Arial", 25, "bold"))
        entry.pack()
        tk.Button(self.frame, text="Join Game", font=("Arial", 30, "bold"), bg="white", fg="green", relief="flat", command=self.join_game).pack(pady=10)
        tk.Button(self.frame, text="Back", font=("Arial", 10, "bold"), bg="white", fg="green", relief="flat", padx=20, pady=6, command=self.back).pack(pady=(10, 0))

    def join_game(self):
        global game_id, player_id
        main.game_mode = "multi"
        main.session_active = True
        code = self.code_entry.get()
        game_id = code
        player = net.join(game_id)
        player_id = player["player_id"]
        main.canvas.itemconfigure("host_label", state="normal", text=f"Joined: {game_id}")
        refresh_lobby()
        self.destroy()

    def destroy(self):
        self.canvas.delete(self.canvas_window)
        self.frame.destroy()
        self.canvas.itemconfigure("lobby_text", state="hidden")

    def back(self):
        main.go_home()
        self.canvas.itemconfigure("enter_code", state="hidden")

def open_multiplayer_screen(root, canvas):
    global multiplayer_screen
    multiplayer_screen = MultiplayerScreen(root, canvas)

def open_hostgame(root, canvas):
    HostScreen(root, canvas)

def open_joingame(root, canvas):
    JoinScreen(root, canvas)

def reset():
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