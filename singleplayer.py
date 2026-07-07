import random
import tkinter as tk
import __main__ as main

deck_cards = []

bot_hands = []
bot_ups = []
bot_downs = []
bot_positions = []

def compute_bot_positions(num_bots):
    global bot_positions
    bot_positions = []
    if num_bots == 1:
        bot_positions = [(main.sx(960), main.sy(260))]
    elif num_bots == 2:
        bot_positions = [(main.sx(660), main.sy(280)), (main.sx(1260), main.sy(280))]
    elif num_bots == 3:
        bot_positions = [(main.sx(500), main.sy(300)), (main.sx(960), main.sy(250)), (main.sx(1420), main.sy(300))]

def reposition_b_hand(bot):
    cards = bot_hands[bot]
    if not cards:
        return
    cards.sort(key=lambda card: main.canvas.coords(card)[0])
    base_x, base_y = bot_positions[bot]
    start = base_x - (len(cards) - 1) * 20
    for i, card in enumerate(cards):
        main.canvas.coords(card, main.sx(start + i * 40), main.sy(base_y))

def reposition_b_up(bot):
    ups = bot_ups[bot]
    if not ups:
        return
    base_x, base_y = bot_positions[bot]
    slots = [
        (main.sx(base_x - 150), main.sy(base_y - 150)),
        (main.sx(base_x), main.sy(base_y - 150)),
        (main.sx(base_x + 150), main.sy(base_y - 150)),
    ]
    for i, card in enumerate(ups):
        if i < len(slots):
            main.canvas.coords(card, *slots[i])

def reposition_b_down(bot):
    downs = bot_downs[bot]
    if not downs:
        return
    base_x, base_y = bot_positions[bot]
    slots = [
        (main.sx(base_x - 150), main.sy(base_y - 150)),
        (main.sx(base_x), main.sy(base_y - 150)),
        (main.sx(base_x + 150), main.sy(base_y - 150)),
    ]
    for i, card in enumerate(downs):
        if i < len(slots):
            main.canvas.coords(card, *slots[i])

def draw_p_hand():
    if deck_cards and len(main.get_p_hand()) < 3:
        cid = deck_cards.pop()
        main.canvas.itemconfigure(cid, tags=("p_hand",))
        main.canvas.itemconfigure(cid, image=main.card_faces[cid])
        main.reposition_p_hand()

def draw_b_hand(bot):
    if deck_cards and len(bot_hands[bot]) < 3:
        cid = deck_cards.pop()
        main.canvas.itemconfigure(cid, tags=(f"b{bot}_hand",))
        main.canvas.itemconfigure(cid, image=main.card_backs[cid])
        bot_hands[bot].append(cid)
        reposition_b_hand(bot)

def any_legal_p():
    if main.p_phase == "hand":
        return any(main.can_play(card) for card in main.get_p_hand())
    if main.p_phase == "up":
        return any(main.can_play(card) for card in main.p_up)
    if main.p_phase == "down":
        return any(main.can_play(card) for card in main.p_down)
    return False

def update_pile_border():
    if main.turn == "player" and not any_legal_p():
        main.canvas.itemconfigure(main.slot_box_pile, outline="red", width=4)
    else:
        main.canvas.itemconfigure(main.slot_box_pile, outline="white", width=2)

def check_win():
    if not main.get_p_hand() and not main.p_up and not main.p_down:
        main.session_active = False
        main.winScreen(main.root, main.canvas, True)
        return True

    if bot_hands:
        all_empty = True
        for bot in range(len(bot_hands)):
            if bot_hands[bot] or bot_ups[bot] or bot_downs[bot]:
                all_empty = False
                break
        if all_empty:
            main.session_active = False
            main.winScreen(main.root, main.canvas, False)
            return True
    return False

def pick_up_pile_player():
    for cid in main.pile_cards_list:
        main.canvas.itemconfigure(cid, tags=("p_hand",))
        main.canvas.itemconfigure(cid, image=main.card_faces[cid])
    main.pile_cards_list.clear()
    main.reposition_p_hand()
    main.p_phase = "hand"
    update_pile_border()

def pick_up_pile_bot(bot):
    for cid in main.pile_cards_list:
        main.canvas.itemconfigure(cid, tags=(f"b{bot}_hand",))
        main.canvas.itemconfigure(cid, image=main.card_backs[cid])
        bot_hands[bot].append(cid)
    main.pile_cards_list.clear()
    reposition_b_hand(bot)

