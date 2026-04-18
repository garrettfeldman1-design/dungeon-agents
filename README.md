# Dungeon Agents

A two-agent dungeon simulation where each agent is powered by Claude Haiku via the Anthropic API. Agents navigate an 8x8 grid, pick up a key, unlock a door, and race to the exit. Each agent perceives only its immediate surroundings and can send messages to the other agent. Every turn is logged as a structured trace and can be replayed in a browser.

## What's in this repo

- `dungeon.py` — the 8x8 game world: grid layout, movement, item pickup, door unlocking
- `agents.py` — two LLM agents using Claude Haiku via the Anthropic API
- `main.py` — game loop, structured trace logging, reward function
- `game_log.json` — full structured trace of one complete game
- `viewer.html` — turn-by-turn replay viewer

## How to run

```bash
pip install anthropic python-dotenv
```

Create a `.env` file with your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Run the simulation:

```bash
python main.py
```

To view the replay, serve the folder locally and open `viewer.html`:

```bash
python -m http.server
# then open http://localhost:8000/viewer.html
```

## Reward function

| Event | Reward |
|---|---|
| Each turn | −0.1 |
| Pick up the key | +1 |
| Unlock the door | +5 |
| Reach the exit | +10 |

## Model

`claude-haiku-4-5-20251001`

## What happened in the recorded game

Agent 1 navigated to the key in the middle of the map, picked it up, unlocked the door at (4, 3), and reached the exit at (6, 6). It then sent messages to Agent 2 with its coordinates and directions. Agent 2 followed the same route and also reached the exit. The game ran for 50 turns total.
