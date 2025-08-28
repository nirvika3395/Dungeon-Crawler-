# game_logic.py
from collections import deque
from dataclasses import dataclass
from typing import List, Tuple, Optional

# --- Symbols for tiles ---
FLOOR, WALL, ITEM, MONSTER, START, EXIT = ".", "#", "I", "M", "S", "E"

# A template map so we can reset easily
TEMPLATE_MAP: List[List[str]] = [
    [START, FLOOR, FLOOR, WALL, FLOOR],
    [FLOOR,  WALL,  ITEM, FLOOR,   FLOOR],
    [FLOOR, ITEM,  MONSTER, WALL,    FLOOR],
    [WALL, FLOOR, FLOOR, FLOOR,   EXIT],
]

# ========== Linked list quest log ==========
@dataclass
class LogNode:
    text: str
    next: Optional["LogNode"] = None

class QuestLog:
    def __init__(self) -> None:
        self.head: Optional[LogNode] = None
        self.tail: Optional[LogNode] = None
        self.size = 0

    def add(self, text: str) -> None:
        node = LogNode(text)
        if not self.head:
            self.head = self.tail = node
        else:
            assert self.tail is not None
            self.tail.next = node
            self.tail = node
        self.size += 1

    def last_n(self, n: int) -> List[str]:
        out: List[str] = []
        cur = self.head
        while cur:
            out.append(cur.text)
            cur = cur.next
        return out[-n:]

# ========== Global state (initialized by _init_state) ==========
dungeon_map: List[List[str]] = []
ROWS = COLS = 0
player_rc: List[int] = [0, 0]              # [row, col]
inventory: List[str] = []
revealed: List[List[bool]] = []            # fog-of-war visibility
quest_log: QuestLog                        # linked-list log
undo_stack: List[Tuple[int, int]]          # stack of previous positions
monster_queue: deque[Tuple[int, int]]      # queue of monster turns
game_over: bool = False

# ========== Helpers ==========
def _copy_map() -> List[List[str]]:
    return [row[:] for row in TEMPLATE_MAP]

def _in_bounds(r: int, c: int) -> bool:
    return 0 <= r < ROWS and 0 <= c < COLS

def _find_start() -> Tuple[int, int]:
    for r in range(ROWS):
        for c in range(COLS):
            if dungeon_map[r][c] == START:
                return r, c
    return 0, 0

def _walkable(r: int, c: int) -> bool:
    return _in_bounds(r, c) and dungeon_map[r][c] != WALL

def reveal_fog(r: int, c: int) -> None:
    """Recursive DFS reveal."""
    if not _in_bounds(r, c) or revealed[r][c]:
        return
    revealed[r][c] = True
    if dungeon_map[r][c] != WALL:
        reveal_fog(r - 1, c)
        reveal_fog(r + 1, c)
        reveal_fog(r, c - 1)
        reveal_fog(r, c + 1)

def _init_state() -> None:
    """Initialize/resets the entire game state."""
    global dungeon_map, ROWS, COLS, player_rc, inventory, revealed
    global quest_log, undo_stack, monster_queue, game_over

    dungeon_map = _copy_map()
    ROWS, COLS = len(dungeon_map), len(dungeon_map[0])

    player_rc = list(_find_start())
    inventory = []
    revealed = [[False for _ in range(COLS)] for _ in range(ROWS)]

    quest_log = QuestLog()
    quest_log.add("Entered the dungeon.")

    undo_stack = []
    monster_queue = deque((r, c)
                          for r in range(ROWS)
                          for c in range(COLS)
                          if dungeon_map[r][c] == MONSTER)

    game_over = False
    reveal_fog(*player_rc)

# Call once on import
_init_state()

# ========== Public getters ==========
def get_player_rc() -> Tuple[int, int]:
    return tuple(player_rc)

def get_map() -> List[List[str]]:
    return dungeon_map

def get_revealed() -> List[List[bool]]:
    return revealed

def get_inventory() -> List[str]:
    return inventory

def get_log_tail(n: int = 6) -> List[str]:
    return quest_log.last_n(n)

def is_game_over() -> bool:
    return game_over

# ========== Core actions ==========
def move_player(dx: int, dy: int) -> None:
    """Attempt to move by (dx, dy) in grid coords. Handles events, fog, logs, turns."""
    global game_over
    if game_over:
        return

    r, c = player_rc
    nr, nc = r + dy, c + dx
    if not _walkable(nr, nc):
        quest_log.add("Bumped into a wall.")
        return

    # push for undo
    undo_stack.append((r, c))
    player_rc[0], player_rc[1] = nr, nc
    reveal_fog(nr, nc)

    cell = dungeon_map[nr][nc]
    if cell == ITEM:
        inventory.append("Mysterious Item")
        dungeon_map[nr][nc] = FLOOR
        quest_log.add("Picked up a Mysterious Item.")
    elif cell == MONSTER:
        quest_log.add("The Monster Ate you ")
        game_over = True 
    elif cell == EXIT:
        quest_log.add("You found the exit! Game over. Press Play Again.")
        game_over = True

    # simple monster turn (queue rotation)
    if monster_queue:
        mr, mc = monster_queue.popleft()
        quest_log.add("Monster growls in the distance...")
        monster_queue.append((mr, mc))

def undo_move() -> None:
    if game_over:
        return
    if not undo_stack:
        quest_log.add("Nothing to undo.")
        return
    prev = undo_stack.pop()
    player_rc[0], player_rc[1] = prev
    reveal_fog(*prev)
    quest_log.add("Undid your last move.")

def reset_game() -> None:
    _init_state()
    quest_log.add("New game started.")

# ========== Text command interface ==========
DIRS = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}

def process_command(text: str) -> str:
    """
    Parse and execute simple text commands.
    Returns a short feedback string for the UI.
    """
    cmd = text.strip().lower()
    if not cmd:
        return ""

    if cmd.startswith("go "):
        d = cmd[3:].strip()
        if d in DIRS:
            before = get_player_rc()
            dx, dy = DIRS[d]
            move_player(dx, dy)
            after = get_player_rc()
            return "You can’t go that way." if before == after else f"You go {d}."
        return "Try: north/south/east/west."

    if cmd in ("get", "take", "pickup", "pick up"):
        r, c = get_player_rc()
        if dungeon_map[r][c] == ITEM:
            inventory.append("Mysterious Item")
            dungeon_map[r][c] = FLOOR
            quest_log.add("Picked up a Mysterious Item.")
            return "Picked up."
        quest_log.add("There is nothing to pick up.")
        return "Nothing to pick up."

    if cmd in ("undo", "back", "backtrack"):
        undo_move()
        return "Undid your last move."

    if cmd in ("inventory", "inv", "i"):
        inv = ", ".join(inventory) if inventory else "(empty)"
        quest_log.add(f"Inventory: {inv}")
        return f"Inventory: {inv}"

    if cmd in ("look", "l"):
        r, c = get_player_rc()
        cell = dungeon_map[r][c]
        names = {FLOOR:"floor", WALL:"wall", ITEM:"item", MONSTER:"monster", START:"start", EXIT:"exit"}
        desc = f"You are on {names.get(cell, 'something')}."
        quest_log.add(desc)
        return desc

    if cmd in ("restart", "reset", "play again"):
        reset_game()
        return "New game started."

    return "Unknown command. Try: go north|south|east|west, get, undo, look, inventory."
