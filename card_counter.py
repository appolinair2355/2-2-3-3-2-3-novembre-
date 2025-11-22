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

    def extract_groups(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Extrait les deux premiers groupes entre parenthèses"""
        groups = re.findall(r"\(([^)]*)\)", text)
        return groups[0] if len(groups) >= 1 else None, groups[1] if len(groups) >= 2 else None

    def normalize(self, s: str) -> str:
        return s if s.endswith("️") else s + "️"

    def count_symbols(self, group: str) -> int:
        """Retourne le nombre total de cartes uniques dans un groupe."""
        SYMBOLS = ("♠️", "♥️", "♦️", "♣️", "♠", "♥", "♦", "♣")
        seen_positions = set()
        unique_card_count = 0
        
        for sym in SYMBOLS:
            start = 0
            while True:
                pos = group.find(sym, start)
                if pos == -1:
                    break
                if pos not in seen_positions:
                    unique_card_count += 1
                    for i in range(len(sym)):
                        seen_positions.add(pos + i)
                start = pos + len(sym)
        
        return unique_card_count

    def get_total_unique_cards(self, group: str) -> int:
        """Alias pour le nombre total de cartes uniques."""
        return self.count_symbols(group)

    def update_pair_counts(self, msg_text: str, game_number: Optional[int]):
        """Met à jour le compteur des paires et stocke le numéro de jeu."""
        group1, group2 = self.extract_groups(msg_text)

        if not group1 or not group2:
            return

        # 1. Compter les cartes uniques dans chaque groupe
        count1 = self.get_total_unique_cards(group1)
        count2 = self.get_total_unique_cards(group2)
        
        # 2. Vérifier si les comptes sont 2 ou 3
        is_count1_valid = count1 in (2, 3)
        is_count2_valid = count2 in (2, 3)
        
        if is_count1_valid and is_count2_valid:
            # 3. Créer la clé de paire (ex: "2/3")
            pair_key = f"{count1}/{count2}"
            
            # 4. Mettre à jour le compteur global et la liste des jeux
            if pair_key in self._PAIR_DATA:
                data = self._PAIR_DATA[pair_key]
                data["count"] += 1
                if game_number is not None:
                    data["games"].append(game_number)

    def reset_all(self):
        """Réinitialise les compteurs de paires et les listes de jeux."""
        self._PAIR_DATA = {
            "2/2": {"count": 0, "games": []}, 
            "2/3": {"count": 0, "games": []}, 
            "3/2": {"count": 0, "games": []}, 
            "3/3": {"count": 0, "games": []}
        }
        print("🔄 Compteurs de paires réinitialisés après bilan horaire.")

    def get_instant_bilan_text(self) -> str:
        """Génère le petit message instantané envoyé après chaque jeu."""
        total_pairs = sum(data["count"] for data in self._PAIR_DATA.values())
        
        lines = [
            "✨ **Instantané** | Stats Paires ✨",
            "━━━━━━━━━━━━━━━━━━━━",
            f"📈 Total jeux analysés : **{total_pairs}**",
            ""
        ]
        
        # Émojis simples pour l'instantané
        emojis = {"2/2": "🃏", "3/3": "🔥", "3/2": "💪", "2/3": "🍀"}
        
        # MODIFICATION ICI : Changement de l'ordre d'affichage (3/2 en premier)
        pair_keys = ["3/2", "3/3", "2/2", "2/3"]
        
        for key in pair_keys:
            count = self._PAIR_DATA[key]["count"]
            pct = count * 100 / total_pairs if total_pairs > 0 else 0
            lines.append(f"• **{key}** : **{count}** ({pct:.1f} %) {emojis.get(key, '')}")
            
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)

    def _get_pairs_bilan_text(self) -> str:
        """Génère le Message 1 : Bilan Général des Paires (Décoré)."""
        total_pairs = sum(data["count"] for data in self._PAIR_DATA.values())
        
        if total_pairs == 0:
            return "Aucune donnée analysée pour le moment."

        lines = [
            "╔════════════════════╗",
            "📊 Bilan Général des Paires",
            "╚════════════════════╝",
            ""
        ]
        
        pair_data_style = {
            "2/2": {"color": "🖤", "emoji": "⬛"},
            "3/3": {"color": "❤️", "emoji": "🟥"},
            "3/2": {"color": "🧡", "emoji": "🔶"},
            "2/3": {"color": "💚", "emoji": "🟩"}
        }
        
        # MODIFICATION ICI : Changement de l'ordre d'affichage pour cohérence
        pair_keys = ["3/2", "3/3", "2/2", "2/3"]
        
        for key in pair_keys:
            data = self._PAIR_DATA.get(key, {"count": 0})
            count = data["count"]
            pct = count * 100 / total_pairs if total_pairs > 0 else 0
            style = pair_data_style[key]
            
            bar_length = int(pct / 10)
            bar = style["emoji"] * bar_length + "⬜" * (10 - bar_length)

            lines.append(f"{style['color']} **{key}**")
            lines.append(f"├─ Compteur: **{count}** numéros")
            lines.append(f"├─ Pourcentage: **{pct:.1f}%**")
            lines.append(f"└─ {bar}")
            lines.append("") 

        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"📌 Total: de numéro analysés : **{total_pairs}**")
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)

    def get_detailed_pair_bilans(self) -> Dict[str, str]:
        """
        Génère les 4 Messages (Bilans Particuliers) avec décoration et liste des numéros.
        """
        detailed_bilans = {}
        
        # MODIFICATION ICI : Changement de l'ordre d'affichage pour cohérence
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

    def get_bilan_text(self) -> str:
        """Retourne le Bilan Général (Message 1)."""
        return self._get_pairs_bilan_text().strip()
    
    def add(self, text: str):
        """Ajoute un message au compteur (extrait le numéro de jeu et compte les paires)."""
        import re
        game_number = None
        match = re.search(r'#N(\d+)', text)
        if match:
            game_number = int(match.group(1))
        self.update_pair_counts(text, game_number)
    
    def build_report(self) -> str:
        """Construit un rapport instantané."""
        return self.get_instant_bilan_text()
    
    def reset(self):
        """Réinitialise tous les compteurs."""
        self.reset_all()
    
    def report_and_reset(self) -> str:
        """Génère un rapport complet et réinitialise les compteurs."""
        general_bilan = self.get_bilan_text()
        detailed_bilans = self.get_detailed_pair_bilans()
        
        all_messages = [general_bilan]
        # Ordre de génération du rapport final (aussi mis à jour)
        for key in ["3/2", "3/3", "2/2", "2/3"]:
            if key in detailed_bilans:
                all_messages.append(detailed_bilans[key])
        
        self.reset_all()
        return "\n\n".join(all_messages)
        
