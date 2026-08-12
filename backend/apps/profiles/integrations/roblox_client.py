import requests


class RobloxClient:
    BASE_URL = "https://users.roblox.com/v1"

    def get_user_by_username(self, username):
        r = requests.post(f"{self.BASE_URL}/usernames/users",
                           json={"usernames": [username], "excludeBannedUsers": True}, timeout=10)
        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            raise ValueError("Игрок не найден в Roblox")
        return data[0]

    def get_user_details(self, user_id):
        r = requests.get(f"{self.BASE_URL}/users/{user_id}", timeout=10)
        r.raise_for_status()
        return r.json()

    def get_friends_count(self, user_id):
        r = requests.get(f"https://friends.roblox.com/v1/users/{user_id}/friends/count", timeout=10)
        r.raise_for_status()
        return r.json().get("count", 0)

    def get_followers_count(self, user_id):
        r = requests.get(f"https://friends.roblox.com/v1/users/{user_id}/followers/count", timeout=10)
        r.raise_for_status()
        return r.json().get("count", 0)