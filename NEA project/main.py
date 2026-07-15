from math import log
import tkinter as tk
import random
import os
import sys
import threading
from dict import cards_dict
import emailer
import accounts
  
root = tk.Tk()
root.attributes("-fullscreen", True)
root.title("Palace")
canvas = tk.Canvas(root, bg="green")
canvas.pack(fill=tk.BOTH, expand=True)

exit_button = tk.Button(root, text="Exit", font=("Arial", 15, "bold"), bg="grey", fg="white", command=root.destroy)
canvas.create_window(1880, 30, window=exit_button)

suits = ["S", "D", "C", "H"]
ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]

rank_values = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
    "8": 8, "9": 9, "10": 10, "J": 11, "Q": 12, "K": 13, "A": 14,
}

img_mem = {}

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

screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()

base_w = 1920
base_h = 1080

card_scale = min(screen_w / base_w, screen_h / base_h)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_card(path, card_sub1, card_sub2):
    real_path = resource_path(path)
    if real_path not in img_mem:
        img_mem[real_path] = tk.PhotoImage(file=real_path).subsample(card_sub1, card_sub2)
    return img_mem[real_path]

def sx(x):
    return int(x * screen_w / base_w)

def sy(y):
    return int(y * screen_h / base_h)

game_mode = "single"   
state = "select_up"   
p_phase = "hand"       
turn = "player"         

p_up = []
p_down = []
pile_cards_list = []

dragging_card = None
selected_group = []
skip_next = False
current_img = None
drag_offset_x = 0
drag_offset_y = 0

session_active = False

p_up_slots = [(sx(810), sy(920)), (sx(960), sy(920)), (sx(1110), sy(920))]
p_down_pos = [(sx(810), sy(920)), (sx(960), sy(920)), (sx(1110), sy(920))]
pile_pos = (sx(960), sy(540))
deck_pos = (sx(1400), sy(540))

width_upcard = 120
height_upcard = 180

upcard_slot_boxes = []
for (slotx, sloty) in p_up_slots:
    box = canvas.create_rectangle(
        slotx - width_upcard // 2, sloty - height_upcard // 2,
        slotx + width_upcard // 2, sloty + height_upcard // 2,
        outline="white", width=3, dash=(4, 2), state="hidden"
    )
    upcard_slot_boxes.append(box)

slot_box_pile = canvas.create_rectangle(0, 0, 0, 0, outline="yellow", width=3, tags=("pile",))
canvas.itemconfigure(slot_box_pile, state="hidden")

deck_label = canvas.create_text(sx(1150), sy(540), text="", font=("Arial", 50, "bold"), fill="white", tags=("deck_label",), state="normal")

home_button_widget = None
home_button_window = None

def check_login(user_var, pass_var):
    global found_login
    found_login = accounts.check_login(user_var, pass_var)

def get_p_hand():
    return list(canvas.find_withtag("p_hand"))

def reposition_p_hand():
    if p_phase != "hand":
        return
    hand = get_p_hand()
    if not hand:
        return
    random.shuffle(hand)
    start = 960 - (len(hand) - 1) * 20
    for i, card in enumerate(hand):
        canvas.coords(card, sx(start + i * 40), sy(760))
        canvas.tag_raise(card)

def reposition_p_up():
    for i, card in enumerate(p_up):
        canvas.coords(card, *p_up_slots[i])

def reposition_p_down():
    for i, card in enumerate(p_down):
        canvas.coords(card, *p_down_pos[i])

def snap_back(cid):
    tags = canvas.gettags(cid)
    if "p_hand" in tags:
        reposition_p_hand()
    elif "p_up" in tags:
        reposition_p_up()
    elif "p_down" in tags:
        reposition_p_down()

def top_effective_pile():
    return pile_cards_list[-1] if pile_cards_list else None

def can_play(cid):
    r = card_ranks[cid]
    v = card_values[cid]
    if r in ("2", "10"):
        return True
    top = top_effective_pile()
    if top is None:
        return True
    if card_ranks[top] == "2":
        return True
    if card_ranks[top] == "7":
        return v <= card_values[top]
    return v >= card_values[top]

