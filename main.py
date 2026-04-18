import json
import copy
from dungeon import DungeonWorld, KEY, LOCKED_DOOR, EXIT
from agents import run_agent_turn

MAX_TURNS = 30

# Grid coordinates derived from the dungeon layout
DOOR_POS  = (4, 3)
EXIT_POS  = (6, 6)

# ---------------------------------------------------------------------------
# Reward bookkeeping
# ---------------------------------------------------------------------------

def make_reward_tracker():
    return {
        "key_collected": {1: False, 2: False},
        "door_unlocked": False,
        "exit_reached":  {1: False, 2: False},
    }


def calculate_reward(agent_id, pre, post, world, tracker):
    """Return the reward earned this turn and update tracker in place."""
    reward = -0.1  # time penalty every turn

    # +1 for picking up the key (first time)
    had_key  = KEY in pre["inventory"]
    have_key = KEY in post["inventory"]
    if have_key and not had_key and not tracker["key_collected"][agent_id]:
        reward += 1.0
        tracker["key_collected"][agent_id] = True

    # +5 for unlocking the door (once, whoever does it)
    if not tracker["door_unlocked"]:
        dr, dc = DOOR_POS
        if world.grid[dr][dc] != LOCKED_DOOR:
            reward += 5.0
            tracker["door_unlocked"] = True

    # +10 for reaching the exit (once per agent)
    if not tracker["exit_reached"][agent_id]:
        r, c = post["position"]
        if world.grid[r][c] == EXIT:
            reward += 10.0
            tracker["exit_reached"][agent_id] = True

    return round(reward, 3)

# ---------------------------------------------------------------------------
# State snapshot helpers
# ---------------------------------------------------------------------------

_CELL_NAMES = {
    0: "empty", 1: "wall", 2: "KEY", 3: "LOCKED_DOOR", 4: "EXIT", 5: "Agent1", 6: "Agent2"
}


def snapshot(agent_id, world, inbox):
    """Capture the observable state for agent_id right now."""
    pos = world.agent_positions[agent_id]
    visible = world.get_visible_cells(agent_id)
    return {
        "position": list(pos),
        "inventory": [_CELL_NAMES.get(i, str(i)) for i in world.agent_inventories[agent_id]],
        "visible_cells": {
            f"{r},{c}": _CELL_NAMES.get(ct, str(ct))
            for (r, c), ct in visible.items()
        },
        "messages_received": list(inbox.get(agent_id, [])),
    }

# ---------------------------------------------------------------------------
# Terminal printer
# ---------------------------------------------------------------------------

def print_turn(turn_num, result, reward):
    agent = result["agent_id"]
    tool  = result["tool_called"]
    args  = result["tool_args"]
    pos   = result["new_position"]
    inv   = result["inventory"]
    res   = result["result"]

    inv_str = ", ".join(_CELL_NAMES.get(i, str(i)) for i in inv) if inv else "—"
    arg_str = ", ".join(f"{k}={v}" for k, v in args.items()) if args else ""

    print(f"Turn {turn_num:>2} | Agent {agent} | {tool}({arg_str})")
    print(f"         result : {res}")
    print(f"         pos    : {pos}  inv: {inv_str}  reward: {reward:+.1f}")
    print()

# ---------------------------------------------------------------------------
# Main game loop
# ---------------------------------------------------------------------------

def run_game():
    world        = DungeonWorld()
    message_inbox = {}
    histories    = {1: [], 2: []}
    tracker      = make_reward_tracker()
    game_log     = []
    total_rewards = {1: 0.0, 2: 0.0}

    print("=" * 60)
    print("DUNGEON SIMULATION — starting")
    print(world)
    print("=" * 60)
    print()

    turn_num = 0

    for _ in range(MAX_TURNS):
        for agent_id in (1, 2):
            turn_num += 1

            # --- pre-turn snapshot (before run_agent_turn clears the inbox) ---
            pre_state = snapshot(agent_id, world, message_inbox)
            pre_inv_raw = list(world.agent_inventories[agent_id])

            try:
                result = run_agent_turn(
                    agent_id,
                    world,
                    message_inbox,
                    histories[agent_id],
                )
            except Exception as exc:
                print(f"[ERROR] Agent {agent_id} turn {turn_num} failed: {exc}")
                game_log.append({
                    "turn": turn_num,
                    "agent_id": agent_id,
                    "error": str(exc),
                })
                break

            # --- post-turn snapshot ---
            post_state = snapshot(agent_id, world, message_inbox)
            post_inv_raw = list(world.agent_inventories[agent_id])

            reward = calculate_reward(
                agent_id,
                {"position": tuple(pre_state["position"]), "inventory": pre_inv_raw},
                {"position": tuple(post_state["position"]), "inventory": post_inv_raw},
                world,
                tracker,
            )
            total_rewards[agent_id] = round(total_rewards[agent_id] + reward, 3)

            log_entry = {
                "turn":     turn_num,
                "agent_id": agent_id,
                "state":    pre_state,
                "action": {
                    "tool_called": result["tool_called"],
                    "tool_args":   result["tool_args"],
                    "reasoning":   result["reasoning"],
                },
                "result":     result["result"],
                "reward":     reward,
                "next_state": post_state,
            }
            game_log.append(log_entry)
            print_turn(turn_num, result, reward)

        # --- end-of-round check ---
        both_at_exit = all(tracker["exit_reached"][a] for a in (1, 2))
        if both_at_exit:
            print("Both agents reached the EXIT! Game complete.")
            break

    else:
        print(f"Turn limit ({MAX_TURNS}) reached.")

    # --- final summary ---
    print()
    print("=" * 60)
    print("GAME OVER")
    print(f"  Turns played : {turn_num}")
    print(f"  Door unlocked: {tracker['door_unlocked']}")
    for a in (1, 2):
        print(
            f"  Agent {a}: exit={'YES' if tracker['exit_reached'][a] else 'no'}"
            f"  total reward={total_rewards[a]:+.2f}"
        )
    print()
    print("Final grid:")
    print(world)
    print()

    # --- save log ---
    with open("game_log.json", "w") as f:
        json.dump(game_log, f, indent=2)
    print("Game log saved to game_log.json")


if __name__ == "__main__":
    run_game()
