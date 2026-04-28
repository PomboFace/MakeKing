import random
import json
import os

BOARD_SIZE = 4
OUTPUT_DIR = "generated_levels"

# ------------------------
# SHAPES
# ------------------------

SHAPES = [
    {"pattern": [(0,0),(1,0)], "element": "fire"},
    {"pattern": [(0,0),(0,1)], "element": "water"},
    {"pattern": [(0,0),(1,0),(0,1)], "element": "water"},
    {"pattern": [(0,0),(1,0),(2,0)], "element": "fire"},
    {"pattern": [(0,0),(1,1),(2,2)], "element": "wind"},
]

DIRECTIONS = [
    None,
    [1,0],
    [-1,0],
    [0,1],
    [0,-1]
]

# ------------------------
# HELPERS
# ------------------------

def empty_board():
    return [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]

def in_bounds(x,y):
    return 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE

# ------------------------
# HAND
# ------------------------

def generate_hand():
    hand = []

    for _ in range(4):
        shape = random.choice(SHAPES)

        direction = None
        if shape["element"] == "wind":
            direction = random.choice([d for d in DIRECTIONS if d])

        hand.append({
            "pattern": shape["pattern"],
            "element": shape["element"],
            "direction": direction
        })

    return hand

# ------------------------
# BOARD
# ------------------------

def generate_board():
    board = empty_board()

    # enemies
    for _ in range(random.randint(3,5)):
        x,y = random.randint(0,3), random.randint(0,3)
        board[y][x] = {
            "kind": "enemy",
            "element": random.choice(["fire","water"]),
            "immovable": False,
            "active": False
        }

    # symbols
    for _ in range(random.randint(1,2)):
        x,y = random.randint(0,3), random.randint(0,3)
        board[y][x] = {
            "kind": "symbol",
            "element": random.choice(["fire","water"]),
            "immovable": True,
            "active": False
        }

    # rocks
    for _ in range(random.randint(0,2)):
        x,y = random.randint(0,3), random.randint(0,3)
        board[y][x] = {
            "kind": "enemy",
            "element": "fire",
            "immovable": True,
            "active": False
        }

    return board

# ------------------------
# LEVEL GENERATION
# ------------------------

def generate_level():
    return {
        "board": generate_board(),
        "hand": generate_hand()
    }

# ------------------------
# FILE OUTPUT
# ------------------------

def save_level(level, index):
    filename = os.path.join(OUTPUT_DIR, f"level_{index:03d}.json")

    with open(filename, "w") as f:
        json.dump(level, f, indent=2)

# ------------------------
# MAIN
# ------------------------

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    NUM_LEVELS = 10

    for i in range(NUM_LEVELS):
        level = generate_level()
        save_level(level, i + 1)

    print(f"Generated {NUM_LEVELS} levels in '{OUTPUT_DIR}/'")