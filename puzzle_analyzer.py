# puzzle_analyzer.py

from math import exp
from copy import deepcopy

BOARD_SIZE = 4


# ----------------------------
# Shape utilities
# ----------------------------

def rotate_shape(shape):
    return [(y, -x) for (x, y) in shape]


def normalize_shape(shape):
    min_x = min(x for x, y in shape)
    min_y = min(y for x, y in shape)
    return sorted([(x - min_x, y - min_y) for x, y in shape])


def get_unique_rotations(pattern):
    shape = [tuple(p) for p in pattern]
    rotations = set()

    for _ in range(4):
        shape = normalize_shape(shape)
        rotations.add(tuple(shape))
        shape = rotate_shape(shape)

    return [list(r) for r in rotations]


# ----------------------------
# Placement logic
# ----------------------------

def get_shape_bounds(shape):
    max_x = max(x for x, y in shape)
    max_y = max(y for x, y in shape)
    return max_x, max_y


def get_valid_placements(shape):
    placements = []
    max_x, max_y = get_shape_bounds(shape)

    for x in range(BOARD_SIZE - max_x):
        for y in range(BOARD_SIZE - max_y):
            cells = [(x + dx, y + dy) for dx, dy in shape]
            placements.append(cells)

    return placements


# ----------------------------
# Evaluation
# ----------------------------

def evaluate_placement(board, placement, piece):
    useful = False

    for x, y in placement:
        cell = board[y][x]

        if cell is None:
            continue

        if piece["element"] == "wind":
            if cell["kind"] == "enemy" and not cell.get("immovable", False):
                useful = True

        else:
            if cell["kind"] == "enemy":
                if cell["element"] == piece["element"] or cell["element"] == "rock":
                    useful = True

            elif cell["kind"] == "symbol":
                if cell["element"] == piece["element"]:
                    useful = True

    return useful


# ----------------------------
# Piece analysis
# ----------------------------

def analyze_piece(board, piece):
    rotations = get_unique_rotations(piece["pattern"])

    valid = 0
    useful = 0

    for shape in rotations:
        placements = get_valid_placements(shape)

        for placement in placements:
            valid += 1
            if evaluate_placement(board, placement, piece):
                useful += 1

    dead = valid - useful

    return {
        "valid": valid,
        "useful": useful,
        "dead": dead,
        "freedom": useful / valid if valid else 0
    }


# ----------------------------
# Count helpers (for Excel stats)
# ----------------------------

def count_board(board):
    enemies = 0
    symbols = 0
    rocks = 0

    for row in board:
        for cell in row:
            if not cell:
                continue
            if cell["kind"] == "enemy":
                enemies += 1
                if cell["element"] == "rock":
                    rocks += 1
            elif cell["kind"] == "symbol":
                symbols += 1

    return enemies, symbols, rocks


def count_hand(hand):
    wind_shapes = 0
    total_size = 0

    for piece in hand:
        total_size += len(piece["pattern"])
        if piece["element"] == "wind":
            wind_shapes += 1

    avg_size = total_size / len(hand)

    return wind_shapes, avg_size


# ----------------------------
# Excel formulas
# ----------------------------

def compute_excel_stats(enemies, symbols, rocks, wind_shapes, avg_size, flexibility, overlap_pressure, dead_ratio):

    # Core counts (kept for reference, not driving difficulty anymore)
    OP = (enemies + symbols) / 4
    IP = round(rocks / max(1, enemies), 3)

    # Wind influence
    WC = wind_shapes * 0.5

    Flex = round(flexibility, 3)


    # ----------------------------
    # DIFFICULTY MODEL - Tuned for variability and prediction
    # ----------------------------
    ED = (
        (4.0 * overlap_pressure) +
        (2.5 * (1 - Flex)) +
        (1.8 * IP) +
        (0.7 * WC) +
        (-1.3 * dead_ratio)
    )

    # Normalize to 1–10 range
    CD = max(1, min(10, round(ED)))

    return {
        "OP": OP,
        "IP": IP,
        "WC": WC,
        "Flex": Flex,
        "OverlapPressure": overlap_pressure,
        "ED": ED,
        "CD": CD
    }


# ----------------------------
# Level analysis
# ----------------------------

