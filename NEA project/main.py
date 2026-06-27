import tkinter as tk
import random
from turtle import Screen
from unittest.mock import Base
from dict import cards_dict
from network import Net

net = Net()
game_id = None
player_id = None

root = tk.Tk()
root.attributes('-fullscreen', True)
root.title("Palace")
canvas = tk.Canvas(root, bg="green")
canvas.pack(fill=tk.BOTH, expand=True)

exit_button = tk.Button(root, text="Exit", font=("Arial", 15, "bold"),bg="grey", fg="white", command=root.destroy)
canvas.pack(fill="both", expand=True)
canvas.create_window(1880, 30, window=exit_button)

suits = ["S", "D", "C", "H"]
ranks = ["2","3","4","5","6","7","8","9","10","J","Q","K","A"]

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
card_images = []
setup_button = None
selected_upcards = []

screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()

base_w = 1920
base_h = 1080

card_scale = min(screen_w/base_w, screen_h/base_h)

def load_card(path, card_sub1, card_sub2):
    if path not in img_mem:
        img_mem[path] = tk.PhotoImage(file=path).subsample(card_sub1, card_sub2)

    return img_mem[path]

def sx(x):
    return int(x * screen_w / base_w)

def sy(y):
    return int(y * screen_h / base_h)

pile_card_obj = None
pile_image = None
last_pile_size = 0
last_hand = None

network_card_lookup = {}

game_mode = "single"

dragging_card = None

selected_group = []
skip_next = False
ARROW_SCALE = 0.4

last_deck_count = -1
deck_cards = []
opponent_texts = []
opponent_up_cards = []
opponent_down_cards = []
opponent_hand = []
last_player_data = None
pile_cards_list = []

p_down = []
p_up = []

setup_text = None

bot_hands = []  
bot_ups = []    
bot_downs = []  
bot_positions = [] 

current_img = None
drag_offset_x = 0
drag_offset_y = 0

multiplayer_screen = None

state = "select_up"
p_phase = "hand"
turn = "player"

p_up_slots  = [(sx(810), sy(920)), (sx(960), sy(920)), (sx(1110), sy(920))]
p_down_pos  = [(sx(810), sy(920)), (sx(960), sy(920)), (sx(1110), sy(920))]
pile_pos    = (sx(960), sy(540))
deck_pos    = (sx(1400), sy(540))

width_upcard = 120
height_upcard = 180

upcard_slot_boxes = []
for (slotx, sloty) in p_up_slots:
    box = canvas.create_rectangle(
        slotx - width_upcard//2, sloty - height_upcard//2,
        slotx + width_upcard//2, sloty + height_upcard//2,
        outline="white", width=3, dash=(4, 2), state="hidden"
    )
    upcard_slot_boxes.append(box)

card_width = 0
card_height = 0

slot_box_pile = canvas.create_rectangle(0, 0, 0, 0, outline="yellow", width=3, tags=("pile",))
canvas.itemconfigure(slot_box_pile, state="hidden")

def get_p_hand():
    return list(canvas.find_withtag("p_hand"))

def pickup_pile():
    result = net.pickup(game_id, player_id)
    if result["success"]:
        sync_player_data()

def clear_network_hand():
    for card in canvas.find_withtag("p_hand"):
        canvas.delete(card)

def sync_player_data():
    global card_images, last_hand

    if dragging_card is not None:
        return
   
    player = net.player(game_id, player_id)
    if player["hand"] == last_hand:
        return
    last_hand = player["hand"].copy()

    card_images.clear()
    clear_network_hand()
    clear_network_upcards()
    clear_network_downcards()

    render_network_hand(player["hand"])
    render_network_downcards(player["down_count"])
    render_network_upcards(player["up"])

    for card in p_up:
        canvas.tag_raise(card)

def current_phase():
    player = net.player(game_id, player_id)
    if len(player["hand"]) > 0:
        return "hand"
    if len(player["up"]) > 0:
        return "up"
    if len(player["down_count"]) > 0:
        return "down"
    return "finished"

def create_opponent_displays():
    global opponent_texts
    for i in range(2):
        text = canvas.create_text(sx(150),sy(150 + i*150),text="",fill="white",font=("Arial", 16))
        opponent_texts.append(text)

