import re
from typing import Tuple, Optional, List

class CardPredictor:
    def __init__(self):
        self.prediction_status = {}
        self.prediction_messages = {}
        self.status_log = []

    def reset(self):
        self.prediction_status.clear()
        self.prediction_messages.clear()
        self.status_log.clear()
        print("Données de prédiction réinitialisées")

    def extract_game_number(self, msg: str) -> Optional[int]:
        m = re.search(r"#N\s*(\d+)\.?|jeu\s*#?\s*(\d+)", msg, re.I)
        return int(m.group(1) or m.group(2)) if m else None

    def verify_prediction(self, msg: str) -> Tuple[Optional[bool], Optional[int]]:
        if "⏰" in msg or "🕐" in msg: return None, None
        if not any(t in msg for t in ("✅", "🔰", "❌", "⭕")): return None, None
        gn = self.extract_game_number(msg)
        if gn is None: return None, None
        # logique existante non utilisée ici → laissée vide
        return None, None

    def store_prediction_message(self, n: int, mid: int, cid: int):
        self.prediction_messages[n] = {"message_id": mid, "chat_id": cid}

    def get_prediction_message(self, n: int):
        return self.prediction_messages.get(n)
        
