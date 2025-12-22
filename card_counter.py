import re
from typing import Dict, List, Tuple, Optional, Any

class CardCounter:
    def __init__(self):
        self._PAIR_DATA: Dict[str, Dict[str, Any]] = {
            "2/2": {"count": 0, "games": []},
            "2/3": {"count": 0, "games": []},
            "3/2": {"count": 0, "games": []},
            "3/3": {"count": 0, "games": []}
        }
        self._VICTORIES_DATA = {
            "joueur": {"count": 0, "games": []},
            "banquier": {"count": 0, "games": []},
            "nul": {"count": 0, "games": []}
        }
        self._ODD_EVEN_DATA = {
            "odd": {"count": 0, "games": []},
            "even": {"count": 0, "games": []}
        }

    def extract_groups(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        groups = re.findall(r"\(([^)]*)\)", text)
        return groups[0] if len(groups) >= 1 else None, groups[1] if len(groups) >= 2 else None

    def extract_game_number(self, text: str) -> Optional[int]:
        match = re.search(r'#N(\d+)', text)
        return int(match.group(1)) if match else None

    def extract_t_number(self, text: str) -> Optional[int]:
        match = re.search(r'#T(\d+)', text)
        return int(match.group(1)) if match else None

    def extract_points(self, text: str) -> Tuple[Optional[int], Optional[int]]:
        pattern = r'#N\d+\.\s*(\d+)\([^)]*\)\s*-\s*[✅🔰]?(\d+)\('
        match = re.search(pattern, text)
        if match:
            return int(match.group(1)), int(match.group(2))
        return None, None

    def count_symbols(self, group: str) -> int:
        pattern = r'[♠♥♦♣]️?'
        matches = re.findall(pattern, group)
        count = len(matches)
        if count in (2, 3):
            return count
        return 0

    def get_total_unique_cards(self, group: str) -> int:
        return self.count_symbols(group)

    def update_pair_counts(self, msg_text: str, game_number: Optional[int]):
        group1, group2 = self.extract_groups(msg_text)
        if not group1 or not group2:
            return
        count1 = self.get_total_unique_cards(group1)
        count2 = self.get_total_unique_cards(group2)
        if count1 in (2, 3) and count2 in (2, 3):
            pair_key = f"{count1}/{count2}"
            if pair_key in self._PAIR_DATA:
                data = self._PAIR_DATA[pair_key]
                data["count"] += 1
                if game_number is not None:
                    data["games"].append(game_number)

    def update_victories(self, msg_text: str, game_number: Optional[int]):
        if "🔰" in msg_text:
            self._VICTORIES_DATA["nul"]["count"] += 1
            if game_number is not None:
                self._VICTORIES_DATA["nul"]["games"].append(game_number)
            return
        pattern_joueur = r'#N\d+\.\s*✅\d+\('
        pattern_banquier = r'-\s*✅\d+\('
        if re.search(pattern_joueur, msg_text):
            self._VICTORIES_DATA["joueur"]["count"] += 1
            if game_number is not None:
                self._VICTORIES_DATA["joueur"]["games"].append(game_number)
        elif re.search(pattern_banquier, msg_text):
            self._VICTORIES_DATA["banquier"]["count"] += 1
            if game_number is not None:
                self._VICTORIES_DATA["banquier"]["games"].append(game_number)

    def update_odd_even(self, msg_text: str, game_number: Optional[int]):
        t_number = self.extract_t_number(msg_text)
        if t_number is None:
            return
        if t_number % 2 == 0:
            self._ODD_EVEN_DATA["even"]["count"] += 1
            if game_number is not None:
                self._ODD_EVEN_DATA["even"]["games"].append(game_number)
        else:
            self._ODD_EVEN_DATA["odd"]["count"] += 1
            if game_number is not None:
                self._ODD_EVEN_DATA["odd"]["games"].append(game_number)

    def reset_all(self):
        self._PAIR_DATA = {
            "2/2": {"count": 0, "games": []},
            "2/3": {"count": 0, "games": []},
            "3/2": {"count": 0, "games": []},
            "3/3": {"count": 0, "games": []}
        }
        self._VICTORIES_DATA = {
            "joueur": {"count": 0, "games": []},
            "banquier": {"count": 0, "games": []},
            "nul": {"count": 0, "games": []}
        }
        self._ODD_EVEN_DATA = {
            "odd": {"count": 0, "games": []},
            "even": {"count": 0, "games": []}
        }

    def get_player_k_counts(self) -> Tuple[int, int]:
        count_3k_joueur = self._PAIR_DATA["3/2"]["count"] + self._PAIR_DATA["3/3"]["count"]
        count_2k_joueur = self._PAIR_DATA["2/2"]["count"] + self._PAIR_DATA["2/3"]["count"]
        return count_3k_joueur, count_2k_joueur

    def get_banker_k_counts(self) -> Tuple[int, int]:
        count_3k_banker = self._PAIR_DATA["2/3"]["count"] + self._PAIR_DATA["3/3"]["count"]
        count_2k_banker = self._PAIR_DATA["2/2"]["count"] + self._PAIR_DATA["3/2"]["count"]
        return count_3k_banker, count_2k_banker

    def get_instant_bilan_text(self) -> str:
        total_pairs = sum(data["count"] for data in self._PAIR_DATA.values())
        if total_pairs == 0:
            return "✨ Statistiques Complètes ✨\n━━━━━━━━━━━━━━━━━━━━\n📈 Total jeux analysés : 0\n\nAucune donnée analysée pour le moment."

        lines = [
            "✨ STATISTIQUES COMPLÈTES ✨",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"📊 Total jeux analysés : {total_pairs}",
            ""
        ]

        joueur_wins = self._VICTORIES_DATA["joueur"]["count"]
        banquier_wins = self._VICTORIES_DATA["banquier"]["count"]
        nul_wins = self._VICTORIES_DATA["nul"]["count"]
        joueur_pct = joueur_wins * 100 / total_pairs if total_pairs > 0 else 0
        banquier_pct = banquier_wins * 100 / total_pairs if total_pairs > 0 else 0
        nul_pct = nul_wins * 100 / total_pairs if total_pairs > 0 else 0

        lines.extend([
            "🎯 VICTOIRES (Joueur/Banquier/Nul)",
            "─────────────────────────────────",
            f"👤 Joueur   : {joueur_wins:3d} ({joueur_pct:6.2f}%)",
            f"🏦 Banquier : {banquier_wins:3d} ({banquier_pct:6.2f}%)",
            f"⚖️  Nul      : {nul_wins:3d} ({nul_pct:6.2f}%)",
            ""
        ])

        odd_count = self._ODD_EVEN_DATA["odd"]["count"]
        even_count = self._ODD_EVEN_DATA["even"]["count"]
        even_pct = even_count * 100 / total_pairs if total_pairs > 0 else 0
        odd_pct = odd_count * 100 / total_pairs if total_pairs > 0 else 0

        lines.extend([
            "🔄 PAIR / IMPAIR",
            "─────────────────────────────────",
            f"🔵 Pair   : {even_count:3d} ({even_pct:6.2f}%)",
            f"🔴 Impair : {odd_count:3d} ({odd_pct:6.2f}%)",
            ""
        ])

        count_3k_joueur, count_2k_joueur = self.get_player_k_counts()
        pct_3k_joueur = count_3k_joueur * 100 / total_pairs if total_pairs > 0 else 0
        pct_2k_joueur = count_2k_joueur * 100 / total_pairs if total_pairs > 0 else 0

        lines.extend([
            "👤 3K/2K JOUEUR",
            "─────────────────────────────────",
            f"💪 3 Cartes (3K) : {count_3k_joueur:3d} ({pct_3k_joueur:6.2f}%)",
            f"💼 2 Cartes (2K) : {count_2k_joueur:3d} ({pct_2k_joueur:6.2f}%)",
            ""
        ])

        count_3k_banker, count_2k_banker = self.get_banker_k_counts()
        pct_3k_banker = count_3k_banker * 100 / total_pairs if total_pairs > 0 else 0
        pct_2k_banker = count_2k_banker * 100 / total_pairs if total_pairs > 0 else 0

        lines.extend([
            "🏦 3K/2K BANQUIER",
            "─────────────────────────────────",
            f"💪 3 Cartes (3K) : {count_3k_banker:3d} ({pct_3k_banker:6.2f}%)",
            f"💼 2 Cartes (2K) : {count_2k_banker:3d} ({pct_2k_banker:6.2f}%)",
            ""
        ])

        lines.extend([
            "🃏 PAIRES (Détails)",
            "─────────────────────────────────"
        ])

        emojis = {"2/2": "🎯", "3/3": "🔥", "3/2": "💪", "2/3": "🍀"}
        pair_keys = ["3/2", "3/3", "2/2", "2/3"]

        for key in pair_keys:
            count = self._PAIR_DATA[key]["count"]
            pct = count * 100 / total_pairs if total_pairs > 0 else 0
            emoji = emojis.get(key, '')
            lines.append(f"{emoji} {key} : {count:3d} ({pct:6.2f}%)")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)

    def get_detailed_pair_bilans(self) -> Dict[str, str]:
        detailed_bilans = {}
        pair_keys = ["3/2", "3/3", "2/2", "2/3"]
        pair_styles = {
            "2/2": {"title": "L'Équilibre du Tapis", "deco": "♦️♣️🎲", "emoji": "🃏"},
            "3/3": {"title": "Le Jackpot des Trois Cartes", "deco": "👑♠️♥️", "emoji": "🔥"},
            "3/2": {"title": "La Main Forte du Joueur", "deco": "🎴🎯✨", "emoji": "💪"},
            "2/3": {"title": "Le Tirage GAGNANT", "deco": "💫💰🎉", "emoji": "🍀"}
        }

        for key in pair_keys:
            data = self._PAIR_DATA.get(key, {"count": 0, "games": []})
            games: List[int] = data["games"]
            count: int = data["count"]
            style = pair_styles[key]

            if not games:
                games_str = "Aucun jeu enregistré dans cette configuration. 🎲"
            else:
                games_with_prefix = [f"**#N{g}**" for g in games]
                lines = []
                for i in range(0, len(games_with_prefix), 10):
                    lines.append(" ".join(games_with_prefix[i:i + 10]))
                games_str = "\n".join(lines)

            bilan_text = [
                f"┏━━━━━━ {style['deco']} **{style['title']}** ({key}) {style['deco']} ━━━━━━┓",
                f"🎯 **Configuration**: {key} | Total des numéros: **{count}** {style['emoji']}",
                f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛",
                "",
                f"**🎰 La liste des numéros (Chronologique) :**",
                "--------------------------------------------------",
                games_str,
                "--------------------------------------------------",
                ""
            ]
            detailed_bilans[key] = "\n".join(bilan_text)

        return detailed_bilans

    def report_and_reset(self) -> str:
        instant_bilan = self.get_instant_bilan_text()
        general_bilan = self.get_bilan_text()
        detailed_bilans = self.get_detailed_pair_bilans()

        all_messages = []
        all_messages.append(instant_bilan)
        all_messages.append(general_bilan)

        for key in ["3/2", "3/3", "2/2", "2/3"]:
            if key in detailed_bilans:
                all_messages.append(detailed_bilans[key])

        self.reset_all()
        return "\n\n".join(all_messages)

    def add(self, text: str):
        game_number = self.extract_game_number(text)
        self.update_pair_counts(text, game_number)
        self.update_victories(text, game_number)
        self.update_odd_even(text, game_number)

    def build_report(self) -> str:
        return self.get_instant_bilan_text()

    def reset(self):
        self.reset_all()
