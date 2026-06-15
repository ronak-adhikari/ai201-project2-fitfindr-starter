"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    listings = load_listings()

    # Step 1: Filter by price and size
    filtered = []
    for item in listings:
        if max_price is not None and item["price"] > max_price:
            continue
        if size is not None and size.lower() not in item["size"].lower():
            continue
        filtered.append(item)

    # Step 2: Score by keyword overlap with description
    keywords = description.lower().split()
    scored = []
    for item in filtered:
        score = 0
        searchable = " ".join([
            item["title"],
            item["description"],
            item["category"],
            " ".join(item["style_tags"]),
            " ".join(item["colors"]),
            item["brand"] or "",
        ]).lower()
        for keyword in keywords:
            if keyword in searchable:
                score += 1
        if score > 0:
            scored.append((score, item))

    # Step 3: Sort by score highest first
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    client = _get_groq_client()
    
    item_summary = (
        f"Item: {new_item['title']}\n"
        f"Category: {new_item['category']}\n"
        f"Style tags: {', '.join(new_item['style_tags'])}\n"
        f"Colors: {', '.join(new_item['colors'])}\n"
        f"Condition: {new_item['condition']}\n"
        f"Price: ${new_item['price']}"
    )

    wardrobe_items = wardrobe.get("items", [])

    if not wardrobe_items:
        prompt = (
            f"A user is considering buying this secondhand item:\n{item_summary}\n\n"
            f"They haven't described their wardrobe. Give them 1-2 general styling "
            f"suggestions — what kinds of bottoms, shoes, or layers would pair well "
            f"with this item based on its style and colors. Be specific and casual."
        )
    else:
        wardrobe_summary = "\n".join(
            f"- {w['name']} ({', '.join(w['style_tags'])})"
            for w in wardrobe_items
        )
        prompt = (
            f"A user is considering buying this secondhand item:\n{item_summary}\n\n"
            f"Their current wardrobe includes:\n{wardrobe_summary}\n\n"
            f"Suggest 1-2 complete outfit combinations using the new item and specific "
            f"pieces from their wardrobe. Be specific about which wardrobe pieces to "
            f"pair it with and describe the overall vibe. Keep it casual and practical."
        )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Outfit suggestion unavailable — try again or describe your wardrobe in your query. Error: {str(e)}"

# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    # Guard against empty outfit string
    if not outfit or not outfit.strip():
        return "Fit card unavailable — outfit suggestion was incomplete. Try running the search again."

    client = _get_groq_client()

    prompt = (
        f"Write a short, casual Instagram/TikTok caption for this thrifted outfit.\n\n"
        f"Item: {new_item['title']}\n"
        f"Price: ${new_item['price']}\n"
        f"Platform: {new_item['platform']}\n"
        f"Outfit: {outfit}\n\n"
        f"Rules:\n"
        f"- 2-4 sentences max\n"
        f"- Sound like a real person posting an OOTD, not a product description\n"
        f"- Mention the item name, price, and platform naturally once each\n"
        f"- Capture the specific vibe of the outfit\n"
        f"- Keep it casual, fun, and authentic\n"
        f"- No hashtags"
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=1.2,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Fit card unavailable — outfit suggestion was incomplete. Try running the search again. Error: {str(e)}"