def render_opponent_upcards(state):
    global opponent_up_cards
    for obj in opponent_up_cards:
        canvas.delete(obj)
    opponent_up_cards.clear()
    opponents = [p for p in state["player_data"] if p["id"] != player_id]
    for row, p in enumerate(opponents):
        for col, card in enumerate(p["up"]):
            rank = card["rank"]
            suit = card["suit"]

            img = load_card(cards_dict(f"{rank}{suit}"), 5, 5)
            if len(opponents) == 1:
                cid = canvas.create_image(sx(810 + col*150), sy(150 + row*150), image=img)
            else:
                cid = canvas.create_image(sx(300 + col*150), sy(150 + row*150), image=img)
            opponent_up_cards.append(cid)
            canvas.tag_raise(cid)

def render_opponent_downcards(state):
    global opponent_down_cards
    for obj in opponent_down_cards:
        canvas.delete(obj)
    opponent_down_cards.clear()
    opponents = [p for p in state["player_data"] if p["id"] != player_id]
    for row, p in enumerate(opponents):
        for col in range(p["down_count"]):
            img = load_card(cards_dict("back"), 22, 22)

            if len(opponents) == 1:
                cid = canvas.create_image(sx(810 + col*150), sy(150 + row*150), image=img)
            else:
                cid = canvas.create_image(sx(300 + col*150), sy(150 + row*150), image=img)
            opponent_down_cards.append(cid)

def render_opponent_hand(state):
    global opponent_hand
    for obj in opponent_hand:
        canvas.delete(obj)
    opponent_hand.clear()
    opponents = [p for p in state["player_data"] if p["id"] != player_id]
    for row, p in enumerate(opponents):
        for col in range(p["hand_count"]):
            img = load_card(cards_dict("back"), 22, 22)

            if len(opponents) == 1:
                cid = canvas.create_image(sx(750 + col*60), sy(300 + row*150), image=img)
            else:
                cid = canvas.create_image(sx(300 + col*60), sy(150 + row*150), image=img)
            opponent_hand.append(cid)


def show_setup_phase():
    global setup_text, setup_button
    setup_text = canvas.create_text(sx(170),sy(40),text="Choose 3 up-cards",fill="white",font=("Arial", 24, "bold"))
    setup_button = tk.Button(root, text="Confirm Selection", font=("Arial", 16, "bold"), bg="green", fg="white", command=finish_setup)
    canvas.create_window(sx(130), sy(90), window=setup_button)
    for box in upcard_slot_boxes:
        canvas.itemconfigure(box, state="normal")

def reposition_p_hand():
    if p_phase != "hand":
        return  
    hand = get_p_hand()
    if not hand:               
        return
    random.shuffle(hand)                   
    start = 960 - (len(hand)-1)*20
    for i, card in enumerate(hand):
        canvas.coords(card, sx(start + i*40), sy(760))
        canvas.tag_raise(card)

def update_pile(state):
    global pile_cards_list, pile_card_obj, last_pile_size
    pile = state["pile"]

    if not pile:
        if pile_card_obj:
            canvas.delete(pile_card_obj)
        pile_card_obj = None
        last_pile_size = 0
        return

    top = pile[-1]
    print("Top card:",top["rank"],top["suit"])

def render_network_hand(cards):
    global card_images, card_width, card_height

    print("render_network_hand called")
    print("cards =", len(cards))

    for i, card in enumerate(cards):
        rank = card["rank"]
        suit = card["suit"]
        face = load_card(cards_dict(f"{rank}{suit}"), 5, 5)
        if card_width == 0:
            card_width = face.width()
            card_height = face.height()
        cid = canvas.create_image(sx(750 + i*60),sy(760),image=face, tags=("p_hand",))

        card_ranks[cid] = rank
        card_values[cid] = rank_values[rank]
        card_faces[cid] = face
        card_suits[cid] = suit
        network_card_lookup[cid] = {
            "rank": rank,
            "suit": suit          
            }
    reposition_p_hand()

def render_network_upcards(cards):
    global card_images
    for i, card in enumerate(cards):
        rank = card["rank"]
        suit = card["suit"]

        face = load_card(cards_dict(f"{rank}{suit}"), 5, 5)
        cid = canvas.create_image(sx(810 + i*150), sy(920), image=face, tags=("p_up",))

        card_ranks[cid] = rank
        card_values[cid] = rank_values[rank]
        card_faces[cid] = face
        card_suits[cid] = suit

        network_card_lookup[cid] = {
            "rank": rank,
            "suit": suit
        }

