# Dungeon Agents

A two-agent simulation where each agent is an LLM (Claude Haiku) navigating an 8×8 dungeon grid. The agents must find a key, unlock a door, and reach the exit — with only local visibility, no shared memory, and the option to send messages to each other. The project demonstrates how to wire LLM tool use into a game loop, log structured traces, and visualize agent behavior in a replay viewer. It's a minimal but complete example of multi-agent coordination: two agents with partial information, milestone rewards, and one-way communication.

## Model

`claude-haiku-4-5-20251001`

Haiku is used deliberately. This simulation doesn't require a smart agent — the task is constrained enough that even a weak model completes it. Dumber agents produce more interesting traces: more backtracking, more redundant `look` calls, longer paths to the key. Smarter agents tend to solve it cleanly and quickly, which is less visually interesting to replay.

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
# optionally specify an output file:
python main.py my_run.json
```

To view the replay, serve the folder locally and open `viewer.html`:

```bash
python -m http.server
# then open http://localhost:8000/viewer.html
```

The viewer loads `game_log.json` by default. To view a different log, edit the `fetch()` call at the bottom of `viewer.html`.

## Reward function

| Event | Reward |
|---|---|
| Each turn | −0.1 |
| Pick up the key | +1 |
| Unlock the door | +5 |
| Reach the exit | +10 |

The −0.1 time penalty discourages wandering and makes every unnecessary `look` or `check_inventory` call visible as a small dip in the cumulative reward chart. The milestone rewards (+1, +5, +10) are sized to create obvious signal spikes — you can see exactly when each agent accomplished something meaningful without reading the log. The door reward (+5) is larger than the key reward (+1) because unlocking the door is the cooperative bottleneck: one agent has to do it before the other can proceed.

## What happened in the recorded game

Agent 1 navigated to the key at (3, 4) and picked it up at turn 13, then moved south and unlocked the door at (4, 3) at turn 17. It reached the exit at (6, 6) at turn 29, then spent several turns sending Agent 2 two messages with explicit coordinates and directions. Agent 2, starting from the top-right, followed the same route and reached the exit at turn 50. Both agents completed the objective in 50 turns total.

## Viewer design decisions

**Key moments are highlighted** in the sidebar and info panel because they're the most information-dense events in the log — key pickup, door unlock, and exit arrival each mark a phase transition. Surfacing them lets you jump directly to the interesting parts without scrubbing.

**Agent messages get a speech bubble** rather than a plain text field because they represent inter-agent coordination — the most interesting behavior in the simulation. The bubble format makes it visually obvious that something different is happening: one agent is trying to influence the other.

**Fog of war** is included in the viewer because it directly mirrors a core game mechanic. Each agent only sees five cells per turn; the fog visualizes that constraint rather than showing you information the agent didn't have. Scrubbing backward re-applies fog correctly because visited cells are precomputed per turn index.

**The reward chart is interactive and clickable** because the quantitative signal (reward curve) and the qualitative event (what actually happened) need to be connected. Hovering shows exact values at any turn; clicking jumps there. The goal is to let you correlate a reward spike with the specific action that caused it without manually cross-referencing turn numbers.

**The game summary screen is shown first** rather than jumping straight to turn 1. Before stepping through 50 individual turns, it's useful to know what the outcome was, which agent performed better, and which turns are worth jumping to. The summary gives that context in one view and includes a "Watch replay" button for when you're ready.

## Repo structure

Two branches:

- `main` — the base version built in roughly one hour: `dungeon.py`, `agents.py`, `main.py`, and a minimal viewer
- `enhanced` — the full version with the complete viewer (fog of war, reward chart, interactive chart, narrative panel, game summary screen, stats bar, agent trail, key moments sidebar, auto-play)
