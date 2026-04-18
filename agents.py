import anthropic
from dotenv import load_dotenv
from dungeon import DungeonWorld, EMPTY, WALL, KEY, LOCKED_DOOR, EXIT, AGENT1, AGENT2

load_dotenv()

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment

# ---------------------------------------------------------------------------
# Tool definitions (Anthropic format)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "move",
        "description": "Move one step in a direction. Fails if the destination is a wall or out of bounds.",
        "input_schema": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "enum": ["up", "down", "left", "right"],
                    "description": "Cardinal direction to move.",
                }
            },
            "required": ["direction"],
        },
    },
    {
        "name": "look",
        "description": "Observe your current cell and the four adjacent cells (north/south/east/west).",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "check_coordinates",
        "description": "Return your current (row, col) position on the 8x8 grid.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "check_inventory",
        "description": "List the items you are currently carrying.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "pick_up_item",
        "description": "Pick up the item in your current cell, if one exists.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "use_item",
        "description": (
            "Use an item from your inventory on an adjacent target cell. "
            'For example, use item "KEY" on the LOCKED_DOOR next to you to open it.'
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "item": {
                    "type": "string",
                    "enum": ["KEY"],
                    "description": "Name of the item to use.",
                },
                "target": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 2,
                    "maxItems": 2,
                    "description": "[row, col] of the target cell.",
                },
            },
            "required": ["item", "target"],
        },
    },
    {
        "name": "send_message",
        "description": "Send a text message to the other agent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "recipient": {
                    "type": "integer",
                    "enum": [1, 2],
                    "description": "Agent ID to send the message to.",
                },
                "message": {
                    "type": "string",
                    "description": "The message text.",
                },
            },
            "required": ["recipient", "message"],
        },
    },
]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_CELL_NAMES = {
    EMPTY: "empty floor",
    WALL: "wall",
    KEY: "KEY (pick me up!)",
    LOCKED_DOOR: "LOCKED DOOR",
    EXIT: "EXIT",
    AGENT1: "Agent 1",
    AGENT2: "Agent 2",
}

_ITEM_MAP = {"KEY": KEY}


def _format_visible(visible: dict, pos: tuple) -> str:
    r0, c0 = pos
    labels = {
        (0, 0): "here",
        (-1, 0): "north",
        (1, 0): "south",
        (0, -1): "west",
        (0, 1): "east",
    }
    lines = []
    for (r, c), ct in visible.items():
        lbl = labels.get((r - r0, c - c0), "?")
        lines.append(f"  ({r},{c}) [{lbl}]: {_CELL_NAMES.get(ct, str(ct))}")
    return "\n".join(lines)


def _execute_tool(
    agent_id: int,
    tool_name: str,
    tool_input: dict,
    world: DungeonWorld,
    message_inbox: dict,
) -> str:
    if tool_name == "move":
        _, msg = world.move_agent(agent_id, tool_input["direction"])
        return msg

    if tool_name == "look":
        pos = world.agent_positions[agent_id]
        visible = world.get_visible_cells(agent_id)
        return "Visible cells:\n" + _format_visible(visible, pos)

    if tool_name == "check_coordinates":
        r, c = world.agent_positions[agent_id]
        return f"You are at ({r}, {c})."

    if tool_name == "check_inventory":
        inv = world.agent_inventories[agent_id]
        if not inv:
            return "Your inventory is empty."
        names = {KEY: "KEY"}
        return "Inventory: " + ", ".join(names.get(i, str(i)) for i in inv)

    if tool_name == "pick_up_item":
        _, msg = world.pick_up_item(agent_id)
        return msg

    if tool_name == "use_item":
        item_const = _ITEM_MAP.get(tool_input["item"])
        if item_const is None:
            return f"Unknown item: {tool_input['item']}"
        target = tuple(tool_input["target"])
        _, msg = world.use_item(agent_id, item_const, target)
        return msg

    if tool_name == "send_message":
        recipient = tool_input["recipient"]
        text = tool_input["message"]
        message_inbox.setdefault(recipient, []).append({"from": agent_id, "text": text})
        return f"Message delivered to Agent {recipient}."

    return f"Unknown tool: {tool_name}"


