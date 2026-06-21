"""
Configuration for the Haiti Anger Index Agent.
All API keys and secrets should be set via environment variables.
"""

import os

# ─── API credentials ──────────────────────────────────────────────────────────

TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", "")

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "HaitiAngerIndex/1.0 (by POLLNEX)")

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

FACEBOOK_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN", "")

# ─── Storage ──────────────────────────────────────────────────────────────────

DB_PATH = os.getenv("HAI_DB_PATH", "haiti_anger_index.db")
REPORTS_DIR = os.getenv("HAI_REPORTS_DIR", "reports")

# ─── Crawler settings ─────────────────────────────────────────────────────────

# Max posts to fetch per run per platform
MAX_POSTS_PER_PLATFORM = int(os.getenv("MAX_POSTS_PER_PLATFORM", "200"))

# Crawl delay in seconds between API calls
CRAWL_DELAY = float(os.getenv("CRAWL_DELAY", "1.0"))

# ─── Keywords for searching Haitian-related content ───────────────────────────

SEARCH_KEYWORDS = [
    # English
    "Haiti", "Haitian", "Port-au-Prince", "gang Haiti", "crisis Haiti",
    "Haiti government", "Haiti earthquake", "Haiti economy",
    # French
    "Haïti", "haïtien", "haïtienne", "gouvernement haïtien",
    "crise en Haïti", "Port-au-Prince",
    # Haitian Creole
    "Ayiti", "ayisyen", "peyi a", "leta ayiti", "kriz Ayiti",
    "gang yo", "pèp ayisyen", "prezidan Ayiti",
]

TWITTER_SEARCH_QUERIES = [
    "(Haiti OR Haïti OR Ayiti) lang:en",
    "(Haiti OR Haïti OR Ayiti) lang:fr",
    "(Haiti OR Haïti OR Ayiti OR ayisyen OR peyi) lang:ht",
]

REDDIT_SUBREDDITS = [
    "haiti",
    "caribbean",
    "latinamerica",
    "worldnews",
    "news",
]

YOUTUBE_SEARCH_TERMS = [
    "Haiti news",
    "Haïti actualité",
    "Ayiti nouvèl",
    "Haiti crisis 2025",
    "Haiti gang violence",
]

# ─── Haitian news RSS feeds ───────────────────────────────────────────────────

RSS_FEEDS = {
    "Le Nouvelliste": "https://lenouvelliste.com/feed/",
    "Haiti Libre": "https://www.haitilibre.com/rss.xml",
    "AlterPresse": "https://www.alterpresse.org/feed/",
    "Haiti Info Projet": "https://haitiinfoproject.org/feed/",
    "Loop Haiti": "https://loophaiti.com/feed/",
    "Rezo Nodwes": "https://rezonodwes.com/feed/",
    "Gazette Haiti": "https://gazettehaiti.com/feed/",
    "HPN Haiti": "https://www.hpnhaiti.com/feed/",
    "Radio Kiskeya": "https://radiokiskeya.com/feed/",
    "Haiti Chery": "https://www.haitichery.com/feed/",
}

# ─── Topic categories and severity weights ────────────────────────────────────

