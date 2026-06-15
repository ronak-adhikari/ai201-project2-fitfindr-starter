# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Searches the mock listings dataset by filtering on price and size, then scoring each remaining item by keyword overlap with the user's description. Returns the best matches sorted by relevance score.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): ... Keywords describing what the user wants, e.g. "vintage graphic tee"
- `size` (str): ... Size string to filter by, e.g. "M". If None, size filter is skipped.
- `max_price` (float): ... Maximum price the user is willing to pay. If None, price filter is skipped.


**What it returns:**
A list of matching listing dicts sorted by relevance score (highest first). Each dict contains: id, title, description, category, style_tags, size, condition, price, colors, brand, and platform. Returns an empty list if nothing matches.

**What happens if it fails or returns nothing:**
The agent stops and tells the user: "No listings matched your search. Try broadening your description, raising your price limit, or removing the size filter." It does not proceed to suggest_outfit with an empty result.

---

### Tool 2: suggest_outfit

**What it does:**
Takes the selected listing item and the user's existing wardrobe and suggests 1-2 complete outfit combinations using pieces the user already owns. If the wardrobe is empty, it offers general styling advice for the item instead.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): ... The selected listing dict from search_listings — contains fields like title, price, style_tags, colors, category, and platform.
- `wardrobe` (dict): ... The user's wardrobe with an 'items' key containing a list of wardrobe item dicts. Each wardrobe item has: id, name, category, colors, style_tags, and notes.

**What it returns:**
A non-empty string with 1-2 outfit suggestions written in natural language. For example: "Pair this faded band tee with your dark wash baggy jeans and chunky white sneakers for a classic 90s streetwear look."

**What happens if it fails or returns nothing:**
If the wardrobe is empty, the agent does not crash — instead it asks the LLM for general styling advice based on the item's style tags and colors, such as what types of bottoms or shoes would pair well with it. If the LLM call fails entirely, the agent returns: "Outfit suggestion unavailable — try again or describe your wardrobe in your query."

---

### Tool 3: create_fit_card

**What it does:**
Takes the outfit suggestion and the selected listing item and generates a short, casual, shareable caption — the kind someone would post on Instagram or TikTok with their OOTD. It should actually sound authentic.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (...): ... The outfit suggestion string returned by suggest_outfit.

**What it returns:**
A 2-4 sentence string written in a casual, social-media-ready tone. It should naturally mention the item name, price, and platform once each, and capture the specific vibe of the outfit. For example: "thrifted this faded band tee off depop for $19 and it was made for my baggy jeans 🖤 full look coming to my stories"

**What happens if it fails or returns nothing:**
If the outfit string is empty or missing, the agent does not crash — it returns a descriptive error message string: "Fit card unavailable — outfit suggestion was incomplete. Try running the search again." It does not raise an exception.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
1. Parse the user's query using the LLM to extract description, size, and max_price.
2. Call search_listings() with the parsed parameters. 
   - If results is empty: set session["error"] to a helpful message and return the session early. Do NOT proceed.
   - If results is not empty keep running the session
3. Call suggest_outfit()
   - If the result is an empty string or error: set session["error"] and return early.
   - If successful: store result and continue.
4. Call create_fit_card()
   - If the result is an error string: set session["error"] and return early.
   - If successful: store result and continue.
5. Return the completed session. The caller checks session["error"] first — if None, all three tools succeeded.
---

## State Management

**How does information from one tool get passed to the next?**
All state is stored in a single session dict initialized at the start of each interaction by new_session(). Each tool call reads its inputs from the session and writes its output back into the session. This means:

- session["parsed"] stores the extracted description, size, and max_price from the query
- session["search_results"] stores the list returned by search_listings()
- session["selected_item"] stores the top result, which gets passed into suggest_outfit()
- session["wardrobe"] stores the user's wardrobe, available throughout the entire interaction
- session["outfit_suggestion"] stores the string from suggest_outfit(), passed into create_fit_card()
- session["fit_card"] stores the final caption from create_fit_card()
- session["error"] is set if any tool fails — the caller checks this first before reading any output

No data needs to be re-entered by the user between steps — everything flows through the session dict.

---