def play_to_pile(cid, from_player=True, bot_index=None):
    canvas = main.canvas
    canvas.coords(cid, *main.pile_pos)
    canvas.tag_raise(cid)
    canvas.itemconfigure(cid, tags=("pile",))
    canvas.itemconfigure(cid, image=main.card_faces[cid])
    main.pile_cards_list.append(cid)
    canvas.itemconfig("deck_label", text=f"{len(deck_cards)}")

    if main.card_ranks[cid] == "10":
        main.burn_pile()
        if from_player:
            draw_p_hand()
        elif bot_index is not None:
            draw_b_hand(bot_index)
        return

    if main.check_four_of_kind():
        main.burn_pile()
        if from_player:
            draw_p_hand()
        elif bot_index is not None:
            draw_b_hand(bot_index)
        return

    if main.card_ranks[cid] == "8":
        main.skip_next = True

    if from_player:
        draw_p_hand()
    elif bot_index is not None:
        draw_b_hand(bot_index)

def create_deck(num_bots):
    global bot_hands, bot_ups, bot_downs

    bot_hands = [[] for _ in range(num_bots)]
    bot_ups = [[] for _ in range(num_bots)]
    bot_downs = [[] for _ in range(num_bots)]
    compute_bot_positions(num_bots)

    deck_specs = [(r, s) for s in main.suits for r in main.ranks]
    random.shuffle(deck_specs)

    back_img = main.load_card(main.cards_dict("back"), 22, 22)
    main.card_width, main.card_height = back_img.width(), back_img.height()

    for i in range(3):
        r, s = deck_specs.pop()
        face = main.load_card(main.cards_dict(f"{r}{s}"), 5, 5)
        cid = main.canvas.create_image(*main.p_down_pos[i], image=back_img, tags=("p_down",))
        main.p_down.append(cid)
        main.card_ranks[cid] = r
        main.card_values[cid] = main.rank_values[r]
        main.card_faces[cid] = face
        main.card_backs[cid] = back_img

    for i in range(6):
        r, s = deck_specs.pop()
        face = main.load_card(main.cards_dict(f"{r}{s}"), 5, 5)
        cid = main.canvas.create_image(main.sx(700 + i * 60), main.sy(760), image=face, tags=("p_hand",))
        main.card_ranks[cid] = r
        main.card_values[cid] = main.rank_values[r]
        main.card_faces[cid] = face
        main.card_backs[cid] = back_img

    for bot in range(num_bots):
        base_x, base_y = bot_positions[bot]

        for i in range(3):
            r, s = deck_specs.pop()
            face = main.load_card(main.cards_dict(f"{r}{s}"), 5, 5)
            cid = main.canvas.create_image(main.sx(base_x + (i - 1) * 80), main.sy(base_y - 160), image=back_img, tags=(f"b{bot}_down",))
            bot_downs[bot].append(cid)
            main.card_ranks[cid] = r
            main.card_values[cid] = main.rank_values[r]
            main.card_faces[cid] = face
            main.card_backs[cid] = back_img

        for i in range(6):
            r, s = deck_specs.pop()
            face = main.load_card(main.cards_dict(f"{r}{s}"), 5, 5)
            cid = main.canvas.create_image(main.sx(base_x + (i - 2.5) * 30), main.sy(base_y), image=back_img, tags=(f"b{bot}_hand",))
            bot_hands[bot].append(cid)
            main.card_ranks[cid] = r
            main.card_values[cid] = main.rank_values[r]
            main.card_faces[cid] = face
            main.card_backs[cid] = back_img

    for r, s in deck_specs:
        face = main.load_card(main.cards_dict(f"{r}{s}"), 5, 5)
        cid = main.canvas.create_image(main.sx(1150), main.sy(540), image=back_img, tags=("deck",))
        deck_cards.append(cid)
        main.card_ranks[cid] = r
        main.card_values[cid] = main.rank_values[r]
        main.card_faces[cid] = face
        main.card_backs[cid] = back_img

    main.canvas.tag_raise(main.deck_label)

    main.reposition_p_hand()
    main.reposition_p_down()
    for bot in range(num_bots):
        reposition_b_hand(bot)
        reposition_b_down(bot)

    main.canvas.coords(
        main.slot_box_pile,
        main.pile_pos[0] - main.card_width // 2 - 10, main.pile_pos[1] - main.card_height // 2 - 10,
        main.pile_pos[0] + main.card_width // 2 + 10, main.pile_pos[1] + main.card_height // 2 + 10,
    )

def bot_choose_upcards():
    for bot in range(len(bot_hands)):
        hand = bot_hands[bot]
        if len(hand) < 3:
            continue
        chosen = sorted(hand, key=lambda card: main.card_values[card])[:3]
        for cid in chosen:
            main.canvas.itemconfigure(cid, tags=(f"b{bot}_up",))
            main.canvas.itemconfigure(cid, image=main.card_faces[cid])
            bot_ups[bot].append(cid)
            if cid in hand:
                hand.remove(cid)
        reposition_b_up(bot)
        reposition_b_hand(bot)

