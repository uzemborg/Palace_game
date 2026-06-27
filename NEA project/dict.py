import os

def cards_dict(getcard):
    base = os.path.join(os.path.dirname(__file__), "PNG-cards-1.3")
    dictcards = {}

    for i in range(2, 11):
        dictcards[f"{i}C"] = os.path.join(base, f"{i}_of_clubs.png")
        dictcards[f"{i}H"] = os.path.join(base, f"{i}_of_hearts.png")
        dictcards[f"{i}S"] = os.path.join(base, f"{i}_of_spades.png")
        dictcards[f"{i}D"] = os.path.join(base, f"{i}_of_diamonds.png")

    faces = {
        "J": "jack",
        "Q": "queen",
        "K": "king",
        "A": "ace"
    }

    for short, long in faces.items():
        dictcards[f"{short}C"] = os.path.join(base, f"{long}_of_clubs.png")
        dictcards[f"{short}H"] = os.path.join(base, f"{long}_of_hearts.png")
        dictcards[f"{short}S"] = os.path.join(base, f"{long}_of_spades.png")
        dictcards[f"{short}D"] = os.path.join(base, f"{long}_of_diamonds.png")

    dictcards["back"] = os.path.join(base, "back_of_card.png")

    return dictcards.get(getcard)