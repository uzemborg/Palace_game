import requests
server="http://192.168.68.58:5000"
class Net:
    def create(self):
        return requests.post(f"{server}/create").json()
    def join(self, game_id):
        url = f"{server}/join/{game_id}"
        print(f"Joining game at URL: {url}")
        r = requests.post(url, timeout=5)
        print(f"Response status code: {r.status_code}")
        print(f"Response: {r.text}")
        return r.json()
    def state(self, game_id):
        return requests.get(f"{server}/state/{game_id}").json()
    def hand(self, game_id, player_id):
        return requests.get(f"{server}/hand/{game_id}/{player_id}").json()
    def play(self, game_id, player_id, card):
        return requests.post(f"{server}/play/{game_id}", json={"card": card, "player": player_id}).json()
    def start(self, game_id):
        return requests.post(f"{server}/start/{game_id}").json()
    def player(self, game_id, player_id):
        return requests.get(f"{server}/player/{game_id}/{player_id}").json()
    def play_down(self, game_id, player_id):
        return requests.post(f"{server}/play_down/{game_id}",json={"player": player_id}).json()
    def setup(self, game_id, player_id, cards):
        return requests.post(f"{server}/setup/{game_id}", json={"player": player_id,"cards": cards}).json()
    def pickup(self, game_id, player_id):
        return requests.post(f"{server}/pickup/{game_id}", json={"player": player_id}).json()
    def has_move(self, game_id, player_id):
        return requests.get(f"{server}/has_move/{game_id}/{player_id}").json()