def _build_observation(agent_id: int, world: DungeonWorld, message_inbox: dict) -> str:
    pos = world.agent_positions[agent_id]
    inv = world.agent_inventories[agent_id]
    visible = world.get_visible_cells(agent_id)

    inv_str = (
        ", ".join({KEY: "KEY"}.get(i, str(i)) for i in inv) if inv else "empty"
    )

    lines = [
        f"=== Agent {agent_id} — your turn ===",
        f"Position : {pos}",
        f"Inventory: {inv_str}",
    ]

    inbox = message_inbox.pop(agent_id, [])
    if inbox:
        lines.append("Incoming messages:")
        for m in inbox:
            lines.append(f"  Agent {m['from']}: {m['text']}")

    lines.append("Visible cells:")
    lines.append(_format_visible(visible, pos))
    lines.append("Choose your next action.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_agent_turn(
    agent_id: int,
    world: DungeonWorld,
    message_inbox: dict,
    conversation_history: list,
) -> dict:
    """Run one turn for the given agent.

    Mutates ``world``, ``message_inbox``, and ``conversation_history`` in place.
    Returns a summary dict.
    """
    start_area = "top-left" if agent_id == 1 else "top-right"
    other = 2 if agent_id == 1 else 1

    system_prompt = f"""\
You are Agent {agent_id} navigating an 8x8 dungeon grid. Your goal is to reach the EXIT.

Map legend:
  empty floor — you can walk here
  wall (#)    — impassable
  KEY         — pick it up; you need it to open the locked door
  LOCKED DOOR — blocks the path south; use the KEY on it to open it
  EXIT        — your destination (bottom-right area)
  Agent {other}  — the other player; you can send it messages

You started in the {start_area} region. The KEY is somewhere in the middle row.
The locked door blocks the corridor to the lower half of the map.
The EXIT is in the bottom-right area.

You must call exactly one tool per turn. Think step-by-step about what to do next \
and pick the most useful action."""

    observation = _build_observation(agent_id, world, message_inbox)

    # Append the observation to history, merging with a pending tool_result if present.
    # The Anthropic API requires messages to alternate user/assistant.  After a tool
    # call the history ends with a user message containing a tool_result block; we
    # append the new observation as an extra text block in that same user message so
    # the turn structure remains valid.
    if (
        conversation_history
        and conversation_history[-1]["role"] == "user"
        and isinstance(conversation_history[-1]["content"], list)
        and conversation_history[-1]["content"]
        and conversation_history[-1]["content"][0].get("type") == "tool_result"
    ):
        conversation_history[-1]["content"].append(
            {"type": "text", "text": observation}
        )
    else:
        conversation_history.append({"role": "user", "content": observation})

    # Call the Claude API — force exactly one tool call per turn.
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=system_prompt,
        tools=TOOLS,
        tool_choice={"type": "any"},
        messages=conversation_history,
    )

    # Parse the response into reasoning text + tool call.
    reasoning = ""
    tool_called = None
    tool_args = None
    tool_use_block = None

    for block in response.content:
        if block.type == "text":
            reasoning += block.text
        elif block.type == "tool_use":
            tool_called = block.name
            tool_args = block.input
            tool_use_block = block

    # Execute the tool against the world.
    result = _execute_tool(agent_id, tool_called, tool_args, world, message_inbox)

    # Persist the full exchange in history so future turns have context.
    conversation_history.append({"role": "assistant", "content": response.content})
    conversation_history.append(
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_block.id,
                    "content": result,
                }
            ],
        }
    )

    return {
        "agent_id": agent_id,
        "tool_called": tool_called,
        "tool_args": tool_args,
        "reasoning": reasoning.strip(),
        "result": result,
        "new_position": world.agent_positions[agent_id],
        "inventory": world.agent_inventories[agent_id][:],
    }
