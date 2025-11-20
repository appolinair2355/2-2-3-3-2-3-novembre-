import re
from typing import Dict

class CardCounter:
    SYMBOLS = ("♠️", "♥️", "♦️", "♣️", "♠", "♥", "♦", "♣")
    _TOTAL = {s: 0 for s in ("♠️", "♥️", "♦️", "♣️")}

    def extract_first_group(self, text: str) -> str:
        """Extrait UNIQUEMENT le 1er groupe entre parenthèses"""
        groups = re.findall(r"\(([^)]*)\)", text)
        return groups[0] if len(groups) >= 1 else ""

    def normalize(self, s: str) -> str:
        return s if s.endswith("️") else s + "️"

    # ---- comptage : 1 par SYMBOLE unique (sans doublon) ----
    def count_symbols(self, group: str) -> Dict[str, int]:
        counts = {s: 0 for s in ("♠️", "♥️", "♦️", "♣️")}
        
        # Parcourir chaque symbole et compter UNE SEULE fois chaque occurrence
        seen_positions = set()
        for sym in self.SYMBOLS:
            normalized = self.normalize(sym)
            # Chercher toutes les positions du symbole
            start = 0
            while True:
                pos = group.find(sym, start)
                if pos == -1:
                    break
                # Vérifier si cette position n'a pas déjà été comptée
                if pos not in seen_positions:
                    counts[normalized] += 1
                    seen_positions.add(pos)
                start = pos + 1
        
        return counts

    def add(self, text: str) -> None:
        """Compte les symboles du 1er groupe uniquement"""
        first_group = self.extract_first_group(text)
        if not first_group: return
        counts = self.count_symbols(first_group)
        for s, c in counts.items():
            self._TOTAL[s] += c

    # ---- rapport SANS reset (instantané) ----
    def build_report(self) -> str:
        total = sum(self._TOTAL.values())
        if total == 0:
            return "📈 Compteur instantané\n♠️ : 0  (0.0 %)\n♥️ : 0  (0.0 %)\n♦️ : 0  (0.0 %)\n♣️ : 0  (0.0 %)"
        
        lines = ["📈 Compteur instantané"]
        
        for s in ("♠️", "♥️", "♦️", "♣️"):
            count = self._TOTAL[s]
            pct = count * 100 / total
            lines.append(f"{s} : {count}  ({pct:.1f} %)")
        
        return "\n".join(lines)

    # ---- bilan + reset (intervalle) ----
    def report_and_reset(self) -> str:
        total = sum(self._TOTAL.values())
        if total == 0:
            self._TOTAL = {s: 0 for s in ("♠️", "♥️", "♦️", "♣️")}
            return "╔════════════════════╗\n📊 Bilan 📊\n╚════════════════════╝\n\n🔍 Aucune carte comptabilisée"
        
        lines = [
            "╔════════════════════╗",
            "📊 Bilan 📊",
            "╚════════════════════╝",
            ""
        ]
        
        # Symboles avec émojis colorés
        symbols_data = {
            "♠️": {"name": "PIQUE", "emoji": "⬛", "color": "🖤"},
            "♥️": {"name": "COEUR", "emoji": "🟥", "color": "❤️"},
            "♦️": {"name": "CARREAU", "emoji": "🔶", "color": "🧡"},
            "♣️": {"name": "TRÈFLE", "emoji": "🟩", "color": "💚"}
        }
        
        for s in ("♠️", "♥️", "♦️", "♣️"):
            count = self._TOTAL[s]
            pct = count * 100 / total
            data = symbols_data[s]
            
            # Barre de progression visuelle
            bar_length = int(pct / 10)
            bar = data["emoji"] * bar_length + "⬜" * (10 - bar_length)
            
            lines.append(f"{data['color']} **{s} {data['name']}**")
            lines.append(f"├─ Compteur: **{count}** carte{'s' if count > 1 else ''}")
            lines.append(f"├─ Pourcentage: **{pct:.1f}%**")
            lines.append(f"└─ {bar}")
            lines.append("")
        
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"📌 Total: {total} carte{'s' if total > 1 else ''}")
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        
        self._TOTAL = {s: 0 for s in ("♠️", "♥️", "♦️", "♣️")}
        return "\n".join(lines)

    def reset(self) -> None:
        self._TOTAL = {s: 0 for s in ("♠️", "♥️", "♦️", "♣️")}
        