def check_four_of_kind():
    if len(pile_cards_list) < 4:
        return False
    last4 = pile_cards_list[-4:]
    ranks4 = [card_ranks[card] for card in last4]  
    return len(set(ranks4)) == 1

def burn_pile():
    global pile_cards_list
    for card in pile_cards_list:
        canvas.delete(card)
    pile_cards_list = []

def update_p_phase():
    global p_phase
    if p_phase == "hand" and not get_p_hand() and not singleplayer.deck_cards:
        p_phase = "up"
    if p_phase == "up" and not p_up:
        p_phase = "down"

def show_home_button():
    global home_button_widget, home_button_window
    hide_home_button()
    home_button_widget = tk.Button(
        root, text="Home", font=("Arial", 14, "bold"),
        bg="white", fg="green", relief="flat", padx=12, pady=4,
        command=confirm_go_home,
    )
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


def go_home():
    global game_mode, state, p_phase, turn, card_width, card_height
    global skip_next, selected_group, current_img, dragging_card, session_active

    session_active = False
    hide_home_button()

    canvas.unbind("<ButtonPress-1>")
    canvas.unbind("<B1-Motion>")
    canvas.unbind("<ButtonRelease-1>")

    singleplayer.reset()
    multiplayer.reset()

    for tag in ("p_hand", "p_up", "p_down", "pile", "deck", "win_overlay", "lobby_text"):
        for item in canvas.find_withtag(tag):
            if item == slot_box_pile:
                continue
            canvas.delete(item)

    for box in upcard_slot_boxes:
        canvas.itemconfigure(box, state="hidden")
    canvas.itemconfigure(slot_box_pile, state="hidden")
    canvas.itemconfigure(deck_label, state="hidden", text="")

    p_up.clear()
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

    StartScreen(root, canvas)

def start_drag(event):
    global current_img, drag_offset_x, drag_offset_y, selected_group, dragging_card
 
    if game_mode == "multi" and turn != "player" and state != "select_up":
        return
 
    clicked = canvas.find_closest(event.x, event.y)
    if not clicked:
        return

    cid = clicked[0]
    if canvas.itemcget(cid, "state") == "hidden":
        return

    dragging_card = cid
    tags = canvas.gettags(cid)

    if state == "select_up":
        if "p_hand" not in tags:
            return
        for box in upcard_slot_boxes:
            canvas.itemconfigure(box, state="normal")
    else:
        if turn != "player":
            return
        if p_phase == "hand" and "p_hand" not in tags:
            return
        if p_phase == "up" and "p_up" not in tags:
            return
        if p_phase == "down" and "p_down" not in tags:
            return

    if event.state & 0x0001:
        rank = card_ranks[cid]
        if "p_hand" in tags:
            source_cards = get_p_hand()
        elif "p_up" in tags:
            source_cards = p_up
        elif "p_down" in tags:
            source_cards = p_down
        else:
            source_cards = [cid]
        selected_group = [card for card in source_cards if card_ranks.get(card) == rank]
        if not selected_group:
            selected_group = [cid]
        for card in selected_group:
            canvas.tag_raise(card)
        current_img = cid
    else:
        selected_group = [cid]
        current_img = cid

    x, y = canvas.coords(cid)
    drag_offset_x = x - event.x
    drag_offset_y = y - event.y

    if state == "play":
        canvas.itemconfigure(slot_box_pile, state="normal")

def do_drag(event):
    if current_img:
        for card in selected_group:
            canvas.coords(card, event.x + drag_offset_x, event.y + drag_offset_y)