def render_network_deck(deck_count):
    global card_images, deck_cards
    img = load_card(cards_dict("back"), 22, 22)
    cid = canvas.create_image(sx(1150), sy(540), image=img, tags=("deck",))

    if deck_count == 0:
        for card in deck_cards:
            canvas.delete(cid)
        deck_cards.clear()
        return
    canvas.itemconfigure(deck_label, text=f"{deck_count}")
    canvas.tag_raise(deck_label)

def clear_network_upcards():
   for card in canvas.find_withtag("p_up"):
       canvas.delete(card)

def render_network_downcards(count):
    global card_images
    back = load_card(cards_dict("back"), 22, 22)
    for i in range(count):
        cid = canvas.create_image(sx(810 + i*150), sy(920), image=back, tags=("p_down",))
       
def clear_network_downcards():
    for card in canvas.find_withtag("p_down"):
        canvas.delete(card)

def pickup_pile(event=None):
    print("Pile clicked")
    if game_mode != "multi":
        return
    if turn != "player":
        return
    if net.has_move(game_id, player_id)["has_move"]:
        return

    result = net.pickup(game_id, player_id)

    if result["success"]:
        state_data = net.state(game_id)
        update_pile(state_data["pile"])
        sync_player_data()
     
def refresh_game():
    global turn, state, last_player_data
    state_data = net.state(game_id)

    if game_mode != "multi":          
        return

    if state_data["winner"] is not None:
        show_winner(state_data["winner"])
        return

    if state == "waiting_setup":
        ready_count = 0
        for p in state_data["player_data"]:
            if p["ready"]:
                ready_count += 1

        if ready_count == state_data["players"]:
            print("All players ready")
            state = "play"
            player = net.player(game_id, player_id)
            sync_player_data()

        root.after(500, refresh_game)
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

    if turn == "player" and not net.has_move(game_id, player_id)["has_move"]:
        canvas.itemconfigure(slot_box_pile, outline="red", width=4)
    else:
        canvas.itemconfigure(slot_box_pile, outline="white", width=2)
        
    sync_player_data()

    if state_data["turn"] == player_id:
        turn = "player"
    else:
        turn = "waiting"

    canvas.itemconfigure(deck_label,text=f"{state_data['deck']}")
    root.after(500, refresh_game)

def show_winner(winner):
    text = f"Player {winner + 1} Wins!"
    canvas.create_rectangle(sx(500), sy(350), sx(1400), sy(700),fill="black")
    canvas.create_text(sx(950), sy(500), text=text, fill="white", font=("Arial", 40, "bold"))

def finish_setup():
    global state, setup_button, setup_text
    cards = []

    if len(p_up) != 3:
        print("Choose 3 up cards first")
        return

    for cid in p_up:
        if cid not in network_card_lookup:
            print("Card missing from lookup:", cid)
            return
        cards.append(network_card_lookup[cid])
    result = net.setup(game_id, player_id, cards)
    print(result)

    if not result["success"]:
        print(result)
        return

    state = "waiting_setup"

    for box in upcard_slot_boxes:
        canvas.itemconfigure(box, state="hidden")
    if setup_button:
        setup_button.destroy()
    if setup_text:
        canvas.delete(setup_text)

def reposition_p_up():
    for i, card in enumerate(p_up):
        canvas.coords(card, *p_up_slots[i])

def reposition_p_down():
    for i, card in enumerate(p_down):
        canvas.coords(card, *p_down_pos[i])

def compute_bot_positions(num_bots):
    global bot_positions
    bot_positions = []
    if num_bots == 1:
        bot_positions = [(sx(960), sy(260))]
    elif num_bots == 2:
        bot_positions = [(sx(660), sy(280)), (sx(1260), sy(280))]
    elif num_bots == 3:
        bot_positions = [(sx(500), sy(300)), (sx(960), sy(250)), (sx(1420), sy(300))]

def reposition_b_hand(bot):
    cards = bot_hands[bot]
    if not cards:
        return
    cards.sort(key=lambda card: canvas.coords(card)[0])
    base_x, base_y = bot_positions[bot]
    start = base_x - (len(cards)-1) * 20
    for i, card in enumerate(cards):
        canvas.coords(card, sx(start+i*40), sy(base_y))

