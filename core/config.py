# core/config.py
from dataclasses import dataclass
import os
import streamlit as st


@dataclass(frozen=True)
class AppConfig:
    # labels
    INTENT: list
    URGENCY: list
    EVENTS: list

    # app
    APP_TITLE: str

    # auth secrets
    APP_USER: str
    APP_SALT: str
    APP_PASS_SHA256: str

    # remember-me
    AUTH_TTL_DAYS: int
    AUTH_STORE_PATH: str
    QP_TOKEN_KEY: str

    # branding login
    APP_BRAND: str
    LOGIN_HERO_URL: str


def load_config() -> AppConfig:
    base_dir = os.path.dirname(os.path.dirname(__file__))  # project root
    auth_store = os.path.join(base_dir, ".auth_tokens.json")

    INTENT = ["SOS", "SOS_POSSIBLE", "NON_SOS"]
    URGENCY = ["HIGH", "MEDIUM", "LOW"]
    EVENTS = [
        "INJURY_MEDICAL",
        "TRAPPED_LOST",
        "COLLISION_VEHICLE",
        "FIRE_EXPLOSION",
        "HAZMAT_RELEASE",
        "GROUND_FAILURE",
        "ELECTRICAL",
        "SECURITY_ASSAULT",
    ]

    APP_USER = st.secrets.get("APP_USER", "admin")
    APP_SALT = st.secrets.get("APP_SALT", "")
    APP_PASS_SHA256 = st.secrets.get("APP_PASS_SHA256", "")

    ttl = int(st.secrets.get("AUTH_TTL_DAYS", os.getenv("AUTH_TTL_DAYS", "14")))

    brand = st.secrets.get("APP_BRAND", "MZone Dataset Review")
    hero = st.secrets.get(
        "LOGIN_HERO_URL",
        "https://images.unsplash.com/photo-1554224155-6726b3ff858f?auto=format&fit=crop&w=1600&q=80",
    )

    return AppConfig(
        INTENT=INTENT,
        URGENCY=URGENCY,
        EVENTS=EVENTS,
        APP_TITLE="MZone Dataset Review (DB)",
        APP_USER=APP_USER,
        APP_SALT=APP_SALT,
        APP_PASS_SHA256=APP_PASS_SHA256,
        AUTH_TTL_DAYS=ttl,
        AUTH_STORE_PATH=auth_store,
        QP_TOKEN_KEY="t",
        APP_BRAND=brand,
        LOGIN_HERO_URL=hero,
    )