def end_drag(event):
    global current_img, state, turn, p_phase, selected_group, dragging_card

    if not current_img:
        return

    cid = current_img

    if state == "select_up":
        x, y = canvas.coords(cid)
        placed = False

        if len(p_up) < 3:
            for i, (slotx, sloty) in enumerate(p_up_slots):
                if abs(x - slotx) <= width_upcard // 2 and abs(y - sloty) <= height_upcard // 2:
                    if cid in get_p_hand():
                        canvas.itemconfigure(cid, tags=("p_up",))
                        p_up.append(cid)
                        reposition_p_up()
                        for card in p_up:
                            canvas.tag_raise(card)
                        reposition_p_hand()
                        placed = True
                    break

        if not placed:
            reposition_p_hand()

        if len(p_up) == 3:
            if game_mode == "single":
                singleplayer.bot_choose_upcards()
                state = "play"
                canvas.itemconfigure(slot_box_pile, state="normal")
                singleplayer.update_pile_border()
            else:
                state = "waiting_setup"


        for box in upcard_slot_boxes:
            canvas.itemconfigure(box, state="hidden")
        current_img = None
        selected_group = []
        dragging_card = None
        return

    if game_mode == "multi" and p_phase == "down":
        for box in upcard_slot_boxes:
            canvas.itemconfigure(box, state="hidden")
        canvas.itemconfigure(slot_box_pile, state="hidden")

        result = multiplayer.net.play_down(multiplayer.game_id, multiplayer.player_id)
        print(result)

        if result.get("success") or result.get("pickup"):
            down_cards = canvas.find_withtag("p_down")
            if down_cards:
                canvas.delete(down_cards[-1])

            if not result.get("success"):
                p_phase = "hand"

        current_img = None
        selected_group = []
        dragging_card = None
        return

    cx, cy = canvas.coords(cid)
    in_pile = (
        abs(cx - pile_pos[0]) <= card_width // 2 and
        abs(cy - pile_pos[1]) <= card_height // 2
    )

    if in_pile:
        if not all(can_play(card) for card in selected_group):
            for card in selected_group:
                t = canvas.gettags(card)
                if "p_down" in t and card in p_down:
                    canvas.itemconfigure(card, image=card_faces[card])
                    p_down.remove(card)
                elif "p_up" in t and card in p_up:
                    p_up.remove(card)
                pile_cards_list.append(card)

            singleplayer.pick_up_pile_player()
            current_img = None
            selected_group = []
            dragging_card = None
            return

        if not selected_group:
            return

        if game_mode == "multi":
            cards_load = [multiplayer.network_card_lookup[card] for card in selected_group]
            result = multiplayer.net.play(multiplayer.game_id, multiplayer.player_id, cards_load)
            

            if result["success"]:
                for played_card in selected_group:
                    t = canvas.gettags(played_card)
                    if "p_down" in t and played_card in p_down:
                        canvas.itemconfigure(played_card, image=card_faces[played_card])
                        p_down.remove(played_card)
                    elif "p_up" in t and played_card in p_up:
                        p_up.remove(played_card)

                    canvas.itemconfigure(played_card, tags=("p_played",))
                    canvas.delete(played_card)
                    multiplayer.network_card_lookup.pop(played_card, None)
                    card_ranks.pop(played_card, None)
                    card_values.pop(played_card, None)
                    card_faces.pop(played_card, None)

                update_p_phase()
                reposition_p_hand()
            else:
                for played_card in selected_group:
                    snap_back(played_card)
                current_img = None
                selected_group = []
                dragging_card = None
                return
        else:
            for card in selected_group:
                t = canvas.gettags(card)
                if "p_down" in t and card in p_down:
                    p_down.remove(card)
                elif "p_up" in t and card in p_up:
                    p_up.remove(card)
            for card in selected_group:
                singleplayer.play_to_pile(card, True)

        update_p_phase()

        if game_mode == "single":
            singleplayer.update_pile_border()
            if singleplayer.check_win():
                canvas.itemconfigure(slot_box_pile, state="hidden")
                current_img = None
                selected_group = []
                dragging_card = None
                return
            singleplayer.next_bot_turn()
    else:
        for card in selected_group:
            snap_back(card)

    for box in upcard_slot_boxes:
        canvas.itemconfigure(box, state="hidden")
    canvas.itemconfigure(slot_box_pile, state="hidden")

    current_img = None
    selected_group = []
    dragging_card = None