def reposition_b_up(bot):
    ups = bot_ups[bot]
    if not ups:
        return
    base_x, base_y = bot_positions[bot]
    slots = [
        (sx(base_x - 150), sy(base_y - 150)),
        (sx(base_x), sy(base_y - 150)),
        (sx(base_x + 150), sy(base_y - 150)),
    ]
    for i, card in enumerate(ups):
        if i < len(slots):
            canvas.coords(card, *slots[i])

def reposition_b_down(bot):
    downs = bot_downs[bot]
    if not downs:
        return
    base_x, base_y = bot_positions[bot]
    slots = [
        (sx(base_x - 150), sy(base_y - 150)),
        (sx(base_x), sy(base_y - 150)),
        (sx(base_x + 150), sy(base_y - 150)),
    ]
    for i, card in enumerate(downs):
        if i < len(slots):
            canvas.coords(card, *slots[i])

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

def draw_p_hand():
    if deck_cards and len(get_p_hand()) < 3:
        cid = deck_cards.pop()
        canvas.itemconfigure(cid, tags=("p_hand",))
        canvas.itemconfigure(cid, image=card_faces[cid])
        reposition_p_hand()

def draw_b_hand(bot):
    if deck_cards and len(bot_hands[bot]) < 3:
        cid = deck_cards.pop()
        canvas.itemconfigure(cid, tags=(f"b{bot}_hand",))
        canvas.itemconfigure(cid, image=card_backs[cid])
        bot_hands[bot].append(cid)
        reposition_b_hand(bot)

def any_legal_p():
    if p_phase == "hand":
        return any(can_play(card) for card in get_p_hand())
    if p_phase == "up":
        return any(can_play(card) for card in p_up)
    return False

def update_p_phase():
    global p_phase
    if p_phase == "hand" and not get_p_hand() and not deck_cards:
        p_phase = "up"
    if p_phase == "up" and not p_up:
        p_phase = "down"

def check_win():
    if not get_p_hand() and not p_up and not p_down:
        winScreen(root, canvas, True)
        return True

    if bot_hands:
        all_empty = True
        for bot in range(len(bot_hands)):
            if bot_hands[bot] or bot_ups[bot] or bot_downs[bot]:
                all_empty = False
                break
        if all_empty:
            winScreen(root, canvas, False)
            return True
    return False

def update_pile(pile):
    global last_pile_size
    global pile_image
    global pile_card_obj

    if len(pile) == last_pile_size:
        return
    last_pile_size = len(pile)
    if not pile:
        if pile_card_obj:
            canvas.delete(pile_card_obj)
            pile_card_obj = None

        last_pile_size = 0
        return
    top = pile[-1]

    rank = top["rank"]
    suit = top["suit"]

    pile_image = load_card(cards_dict(f"{rank}{suit}"), 5, 5)
    if pile_card_obj:
        canvas.delete(pile_card_obj)

    pile_card_obj = canvas.create_image(pile_pos[0],pile_pos[1],image=pile_image)
    canvas.tag_bind(pile_card_obj, "<Button-1>", pickup_pile)

def snap_back(cid):
    tags = canvas.gettags(cid)
    if "p_hand" in tags:
        reposition_p_hand()
    elif "p_up" in tags:
        reposition_p_up()
    elif "p_down" in tags:
        reposition_p_down()

def pick_up_pile_player():
    global pile_cards_list, p_phase
    for cid in pile_cards_list:
        canvas.itemconfigure(cid, tags=("p_hand",))
        canvas.itemconfigure(cid, image=card_faces[cid])
    pile_cards_list = []
    reposition_p_hand()
    p_phase = "hand"

def pick_up_pile_bot(bot):
    global pile_cards_list
    for cid in pile_cards_list:
        canvas.itemconfigure(cid, tags=(f"b{bot}_hand",))
        canvas.itemconfigure(cid, image=card_backs[cid])
        bot_hands[bot].append(cid)
    pile_cards_list = []
    reposition_b_hand(bot)

