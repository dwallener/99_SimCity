from __future__ import annotations


def classify_category(category: str | None) -> str:
    value = (category or "").lower()
    if not value:
        return "other"

    if any(token in value for token in ["college", "university", "school", "education", "campus"]):
        return "education"
    if any(token in value for token in ["hospital", "medical", "clinic", "dentist", "pharmacy", "health"]):
        return "health"
    if any(token in value for token in ["restaurant", "coffee", "cafe", "bar", "pub", "brewery", "food", "pizza", "sushi"]):
        return "food_drink"
    if any(token in value for token in ["hotel", "motel", "lodging"]):
        return "hotel"
    if any(token in value for token in ["park", "recreation", "sports", "gym", "fitness", "beach", "trail"]):
        return "recreation"
    if any(token in value for token in ["retail", "store", "shop", "mall", "clothing", "market", "grocery"]):
        return "retail"
    if any(token in value for token in ["transit", "airport", "parking", "train", "station", "transport"]):
        return "transport"
    if any(token in value for token in ["office", "professional", "service", "bank", "financial", "insurance", "agency", "real_estate"]):
        return "work_service"
    if any(token in value for token in ["church", "community", "non_profit", "government", "library"]):
        return "civic"
    return "other"


def destination_weight(category_class: str) -> float:
    return {
        "work_service": 0.45,
        "retail": 2.2,
        "food_drink": 3.0,
        "education": 1.4,
        "health": 1.2,
        "transport": 1.1,
        "recreation": 1.6,
        "hotel": 0.8,
        "civic": 0.7,
        "other": 0.08,
    }.get(category_class, 0.25)


CHAIN_TOKENS = [
    "starbucks",
    "tim hortons",
    "mcdonald",
    "a&w",
    "subway",
    "costco",
    "walmart",
    "save-on-foods",
    "superstore",
    "shoppers drug mart",
    "london drugs",
    "cineplex",
    "whole foods",
    "safeway",
    "no frills",
]

LOW_ATTRACTION_TOKENS = [
    "real estate",
    "realtor",
    "law",
    "accountant",
    "accounting",
    "insurance",
    "mortgage",
    "contractor",
    "construction",
    "repair",
    "auto",
    "automotive",
    "machining",
    "freight",
    "cargo",
    "warehouse",
    "web designer",
    "marketing",
    "consulting",
]


def attraction_weight(name: str | None, brand: str | None, category: str | None, category_class: str) -> float:
    text = " ".join(value for value in [name or "", brand or "", category or ""] if value).lower()
    weight = destination_weight(category_class)

    if any(token in text for token in CHAIN_TOKENS):
        weight *= 5.0
    if category_class in {"food_drink", "retail", "recreation", "transport"}:
        weight *= 1.4
    if any(token in text for token in LOW_ATTRACTION_TOKENS):
        weight *= 0.12
    if category_class == "work_service":
        weight *= 0.5
    if category_class == "other":
        weight *= 0.3

    return max(weight, 0.01)
