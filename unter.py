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

    def extract_groups(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Extrait les deux premiers groupes entre parenthèses"""
        groups = re.findall(r"\(([^)]*)\)", text)
        return groups[0] if len(groups) >= 1 else None, groups[1] if len(groups) >= 2 else None

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

                       