def play_to_pile(cid, from_player=True, bot_index=None):
    global skip_next
    canvas.coords(cid, *pile_pos)
    canvas.tag_raise(cid)
    canvas.itemconfigure(cid, tags=("pile",))
    canvas.itemconfigure(cid, image=card_faces[cid])
    pile_cards_list.append(cid)
    canvas.itemconfig("deck_label", text=f"{len(deck_cards)}")

    if card_ranks[cid] == "10":
        burn_pile()
        if from_player:
            draw_p_hand()
        else:
            if bot_index is not None:
                draw_b_hand(bot_index)
        return

    if check_four_of_kind():
        burn_pile()
        if from_player:
            draw_p_hand()
        else:
            if bot_index is not None:
                draw_b_hand(bot_index)
        return

    if card_ranks[cid] == "8":     
        skip_next = True

    if from_player:
        draw_p_hand()
    else:
        if bot_index is not None:
            draw_b_hand(bot_index)

def create_deck(num_bots):
    global card_width, card_height, bot_hands, bot_ups, bot_downs

    bot_hands = [[] for _ in range(num_bots)]
    bot_ups = [[] for _ in range(num_bots)]
    bot_downs = [[] for _ in range(num_bots)]
    compute_bot_positions(num_bots)

    deck_specs = [(r, s) for s in suits for r in ranks]
    random.shuffle(deck_specs)

    back_img = load_card(cards_dict("back"), 22, 22)
    card_width, card_height = back_img.width(), back_img.height()

    for i in range(3):
        r, s = deck_specs.pop()
        face = load_card(cards_dict(f"{r}{s}"), 5, 5)
        cid = canvas.create_image(*p_down_pos[i], image=back_img, tags=("p_down",))
        p_down.append(cid)
        card_ranks[cid] = r; card_values[cid] = rank_values[r]
        card_faces[cid] = face; card_backs[cid] = back_img

    for i in range(6):
        r, s = deck_specs.pop()
        face = load_card(cards_dict(f"{r}{s}"), 5, 5)
        cid = canvas.create_image(sx(700+i*60), sy(760), image=face, tags=("p_hand",))
        card_ranks[cid] = r; card_values[cid] = rank_values[r]
        card_faces[cid] = face; card_backs[cid] = back_img

    for bot in range(num_bots):
        base_x, base_y = bot_positions[bot]

        for i in range(3):
            r, s = deck_specs.pop()
            face = load_card(cards_dict(f"{r}{s}"), 5, 5)
            cid = canvas.create_image(sx(base_x + (i-1)*80), sy(base_y-160), image=back_img, tags=(f"b{bot}_down",))
            bot_downs[bot].append(cid)
            card_ranks[cid] = r; card_values[cid] = rank_values[r]
            card_faces[cid] = face; card_backs[cid] = back_img

        for i in range(6):
            r, s = deck_specs.pop()
            face = load_card(cards_dict(f"{r}{s}"), 5, 5)
            cid = canvas.create_image(sx(base_x + (i-2.5)*30), sy(base_y), image=back_img, tags=(f"b{bot}_hand",))
            bot_hands[bot].append(cid)
            card_ranks[cid] = r; card_values[cid] = rank_values[r]
            card_faces[cid] = face; card_backs[cid] = back_img

    for r, s in deck_specs:
        face = load_card(cards_dict(f"{r}{s}"), 5, 5)
        cid = canvas.create_image(*deck_pos, image=face, tags=("deck",))
        deck_cards.append(cid)
        card_ranks[cid] = r; card_values[cid] = rank_values[r]
        card_faces[cid] = face; card_backs[cid] = back_img

    reposition_p_hand()
    reposition_p_down()
    for bot in range(num_bots):
        reposition_b_hand(bot)
        reposition_b_down(bot)

    canvas.coords(
        slot_box_pile,
        pile_pos[0]-card_width//2-10, pile_pos[1]-card_height//2-10,
        pile_pos[0]+card_width//2+10, pile_pos[1]+card_height//2+10,
    )

def bot_choose_upcards():
    for bot in range(len(bot_hands)):
        hand = bot_hands[bot]
        if len(hand) < 3:
            continue
        chosen = sorted(hand, key=lambda card: card_values[card])[:3]
        for cid in chosen:
            canvas.itemconfigure(cid, tags=(f"b{bot}_up",))
            canvas.itemconfigure(cid, image=card_faces[cid])
            bot_ups[bot].append(cid)
            if cid in hand:
                hand.remove(cid)
        reposition_b_up(bot)
        reposition_b_hand(bot)

def next_bot_turn():
    root.after(500, bot_play)