class winScreen:
    def __init__(self, root, canvas, win):
        self.root = root
        self.canvas = canvas
        hide_home_button()
        self.frame = tk.Frame(root, bg="darkgreen")
        self.canvas_window = canvas.create_window(sx(960), sy(540), window=self.frame)
        self.canvas.create_rectangle(sx(0), sy(0), sx(1920), sy(1080), fill="darkgreen", tags=("win_overlay",))

        text = "You Win!" if win else "You Lose!"
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

        standings = accounts.get_leaderboard()

        header = tk.Frame(rows_frame, bg="green")
        header.pack(fill="x")
        tk.Label(header, text="Rank", font=("Arial", 16, "bold"), bg="green", fg="white", width=6, anchor="w").pack(side="left")
        tk.Label(header, text="Player", font=("Arial", 16, "bold"), bg="green", fg="white", width=20, anchor="w").pack(side="left")
        tk.Label(header, text="ELO", font=("Arial", 16, "bold"), bg="green", fg="white", width=8, anchor="e").pack(side="left")

        for rank, (username, elo) in enumerate(standings, start=1):
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

        tk.Label(canvas, text=f"Elo: {str(accounts.get_elo(user_var))}", font=("Arial", 20, "bold"), bg="green", fg="white").place(x=sx(80), y=sy(7), anchor="n")

        tk.Label(self.frame, text="Palace", font=("Arial", 80, "bold"), bg="green", fg="white").pack(pady=(0, 10))
        tk.Button(self.frame, text="Single Player", font=("Arial", 30, "bold"), bg="white", fg="green", relief="flat", padx=30, pady=10, command=self.open_singleplayer).pack()
        tk.Button(self.frame, text="Multiplayer", font=("Arial", 30, "bold"), bg="white", fg="green", relief="flat", padx=30, pady=10, command=self.open_multiplayer).pack(pady=20)
        canvas.itemconfigure(deck_label, state="hidden")
        tk.Button(self.frame, text="Information", font=("Arial", 25, "bold"), bg="white", fg="green", relief="flat", padx=30, pady=10, command=self.show_info).pack(pady=20)
        tk.Button(self.frame, text="Leaderboard", font=("Arial", 25, "bold"), bg="white", fg="green", relief="flat", padx=30, pady=10, command=self.show_leaderboard).pack()

        if user_var == "admin":
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

    def send_emails(self):
        self.email_status.config(text="Sending...")
        threading.Thread(target=self._send_emails_worker, daemon=True).start()

    def _send_emails_worker(self):
        sent = []
        failed = []
        text = ""

        standings = accounts.get_leaderboard()
        for accounts.rank, (accounts.username, accounts.elo) in enumerate(standings, start=1):
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

        self.root.after(0, lambda: self._report_email_result(addresses, sent, failed))

    def _report_email_result(self, addresses, sent, failed):
        if not addresses:
            self.email_status.config(text="No email addresses found in emails.txt")
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
        self.pass_entry = tk.Entry(self.frame, font=("Arial", 25, "bold"))
        self.pass_entry.pack(pady=(0, 10))

        tk.Button(self.frame, text = "Submit", font=("Arial", 20, "bold"), bg="green", fg="white", command = self.submit).pack(pady=(0, 30))

        tk.Label(self.frame, text="Don't have an account? Create one.", font=("Arial", 10, "bold"), bg="green", fg="white").pack(pady=(0, 10))
        tk.Button(self.frame, text = "Create Account", font=("Arial", 10, "bold"), bg="green", fg="white", command = self.open_createaccount).pack(pady=(0, 30))

    def submit(self):
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
        if found_login == True:
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
        self.email_entry.pack(pady=(0, 10))

        tk.Label(self.frame, text="Password", font=("Arial", 20, "bold"), bg="green", fg="white").pack(pady=(0, 2))
        self.pass_entry = tk.Entry(self.frame, font=("Arial", 25, "bold"))
        self.pass_entry.pack(pady=(0, 10))

        tk.Label(self.frame, text="By singing up, you will recieve emails of weekly standings each week", font=("Arial", 10, "bold"), bg="green", fg="white").pack(pady=(0, 2))
        tk.Button(self.frame, text = "Submit", font=("Arial", 20, "bold"), bg="green", fg="white", command = self.submit).pack(pady=(0, 30))

    def submit(self):
        user_var = self.user_entry.get()
        pass_var = self.pass_entry.get()
        email_var = self.email_entry.get()
        accounts.create_account(user_var, pass_var)
        with open("emails.txt", "a") as email_file:
            email_file.write(email_var + "\n")
        self.destroy()

    def destroy(self):
        self.canvas.delete(self.canvas_window)
        self.frame.destroy()
        LoginScreen(self.root, self.canvas)

import singleplayer
import multiplayer

LoginScreen(root, canvas)
root.mainloop()