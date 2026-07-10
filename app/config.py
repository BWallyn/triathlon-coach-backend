"""
Configuration de l'application lue depuis les variables d'environnement.

Les noms des athlètes sont volontairement tenus hors du code source : ils sont
définis via les variables d'environnement ATHLETE_B_NAME / ATHLETE_H_NAME
(ex: fichier .env en local, ou "secrets" sur Render/Vercel en production).

Les identifiants internes 'B' et 'H' restent fixes dans tout le code (clés de
base de données, types TypeScript, couleurs UI, etc.) — seul le nom affiché
change.
"""
# =================
# ==== IMPORTS ====
# =================

from __future__ import annotations

import os

# =================
# ==== OPTIONS ====
# =================

ATHLETE_B_NAME: str = os.getenv("ATHLETE_B_NAME", "Athlète B")
ATHLETE_H_NAME: str = os.getenv("ATHLETE_H_NAME", "Athlète H")

ATHLETE_NAMES: dict[str, str] = {
    "B": ATHLETE_B_NAME,
    "H": ATHLETE_H_NAME,
}