def play_single_bot(bot):
    hand = bot_hands[bot]
    ups = bot_ups[bot]
    downs = bot_downs[bot]

    if hand or deck_cards:
        phase = "hand"
    elif ups:
        phase = "up"
    else:
        phase = "down"

    if phase == "hand":
        legal = [card for card in hand if can_play(card)]
        if not legal:
            if pile_cards_list:
                pick_up_pile_bot(bot)
            return
        cid = min(legal, key=lambda card: card_values[card])
        if cid in hand:
            hand.remove(cid)
        play_to_pile(cid, False, bot_index=bot)

    elif phase == "up":
        legal = [card for card in ups if can_play(card)]
        if not legal:
            if pile_cards_list:
                pick_up_pile_bot(bot)
            return
        cid = min(legal, key=lambda card: card_values[card])
        if cid in ups:
            ups.remove(cid)
        play_to_pile(cid, False, bot_index=bot)

    else:
        if not downs: 
            return
        cid = random.choice(downs)
        downs.remove(cid)
        canvas.itemconfigure(cid, image=card_faces[cid])
        if not can_play(cid):
            pile_cards_list.append(cid)
            pick_up_pile_bot(bot)
        else:
            play_to_pile(cid, False, bot_index=bot)

def bot_play():
    global turn, skip_next
    turn = "bot"
    delay = 500
    n = len(bot_hands)

    def play_index(i):
        global skip_next, turn
        if i >= n:
            if skip_next:
                skip_next = False
                root.after(delay, bot_play)
                return
            turn = "player"
            return

        if skip_next:
            skip_next = False
            root.after(delay, lambda: play_index(i+1))
            return
        play_single_bot(i)
        if check_win():
            return
        root.after(delay, lambda: play_index(i+1))
    play_index(0)

def refresh_lobby():
    global game_id
    if not game_id:
        return
    state = net.state(game_id)
    num_players = state["players"]
    if state["started"]:
        start_multiplayer_game()
        return
    canvas.itemconfigure("lobby_text", state="hidden")
    root.after(1000, refresh_lobby)
    canvas.create_text(sx(960), sy(200), text=f"Players in lobby: {num_players}/3", fill="white", font=("Arial", 24, "bold"), tags="lobby_text")