TOPICS = {
    "government_corruption": {
        "label": "Government & Corruption",
        "label_fr": "Gouvernement & Corruption",
        "label_ht": "Gouvènman & Koripsyon",
        "weight": 1.5,
        "keywords_en": ["corruption", "government", "president", "parliament", "prime minister", "coup", "democracy"],
        "keywords_fr": ["corruption", "gouvernement", "président", "parlement", "premier ministre", "coup d'état"],
        "keywords_ht": ["koripsyon", "gouvènman", "prezidan", "palman", "premier minis", "demokrasi"],
    },
    "public_safety": {
        "label": "Public Safety & Crime",
        "label_fr": "Sécurité Publique",
        "label_ht": "Sekirite Piblik",
        "weight": 1.4,
        "keywords_en": ["gang", "kidnapping", "violence", "murder", "shooting", "crime", "police", "security"],
        "keywords_fr": ["gang", "enlèvement", "violence", "meurtre", "fusillade", "criminalité", "police", "sécurité"],
        "keywords_ht": ["gang", "kidnaping", "vyolans", "mèt", "tire", "krim", "lapolis", "sekirite"],
    },
    "economy": {
        "label": "Economy & Poverty",
        "label_fr": "Économie & Pauvreté",
        "label_ht": "Ekonomi & Pòvrete",
        "weight": 1.3,
        "keywords_en": ["economy", "poverty", "unemployment", "inflation", "price", "money", "dollar", "hunger", "food"],
        "keywords_fr": ["économie", "pauvreté", "chômage", "inflation", "prix", "argent", "famine", "nourriture"],
        "keywords_ht": ["ekonomi", "pòvrete", "chomaj", "enflasyon", "pri", "lajan", "grangou", "manje"],
    },
    "natural_disaster": {
        "label": "Natural Disasters",
        "label_fr": "Catastrophes Naturelles",
        "label_ht": "Katastwòf Natirèl",
        "weight": 1.2,
        "keywords_en": ["earthquake", "hurricane", "flood", "disaster", "storm", "cyclone"],
        "keywords_fr": ["tremblement de terre", "ouragan", "inondation", "catastrophe", "tempête", "cyclone"],
        "keywords_ht": ["tranblemanntè", "siklòn", "inondasyon", "katastwòf", "tanpèt"],
    },
    "health": {
        "label": "Health & Healthcare",
        "label_fr": "Santé",
        "label_ht": "Sante",
        "weight": 1.1,
        "keywords_en": ["health", "hospital", "cholera", "disease", "medicine", "doctor", "epidemic"],
        "keywords_fr": ["santé", "hôpital", "choléra", "maladie", "médicament", "médecin", "épidémie"],
        "keywords_ht": ["sante", "lopital", "kolera", "maladi", "medikaman", "doktè", "epidemi"],
    },
    "infrastructure": {
        "label": "Infrastructure",
        "label_fr": "Infrastructure",
        "label_ht": "Enfrastrikti",
        "weight": 1.0,
        "keywords_en": ["electricity", "water", "road", "infrastructure", "fuel", "gas", "internet"],
        "keywords_fr": ["électricité", "eau", "route", "infrastructure", "carburant", "internet"],
        "keywords_ht": ["elektrisite", "dlo", "wout", "enfrastrikti", "gaz", "entènèt"],
    },
    "human_rights": {
        "label": "Human Rights & Diaspora",
        "label_fr": "Droits Humains & Diaspora",
        "label_ht": "Dwa Moun & Dyaspora",
        "weight": 1.3,
        "keywords_en": ["human rights", "deportation", "diaspora", "refugee", "abuse", "freedom", "protest"],
        "keywords_fr": ["droits humains", "déportation", "diaspora", "réfugié", "abus", "liberté", "manifestation"],
        "keywords_ht": ["dwa moun", "depòtasyon", "dyaspora", "refijye", "abi", "libète", "manifestasyon"],
    },
    "education": {
        "label": "Education",
        "label_fr": "Éducation",
        "label_ht": "Edikasyon",
        "weight": 0.9,
        "keywords_en": ["education", "school", "teacher", "university", "students"],
        "keywords_fr": ["éducation", "école", "enseignant", "université", "étudiants"],
        "keywords_ht": ["edikasyon", "lekòl", "pwofesè", "inivèsite", "elèv"],
    },
    "international_relations": {
        "label": "International Relations",
        "label_fr": "Relations Internationales",
        "label_ht": "Relasyon Entènasyonal",
        "weight": 0.9,
        "keywords_en": ["UN", "United Nations", "USA", "CARICOM", "Kenya", "aid", "international", "sanctions"],
        "keywords_fr": ["ONU", "Nations Unies", "États-Unis", "CARICOM", "aide internationale", "sanctions"],
        "keywords_ht": ["ONU", "Nasyon Zini", "Etazini", "CARICOM", "èd entènasyonal", "sanksyon"],
    },
}

# ─── Anger Index scale thresholds ────────────────────────────────────────────

ANGER_LEVELS = [
    (0, 25, "Calm", "Calme", "Kalm", "#4CAF50"),
    (25, 50, "Concerned", "Préoccupé", "Enkyete", "#FFC107"),
    (50, 75, "Agitated", "Agité", "Ajite", "#FF9800"),
    (75, 100, "Enraged", "Enragé", "Anraje", "#F44336"),
]

# ─── Sentiment model ──────────────────────────────────────────────────────────

SENTIMENT_MODEL = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
SENTIMENT_MAX_LENGTH = 512
SENTIMENT_BATCH_SIZE = 16