def next_bot_turn():
    main.root.after(500, bot_play)

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
        legal = [card for card in hand if main.can_play(card)]
        if not legal:
            if main.pile_cards_list:
                pick_up_pile_bot(bot)
            return
        cid = min(legal, key=lambda card: main.card_values[card])
        if cid in hand:
            hand.remove(cid)
        play_to_pile(cid, False, bot_index=bot)

    elif phase == "up":
        legal = [card for card in ups if main.can_play(card)]
        if not legal:
            if main.pile_cards_list:
                pick_up_pile_bot(bot)
            return
        cid = min(legal, key=lambda card: main.card_values[card])
        if cid in ups:
            ups.remove(cid)
        play_to_pile(cid, False, bot_index=bot)

    else:
        if not downs:
            return
        cid = random.choice(downs)
        downs.remove(cid)
        main.canvas.itemconfigure(cid, image=main.card_faces[cid])
        if not main.can_play(cid):
            main.pile_cards_list.append(cid)
            pick_up_pile_bot(bot)
        else:
            play_to_pile(cid, False, bot_index=bot)

def bot_play():
    if not main.session_active:
        return
    main.turn = "bot"
    delay = 500
    n = len(bot_hands)

    def play_index(i):
        if not main.session_active:
            return
        if i >= n:
            if main.skip_next:
                main.skip_next = False
                main.root.after(delay, bot_play)
                return
            main.turn = "player"
            return

        if main.skip_next:
            main.skip_next = False
            main.root.after(delay, lambda: play_index(i + 1))
            return
        play_single_bot(i)
        if check_win():
            return
        main.root.after(delay, lambda: play_index(i + 1))

    play_index(0)
    
class GameSettings:
    def __init__(self, root, canvas, on_start):
        self.root = root
        self.canvas = canvas
        self.on_start = on_start
        self.frame = tk.Frame(root, bg="green")
        self.canvas_window = canvas.create_window(main.sx(960), main.sy(540), window=self.frame)

        tk.Label(self.frame, text="Game Settings", font=("Arial", 40, "bold"), bg="green", fg="white").pack(pady=(0, 10))
        tk.Label(self.frame, text="Number of Bots", font=("Arial", 20, "bold"), bg="green", fg="white").pack(pady=(0, 10))

        self.num_bots = tk.IntVar(value=1)
        tk.Radiobutton(self.frame, text="1", font=("Arial", 15), bg="green", fg="white", variable=self.num_bots, value=1, selectcolor="green", activebackground="green", activeforeground="white").pack()
        tk.Radiobutton(self.frame, text="2", font=("Arial", 15), bg="green", fg="white", variable=self.num_bots, value=2, selectcolor="green", activebackground="green", activeforeground="white").pack()
        tk.Radiobutton(self.frame, text="3", font=("Arial", 15), bg="green", fg="white", variable=self.num_bots, value=3, selectcolor="green", activebackground="green", activeforeground="white").pack()

        tk.Button(self.frame, text="Play", font=("Arial", 20, "bold"), bg="white", fg="green", relief="flat", padx=30, pady=10, command=self.start).pack(pady=20)
        tk.Button(self.frame, text="Back", font=("Arial", 16, "bold"), bg="white", fg="green", relief="flat", padx=20, pady=6, command=self.back).pack()
        main.canvas.itemconfigure(main.deck_label, state="hidden")

    def start(self):
        bots = self.num_bots.get()
        self.canvas.delete(self.canvas_window)
        self.frame.destroy()
        if callable(self.on_start):
            self.on_start(bots)

    def back(self):
        self.canvas.delete(self.canvas_window)
        self.frame.destroy()
        main.go_home()

def open_singleplayer_settings(root, canvas):
    GameSettings(root, canvas, start_singleplayer)

def start_singleplayer(bots):
    global deck_cards, bot_hands, bot_ups, bot_downs

    main.game_mode = "single"
    main.state = "select_up"
    main.p_phase = "hand"
    main.turn = "player"
    main.session_active = True

    main.pile_cards_list.clear()
    main.p_down.clear()
    main.p_up.clear()

    deck_cards = []
    bot_hands = []
    bot_ups = []
    bot_downs = []

    create_deck(bots)

    main.canvas.bind("<ButtonPress-1>", main.start_drag)
    main.canvas.bind("<B1-Motion>", main.do_drag)
    main.canvas.bind("<ButtonRelease-1>", main.end_drag)
    main.canvas.itemconfigure(main.deck_label, state="normal")
    main.canvas.itemconfig(main.deck_label, text=f"{len(deck_cards)}")
    main.show_home_button()

def reset():
    global deck_cards, bot_hands, bot_ups, bot_downs, bot_positions

    for hand in bot_hands:
        for cid in hand:
            main.canvas.delete(cid)
    for ups in bot_ups:
        for cid in ups:
            main.canvas.delete(cid)
    for downs in bot_downs:
        for cid in downs:
            main.canvas.delete(cid)
    for cid in deck_cards:
        main.canvas.delete(cid)

    deck_cards = []
    bot_hands = []
    bot_ups = []
    bot_downs = []
    bot_positions = []
