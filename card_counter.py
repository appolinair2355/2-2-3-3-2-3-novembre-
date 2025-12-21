import re
from typing import Dict, List, Tuple, Optional, Any

class CardCounter:
    def __init__(self):
        # Initialisation des compteurs et des listes de jeux pour chaque paire
        self._PAIR_DATA: Dict[str, Dict[str, Any]] = {
            "2/2": {"count": 0, "games": []},
            "2/3": {"count": 0, "games": []},
            "3/2": {"count": 0, "games": []},
            "3/3": {"count": 0, "games": []}
        }
        
        # Nouveau tracking: Victoires, Impair/Pair, Match nul
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
        """Extrait les deux premiers groupes entre parenthèses"""
        groups = re.findall(r"\(([^)]*)\)", text)
        return groups[0] if len(groups) >= 1 else None, groups[1] if len(groups) >= 2 else None

    def extract_game_number(self, text: str) -> Optional[int]:
        """Extrait le numéro de jeu #N"""
        match = re.search(r'#N(\d+)', text)
        return int(match.group(1)) if match else None

    def extract_t_number(self, text: str) -> Optional[int]:
        """Extrait le numéro #T pour pair/impair"""
        match = re.search(r'#T(\d+)', text)
        return int(match.group(1)) if match else None

    def extract_points(self, text: str) -> Tuple[Optional[int], Optional[int]]:
        """Extrait les points Pg1 et Pg2 du format: #N1127. 1(A♠️3♠️7♣️) - ✅5(Q♠️5♦️J♦️)"""
        # Pattern: #N\d+\. ... chiffre ( ... ) - chiffre (
        # On cherche: un nombre avant une parenthèse, puis après le "-", un autre nombre avant une parenthèse
        pattern = r'#N\d+\.\s*(\d+)\([^)]*\)\s*-\s*[✅🔰]?(\d+)\('
        match = re.search(pattern, text)
        if match:
            pg1 = int(match.group(1))
            pg2 = int(match.group(2))
            return pg1, pg2
        return None, None

    def count_symbols(self, group: str) -> int:
        """
        ✅ CORRECTION BUG DE COMPTAGE
        Retourne le nombre total de cartes dans un groupe en comptant les symboles de carte.
        Utilise regex pour éviter le double comptage des symboles avec/sans variante emoji.
        """
        # Regex qui capture les symboles de carte (avec ou sans variante emoji FE0F)
        pattern = r'[♠♥♦♣]️?'
        matches = re.findall(pattern, group)
        count = len(matches)
        
        print(f"🔍 DEBUG: groupe='{group}' → {count} cartes détectées: {matches}")
        
        # Le jeu doit être soit 2 cartes, soit 3 cartes pour être valide
        if count in (2, 3):
            return count
        return 0

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

    def update_victories(self, msg_text: str, game_number: Optional[int]):
        """Analyse les victoires basées sur la position du checkmark (✅)"""
        
        # Match nul si 🔰 dans le message
        if "🔰" in msg_text:
            self._VICTORIES_DATA["nul"]["count"] += 1
            if game_number is not None:
                self._VICTORIES_DATA["nul"]["games"].append(game_number)
            return

        # Chercher la position du checkmark ✅
        # Pattern: ✅ peut être avant le premier groupe (victoire Joueur) ou avant le second groupe (victoire Banquier)
        # Exemple 1: #N151. 1(...) - ✅2(...) → Banquier a ✅ → Banquier gagne
        # Exemple 2: #N153. ✅7(...) - 3(...) → Joueur a ✅ → Joueur gagne
        
        # Chercher si ✅ est avant le premier groupe (nombre avant la parenthèse)
        pattern_joueur = r'#N\d+\.\s*✅\d+\('
        # Chercher si ✅ est avant le second groupe (après le tiret)
        pattern_banquier = r'-\s*✅\d+\('
        
        if re.search(pattern_joueur, msg_text):
            # Victoire Joueur (✅ avant le premier groupe)
            self._VICTORIES_DATA["joueur"]["count"] += 1
            if game_number is not None:
                self._VICTORIES_DATA["joueur"]["games"].append(game_number)
        elif re.search(pattern_banquier, msg_text):
            # Victoire Banquier (✅ avant le second groupe)
            self._VICTORIES_DATA["banquier"]["count"] += 1
            if game_number is not None:
                self._VICTORIES_DATA["banquier"]["games"].append(game_number)

    def update_odd_even(self, msg_text: str, game_number: Optional[int]):
        """Analyse pair/impair basé sur le numéro #T"""
        t_number = self.extract_t_number(msg_text)
        if t_number is None:
            return

        if t_number % 2 == 0:
            # Pair
            self._ODD_EVEN_DATA["even"]["count"] += 1
            if game_number is not None:
                self._ODD_EVEN_DATA["even"]["games"].append(game_number)
        else:
            # Impair
            self._ODD_EVEN_DATA["odd"]["count"] += 1
            if game_number is not None:
                self._ODD_EVEN_DATA["odd"]["games"].append(game_number)

    def reset_all(self):
        """Réinitialise les compteurs de paires et les listes de jeux."""
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

    # --- FONCTIONS D'ANALYSE 3K/2K ---
    
    def get_player_k_counts(self) -> Tuple[int, int]:
        """Calcule et retourne le total 3K et 2K basés sur le Joueur (le premier nombre dans X/Y)."""
        count_3k_joueur = self._PAIR_DATA["3/2"]["count"] + self._PAIR_DATA["3/3"]["count"]
        count_2k_joueur = self._PAIR_DATA["2/2"]["count"] + self._PAIR_DATA["2/3"]["count"]
        return count_3k_joueur, count_2k_joueur
    
    def get_banker_k_counts(self) -> Tuple[int, int]:
        """Calcule et retourne le total 3K et 2K basés sur le Banquier (le second nombre dans X/Y)."""
        count_3k_banker = self._PAIR_DATA["2/3"]["count"] + self._PAIR_DATA["3/3"]["count"]
        count_2k_banker = self._PAIR_DATA["2/2"]["count"] + self._PAIR_DATA["3/2"]["count"]
        return count_3k_banker, count_2k_banker


    # --- MISE À JOUR DU BILAN INSTANTANÉ (Message 1 - Prioritaire) ---

    def get_instant_bilan_text(self) -> str:
        """Génère la SYNTHÈSE INSTANTANÉE avec toutes les statistiques séparées et pourcentages."""
        total_pairs = sum(data["count"] for data in self._PAIR_DATA.values())
        
        if total_pairs == 0:
            return "✨ Statistiques Complètes ✨\n━━━━━━━━━━━━━━━━━━━━\n📈 Total jeux analysés : 0\n\nAucune donnée analysée pour le moment."

        lines = [
            "✨ STATISTIQUES COMPLÈTES ✨",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"📊 Total jeux analysés : {total_pairs}",
            ""
        ]

        # --- VICTOIRES JOUEUR/BANQUIER/NUL ---
        joueur_wins = self._VICTORIES_DATA["joueur"]["count"]
        banquier_wins = self._VICTORIES_DATA["banquier"]["count"]
        nul_wins = self._VICTORIES_DATA["nul"]["count"]
        
        lines.append("🎯 VICTOIRES (Joueur/Banquier/Nul)")
        lines.append("─────────────────────────────────")
        joueur_pct = joueur_wins * 100 / total_pairs if total_pairs > 0 else 0
        banquier_pct = banquier_wins * 100 / total_pairs if total_pairs > 0 else 0
        nul_pct = nul_wins * 100 / total_pairs if total_pairs > 0 else 0
        
        lines.append(f"👤 Joueur   : {joueur_wins:3d} ({joueur_pct:6.2f}%)")
        lines.append(f"🏦 Banquier : {banquier_wins:3d} ({banquier_pct:6.2f}%)")
        lines.append(f"⚖️  Nul      : {nul_wins:3d} ({nul_pct:6.2f}%)")
        lines.append("")

        # --- PAIR / IMPAIR ---
        odd_count = self._ODD_EVEN_DATA["odd"]["count"]
        even_count = self._ODD_EVEN_DATA["even"]["count"]
        
        lines.append("🔄 PAIR / IMPAIR")
        lines.append("─────────────────────────────────")
        even_pct = even_count * 100 / total_pairs if total_pairs > 0 else 0
        odd_pct = odd_count * 100 / total_pairs if total_pairs > 0 else 0
        
        lines.append(f"🔵 Pair   : {even_count:3d} ({even_pct:6.2f}%)")
        lines.append(f"🔴 Impair : {odd_count:3d} ({odd_pct:6.2f}%)")
        lines.append("")

        # --- ANALYSE JOUEUR/BANQUIER (3K/2K) ---
        count_3k_joueur, count_2k_joueur = self.get_player_k_counts()
        pct_3k_joueur = count_3k_joueur * 100 / total_pairs if total_pairs > 0 else 0
        pct_2k_joueur = count_2k_joueur * 100 / total_pairs if total_pairs > 0 else 0
        
        count_3k_banker, count_2k_banker = self.get_banker_k_counts()
        pct_3k_banker = count_3k_banker * 100 / total_pairs if total_pairs > 0 else 0
        pct_2k_banker = count_2k_banker * 100 / total_pairs if total_pairs > 0 else 0
        
        lines.append("👤 3K/2K JOUEUR")
        lines.append("─────────────────────────────────")
        lines.append(f"💪 3 Cartes (3K) : {count_3k_joueur:3d} ({pct_3k_joueur:6.2f}%)")
        lines.append(f"💼 2 Cartes (2K) : {count_2k_joueur:3d} ({pct_2k_joueur:6.2f}%)")
        lines.append("")
        
        lines.append("🏦 3K/2K BANQUIER")
        lines.append("─────────────────────────────────")
        lines.append(f"💪 3 Cartes (3K) : {count_3k_banker:3d} ({pct_3k_banker:6.2f}%)")
        lines.append(f"💼 2 Cartes (2K) : {count_2k_banker:3d} ({pct_2k_banker:6.2f}%)")
        lines.append("")
        
        lines.append("🃏 PAIRES (Détails)")
        lines.append("─────────────────────────────────")
        
        emojis = {"2/2": "🎯", "3/3": "🔥", "3/2": "💪", "2/3": "🍀"}
        pair_keys = ["3/2", "3/3", "2/2", "2/3"]
        
        for key in pair_keys:
            count = self._PAIR_DATA[key]["count"]
            pct = count * 100 / total_pairs if total_pairs > 0 else 0
            emoji = emojis.get(key, '')
            lines.append(f"{emoji} {key} : {count:3d} ({pct:6.2f}%)")
            
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)


    def _get_pairs_bilan_text(self) -> str:
        """Génère le Bilan Général des Paires (Décoré) (Message 2)."""
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
        
        pair_keys = ["3/2", "3/3", "2/2", "2/3"]
        
        for key in pair_keys:
            data = self._PAIR_DATA.get(key, {"count": 0, "games": []})
            count = data["count"]
            pct = count * 100 / total_pairs if total_pairs > 0 else 0
            style = pair_data_style[key]
            
            bar_length = int(pct / 10) # 10 icônes max
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
        Génère les Bilans Détaillés (Liste des numéros de jeu) (Messages 3, 4, 5, 6).
        """
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
                # Affichage de 10 numéros par ligne pour la lisibilité
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
        """Retourne le Bilan Général."""
        return self._get_pairs_bilan_text().strip()
    
    def add(self, text: str):
        """Ajoute un message au compteur (extrait les numéros de jeu et compte les paires)."""
        game_number = self.extract_game_number(text)
        self.update_pair_counts(text, game_number)
        self.update_victories(text, game_number)
        self.update_odd_even(text, game_number)
    
    def build_report(self) -> str:
        """Construit un rapport instantané (synthèse rapide)."""
        return self.get_instant_bilan_text()
    
    def reset(self):
        """Réinitialise tous les compteurs."""
        self.reset_all()
    
    def report_and_reset(self) -> str:
        """
        [ORDRE D'ENVOI FINAL]
        Génère un rapport complet et réinitialise les compteurs.
        Ordre : 1. Synthèse (Victoires/Impair-Pair/Joueur/Banquier), 2. Bilan Général, 3. Bilans Détaillés.
        """
        # 1. Générer le rapport INSTANTANÉ/SYNTHÈSE - Message 1
        instant_bilan = self.get_instant_bilan_text()
        
        # 2. Générer le Bilan Général (Décoré) - Message 2
        general_bilan = self.get_bilan_text()
        
        # 3. Générer les Bilans Détaillés (Listes de jeux)
        detailed_bilans = self.get_detailed_pair_bilans()
        
        all_messages = []
        
        # --- ORDRE D'ENVOI FINAL ---
        all_messages.append(instant_bilan)
        all_messages.append(general_bilan)
        
        # Bilans Détaillés par paire
        for key in ["3/2", "3/3", "2/2", "2/3"]:
            if key in detailed_bilans:
                all_messages.append(detailed_bilans[key])
        
        self.reset_all()
        return "\n\n".join(all_messages)
