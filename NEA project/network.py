import requests
server="https://palace-game.onrender.com"  # Address of the Flask game server used by the client

class Net:
    def _request(self, method, url, **kwargs):  # Centralised request helper with network and JSON error handling
        try:
            response = requests.request(method, url, timeout=5, **kwargs)  # Stop a request after five seconds rather than waiting indefinitely
        except requests.exceptions.ConnectionError:
            return {"error": "Could not reach the server. Check your internet connection and try again."}
        except requests.exceptions.Timeout:
            return {"error": "The server took too long to respond. Please try again."}
        except requests.exceptions.RequestException as e:
            return {"error": f"Network error: {e}"}

        try:  # A valid HTTP response might still contain invalid JSON
            return response.json()
        except ValueError:
            return {"error": f"Server returned an unexpected response (status {response.status_code})."}

    def create(self, match_type):  # Ask Flask to create a new session and return its join code
        return self._request("POST", f"{server}/create", json={"match_type": match_type})

    def join(self, game_id):
        url = f"{server}/join/{game_id}"
        print(f"Joining game at URL: {url}")
        r = requests.post(url, timeout=5)
        print(f"Response status code: {r.status_code}")
        print(f"Response: {r.text}")
        return r.json()

    def state(self, game_id):  # Retrieve the public match state for periodic screen updates
        return requests.get(f"{server}/state/{game_id}").json()

    def hand(self, game_id, player_id):
        return requests.get(f"{server}/hand/{game_id}/{player_id}").json()

    def play(self, game_id, player_id, cards):
        return requests.post(f"{server}/play/{game_id}", json={"cards": cards, "player": player_id}).json()  # Send the selected card records and player ID for server validation

    def start(self, game_id):
        return requests.post(f"{server}/start/{game_id}").json()

    def player(self, game_id, player_id):  # Request the local player hand and face-up records for display
        return requests.get(f"{server}/player/{game_id}/{player_id}").json()

    def play_down(self, game_id, player_id):
        return requests.post(f"{server}/play_down/{game_id}",json={"player": player_id}).json()  # Face-down cards are selected by the server rather than the client

    def setup(self, game_id, player_id, cards):  # Submit the three selected face-up cards during game setup
        return requests.post(f"{server}/setup/{game_id}", json={"player": player_id,"cards": cards}).json()

    def pickup(self, game_id, player_id):  # Ask the server to move the pile into the active player hand
        return requests.post(f"{server}/pickup/{game_id}", json={"player": player_id}).json()

    def has_move(self, game_id, player_id):
        return requests.get(f"{server}/has_move/{game_id}/{player_id}").json()