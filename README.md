# FitFindr

FitFindr is a multi-tool AI agent that helps users find secondhand clothing 
and build outfits around it. Given a natural language query, it searches a 
mock listings dataset, suggests outfit combinations based on the user's 
wardrobe, and generates a shareable fit card caption — all in one interaction.

---

## How to Run

1. Clone the repo and activate your virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Add your Groq API key to a `.env` file in the project root:
3. Run the app:
```bash
python3 app.py
```

4. Open the URL shown in your terminal

---

## Tool Inventory

### search_listings(description, size, max_price) -- Tool 1
- **Purpose**: Searches the mock listings dataset for items matching the user's description, size, and price ceiling.
- **Inputs:**
  - `description` (str): Keywords describing the item, e.g. "vintage graphic tee"
  - `size` (str or None): Size filter, e.g. "M". Skipped if None.
  - `max_price` (float or None): Maximum price. Skipped if None.
- **Output:** A list of matching listing dicts sorted by relevance score. Returns an empty list if nothing matches — does not raise an exception.

### suggest_outfit(new_item, wardrobe) -- Tool 2
- **Purpose:** Suggests 1-2 complete outfit combinations using the new item and pieces from the user's existing wardrobe.
- **Inputs:**
  - `new_item` (dict): The selected listing dict from search_listings.
  - `wardrobe` (dict): The user's wardrobe with an 'items' key containing a list of wardrobe item dicts.
- **Output:** A non-empty string with outfit suggestions in natural language. If the wardrobe is empty, returns general styling advice instead.

### create_fit_card(outfit, new_item) -- Tool 3
- **Purpose:** Generates a short, casual, shareable caption for the outfit — the kind someone would post on Instagram or TikTok.
- **Inputs:**
  - `outfit` (str): The outfit suggestion string from suggest_outfit.
  - `new_item` (dict): The selected listing dict, used for item name, price, and platform.
- **Output:** A 2-4 sentence caption string written in a casual, social-media-ready tone.

---

## Planning Loop

The agent runs a conditional planning loop, it does not call all three tools 
unconditionally. Here is how it decides what to do:

1. The user's query is parsed by the LLM to extract a description, size, 
   and max_price. These are stored in the session dict.
2. `search_listings` is called with the parsed parameters. If it returns 
   an empty list, the agent sets an error message in the session and returns 
   early — `suggest_outfit` is never called with empty input.
3. If results were found, the top result is selected and stored as 
   `session["selected_item"]`.
4. `suggest_outfit` is called with the selected item and the user's wardrobe. 
   If it returns an empty string, the agent sets an error and returns early.
5. `create_fit_card` is called with the outfit suggestion and selected item. 
   The result is stored in `session["fit_card"]`.
6. The completed session is returned. The caller checks `session["error"]` 
   first — if it is not None, the interaction ended early.

---

## State Management

All state is stored in a single session dict initialized at the start of each 
interaction. Each tool reads its inputs from the session and writes its output 
back into it — no data needs to be re-entered between steps. Key fields:

- `session["parsed"]` — extracted description, size, and max_price
- `session["search_results"]` — full list returned by search_listings
- `session["selected_item"]` — top result, passed into suggest_outfit
- `session["wardrobe"]` — user's wardrobe, available throughout
- `session["outfit_suggestion"]` — string from suggest_outfit, passed into create_fit_card
- `session["fit_card"]` — final caption from create_fit_card
- `session["error"]` — set if any tool fails; signals early termination

---

## Error Handling

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Returns empty list. Agent sets session["error"] to: "No listings matched your search. Try broadening your description, raising your price limit, or removing the size filter." Does not proceed to suggest_outfit. |
| suggest_outfit | Wardrobe is empty | Does not crash. Calls LLM for general styling advice based on the item's style tags and colors instead of referencing specific wardrobe pieces. |
| create_fit_card | Outfit string is empty or missing | Returns: "Fit card unavailable — outfit suggestion was incomplete. Try running the search again." Does not raise an exception. |

**Example from testing:** Running `run_agent("designer ballgown size XXS under $5", 
get_example_wardrobe())` returned `session["error"] = "No listings matched your 
search..."` and `session["fit_card"] = None`, confirming the agent stopped before 
calling suggest_outfit.

---

## Spec Reflection

Writing `planning.md` before any code made the implementation significantly 
easier. Having the exact input/output types defined for each tool meant I could 
test them in isolation with confidence before wiring them together. The agent 
diagram was pretty useful — it made the conditional branching logic clear 
before writing a single line of the planning loop.

The main thing that changed from spec to implementation was query parsing. The 
spec described parsing as a simple step, but in practice using the LLM to extract 
structured parameters from natural language required careful prompting to get 
consistent output.

---

## AI Usage

**Instance 1 — search_listings implementation:**
I gave Claude the Tool 1 spec block from planning.md (inputs, return value, 
failure mode) and asked it to implement the filtering and keyword scoring logic 
using load_listings() from the data loader. The generated code correctly filtered 
by price and size and scored by keyword overlap. I reviewed it against my spec 
before running it and verified it handled the empty results case by testing with 
an impossible query.

**Instance 2 — planning loop implementation:**
I gave Claude the full Architecture diagram and Planning Loop + State Management 
sections from planning.md and asked it to implement run_agent() in agent.py. 
I reviewed the generated code to confirm it branched on search_results being 
empty and stored values in the session dict rather than calling all three tools 
unconditionally. I then tested both the happy path and no-results path using the 
example queries already in agent.py before trusting the output.