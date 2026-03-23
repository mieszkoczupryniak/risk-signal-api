from __future__ import annotations

from typing import Dict, List

# Negative and positive keywords for sentiment
NEGATIVE_KEYWORDS: List[str] = [
    "war", "attack", "attacks", "military", "conflict", "tensions",
    "escalation", "escalates", "clashes", "strike", "strikes",
    "sanctions", "sanction", "ban", "bans", "restriction", "restrictions",
    "embargo", "embargoes", "investigation", "investigations",
    "probe", "probes", "lawsuit", "lawsuits", "fine", "fines",
    "regulator", "regulators", "default", "defaults", "collapse",
    "collapses", "crisis", "crises", "downgrade", "downgrades",
    "suspension", "suspended", "fraud", "corruption", "terror",
    "terrorist", "airstrike", "cyberattack",
]

POSITIVE_KEYWORDS: List[str] = [
    "ceasefire", "truce", "peace talk", "peace talks", "peace deal",
    "peace agreement", "deal", "deals", "agreement", "agreements",
    "partnership", "partnerships", "approval", "approvals",
    "green light", "green-light", "upgrade", "upgrades",
    "settlement", "resolved", "resolution",
]

# Category keyword mapping
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "geopolitics": [
        "war", "military", "border", "conflict", "tensions",
        "sanctions", "embargo", "ceasefire", "truce",
        "geopolitics", "diplomatic", "missile", "nato",
    ],
    "regulation": [
        "regulation", "regulations", "regulator", "regulators",
        "policy", "policies", "law", "laws", "bill", "bills",
        "compliance", "oversight", "ban", "restriction", "rules",
    ],
    "sanctions": [
        "sanction", "sanctions", "embargo", "blacklist",
        "export control", "asset freeze",
    ],
    "energy": [
        "oil", "gas", "lng", "pipeline", "energy",
        "renewable", "power plant", "electricity",
    ],
    "banking": [
        "bank", "banks", "lender", "lenders", "default",
        "loan", "loans", "credit", "liquidity", "capital",
    ],
    "defense": [
        "defense", "defence", "military", "weapons", "arms",
        "missile", "contract",
    ],
    "macro": [
        "inflation", "recession", "gdp", "growth", "downgrade",
        "unemployment", "interest rate", "central bank", "yield",
    ],
}

# Category weights for risk contribution
CATEGORY_WEIGHTS: Dict[str, float] = {
    "geopolitics": 3.0,
    "sanctions": 3.0,
    "regulation": 2.5,
    "energy": 2.0,
    "banking": 2.0,
    "defense": 2.0,
    "macro": 2.0,
    "other": 1.0,
}

# Scoring configuration
MAX_PER_ITEM_RISK: int = 20  # max contribution of a single news item
MAX_EFFECTIVE_ITEMS: int = 10  # how many "strong" items correspond to score 100

# === Granular risk tags rules (NEW) ===

GRANULAR_RISK_TAG_RULES: list[dict] = [
    # sanctions
    {"tag": "sanctions_risk_russia", "category": "sanctions", "region": "RU"},
    {"tag": "sanctions_risk_russia", "category": "sanctions", "region": "EU"},
    {"tag": "sanctions_risk_iran", "category": "sanctions", "region": "IR"},
    {"tag": "sanctions_risk_iran", "category": "sanctions", "region": "US"},

    # regulation
    {"tag": "regulatory_risk_eu", "category": "regulation", "region": "EU"},
    {"tag": "regulatory_risk_us", "category": "regulation", "region": "US"},

    # banking
    {"tag": "banking_stress_us", "category": "banking", "region": "US"},
    {"tag": "banking_stress_eu", "category": "banking", "region": "EU"},

    # energy
    {"tag": "energy_supply_risk_eu", "category": "energy", "region": "EU"},
    {"tag": "energy_price_risk_global", "category": "energy", "region": None},

    # defense / geopolitics / trade
    {"tag": "defense_spending_risk", "category": "defense", "region": None},
    {"tag": "trade_disruption_risk_china", "category": "trade", "region": "CN"},
]