def analyze_level(level_data):
    board = level_data["board"]
    hand = level_data["hand"]

    # Placement stats
    piece_stats = [analyze_piece(board, p) for p in hand]

    total_valid = sum(p["valid"] for p in piece_stats)
    total_useful = sum(p["useful"] for p in piece_stats)
    total_dead = sum(p["dead"] for p in piece_stats)

    avg_freedom = sum(p["freedom"] for p in piece_stats) / len(piece_stats)
    dead_ratio = total_dead / total_valid if total_valid else 0

    # Counts
    enemies, symbols, rocks = count_board(board)
    wind_shapes, avg_size = count_hand(hand)

    # ----------------------------
    # Overlap Pressure (NEW CORE METRIC)
    # ----------------------------
    num_pieces = len(hand)
    board_cells = BOARD_SIZE * BOARD_SIZE

    overlap_pressure = total_valid / (board_cells * num_pieces)

    # Flexibility = how many useful placements exist
    flexibility = avg_freedom

    excel = compute_excel_stats(
        enemies, symbols, rocks,
        wind_shapes, avg_size,
        flexibility,
        overlap_pressure,
        dead_ratio
    )

    return {
        # Original counts
        "Enemies": enemies,
        "Symbols": symbols,
        "Rocks": rocks,
        "WindShapes": wind_shapes,
        "ShapeSizeAvg": avg_size,
        "OverlapPressure": overlap_pressure,

        # New metrics
        "AvgFreedom": avg_freedom,
        "DeadRatio": dead_ratio,
        "TotalValidPlacements": total_valid,
        "TotalUsefulPlacements": total_useful,

        # Excel stats
        **excel
    }


# ----------------------------
# File dialogs
# ----------------------------

def pick_input_files():
    from tkinter import Tk, filedialog
    root = Tk()
    root.withdraw()
    files = filedialog.askopenfilenames(
        title="Select level JSON file(s)",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    root.destroy()
    return list(files)


def pick_save_file():
    from tkinter import Tk, filedialog
    root = Tk()
    root.withdraw()
    file_path = filedialog.asksaveasfilename(
        title="Save CSV as",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")]
    )
    root.destroy()
    return file_path


# ----------------------------
# Load levels
# ----------------------------

def load_levels_from_files(filepaths):
    import json
    levels = []
    for path in filepaths:
        with open(path, "r") as f:
            data = json.load(f)

        if isinstance(data, list):
            levels.extend(data)
        else:
            levels.append(data)

    return levels


# ----------------------------
# Table output columns
# ----------------------------

OUTPUT_COLUMNS = [
    "Level", "Enemies", "Symbols", "Rocks", "WindShapes", "ShapeSizeAvg", "AvgFreedom", "DeadRatio",
    "TotalValidPlacements", "TotalUsefulPlacements", "OP", "IP", "WC", "Flex", "OverlapPressure", "ED", "CD", "PlayerDifficulty"
]


# ----------------------------
# Table printing
# ----------------------------

def print_table(results, columns=None):
    if not results:
        return

    if columns is None:
        columns = OUTPUT_COLUMNS

    # Ensure all keys exist
    for r in results:
        for col in columns:
            if col not in r:
                r[col] = ""

    # Column widths
    col_widths = {}
    for col in columns:
        max_len = max(len(str(r[col])) for r in results)
        col_widths[col] = max(max_len, len(col)) + 2

    # Header
    header = "".join(col.ljust(col_widths[col]) for col in columns)
    print("\n" + header)
    print("-" * len(header))

    # Rows
    for r in results:
        row = ""
        for col in columns:
            val = r[col]
            if isinstance(val, float):
                val = round(val, 4)
            row += str(val).ljust(col_widths[col])
        print(row)


# ----------------------------
# CSV export
# ----------------------------

def save_results_to_csv(results, filepath, columns=None):
    import csv
    if columns is None:
        columns = OUTPUT_COLUMNS

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for r in results:
            writer.writerow(r)


if __name__ == "__main__":
    import json
    import sys
    from tkinter import messagebox

    # ----------------------------
    # Run
    # ----------------------------

    filepaths = pick_input_files()

    if not filepaths:
        print("No files selected. Exiting.")
        sys.exit(0)

    levels = load_levels_from_files(filepaths)

    results = []

    for i, lvl in enumerate(levels, start=1):
        res = analyze_level(lvl)

        # Add metadata
        res["Level"] = i
        res["PlayerDifficulty"] = lvl.get("difficulty", "")

        results.append(res)

    # ----------------------------
    # Sorting
    # ----------------------------

    # Change this depending on what you want:
    SORT_BY = "Level"#"CD"  # options: "CD", "AvgFreedom", "DeadRatio"

    results.sort(key=lambda x: x.get(SORT_BY, 0))

    # ----------------------------
    # Output
    # ----------------------------

    print_table(results)

    # ----------------------------
    # Save CSV (dialog)
    # ----------------------------

    if messagebox.askyesno("Export", "Save results to CSV?"):
        out_path = pick_save_file()

        if not out_path:
            print("Save cancelled.")
            sys.exit(0)

        save_results_to_csv(results, out_path)
        print(f"Saved to {out_path}")