#-IMPORTS-----------------------------------------------------------------------------------------------------------------------------------------
from math import log
import tkinter as tk
import random
import os
import sys
import threading
import sqlite3
from dict import cards_dict
import emailer
import accounts

#-TKINTER GAME SETUP------------------------------------------------------------------------------------------------------------------------------  
root = tk.Tk()
root.attributes("-fullscreen", True)
root.title("Palace")
canvas = tk.Canvas(root, bg="green")
canvas.pack(fill=tk.BOTH, expand=True)


#-DEFINING GLOBAL VARIABLES-----------------------------------------------------------------------------------------------------------------------

exit_button = tk.Button(root, text="Exit", font=("Arial", 15, "bold"), bg="grey", fg="white", command=root.destroy)
canvas.create_window(1880, 30, window=exit_button)

suits = ["S", "D", "C", "H"]
ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]

rank_values = {  # Assign a numerical order to ranks for legality checks and bot decisions
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
    "8": 8, "9": 9, "10": 10, "J": 11, "Q": 12, "K": 13, "A": 14,
}

img_mem = {}  # Reuse loaded images instead of reading each card from disk again

card_values = {}
card_ranks = {}
card_faces = {}
card_backs = {}
card_suits = {}

user_var = ""
pass_var = ""
found_login = False

card_width = 0
card_height = 0

screen_w = root.winfo_screenwidth()  # Use the actual monitor dimensions when scaling the game layout
screen_h = root.winfo_screenheight()

base_w = 1920
base_h = 1080

card_scale = min(screen_w / base_w, screen_h / base_h)

def resource_path(relative_path):  # Works both when run normally and when bundled into an executable
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_card(path, card_sub1, card_sub2):  # Use a path-and-scale key so resized card images can be reused
    real_path = resource_path(path)
    cache_key = (real_path, card_sub1, card_sub2)
    if cache_key not in img_mem:
        img_mem[cache_key] = tk.PhotoImage(file=real_path).subsample(card_sub1, card_sub2)
    return img_mem[cache_key]

def sx(x):  # Scale canvas x-coordinates from the original 1920px layout
    return int(x * screen_w / base_w)

def sy(y):  # Scale canvas y-coordinates from the original 1080px layout
    return int(y * screen_h / base_h)

game_mode = "single"
state = "select_up"  # Distinguish choosing upcards, active play and waiting for setup
p_phase = "hand"  # Players use their hand first, then face-up cards, then hidden cards
turn = "player"

p_up = []
p_down = []
pile_cards_list = []

dragging_card = None
selected_group = []  # Keep same-rank cards together when Shift-click dragging
skip_next = False  # An eight causes the following turn to be skipped
current_img = None
drag_offset_x = 0
drag_offset_y = 0

session_active = False

p_up_slots = [(sx(810), sy(920)), (sx(960), sy(920)), (sx(1110), sy(920))]  # Keep the three face-up slots aligned with the hidden cards underneath
p_down_pos = [(sx(810), sy(920)), (sx(960), sy(920)), (sx(1110), sy(920))]
pile_pos = (sx(960), sy(540))
deck_pos = (sx(1400), sy(540))

width_upcard = 120
height_upcard = 180

upcard_slot_boxes = []
for (slotx, sloty) in p_up_slots:  # Create visible guides so players know where to place setup cards
    box = canvas.create_rectangle(
        slotx - width_upcard // 2, sloty - height_upcard // 2,
        slotx + width_upcard // 2, sloty + height_upcard // 2,
        outline="white", width=3, dash=(4, 2), state="hidden"
    )
    upcard_slot_boxes.append(box)

slot_box_pile = canvas.create_rectangle(0, 0, 0, 0, outline="yellow", width=3, tags=("pile",))
canvas.itemconfigure(slot_box_pile, state="hidden")

deck_label = canvas.create_text(sx(1150), sy(540), text="", font=("Arial", 50, "bold"), fill="white", tags=("deck_label",), state="normal")
game_error_label = canvas.create_text(sx(960), sy(650), text="", font=("Arial", 16, "bold"), fill="#ff6666", state="hidden")
game_error_hide_job = None
turn_indicator = canvas.create_oval(0, 0, 20, 20, fill="white", state="hidden")  # Move this indicator next to the player whose turn is active

home_button_widget = None
home_button_window = None

#-MAIN FUNCTIONS--------------------------------------------------------------------------------------------------------------------------------

def make_error_label(frame):
    label = tk.Label(frame, text="", font=("Arial", 12, "bold"), bg="green", fg="#ff6666", wraplength=400, justify="center")
    label.pack(pady=(10, 0))
    return label

def show_error(label, message):
    label.configure(text=message)

def clear_error(label):
    label.configure(text="")