## Error Handling

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Agent stops and tells the user: "No listings matched your search. Try broadening your description, raising your price limit, or removing the size filter." Does not proceed to suggest_outfit. |
| suggest_outfit | Wardrobe is empty | Agent does not crash — asks LLM for general styling advice based on the item's style tags and colors instead of referencing specific wardrobe pieces. |
| create_fit_card | Outfit input is empty or missing | Agent returns a descriptive error string: "Fit card unavailable — outfit suggestion was incomplete. Try running the search again." Does not raise an exception. |

## Architecture

## Architecture

```
User query + wardrobe
        │
        ▼
Planning Loop (run_agent)
        │
        ▼
Step 1: Parse query with LLM
        │ → session["parsed"] = {description, size, max_price}
        │
        ▼
Step 2: search_listings(description, size, max_price)
        │
        ├── results = [] ──► session["error"] = "No listings matched your search.
        │                    Try broadening your description, raising your price
        │                    limit, or removing the size filter." → return session
        │
        │ results = [item, ...]
        ▼
session["selected_item"] = results[0]
        │
        ▼
Step 3: suggest_outfit(selected_item, wardrobe)
        │
        ├── wardrobe empty ──► LLM gives general styling advice (no crash)
        │
        ├── result = "" ──► session["error"] = "Outfit suggestion unavailable." 
        │                   → return session
        │
        │ result = "Pair this with..."
        ▼
session["outfit_suggestion"] = result
        │
        ▼
Step 4: create_fit_card(outfit_suggestion, selected_item)
        │
        ├── outfit empty ──► session["error"] = "Fit card unavailable." 
        │                    → return session
        │
        │ result = "thrifted this..."
        ▼
session["fit_card"] = result
        │
        ▼
Return completed session
```

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**
For search_listings, I'll give Claude the Tool 1 spec from planning.md (inputs, 
return value, failure mode) and the load_listings() function from data_loader.py, 
and ask it to implement the filtering and keyword scoring logic. Before using it 
I'll verify it filters by price and size correctly and handles empty results 
without crashing. I'll test it with 3 queries: one that should match, one with 
a price too low to match anything, and one with a very specific description.

For suggest_outfit, I'll give Claude the Tool 2 spec from planning.md and the 
wardrobe schema from wardrobe_schema.json, and ask it to implement the LLM prompt 
that suggests outfits. Before using it I'll verify it handles both a full wardrobe 
and an empty wardrobe without crashing, and that the output is a non-empty string.

For create_fit_card, I'll give Claude the Tool 3 spec from planning.md and ask it 
to implement the LLM prompt with a higher temperature setting for variety. Before 
using it I'll verify the output sounds casual and social-media-ready, mentions the 
item name, price, and platform, and that it handles an empty outfit string gracefully.


**Milestone 4 — Planning loop and state management:**
I'll give Claude the full Architecture diagram and Planning Loop section from 
planning.md and ask it to implement run_agent() in agent.py. Before using it I'll 
verify that: (1) the session dict is initialized correctly, (2) the loop stops early 
if search_listings returns nothing, (3) state flows correctly between all three tools, 
and (4) session["error"] is set properly on every failure path. I'll test with the 
two example queries already in agent.py — the happy path and the no-results path.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
**Step 1:**
The agent parses the query and calls search_listings("vintage graphic tee", size=None, max_price=30.0). Size is not mentioned so it is left out. The tool searches through listings.json, scores each item by keyword overlap, and returns a list of matches sorted by relevance. The agent selects results[0] — for example: "Vintage Band Tee — Faded Grey, $19, depop" — and stores it as session["selected_item"].

**Step 2:**
Since Step 1 returned a result, the agent calls suggest_outfit(new_item=<band tee>, wardrobe=<baggy jeans, chunky sneakers>). The wardrobe comes from what the user described in their query. The tool returns an outfit suggestion like: "Pair this with your wide-leg jeans and chunky sneakers for a 90s grunge look."


**Step 3:**
Since Step 2 returned a suggestion, the agent calls create_fit_card(outfit=<suggestion>, new_item=<band tee>). The tool generates a short shareable caption like: "thrifted this faded band tee off depop for $22 and it was made for my wide-legs 🖤"

**Final output to user:**
The user sees the matched listing, the outfit suggestion, and the fit card caption all together.
