import random
import tkinter as tk
import __main__ as main

deck_cards = []  # The undealt deck is stored as a list; drawing uses pop()

bot_hands = []  # Each bot has its own hand, face-up list and face-down list
bot_ups = []
bot_downs = []
bot_positions = []

def compute_bot_positions(num_bots):  # Place one, two or three bots in distinct canvas locations
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
    cards.sort(key=lambda card: main.canvas.coords(card)[0])  # Retain the horizontal card order while repositioning the bot hand
    base_x, base_y = bot_positions[bot]
    start = base_x - (len(cards) - 1) * 20  # Centre the bot hand around its assigned screen position
    for i, card in enumerate(cards):
        main.canvas.coords(card, main.sx(start + i * 40), main.sy(base_y))

def reposition_b_up(bot):
    ups = bot_ups[bot]
    if not ups:
        return
    base_x, base_y = bot_positions[bot]
    slots = [  # Place face-up slots above the bot hand, aligned with hidden cards
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

def update_deck_label():
    remaining = len(deck_cards)
    if remaining:
        label_text = str(remaining)
        label_state = "normal"
    else:
        label_text = ""
        label_state = "hidden"

    main.canvas.itemconfigure(
        main.deck_label,
        text=label_text,
        state=label_state,
    )  # Hide the counter when no draw cards remain


def draw_p_hand():
    if deck_cards and len(main.get_p_hand()) < 3:  # Refill the human hand up to three cards while the deck is nonempty
        cid = deck_cards.pop()  # Take the next undealt card from the end of the shuffled deck
        update_deck_label()
        main.canvas.itemconfigure(cid, tags=("p_hand",))
        main.canvas.itemconfigure(cid, image=main.card_faces[cid])
        main.reposition_p_hand()

def draw_b_hand(bot):
    if deck_cards and len(bot_hands[bot]) < 3:  # Bot hands are also replenished up to three cards
        cid = deck_cards.pop()
        update_deck_label()
        main.canvas.itemconfigure(cid, tags=(f"b{bot}_hand",))
        main.canvas.itemconfigure(cid, image=main.card_backs[cid])
        bot_hands[bot].append(cid)
        reposition_b_hand(bot)

def any_legal_p():  # Search the player’s active card area for any legal move
    if main.p_phase == "hand":
        for card in main.get_p_hand():
            if main.can_play(card):
                return True
        return False
    if main.p_phase == "up":
        for card in main.p_up:
            if main.can_play(card):
                return True
        return False
    if main.p_phase == "down":
        return bool(main.p_down)  # Hidden cards must be tried blind, not inspected to decide on pickup
    return False

def pickup_pile(event=None):  # Handle a player clicking the pile to collect its cards
    if main.game_mode != "single":
        return
    if main.turn != "player":
        return
    if not main.pile_cards_list:
        return
    if any_legal_p():  # The player may pick up only when no legal play remains
        return
    pick_up_pile_player()

def update_pile_border():
    # The target outline appears only while the human is actively holding a card.
    if (main.game_mode != "single" or main.state != "play"
            or not main.session_active or main.turn != "player"
            or main.current_img is None or not main.selected_group):
        main.canvas.itemconfigure(main.slot_box_pile, state="hidden")
        return

    # A red border means no visible card in this phase can be played.
    # Do not inspect hidden cards while deciding what colour to show.
    must_pick_up = (bool(main.pile_cards_list)
                    and main.p_phase in ("hand", "up")
                    and not any_legal_p())
    if must_pick_up:
        border_colour = "red"
        border_width = 4
    else:
        border_colour = "white"
        border_width = 2

    main.canvas.itemconfigure(
        main.slot_box_pile,
        state="normal",
        outline=border_colour,
        width=border_width,
    )

def check_win():  # A win requires the player to have no hand, face-up or face-down cards
    if not main.get_p_hand() and not main.p_up and not main.p_down:
        main.session_active = False
        main.winScreen(main.root, main.canvas, True)
        return True

    if bot_hands:  # Check that every bot has finished before declaring a player loss
        all_empty = True
        for bot in range(len(bot_hands)):
            if bot_hands[bot] or bot_ups[bot] or bot_downs[bot]:
                all_empty = False
                break
        if all_empty:  # A loss is displayed only when no bot has any cards left
            main.session_active = False
            main.winScreen(main.root, main.canvas, False)
            return True
    return False

def pick_up_pile_player():  # Transfer all pile cards into the human player hand
    for cid in main.pile_cards_list:
        main.canvas.itemconfigure(cid, tags=("p_hand",))
        main.canvas.itemconfigure(cid, image=main.card_faces[cid])
    main.pile_cards_list.clear()
    main.p_phase = "hand"  # Taking the pile returns the player to the hand phase
    main.reposition_p_hand()
    next_bot_turn()  # Picking up ends the player's turn, including after an illegal move

def pick_up_pile_bot(bot):  # Transfer a collected pile into one particular bot hand
    for cid in main.pile_cards_list:
        main.canvas.itemconfigure(cid, tags=(f"b{bot}_hand",))
        main.canvas.itemconfigure(cid, image=main.card_backs[cid])
        bot_hands[bot].append(cid)
    main.pile_cards_list.clear()
    reposition_b_hand(bot)

def play_to_pile(cid, from_player=True, bot_index=None):  # Move a card onto the pile and process any special effects
    canvas = main.canvas
    canvas.coords(cid, *main.pile_pos)
    canvas.tag_raise(cid)  # Move the played card to the centre before applying rank effects
    canvas.itemconfigure(cid, tags=("pile",))
    canvas.itemconfigure(cid, image=main.card_faces[cid])
    main.pile_cards_list.append(cid)
    # The deck counter is updated by draw_p_hand/draw_b_hand after a replacement card is drawn.

    if main.card_ranks[cid] == "10":  # A ten burns the pile immediately
        main.burn_pile()
        if from_player:
            draw_p_hand()
        elif bot_index is not None:
            draw_b_hand(bot_index)
        return True  # A burn gives the same player or bot another turn

    if main.check_four_of_kind():  # Four consecutive cards of the same rank also burn the pile
        main.burn_pile()
        if from_player:
            draw_p_hand()
        elif bot_index is not None:
            draw_b_hand(bot_index)
        return True  # Four of a kind also gives another turn

    if main.card_ranks[cid] == "8":  # An eight marks the next player or bot turn to be skipped
        main.skip_next = True

    if from_player:
        draw_p_hand()
    elif bot_index is not None:
        draw_b_hand(bot_index)
    return False  # Normal play passes the turn to the next player

def create_deck(num_bots):  # Create, shuffle and deal the canvas cards for the selected bot count
    global bot_hands, bot_ups, bot_downs

    bot_hands = []  # Create independent card collections for the selected number of bots
    bot_ups = []
    bot_downs = []
    for bot in range(num_bots):
        bot_hands.append([])
        bot_ups.append([])
        bot_downs.append([])
    compute_bot_positions(num_bots)

    deck_specs = []  # Generate every rank-and-suit pair before shuffling the deck
    for suit in main.suits:
        for rank in main.ranks:
            deck_specs.append((rank, suit))
    random.shuffle(deck_specs)

    back_img = main.load_card(main.cards_dict("back"), 22, 22)
    main.card_width, main.card_height = back_img.width(), back_img.height()

    for i in range(3):  # Deal three initially hidden cards to the player
        r, s = deck_specs.pop()
        face = main.load_card(main.cards_dict(f"{r}{s}"), 5, 5)
        cid = main.canvas.create_image(*main.p_down_pos[i], image=back_img, tags=("p_down",))
        main.p_down.append(cid)
        main.card_ranks[cid] = r
        main.card_values[cid] = main.rank_values[r]
        main.card_faces[cid] = face
        main.card_backs[cid] = back_img

    for i in range(6):  # Deal six hand cards so three can later be chosen as face-up cards
        r, s = deck_specs.pop()
        face = main.load_card(main.cards_dict(f"{r}{s}"), 5, 5)
        cid = main.canvas.create_image(main.sx(700 + i * 60), main.sy(760), image=face, tags=("p_hand",))
        main.card_ranks[cid] = r
        main.card_values[cid] = main.rank_values[r]
        main.card_faces[cid] = face
        main.card_backs[cid] = back_img

    for bot in range(num_bots):  # Deal each bot separately to avoid mixing opponents cards
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

    for r, s in deck_specs:  # Turn all remaining undealt cards into the draw pile
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

def bot_choose_upcards():  # Bots select their initial face-up cards from their hand
    for bot in range(len(bot_hands)):
        hand = bot_hands[bot]
        if len(hand) < 3:
            continue
        chosen = sorted(hand, key=lambda card: main.card_values[card])[:3]  # Sort by rank and choose the three lowest-value cards
        for cid in chosen:
            main.canvas.itemconfigure(cid, tags=(f"b{bot}_up",))  # Reveal the selected bot cards while moving them into the face-up area
            main.canvas.itemconfigure(cid, image=main.card_faces[cid])
            bot_ups[bot].append(cid)
            if cid in hand:
                hand.remove(cid)
        reposition_b_up(bot)
        reposition_b_hand(bot)

def next_bot_turn():  # Delay bot actions so their turns are visible rather than instantaneous
    main.turn = "bot"  # Lock player input immediately, before the scheduled bot action
    update_pile_border()
    main.root.after(500, bot_play)

def play_single_bot(bot):  # Use a greedy choice: play the lowest legal card if possible
    hand = bot_hands[bot]
    ups = bot_ups[bot]
    downs = bot_downs[bot]

    if hand or deck_cards:  # Bots keep using hand cards while the deck still has cards
        phase = "hand"
    elif ups:
        phase = "up"
    else:
        phase = "down"

    if phase == "hand":
        legal = []  # Filter the bot hand to cards that meet the pile rule
        for card in hand:
            if main.can_play(card):
                legal.append(card)
        if not legal:  # Without a valid hand card, the bot has to pick up the pile
            if main.pile_cards_list:
                pick_up_pile_bot(bot)
            return
        cid = min(legal, key=lambda card: main.card_values[card])  # Choose the lowest ranked legal card from the filtered list
        if cid in hand:
            hand.remove(cid)
        return play_to_pile(cid, False, bot_index=bot)

    elif phase == "up":  # After the hand phase, the bot uses its face-up cards
        legal = []
        for card in ups:
            if main.can_play(card):
                legal.append(card)
        if not legal:  # Apply the same legal-card search to the bot face-up phase
            if main.pile_cards_list:
                pick_up_pile_bot(bot)
            return
        cid = min(legal, key=lambda card: main.card_values[card])
        if cid in ups:
            ups.remove(cid)
        return play_to_pile(cid, False, bot_index=bot)

    else:  # The face-down phase does not allow the bot to inspect its cards
        if not downs:
            return
        cid = random.choice(downs)  # Choose a hidden card at random to simulate a blind play
        downs.remove(cid)
        main.canvas.itemconfigure(cid, image=main.card_faces[cid])
        if not main.can_play(cid):  # An illegal hidden card is added to the pile before collecting it
            main.pile_cards_list.append(cid)
            pick_up_pile_bot(bot)
        else:
            return play_to_pile(cid, False, bot_index=bot)

def bot_play():  # Run each bot turn through scheduled Tkinter callbacks
    if not main.session_active:
        return
    main.turn = "bot"
    delay = 500
    n = len(bot_hands)

    def play_index(i):  # Advance through bots by index rather than a blocking loop
        if not main.session_active:
            return
        if i >= n:
            if main.skip_next:  # A skipped human turn starts another round of bot actions
                main.skip_next = False
                main.root.after(delay, bot_play)
                return
            main.turn = "player"  # Return control to the human player when the bots have finished
            main.update_p_phase()
            update_pile_border()  # Recheck the player's legal moves after the bots changed the pile
            return

        if main.skip_next:  # Skip the bot marked by the previously played eight
            main.skip_next = False
            main.root.after(delay, lambda: play_index(i + 1))
            return
        burned = play_single_bot(i)
        if check_win():
            return
        # If a bot burned the pile, it keeps its turn rather than advancing to the next bot.
        if burned:
            next_index = i
        else:
            next_index = i + 1
        main.root.after(delay, lambda: play_index(next_index))

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

        self.num_bots = tk.IntVar(value=1)  # Store the selected bot count until the player starts the match
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

def start_singleplayer(bots):  # Initialise game state, deal cards and register mouse actions
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

    main.canvas.bind("<ButtonPress-1>", main.start_drag)  # Connect mouse press, movement and release to the drag handlers
    main.canvas.bind("<B1-Motion>", main.do_drag)
    main.canvas.bind("<ButtonRelease-1>", main.end_drag)
    main.canvas.tag_bind("pile", "<Button-1>", pickup_pile)
    update_deck_label()
    main.show_home_button()

def reset():  # Remove old canvas items and state before starting another match
    global deck_cards, bot_hands, bot_ups, bot_downs, bot_positions

    for hand in bot_hands:  # Delete old bot card images so a new game starts with a clean canvas
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
