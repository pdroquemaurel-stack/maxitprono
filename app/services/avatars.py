"""Avatars par défaut : initiales du pseudo (en attendant les photos de profil)."""
import re


def initials(nickname: str) -> str:
    """« Kevin_M » -> « KM », « Awa » -> « AW », « 007 » -> « 00 »."""
    parts = [part for part in re.split(r"[\s_\-]+", nickname) if part]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return nickname[:2].upper()