def show_game_error(message, duration_ms=3000):  # Use a delayed callback to hide transient errors automatically
    global game_error_hide_job
    canvas.itemconfigure(game_error_label, text=message, state="normal")
    canvas.tag_raise(game_error_label)
    if game_error_hide_job is not None:  # Cancel the old hide callback so a newer error stays visible
        root.after_cancel(game_error_hide_job)
    game_error_hide_job = root.after(duration_ms, hide_game_error)

def hide_game_error():
    global game_error_hide_job
    canvas.itemconfigure(game_error_label, state="hidden")
    game_error_hide_job = None

def create_rounded_rect(canvas, x1, y1, x2, y2, radius=25, **kwargs):  # Build curved corners from Tkinter shapes
    radius = min(radius, abs(x2 - x1) // 2, abs(y2 - y1) // 2)

    canvas.create_arc(x1, y1, x1 + 2*radius, y1 + 2*radius, start=90, extent=90, style=tk.ARC, **kwargs)
    canvas.create_arc(x2 - 2*radius, y1, x2, y1 + 2*radius, start=0, extent=90, style=tk.ARC, **kwargs)
    canvas.create_arc(x2 - 2*radius, y2 - 2*radius, x2, y2, start=270, extent=90, style=tk.ARC, **kwargs)
    canvas.create_arc(x1, y2 - 2*radius, x1 + 2*radius, y2, start=180, extent=90, style=tk.ARC, **kwargs)

    canvas.create_rectangle(x1 + radius, y1, x2 - radius, y2, **kwargs)
    canvas.create_rectangle(x1, y1 + radius, x2, y2 - radius, **kwargs)

def check_login(user_var, pass_var):  # Keep the login screen separate from the database authentication logic
    global found_login
    found_login = accounts.check_login(user_var, pass_var)

def get_p_hand():  # Use the canvas tag to find the cards currently in the player hand
    return list(canvas.find_withtag("p_hand"))

def reposition_p_hand():  # Spread cards horizontally based on the current hand size
    if p_phase != "hand":
        return
    hand = get_p_hand()
    if not hand:
        return
    random.shuffle(hand)  # Shuffle the order before laying out cards again
    start = 960 - (len(hand) - 1) * 20  # Shift the first card left as the hand grows to keep it centred
    for i, card in enumerate(hand):
        canvas.coords(card, sx(start + i * 40), sy(760))
        canvas.tag_raise(card)

def reposition_p_up():
    for i, card in enumerate(p_up):
        canvas.coords(card, *p_up_slots[i])

def reposition_p_down():
    for i, card in enumerate(p_down):
        canvas.coords(card, *p_down_pos[i])

def snap_back(cid):  # Return a rejected drag to its original card area
    tags = canvas.gettags(cid)
    if "p_hand" in tags:
        reposition_p_hand()
    elif "p_up" in tags:
        reposition_p_up()
    elif "p_down" in tags:
        reposition_p_down()

def top_effective_pile():  # An empty pile has no rank restriction for the next card
    if pile_cards_list:
        return pile_cards_list[-1]
    else:
        return None

def can_play(cid):  # Apply Palace rank restrictions and the special-card rules
    r = card_ranks[cid]
    v = card_values[cid]
    if r in ("2", "10"):  # Twos and tens can be played on any rank
        return True
    top = top_effective_pile()
    if top is None:
        return True
    if card_ranks[top] == "2":  # After a two, any rank may be played
        return True
    if card_ranks[top] == "7":  # A seven reverses the normal rank requirement
        return v <= card_values[top]
    return v >= card_values[top]  # Otherwise the next card cannot be lower than the top card

def check_four_of_kind():  # Only the latest four cards count toward a four-of-a-kind burn
    if len(pile_cards_list) < 4:
        return False
    last4 = pile_cards_list[-4:]
    ranks4 = []
    for card in last4:
        ranks4.append(card_ranks[card])
    return len(set(ranks4)) == 1  # A set of size one means all four ranks are identical

def burn_pile():  # Remove the whole pile when a ten or four equal ranks trigger a burn
    global pile_cards_list
    for card in pile_cards_list:
        canvas.delete(card)
    pile_cards_list = []

def update_p_phase():  # Move through the hand, face-up and face-down phases
    global p_phase
    if p_phase == "hand" and not get_p_hand() and not singleplayer.deck_cards:  # Face-up cards become available only after both hand and deck are empty
        p_phase = "up"
    if p_phase == "up" and not p_up:
        p_phase = "down"

#-HOME BUTTON LOGIC---------------------------------------------------------------------------------------------------------------------------

def show_home_button():
    global home_button_widget, home_button_window
    hide_home_button()
    home_button_widget = tk.Button(root, text="Home", font=("Arial", 14, "bold"), bg="white", fg="green", relief="flat", padx=12, pady=4, command=confirm_go_home,)
    home_button_window = canvas.create_window(sx(70), sy(1040), window=home_button_widget)

def hide_home_button():
    global home_button_widget, home_button_window
    if home_button_window is not None:
        canvas.delete(home_button_window)
        home_button_window = None
    if home_button_widget is not None:
        home_button_widget.destroy()
        home_button_widget = None

def confirm_go_home():
    ConfirmHome(root, canvas)

class ConfirmHome:
    def __init__(self, root, canvas):
        self.canvas = canvas
        self.frame = tk.Frame(root, bg="black", highlightbackground="white", highlightthickness=2)
        self.window = canvas.create_window(sx(960), sy(540), window=self.frame)

        tk.Label(self.frame, text="Are you sure?", font=("Arial", 26, "bold"), bg="black", fg="white").pack(padx=50, pady=(25, 10))
        tk.Label(self.frame, text="You'll leave this game and return to the home screen.", font=("Arial", 12), bg="black", fg="white").pack(padx=30, pady=(0, 15))

        btn_frame = tk.Frame(self.frame, bg="black")
        btn_frame.pack(pady=(0, 20))
        tk.Button(btn_frame, text="Yes", font=("Arial", 16, "bold"), bg="white", fg="darkgreen", relief="flat", padx=20, pady=6, command=self.confirm).pack(side="left", padx=10)
        tk.Button(btn_frame, text="No", font=("Arial", 16, "bold"), bg="white", fg="darkred", relief="flat", padx=20, pady=6, command=self.cancel).pack(side="left", padx=10)

    def confirm(self):
        self.canvas.delete(self.window)
        self.frame.destroy()
        go_home()

    def cancel(self):
        self.canvas.delete(self.window)
        self.frame.destroy()


def go_home():  # Reset the canvas, game data and event bindings before returning home
    global game_mode, state, p_phase, turn, card_width, card_height, game_error_hide_job
    global skip_next, selected_group, current_img, dragging_card, session_active, turn_indicator

    session_active = False  # Stop pending game callbacks from continuing after leaving a match
    hide_home_button()

    canvas.unbind("<ButtonPress-1>")  # Remove game-specific mouse controls before showing the main menu
    canvas.unbind("<B1-Motion>")
    canvas.unbind("<ButtonRelease-1>")

    singleplayer.reset()
    multiplayer.reset()

    for tag in ("p_hand", "p_up", "p_down", "pile", "deck", "win_overlay", "lobby_text"):  # Clear items by game tag while retaining the pile target rectangle
        for item in canvas.find_withtag(tag):
            if item == slot_box_pile:
                continue
            canvas.delete(item)

    for box in upcard_slot_boxes:
        canvas.itemconfigure(box, state="hidden")
    canvas.itemconfigure(slot_box_pile, state="hidden")
    canvas.itemconfigure(deck_label, state="hidden", text="")

    if game_error_hide_job is not None:  # Prevent a scheduled error callback from affecting the new screen
        root.after_cancel(game_error_hide_job)
        game_error_hide_job = None
    canvas.itemconfigure(game_error_label, state="hidden")

    p_up.clear()  # Clear cards from the previous session before another game begins
    p_down.clear()
    pile_cards_list.clear()
    card_values.clear()
    card_ranks.clear()
    card_faces.clear()
    card_backs.clear()
    card_suits.clear()

    game_mode = "single"
    state = "select_up"
    p_phase = "hand"
    turn = "player"
    card_width = 0
    card_height = 0
    skip_next = False
    selected_group = []
    current_img = None
    dragging_card = None

    canvas.itemconfigure("join_label", state="hidden")
    canvas.itemconfigure("host_label", state="hidden")
    canvas.itemconfigure("turn_indicator", state="hidden")

    StartScreen(root, canvas)


#-DRAG LOGIC--------------------------------------------------------------------------------------------------------------------------------------------


def start_drag(event):  # Only grab a visible card from the currently playable area
    global current_img, drag_offset_x, drag_offset_y, selected_group, dragging_card

    if state == "select_up":
        allowed_tag = "p_hand"
    else:
        if turn != "player":
            return
        allowed_tag = {"hand": "p_hand", "up": "p_up", "down": "p_down"}.get(p_phase)

    if not allowed_tag:
        return

    # Use the uppermost card actually beneath the cursor. find_closest() can
    # select a neighbouring, overlapped card that has a different (illegal) rank.
    cid = None
    overlapping_items = canvas.find_overlapping(event.x, event.y, event.x, event.y)
    for item in reversed(overlapping_items):
        if allowed_tag in canvas.gettags(item) and canvas.itemcget(item, "state") != "hidden":
            cid = item
            break
    if cid is None:
        return

    dragging_card = cid
    tags = canvas.gettags(cid)
    if state == "select_up":
        for box in upcard_slot_boxes:
            canvas.itemconfigure(box, state="normal")

    # Face-down cards must be played blindly, even when Shift is held.
    if event.state & 0x0001 and p_phase != "down" and state != "select_up":
        rank = card_ranks[cid]
        if "p_hand" in tags:
            source_cards = get_p_hand()
        else:
            source_cards = p_up
        selected_group = []
        for card in source_cards:
            if card_ranks.get(card) == rank:
                selected_group.append(card)
        for card in selected_group:
            canvas.tag_raise(card)
    else:
        selected_group = [cid]

    current_img = cid
    x, y = canvas.coords(cid)
    drag_offset_x = x - event.x
    drag_offset_y = y - event.y

    if state == "play":
        if game_mode == "single":
            singleplayer.update_pile_border()  # Border only while a card is selected
        else:
            canvas.itemconfigure(slot_box_pile, state="normal")

def do_drag(event):
    if current_img:
        for card in selected_group:
            canvas.coords(card, event.x + drag_offset_x, event.y + drag_offset_y)

def _end_drag_inner(event):  # Choose between setup, playing a card and returning it on release
    global current_img, state, turn, p_phase, selected_group, dragging_card

    if not current_img:
        return

    cid = current_img

    if state == "select_up":
        x, y = canvas.coords(cid)
        placed = False

        if len(p_up) < 3:  # A setup selection is valid only while fewer than three cards are face-up
            for i, (slotx, sloty) in enumerate(p_up_slots):
                if abs(x - slotx) <= width_upcard // 2 and abs(y - sloty) <= height_upcard // 2:  # Use rectangular hit-testing around each face-up card slot
                    if cid in get_p_hand():
                        canvas.itemconfigure(cid, tags=("p_up",))
                        p_up.append(cid)
                        reposition_p_up()
                        for card in p_up:
                            canvas.tag_raise(card)
                        reposition_p_hand()
                        placed = True
                    break

        if not placed:  # Return the card to the hand if it missed every face-up slot
            reposition_p_hand()

        if len(p_up) == 3:  # The game begins only after exactly three face-up cards are selected
            if game_mode == "single":
                singleplayer.bot_choose_upcards()
                state = "play"
                canvas.itemconfigure(slot_box_pile, state="hidden")  # No outline until dragging
            else:
                state = "waiting_setup"  # Wait for the server to confirm all multiplayer players are ready


        for box in upcard_slot_boxes:
            canvas.itemconfigure(box, state="hidden")
        current_img = None
        selected_group = []
        dragging_card = None
        return

    if game_mode == "multi" and p_phase == "down":  # Hidden multiplayer cards are played blindly by the server
        for box in upcard_slot_boxes:
            canvas.itemconfigure(box, state="hidden")
        canvas.itemconfigure(slot_box_pile, state="hidden")

        result = multiplayer.net.play_down(multiplayer.game_id, multiplayer.player_id)  # The server decides whether the unseen card is a legal play

        if "success" not in result:
            show_game_error(result.get("error", "Network error. Please try again."))
        else:
            down_cards = canvas.find_withtag("p_down")  # Remove the local hidden-card image after the server handles the play
            if down_cards:
                canvas.delete(down_cards[-1])

            if not result["success"]:
                show_game_error(result.get("error", "Couldn't play that card. Please try again."))
                p_phase = "hand"  # An invalid hidden play sends the player back to their hand

        current_img = None
        selected_group = []
        dragging_card = None
        return

    cx, cy = canvas.coords(cid)  # Read the released card position before checking the pile drop area
    in_pile = (  # Treat the drag as a play only when released over the pile
        abs(cx - pile_pos[0]) <= card_width // 2 and
        abs(cy - pile_pos[1]) <= card_height // 2
    )

    if in_pile:
        if not selected_group:
            return

        all_cards_legal = True
        if game_mode == "single":
            for card in selected_group:
                if not can_play(card):
                    all_cards_legal = False
                    break

        if game_mode == "single" and not all_cards_legal:
            if p_phase == "down":
                # A blind face-down attempt is the only illegal card play that
                # should collect the pile: its value was unknown when selected.
                for card in selected_group:
                    if card in p_down:
                        p_down.remove(card)
                    canvas.itemconfigure(card, image=card_faces[card])
                    pile_cards_list.append(card)
                singleplayer.pick_up_pile_player()
            else:
                # Incorrect visible cards are simply rejected. The player can
                # try a different card, or click the pile when no legal move exists.
                for card in selected_group:
                    snap_back(card)
            current_img = None
            selected_group = []
            dragging_card = None
            return

        if game_mode == "multi":  # Multiplayer moves must be validated by the shared server state
            cards_load = []
            for card in selected_group:
                cards_load.append(multiplayer.network_card_lookup[card])  # Convert local canvas IDs into server card data
            result = multiplayer.net.play(multiplayer.game_id, multiplayer.player_id, cards_load)

            if result.get("success"):  # Only remove local card images after the multiplayer server accepts the move
                for played_card in selected_group:
                    t = canvas.gettags(played_card)
                    if "p_down" in t and played_card in p_down:
                        canvas.itemconfigure(played_card, image=card_faces[played_card])
                        p_down.remove(played_card)
                    elif "p_up" in t and played_card in p_up:
                        p_up.remove(played_card)

                    canvas.itemconfigure(played_card, tags=("p_played",))
                    canvas.delete(played_card)
                    multiplayer.network_card_lookup.pop(played_card, None)  # Discard the card-to-server mapping once the played image no longer exists
                    card_ranks.pop(played_card, None)
                    card_values.pop(played_card, None)
                    card_faces.pop(played_card, None)

                update_p_phase()
                reposition_p_hand()
            else:  # If the server rejects the move, restore the original card positions
                show_game_error(result.get("error", "Couldn't play that card. Please try again."))
                for played_card in selected_group:
                    snap_back(played_card)
                current_img = None
                selected_group = []
                dragging_card = None
                return
        else:
            burned = False
            for card in selected_group:  # Singleplayer applies the card movement locally without a server request
                t = canvas.gettags(card)
                if "p_down" in t and card in p_down:
                    p_down.remove(card)
                elif "p_up" in t and card in p_up:
                    p_up.remove(card)
            for card in selected_group:
                burned = singleplayer.play_to_pile(card, True) or burned

        update_p_phase()

        if game_mode == "single":
            if singleplayer.check_win():
                canvas.itemconfigure(slot_box_pile, state="hidden")
                current_img = None
                selected_group = []
                dragging_card = None
                return
            if not burned:
                singleplayer.next_bot_turn()  # A burn keeps the player's turn
    else:
        for card in selected_group:
            snap_back(card)

    for box in upcard_slot_boxes:
        canvas.itemconfigure(box, state="hidden")
    canvas.itemconfigure(slot_box_pile, state="hidden")

    current_img = None  # Clear temporary drag data so the next click starts a fresh selection
    selected_group = []
    dragging_card = None

def end_drag(event):  # Always hide the drop outline when dragging stops
    global current_img, state, turn, p_phase, selected_group, dragging_card
    try:
        _end_drag_inner(event)
    except Exception as e:
        print("end_drag() error (continuing anyway):", e)
        show_game_error("Something went wrong with that move. Please try again.")
        for card in selected_group:
            snap_back(card)
        current_img = None
        selected_group = []
        dragging_card = None
        for box in upcard_slot_boxes:
            canvas.itemconfigure(box, state="hidden")
    finally:
        canvas.itemconfigure(slot_box_pile, state="hidden")

#-WIN SCREEN-------------------------------------------------------------------------------------------------------------------------------------------------------

class winScreen:
    def __init__(self, root, canvas, win):
        self.root = root
        self.canvas = canvas
        hide_home_button()
        self.frame = tk.Frame(root, bg="darkgreen")
        self.canvas_window = canvas.create_window(sx(960), sy(540), window=self.frame)
        self.canvas.create_rectangle(sx(0), sy(0), sx(1920), sy(1080), fill="darkgreen", tags=("win_overlay",))

        if win:
            text = "You Win!"
        else:
            text = "You Lose!"
        tk.Label(self.frame, text=text, font=("Arial", 80, "bold"), bg="darkgreen", fg="white").pack(pady=(0, 10))
        tk.Button(self.frame, text="Exit", font=("Arial", 30, "bold"), bg="white", fg="darkgreen", relief="flat", padx=30, pady=10, command=root.destroy).pack()
        tk.Button(self.frame, text="Home", font=("Arial", 30, "bold"), bg="white", fg="darkgreen", relief="flat", padx=30, pady=10, command=self.go_home).pack(pady=(10, 0))

    def go_home(self):
        self.canvas.delete(self.canvas_window)
        self.canvas.delete("win_overlay")
        self.frame.destroy()
        go_home()

class InfoScreen:
    def __init__(self, canvas, start_screen):
        self.canvas = canvas
        self.start_screen = start_screen
        self.frame = tk.Frame(canvas, bg="green")
        self.window = canvas.create_window(sx(960), sy(540), window=self.frame)

        tk.Label(self.frame, text="Instructions", font=("Arial", 50, "bold"), bg="green", fg="white").pack(pady=20)

        basics_text = (
            "Welcome to Palace! The objective of the game is to be the first player to get rid of all your cards."
            "\n"
            "\nYou are given 3 down-cards and 6 cards at the start of the game."
            "\nYou can choose 3 of your hand cards to place face-up on top of the down-cards. These will be revealed once you have played all your hand cards."
            "\n"
            "\nYou can only play cards that are equal to or higher than the top card of the pile, except for 2s and 10s which can be played on any card."
            "\nIf you play a 7, the next player must play a card 7 or lower. If you play a 10, the pile is burned and removed from the game."
            "\nIf four cards of the same rank are played in a row, the pile is also burned."
            "\nIf you play an 8, you skip your opponent's turn."
            "\n"
            "\nIf you cannot play a card, you must pick up the entire pile and add it to your hand."
            "\nYou must also maintain at least 3 cards in your hand if there are cards left in the deck."
            "\nIf you have less than 3 cards in your hand, you must draw from the deck until you have 3 cards or the deck is empty."
            "\n"
            "\nOnce the deck is empty and you have no cards in your hand, you must play your face-up cards."
            "\nOnce those are gone, you must play your face-down cards blindly. If you cannot play a card at any point, you pick up."
            "\nOnce you have no cards left, you win the game!"
        )

        tk.Label(self.frame, text=basics_text, font=("Arial", 12), bg="green", fg="white", justify="center").pack(pady=10)
        tk.Label(self.frame, text="Controls", font=("Arial", 50, "bold"), bg="green", fg="white").pack(pady=20)

        controls_text = (
            "To play a card, click and drag it onto the pile in the center of the screen. You can only play cards that are legal according to the game rules."
            "\nIf you want to play multiple cards of the same rank, hold the Shift key while clicking to select all cards of that rank in your hand. Then drag any one of them to the pile to play them all together."
            "\nIf you try to play an illegal card, it will snap back to its original position."
            "\nIf you cannot play any card, you must pick up the pile instead."
            "\n"
            "\nTo select your face-up cards at the start of the game, drag them from your hand to the three slots above your down-cards."
            "\nYou must select exactly 3 cards to place face-up."
            "\nYou can only interact with your hand cards during the hand phase, your face-up cards during the up phase, and your face-down cards during the down phase."
            "\n"
            "\nThe bots will automatically take their turns. Focus on playing strategically to beat them."
            "\n"
            "\nYou can view the number of cards in the pile and the deck at any time using the labels in the top left corner."
            "\n"
            "\nPress 'Play' to choose the number of bots to play against, and start the game!"
            "\n"
            "\nHave fun playing Palace and good luck! :)"
        )

        tk.Label(self.frame, text=controls_text, font=("Arial", 12), bg="green", fg="white", justify="center").pack(pady=10)
        tk.Button(self.frame, text="Back", font=("Arial", 25, "bold"), bg="white", fg="green", relief="flat", padx=30, pady=10, command=self.close).pack(pady=20)

    def close(self):
        self.start_screen.canvas.itemconfigure(self.start_screen.canvas_window, state="normal")
        self.frame.destroy()

class LeaderboardScreen:
    def __init__(self, canvas, start_screen):
        self.canvas = canvas
        self.start_screen = start_screen
        self.frame = tk.Frame(canvas, bg="green")
        self.window = canvas.create_window(sx(960), sy(540), window=self.frame)

        tk.Label(self.frame, text="Leaderboard", font=("Arial", 50, "bold"), bg="green", fg="white").pack(pady=(0, 20))

        rows_frame = tk.Frame(self.frame, bg="green")
        rows_frame.pack(pady=(0, 20))

        standings = accounts.get_leaderboard()  # Get the database results already ordered by rating

        header = tk.Frame(rows_frame, bg="green")
        header.pack(fill="x")
        tk.Label(header, text="Rank", font=("Arial", 16, "bold"), bg="green", fg="white", width=6, anchor="w").pack(side="left")
        tk.Label(header, text="Player", font=("Arial", 16, "bold"), bg="green", fg="white", width=20, anchor="w").pack(side="left")
        tk.Label(header, text="ELO", font=("Arial", 16, "bold"), bg="green", fg="white", width=8, anchor="e").pack(side="left")

        for rank, (username, elo) in enumerate(standings, start=1):  # Number each row after the database has sorted the players
            row = tk.Frame(rows_frame, bg="green")
            row.pack(fill="x")
            if username == user_var:
                fg = "yellow"
            else:
                fg = "white"
            tk.Label(row, text=str(rank), font=("Arial", 14), bg="green", fg=fg, width=6, anchor="w").pack(side="left")
            tk.Label(row, text=username, font=("Arial", 14), bg="green", fg=fg, width=20, anchor="w").pack(side="left")
            tk.Label(row, text=str(elo), font=("Arial", 14), bg="green", fg=fg, width=8, anchor="e").pack(side="left")

        tk.Button(self.frame, text="Back", font=("Arial", 25, "bold"), bg="white", fg="green", relief="flat", padx=30, pady=10, command=self.close).pack(pady=10)

    def close(self):
        self.start_screen.canvas.itemconfigure(self.start_screen.canvas_window, state="normal")
        self.frame.destroy()
        
class StartScreen:
    def __init__(self, root, canvas):
        global user_var
        self.root = root
        self.canvas = canvas
        self.frame = tk.Frame(root, bg="green")
        self.canvas_window = canvas.create_window(sx(960), sy(540), window=self.frame)

        self.canvas.create_rectangle(sx(10), sy(10), sx(200), sy(62), fill="darkgreen", outline="darkgreen")
        tk.Label(canvas, text=f"Logged in as: {user_var}", font=("Arial", 11, "bold"), bg="darkgreen", fg="white").place(x=sx(70), y=sy(12), anchor="n")
        tk.Label(canvas, text=f"Elo: {str(accounts.get_elo(user_var))}", font=("Arial", 11, "bold"), bg="darkgreen", fg="white").place(x=sx(48), y=sy(35), anchor="n")

        tk.Label(self.frame, text="Palace", font=("Arial", 80, "bold"), bg="green", fg="white").pack(pady=(0, 10))
        tk.Button(self.frame, text="Single Player", font=("Arial", 30, "bold"), bg="white", fg="green", relief="flat", padx=30, pady=10, command=self.open_singleplayer).pack()
        tk.Button(self.frame, text="Multiplayer", font=("Arial", 30, "bold"), bg="white", fg="green", relief="flat", padx=30, pady=10, command=self.open_multiplayer).pack(pady=20)
        canvas.itemconfigure(deck_label, state="hidden")
        tk.Button(self.frame, text="Information", font=("Arial", 25, "bold"), bg="white", fg="green", relief="flat", padx=30, pady=10, command=self.show_info).pack(pady=20)
        tk.Button(self.frame, text="Leaderboard", font=("Arial", 25, "bold"), bg="white", fg="green", relief="flat", padx=30, pady=10, command=self.show_leaderboard).pack()

        if user_var == "admin":  # Only display the email controls when the admin account is logged in
            tk.Button(self.frame, text="Email Players", font=("Arial", 16, "bold"), bg="white", fg="green", relief="flat", padx=20, pady=8, command=self.send_emails).pack(pady=(20, 0))
            self.email_status = tk.Label(self.frame, text="", font=("Arial", 10, "bold"), bg="green", fg="white")
            self.email_status.pack(pady=(5, 0))

    def show_info(self):
        self.canvas.itemconfigure(self.canvas_window, state="hidden")
        InfoScreen(self.canvas, self)

    def show_leaderboard(self):
        self.canvas.itemconfigure(self.canvas_window, state="hidden")
        LeaderboardScreen(self.canvas, self)

    def destroy(self):
        self.canvas.delete(self.canvas_window)
        self.frame.destroy()

    def open_singleplayer(self):
        self.destroy()
        singleplayer.open_singleplayer_settings(self.root, self.canvas)

    def open_multiplayer(self):
        self.destroy()
        multiplayer.open_multiplayer_screen(self.root, self.canvas)

    def send_emails(self):  # Send the newsletter outside the Tkinter GUI thread
        self.email_status.config(text="Sending...")
        threading.Thread(target=self._send_emails_worker, daemon=True).start()  # A daemon thread prevents email delivery from freezing the interface

    def _send_emails_worker(self):
        sent = []
        failed = []
        text = ""

        standings = accounts.get_leaderboard()
        for accounts.rank, (accounts.username, accounts.elo) in enumerate(standings, start=1):  # Build leaderboard rows ordered by the database ELO results
            text += f"\n{str(accounts.rank)}       {accounts.username}        {str(accounts.elo)}"

        def on_result(address, success, error):
            if success:
                sent.append(address)
            else:
                failed.append((address, error))

        addresses = emailer.send_to_all(
            subject="Palace Weekly Update",
            body=
            "Hi! Here's your weekly Palace update. Thanks for playing!"
            "\nRANK        USERNAME       ELO"
            f"\n{text}",
            on_result=on_result,
        )

        self.root.after(0, lambda: self._report_email_result(addresses, sent, failed))  # Tkinter widget updates must happen on the main event loop

    def _report_email_result(self, addresses, sent, failed):
        if not addresses:
            self.email_status.config(text="No email addresses found in database")
        elif failed:
            self.email_status.config(text=f"Sent to {len(sent)}, failed for {len(failed)}")
            print("Failed sends:", failed)
        else:
            self.email_status.config(text=f"Sent to {len(sent)} player(s)!")

class LoginScreen:
    def __init__(self, root, canvas):
        self.root = root
        self.canvas = canvas
        self.frame = tk.Frame(root, bg="green")
        self.canvas_window = canvas.create_window(sx(960), sy(540), window=self.frame)

        tk.Label(self.frame, text="Palace", font=("Arial", 80, "bold"), bg="green", fg="white").pack(pady=(0, 10), anchor="n")
        tk.Label(self.frame, text="Login", font=("Arial", 50, "bold"), bg="green", fg="white").pack(pady=(0, 60), anchor="n")

        tk.Label(self.frame, text="Username", font=("Arial", 20, "bold"), bg="green", fg="white").pack(pady=(0, 2))
        self.user_entry = tk.Entry(self.frame, font=("Arial", 25, "bold"))
        self.user_entry.pack(pady=(0, 2))

        tk.Label(self.frame, text="Password", font=("Arial", 20, "bold"), bg="green", fg="white").pack(pady=(0, 2))
        self.pass_entry = tk.Entry(self.frame, font=("Arial", 25, "bold"), show="*")
        self.pass_entry.pack(pady=(0, 10))

        tk.Button(self.frame, text = "Submit", font=("Arial", 20, "bold"), bg="green", fg="white", command = self.submit).pack(pady=(0, 30))

        tk.Label(self.frame, text="Don't have an account? Create one.", font=("Arial", 10, "bold"), bg="green", fg="white").pack(pady=(0, 10))
        tk.Button(self.frame, text = "Create Account", font=("Arial", 10, "bold"), bg="green", fg="white", command = self.open_createaccount).pack(pady=(0, 30))

    def submit(self):  # Read the two login fields before checking them against saved credentials
        global user_var, pass_var
        user_var = self.user_entry.get()
        pass_var = self.pass_entry.get()
        check_login(user_var, pass_var)
        self.destroy()

    def open_createaccount(self):
        self.canvas.delete(self.canvas_window)
        self.frame.destroy()
        CreateAccountScreen(self.root, self.canvas)

    def destroy(self):
        global found_login
        if found_login == True:  # Open the main menu only when the account check succeeded
            self.canvas.delete(self.canvas_window)
            self.frame.destroy()
            StartScreen(self.root, self.canvas)
        else:
            tk.Label(self.frame, text="Invalid username or password", font=("Arial", 10, "bold"), bg="green", fg="red").pack(pady=(0, 10))
            
class CreateAccountScreen:
    def __init__(self, root, canvas):
        self.root = root
        self.canvas = canvas
        self.frame = tk.Frame(root, bg="green")
        self.canvas_window = canvas.create_window(sx(960), sy(540), window=self.frame)

        tk.Label(self.frame, text="Palace", font=("Arial", 80, "bold"), bg="green", fg="white").pack(pady=(0, 10), anchor="n")
        tk.Label(self.frame, text="Create Account", font=("Arial", 50, "bold"), bg="green", fg="white").pack(pady=(0, 60), anchor="n")

        tk.Label(self.frame, text="Username", font=("Arial", 20, "bold"), bg="green", fg="white").pack(pady=(0, 2))
        self.user_entry = tk.Entry(self.frame, font=("Arial", 25, "bold"))
        self.user_entry.pack(pady=(0, 2))

        tk.Label(self.frame, text="Email", font=("Arial", 20, "bold"), bg="green", fg="white").pack(pady=(0, 2))
        self.email_entry = tk.Entry(self.frame, font=("Arial", 25, "bold"))
        self.email_entry.pack(pady=(0, 4))

        self.email_opt_in = tk.BooleanVar(value=False)  # Email updates are optional and off by default
        tk.Checkbutton(
            self.frame,
            text="Email me weekly leaderboard updates",
            variable=self.email_opt_in,
            font=("Arial", 11, "bold"),
            bg="green", fg="white", selectcolor="green",
            activebackground="green", activeforeground="white",
        ).pack(pady=(0, 12))

        tk.Label(self.frame, text="Password", font=("Arial", 20, "bold"), bg="green", fg="white").pack(pady=(0, 2))
        self.pass_entry = tk.Entry(self.frame, font=("Arial", 25, "bold"), show="*")
        self.pass_entry.pack(pady=(0, 10))

        self.error_label = tk.Label(self.frame, text="", font=("Arial", 11, "bold"), bg="green", fg="red")
        self.error_label.pack(pady=(0, 5))
        tk.Button(self.frame, text="Submit", font=("Arial", 20, "bold"), bg="green", fg="white", command=self.submit).pack(pady=(0, 30))

    def submit(self):
        username = self.user_entry.get().strip()
        password = self.pass_entry.get()
        email = self.email_entry.get().strip()
        opted_in = self.email_opt_in.get()

        if not username or not password:
            self.error_label.config(text="Please enter a username and password")
            return
        if opted_in and (not email or "@" not in email or "." not in email.split("@")[-1]):
            self.error_label.config(text="Please enter a valid email address to receive updates")
            return

        try:
            accounts.create_account(username, password, email=email or None, email_opt_in=opted_in)
        except sqlite3.IntegrityError:
            self.error_label.config(text="This username is already registered")
            return
        except (ValueError, sqlite3.Error):
            self.error_label.config(text="Could not create account. Please try again")
            return

        self.destroy()

    def destroy(self):
        self.canvas.delete(self.canvas_window)
        self.frame.destroy()
        LoginScreen(self.root, self.canvas)

import singleplayer
import multiplayer

LoginScreen(root, canvas)
root.mainloop()