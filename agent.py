"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    session = _new_session(query, wardrobe)

    # Step 2: Parse the query using the LLM
    client = _get_groq_client()
    parse_prompt = (
        f"Extract search parameters from this clothing query: '{query}'\n\n"
        f"Respond in this exact format with no extra text:\n"
        f"description: <keywords describing the item>\n"
        f"size: <size if mentioned, or None>\n"
        f"max_price: <maximum price as a number if mentioned, or None>"
    )
    try:
        parse_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": parse_prompt}],
            max_tokens=100,
        )
        parse_text = parse_response.choices[0].message.content.strip()
        parsed = {}
        for line in parse_text.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                parsed[key.strip()] = value.strip()

        description = parsed.get("description", query)
        size_raw = parsed.get("size", "None")
        price_raw = parsed.get("max_price", "None")
        size = None if size_raw == "None" else size_raw
        max_price = None if price_raw == "None" else float(price_raw)
    except Exception:
        description = query
        size = None
        max_price = None

    session["parsed"] = {
        "description": description,
        "size": size,
        "max_price": max_price,
    }

    # Step 3: Call search_listings
    session["search_results"] = search_listings(description, size, max_price)

    if not session["search_results"]:
        session["error"] = (
            "No listings matched your search. Try broadening your description, "
            "raising your price limit, or removing the size filter."
        )
        return session

    # Step 4: Select the top result
    session["selected_item"] = session["search_results"][0]

    # Step 5: Call suggest_outfit
    session["outfit_suggestion"] = suggest_outfit(
        session["selected_item"], session["wardrobe"]
    )

    if not session["outfit_suggestion"]:
        session["error"] = (
            "Outfit suggestion unavailable — try again or describe "
            "your wardrobe in your query."
        )
        return session

    # Step 6: Call create_fit_card
    session["fit_card"] = create_fit_card(
        session["outfit_suggestion"], session["selected_item"]
    )

    # Step 7: Return completed session
    return session


def _get_groq_client():
    from groq import Groq
    import os
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)



# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
