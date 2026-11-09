import os

def cards_dict(getcard):  # Convert a rank-and-suit code to the matching card image path
    base = os.path.join(os.path.dirname(__file__), "PNG-cards-1.3")
    dictcards = {}

    for i in range(2, 11):  # Create a filename lookup for the numbered cards in all four suits
        dictcards[f"{i}C"] = os.path.join(base, f"{i}_of_clubs.png")
        dictcards[f"{i}H"] = os.path.join(base, f"{i}_of_hearts.png")
        dictcards[f"{i}S"] = os.path.join(base, f"{i}_of_spades.png")
        dictcards[f"{i}D"] = os.path.join(base, f"{i}_of_diamonds.png")

    faces = {  # Face cards use word-based image filenames rather than numbers
        "J": "jack",
        "Q": "queen",
        "K": "king",
        "A": "ace"
    }

    for short, long in faces.items():  # Use the written face-card names that appear in image filenames
        dictcards[f"{short}C"] = os.path.join(base, f"{long}_of_clubs.png")
        dictcards[f"{short}H"] = os.path.join(base, f"{long}_of_hearts.png")
        dictcards[f"{short}S"] = os.path.join(base, f"{long}_of_spades.png")
        dictcards[f"{short}D"] = os.path.join(base, f"{long}_of_diamonds.png")

    dictcards["back"] = os.path.join(base, "back_of_card.png")  # Include a separate image for the reverse side of hidden cards

    return dictcards.get(getcard)