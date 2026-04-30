import datetime
import json
import os
import sys

PRESET_DIR = "assets/presets"

GRID_SIZE = 4
CELL_SIZE = 90
UI_HEIGHT = 160
WIDTH = GRID_SIZE * CELL_SIZE
HEIGHT = GRID_SIZE * CELL_SIZE + UI_HEIGHT
HAND_Y = GRID_SIZE * CELL_SIZE + 20
CARD_W = 90
CARD_H = 90

TAN = (108,97,91)
DARK_TAN = (61,44,56)
WHITE = (240, 240, 240)
BLACK = (30, 30, 30)
RED = (200, 60, 60)
BLUE = (60, 60, 200)
GRAY = (120, 120, 120)
GREEN = (60, 180, 60)
YELLOW = (220, 220, 60)
LIGHT_RED = (255, 120, 120)

BOARD_CHOICES = [
    "Empty",
    "Enemy Fire",
    "Enemy Water",
    "Enemy Rock",
    "Symbol Fire",
    "Symbol Water",
    "Symbol Wind",
]

HAND_ELEMENTS = ["fire", "water", "wind", "rock"]
HAND_SHAPE_PATTERNS = {
    "Small L": [[0, 0], [1, 0], [0, 1]],
    "Long L Right": [[0, 0], [0, 1], [0, 2], [1, 2]],
    "Long L Left": [[0, 0], [0, 1], [0, 2], [-1, 2]],
    "Line 2": [[0, 0], [1, 0]],
    "Line 3": [[0, 0], [1, 0], [2, 0]],
    "Line 4": [[0, 0], [1, 0], [2, 0], [3, 0]],
    "Square": [[0, 0], [1, 0], [0, 1], [1, 1]],
    "T": [[0, 0], [1, 0], [2, 0], [1, 1]],
    "Diagonal 2": [[0, 0], [1, 1]],
    "Diagonal 3": [[0, 0], [1, 1], [2, 2]],
}
HAND_SHAPE_CHOICES = list(HAND_SHAPE_PATTERNS)
HAND_PATTERN_TO_NAME = {
    tuple(map(tuple, pattern)): name
    for name, pattern in HAND_SHAPE_PATTERNS.items()
}
DIRECTION_CHOICES = ["None", "Right", "Left", "Down", "Up"]
SHAPES = list(HAND_SHAPE_PATTERNS.values())

ELEMENTS = ["fire", "wind", "water", "rock"]
ELEMENT_COLORS = {
    "fire": RED,
    "water": BLUE,
    "rock": BLACK,
    "wind": YELLOW,
}
WEAKNESS = {
    "fire": ["fire"],
    "water": ["water"],
    "rock": ["fire", "water"],
}


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def ensure_preset_dir():
    os.makedirs(PRESET_DIR, exist_ok=True)
    return PRESET_DIR


def get_preset_path(filename):
    return ensure_preset_dir() + "/" + filename


def save_json_preset(payload, name=None):
    if name is None or not name.strip():
        name = datetime.datetime.now().strftime("preset_%Y%m%d_%H%M%S.json")
    elif not os.path.isabs(name) and not name.lower().endswith(".json"):
        name = f"{name}.json"

    path = name if os.path.isabs(name) else get_preset_path(name)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return path


def read_json_preset(filename_or_path):
    path = filename_or_path
    if not os.path.isabs(path):
        path = get_preset_path(path)

    if not os.path.exists(path):
        raise FileNotFoundError(f"Preset file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_preset_files():
    root = ensure_preset_dir()
    presets = [f for f in os.listdir(root) if f.lower().endswith(".json")]
    presets.sort(key=lambda f: os.path.getmtime(os.path.join(root, f)), reverse=True)
    return presets

def preload_levels():
    levels = []

    for i in range(1, 99):
        filename = f"preset_{i:02d}.json"
        path = get_preset_path(filename)
       
        if not os.path.exists(path):
            continue
        name = f"Level {i:02d}"

        levels.append((name, filename))
    return levels


def shape_choice_to_pattern(choice):
    return HAND_SHAPE_PATTERNS.get(choice, [[0, 0]])


def pattern_to_shape_choice(pattern):
    return HAND_PATTERN_TO_NAME.get(tuple(map(tuple, pattern)), HAND_SHAPE_CHOICES[0])