def start_drag(event):
    global current_img, drag_offset_x, drag_offset_y, selected_group, dragging_card

    print("CLICK")
    print("state =", state)
    print("turn =", turn)
    print("game_mode =", game_mode)
    print("p_phase =", p_phase)
    
    if game_mode == "multi" and turn != "player" and state != "select_up":
        return

    phase = current_phase()
    clicked = canvas.find_closest(event.x, event.y)
    if not clicked:
        return

    cid = clicked[0]
    dragging_card = cid
    tags = canvas.gettags(cid)

    if state == "select_up":
        card = network_card_lookup[cid]
        if card in selected_upcards:
            selected_upcards.remove(card)
        else:
            if len(selected_upcards) < 3:
                selected_upcards.append(card)
                
    if phase == "hand" and "p_hand" not in tags:
        return
    if phase == "up" and "p_up" not in tags:
        return

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
        hand_cards = get_p_hand()

        selected_group = [card for card in hand_cards if card_ranks[card] == rank]

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
    tags = canvas.gettags(cid)

    if state == "select_up":
        x, y = canvas.coords(cid)
        placed = False

        if len(p_up) < 3:
            for i, (slotx, sloty) in enumerate(p_up_slots):
                if abs(x - slotx) <= width_upcard//2 and abs(y - sloty) <= height_upcard//2:
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
            state = "waiting_setup"
            bot_choose_upcards()

        for box in upcard_slot_boxes:
            canvas.itemconfigure(box, state="hidden")
        current_img = None
        selected_group = []
        return

    cx, cy = canvas.coords(cid)
    in_pile = (
        abs(cx - pile_pos[0]) <= card_width//2 and
        abs(cy - pile_pos[1]) <= card_height//2
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

            pick_up_pile_player()
            current_img = None
            selected_group = []
            return

        if not selected_group:
            return
        played_card = selected_group[0]

        if game_mode == "multi":
            result = net.play(game_id, player_id, network_card_lookup[played_card])

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
                    network_card_lookup.pop(played_card, None)
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
            play_to_pile(card, True)
        update_p_phase()

        if check_win():
            canvas.itemconfigure(slot_box_pile, state="hidden")
            current_img = None
            selected_group = []
            return
        next_bot_turn()
    else:
        for card in selected_group:
            snap_back(card)

    for box in upcard_slot_boxes:
        canvas.itemconfigure(box, state="hidden")
    canvas.itemconfigure(slot_box_pile, state="hidden")

    if p_phase == "down":
        result = net.play_down(game_id, player_id)
        print(result)

    current_img = None
    selected_group = []

    dragging_card = None    

def play_player():
    pass

deck_label = canvas.create_text(sx(1150), sy(540), text="", font=("Arial", 50, "bold"), fill="white", tags=("deck_label",), state="normal")

class winScreen:
    def __init__(self, root, canvas, win):
        self.root = root
        self.canvas = canvas
        self.frame = tk.Frame(root, bg="darkgreen")
        self.canvas_window = canvas.create_window(sx(960), sy(540), window=self.frame)
        self.canvas.create_rectangle(sx(0), sy(0), sx(1920), sy(1080), fill="darkgreen", tags=("win_overlay",))

        text = "You Win!" if win else "You Lose!"
        tk.Label(self.frame, text=text, font=("Arial", 80, "bold"), bg="darkgreen", fg="white").pack(pady=(0, 10))
        tk.Button(self.frame, text="Exit", font=("Arial", 30, "bold"), bg="white", fg="darkgreen", relief="flat", padx=30, pady=10, command=root.destroy).pack()
        exit_button.destroy()

class StartScreen:
    def __init__(self, root, canvas, on_start):
        self.root = root
        self.canvas = canvas
        self.on_start = on_start
        self.frame = tk.Frame(root, bg="green")
        self.canvas_window = canvas.create_window(sx(960), sy(540), window=self.frame)

        tk.Label(self.frame, text="Palace", font=("Arial", 80, "bold"), bg="green", fg="white").pack(pady=(0, 10))
        tk.Button(self.frame, text="Single Player", font=("Arial", 30, "bold"), bg="white", fg="green", relief="flat", padx=30, pady=10, command=self.open_singleplayer).pack()
        tk.Button(self.frame, text="Multiplayer", font=("Arial", 30, "bold"), bg="white", fg="green", relief="flat", padx=30, pady=10, command=self.open_multiplayer).pack(pady=20)
        canvas.itemconfigure(deck_label, state="hidden")
        tk.Button(self.frame, text="Information", font=("Arial", 25, "bold"), bg="white", fg="green", relief="flat", padx=30, pady=10, command=self.show_info).pack(pady=20)

    def show_info(self):
        self.canvas.itemconfigure(self.canvas_window, state="hidden")
        InfoScreen(self.canvas, self)

    def open_settings(self):
        self.destroy()
        GameSettings(self.root, self.canvas, self.on_start)
        
    def destroy(self):
        self.canvas.delete(self.canvas_window)
        self.frame.destroy()

    def open_singleplayer(self):
        self.destroy()
        GameSettings(self.root, self.canvas, self.on_start)

    def open_multiplayer(self):
        global multiplayer_screen
        self.destroy()
        multiplayer_screen = MultiplayerScreen(self.root,self.canvas,self.on_start)

class GameSettings:
    def __init__(self, root, canvas, on_start):
        self.root = root
        self.canvas = canvas
        self.on_start = on_start
        self.frame = tk.Frame(root, bg="green")
        self.canvas_window = canvas.create_window(sx(960), sy(540), window=self.frame)

        tk.Label(self.frame, text="Game Settings", font=("Arial", 40, "bold"), bg="green", fg="white").pack(pady=(0, 10))
        tk.Label(self.frame, text="Number of Bots", font=("Arial", 20, "bold"), bg="green", fg="white").pack(pady=(0, 10))

        self.num_bots = tk.IntVar(value=1)
        tk.Radiobutton(self.frame, text="1", font=("Arial", 15), bg="green", fg="white", variable=self.num_bots, value=1, selectcolor="green", activebackground="green", activeforeground="white").pack()
        tk.Radiobutton(self.frame, text="2", font=("Arial", 15), bg="green", fg="white", variable=self.num_bots, value=2, selectcolor="green", activebackground="green", activeforeground="white").pack()
        tk.Radiobutton(self.frame, text="3", font=("Arial", 15), bg="green", fg="white", variable=self.num_bots, value=3, selectcolor="green", activebackground="green", activeforeground="white").pack()

        tk.Button(self.frame, text="Play", font=("Arial", 20, "bold"), bg="white", fg="green", relief="flat", padx=30, pady=10, command=self.start).pack(pady=20)
        canvas.itemconfigure(deck_label, state="hidden")

    def start(self):
        bots = self.num_bots.get()
        self.canvas.delete(self.canvas_window)
        self.frame.destroy()
        if callable(self.on_start):
            self.on_start(bots)

class MultiplayerScreen:
    def __init__(self, root, canvas, on_start):
        self.root = root
        self.canvas = canvas
        self.on_start = on_start
        self.frame = tk.Frame(root, bg="green")
        self.canvas_window = canvas.create_window(sx(960), sy(540), window=self.frame)
  
        tk.Button(self.frame, text="Host Game", font=("Arial", 20), command=self.host_game).pack(pady=10)
        tk.Button(self.frame, text="Start Game", command=self.start_game).pack(pady=10)
        tk.Label(self.frame, text="Join Code", font=("Arial", 16), bg="green", fg="white").pack()
        self.code_entry = tk.Entry(self.frame, font=("Arial", 16))
        self.code_entry.pack()
        tk.Button(self.frame, text="Join Game", font=("Arial", 20), command=self.join_game).pack(pady=10)

    def host_game(self):
        global game_mode, game_id, player_id
        game_mode = "multi"
        game = net.create()
        game_id = game["game_id"]
        player = net.join(game_id)
        player_id = player["player_id"]
        tk.Label(root, text=f"Hosting at: {game_id}", font=("Arial", 20, "bold"), bg="white", fg="green", highlightbackground="green").pack(pady=0, padx=0)
        refresh_lobby()

    def join_game(self):
        global game_mode, game_id, player_id
        game_mode = "multi"
        code = self.code_entry.get()
        game_id = code
        player = net.join(game_id)
        player_id = player["player_id"]
        tk.Label(root, text=f"Joined: {game_id}", font=("Arial", 20, "bold"), bg="green", fg="white", highlightbackground="green").pack(pady=20)
        refresh_lobby()

    def start_game(self):
        net.start(game_id)
    
    def destroy(self):
        self.canvas.delete(self.canvas_window)
        self.frame.destroy()
        canvas.itemconfigure("lobby_text", state="hidden")

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
       
def start_multiplayer_game():
    global multiplayer_screen, state, p_phase, turn

    if multiplayer_screen:
        multiplayer_screen.destroy()
        multiplayer_screen = None

    create_opponent_displays()

    state = "select_up"
    p_phase = "hand"
    turn = "waiting"

    canvas.coords(slot_box_pile, sx(pile_pos[0]-80), sy(pile_pos[1]-120), sx(pile_pos[0]+80), sy(pile_pos[1]+120))
    canvas.itemconfigure(slot_box_pile, state="normal")
    canvas.itemconfigure(deck_label, state="normal")

    canvas.bind("<ButtonPress-1>", start_drag)
    canvas.bind("<B1-Motion>", do_drag)
    canvas.bind("<ButtonRelease-1>", end_drag)
    canvas.tag_bind("pile", "<Button-1>", pickup_pile)

    player = net.player(game_id, player_id)
    render_network_hand(player["hand"])

    show_setup_phase()
    refresh_game()

class Game:
    def __init__(self, root, canvas):
        self.root = root
        self.canvas = canvas
        self.start_screen = StartScreen(root, canvas, self.start)

    def start(self, bots=0):
        global state, p_phase, turn, deck_cards, pile_cards_list, p_down, p_up, game_id

        game = net.create()
        game_id = game["game_id"]
        print("game id = ", game_id)

        state = "select_up"
        p_phase = "hand"
        turn = "player"
        deck_cards = []
        pile_cards_list = []
        p_down = []
        p_up = []

        self.start_screen.destroy()
        create_deck(bots)
        canvas.bind("<ButtonPress-1>", start_drag)
        canvas.bind("<B1-Motion>", do_drag)
        canvas.bind("<ButtonRelease-1>", end_drag)
        canvas.itemconfigure(deck_label, state="normal")
        canvas.itemconfig("deck_label", text=f"Cards left in deck: {len(deck_cards)}")

print(len(card_images))

game = Game(root, canvas)
root.mainloop()


