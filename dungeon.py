# Cell type constants
EMPTY = 0
WALL = 1
KEY = 2
LOCKED_DOOR = 3
EXIT = 4
AGENT1 = 5
AGENT2 = 6

CELL_SYMBOLS = {
    EMPTY: " .",
    WALL: " #",
    KEY: " K",
    LOCKED_DOOR: " D",
    EXIT: " X",
    AGENT1: " 1",
    AGENT2: " 2",
}

DIRECTIONS = {
    "up":    (-1, 0),
    "down":  ( 1, 0),
    "left":  ( 0,-1),
    "right": ( 0, 1),
}

# Base grid layout (no agent positions — those are tracked separately)
# Row 0 is the top of the map.
#
#   0  1  2  3  4  5  6  7
# 0 #  #  #  #  #  #  #  #
# 1 #  1  .  #  .  .  2  #
# 2 #  .  .  #  .  #  .  #
# 3 #  #  .  .  K  .  .  #
# 4 #  .  .  D  .  .  #  #
# 5 #  .  #  #  .  .  .  #
# 6 #  .  .  .  .  #  X  #
# 7 #  #  #  #  #  #  #  #

_BASE_GRID = [
    [WALL,  WALL,  WALL,  WALL,  WALL,  WALL,  WALL,  WALL],
    [WALL,  EMPTY, EMPTY, WALL,  EMPTY, EMPTY, EMPTY, WALL],
    [WALL,  EMPTY, EMPTY, WALL,  EMPTY, WALL,  EMPTY, WALL],
    [WALL,  WALL,  EMPTY, EMPTY, KEY,   EMPTY, EMPTY, WALL],
    [WALL,  EMPTY, EMPTY, LOCKED_DOOR, EMPTY, EMPTY, WALL, WALL],
    [WALL,  EMPTY, WALL,  WALL,  EMPTY, EMPTY, EMPTY, WALL],
    [WALL,  EMPTY, EMPTY, EMPTY, EMPTY, WALL,  EXIT,  WALL],
    [WALL,  WALL,  WALL,  WALL,  WALL,  WALL,  WALL,  WALL],
]

_AGENT_STARTS = {
    1: (1, 1),
    2: (1, 6),
}


class DungeonWorld:
    def __init__(self):
        self.grid = [row[:] for row in _BASE_GRID]
        self.agent_positions = dict(_AGENT_STARTS)
        self.agent_inventories = {1: [], 2: []}
        self.agent_visited = {1: set(), 2: set()}

        for agent_id, pos in self.agent_positions.items():
            self.agent_visited[agent_id].add(pos)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def _cell_type(self, row, col):
        return self.grid[row][col]

    def get_visible_cells(self, agent_id):
        """Return a dict of (row, col) -> cell_type for the agent's current
        cell and the four cardinal neighbours (walls and out-of-bounds cells
        are included so the agent knows they are blocked)."""
        r, c = self.agent_positions[agent_id]
        cells = {}
        for dr, dc in [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < 8 and 0 <= nc < 8:
                cells[(nr, nc)] = self._cell_type(nr, nc)
            else:
                cells[(nr, nc)] = WALL  # treat out-of-bounds as wall
        return cells

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def move_agent(self, agent_id, direction):
        """Move the agent one step in the given direction.

        Returns (success: bool, message: str).
        """
        if direction not in DIRECTIONS:
            return False, f"Unknown direction '{direction}'."

        dr, dc = DIRECTIONS[direction]
        r, c = self.agent_positions[agent_id]
        nr, nc = r + dr, c + dc

        if not (0 <= nr < 8 and 0 <= nc < 8):
            return False, "Can't move out of bounds."

        cell = self._cell_type(nr, nc)
        if cell == WALL:
            return False, "There's a wall there."
        if cell == LOCKED_DOOR:
            return False, "The door is locked — you need a key."

        self.agent_positions[agent_id] = (nr, nc)
        self.agent_visited[agent_id].add((nr, nc))
        return True, f"Agent {agent_id} moved {direction} to ({nr}, {nc})."

    def pick_up_item(self, agent_id):
        """Pick up the item at the agent's current cell (if any).

        Returns (success: bool, message: str).
        """
        r, c = self.agent_positions[agent_id]
        cell = self._cell_type(r, c)

        if cell == KEY:
            self.agent_inventories[agent_id].append(KEY)
            self.grid[r][c] = EMPTY
            return True, f"Agent {agent_id} picked up the KEY."
        if cell == EMPTY or cell == WALL or cell == LOCKED_DOOR or cell == EXIT:
            return False, "Nothing to pick up here."
        return False, f"Can't pick up cell type {cell}."

    def use_item(self, agent_id, item, target):
        """Use an item from the agent's inventory on a target.

        target is a (row, col) tuple.
        Returns (success: bool, message: str).
        """
        if item not in self.agent_inventories[agent_id]:
            return False, f"Agent {agent_id} doesn't have that item."

        tr, tc = target
        if not (0 <= tr < 8 and 0 <= tc < 8):
            return False, "Target is out of bounds."

        cell = self._cell_type(tr, tc)

        if item == KEY and cell == LOCKED_DOOR:
            # Verify the target is adjacent to the agent
            ar, ac = self.agent_positions[agent_id]
            if abs(ar - tr) + abs(ac - tc) > 1:
                return False, "Target is not adjacent — move closer first."
            self.agent_inventories[agent_id].remove(KEY)
            self.grid[tr][tc] = EMPTY
            return True, f"Agent {agent_id} unlocked the door at ({tr}, {tc})!"

        return False, f"Can't use item {item} on cell type {cell}."

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def __str__(self):
        # Build a rendering grid that overlays agent positions
        render = [row[:] for row in self.grid]
        for agent_id, (r, c) in self.agent_positions.items():
            render[r][c] = AGENT1 if agent_id == 1 else AGENT2

        col_header = "   " + "".join(f" {c}" for c in range(8))
        separator  = "   " + "--" * 8
        lines = [col_header, separator]
        for r, row in enumerate(render):
            row_str = "".join(CELL_SYMBOLS[cell] for cell in row)
            lines.append(f"{r} |{row_str}")
        return "\n".join(lines)
