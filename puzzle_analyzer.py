# puzzle_analyzer.py

from math import exp
from copy import deepcopy
from statistics import mean
import json
import csv
import numpy as np

BOARD_SIZE = 4


# ----------------------------
# Shape utilities
# ----------------------------

def rotate_shape(shape):
    return [(y, -x) for x, y in shape]


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


def inside_board(x, y):
    return 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE


# ----------------------------
# Shape complexity
# ----------------------------

def compute_shape_awkwardness(piece):

    shape = piece["pattern"]

    xs = [x for x, y in shape]
    ys = [y for x, y in shape]

    width = max(xs) - min(xs) + 1
    height = max(ys) - min(ys) + 1

    cells = len(shape)
    box_area = width * height

    waste = box_area - cells

    rotations = len(get_unique_rotations(shape))

    thinness = max(width, height) / max(1, min(width, height))

    awkwardness = (
        waste * 1.0 +
        rotations * 0.6 +
        thinness * 0.8
    )

    return awkwardness


# ----------------------------
# Placement evaluation
# ----------------------------

def evaluate_placement(board, placement, piece):

    score = 0
    punishment = 0
    interactions = 0

    for x, y in placement:

        cell = board[y][x]

        if cell is None:
            score -= 0.1
            continue

        # ---------------------------------
        # WIND
        # ---------------------------------

        if piece["element"] == "wind":

            if cell["kind"] == "enemy":

                if not cell.get("immovable", False):

                    score += 3
                    interactions += 2

                    dx, dy = piece["direction"]

                    nx = x + dx
                    ny = y + dy

                    if inside_board(nx, ny):

                        next_cell = board[ny][nx]

                        if next_cell is not None:

                            # collision setup
                            score += 4
                            interactions += 3

                            if next_cell["kind"] == "symbol":
                                punishment += 2

                else:
                    score -= 0.5

        # ---------------------------------
        # NORMAL ELEMENTS
        # ---------------------------------

        else:

            if cell["kind"] == "enemy":

                if (
                    cell["element"] == piece["element"] or
                    cell["element"] == "rock"
                ):
                    score += 5
                    interactions += 2

                else:
                    score -= 1
                    punishment += 1

            elif cell["kind"] == "symbol":

                if cell["element"] == piece["element"]:
                    score += 4
                    interactions += 1

                else:
                    score -= 4
                    punishment += 3

    return {
        "score": score,
        "punishment": punishment,
        "interactions": interactions
    }


# ----------------------------
# Piece analysis
# ----------------------------

def analyze_piece(board, piece):

    rotations = get_unique_rotations(piece["pattern"])

    valid = 0

    scores = []
    punishments = []
    interactions = []

    useful = 0
    optimal = 0

    best_score = -999999

    for shape in rotations:

        placements = get_valid_placements(shape)

        for placement in placements:

            valid += 1

            result = evaluate_placement(board, placement, piece)

            score = result["score"]

            scores.append(score)
            punishments.append(result["punishment"])
            interactions.append(result["interactions"])

            if score > 0:
                useful += 1

            if score > best_score:
                best_score = score

    for s in scores:
        if s >= best_score * 0.8:
            optimal += 1

    dead = valid - useful

    ambiguity = optimal / max(1, useful)

    return {
        "valid": valid,
        "useful": useful,
        "dead": dead,

        "freedom": useful / valid if valid else 0,

        "avg_score": mean(scores) if scores else 0,

        "best_score": best_score,

        "ambiguity": ambiguity,

        "avg_punishment": mean(punishments) if punishments else 0,

        "interaction_density": mean(interactions) if interactions else 0,

        "shape_awkwardness": compute_shape_awkwardness(piece)
    }


# ----------------------------
# Count helpers
# ----------------------------

def count_board(board):

    enemies = 0
    symbols = 0
    rocks = 0
    movable_enemies = 0
    occupied = 0

    for row in board:
        for cell in row:

            if not cell:
                continue

            occupied += 1

            if cell["kind"] == "enemy":

                enemies += 1

                if cell["element"] == "rock":
                    rocks += 1

                if not cell.get("immovable", False):
                    movable_enemies += 1

            elif cell["kind"] == "symbol":
                symbols += 1

    return {
        "Enemies": enemies,
        "Symbols": symbols,
        "Rocks": rocks,
        "MovableEnemies": movable_enemies,
        "OccupiedCells": occupied
    }


def count_hand(hand):

    wind_shapes = 0
    total_size = 0

    for piece in hand:

        total_size += len(piece["pattern"])

        if piece["element"] == "wind":
            wind_shapes += 1

    return {
        "WindShapes": wind_shapes,
        "ShapeSizeAvg": total_size / len(hand)
    }


# ----------------------------
# Higher-level metrics
# ----------------------------

def compute_metrics(piece_stats, board_stats, hand_stats):

    total_valid = sum(p["valid"] for p in piece_stats)
    total_useful = sum(p["useful"] for p in piece_stats)
    total_dead = sum(p["dead"] for p in piece_stats)

    avg_freedom = mean(p["freedom"] for p in piece_stats)

    avg_ambiguity = mean(p["ambiguity"] for p in piece_stats)

    avg_interaction = mean(
        p["interaction_density"]
        for p in piece_stats
    )

    avg_punishment = mean(
        p["avg_punishment"]
        for p in piece_stats
    )

    avg_awkwardness = mean(
        p["shape_awkwardness"]
        for p in piece_stats
    )

    avg_score = mean(
        p["avg_score"]
        for p in piece_stats
    )

    dead_ratio = total_dead / max(1, total_valid)

    occupied_ratio = (
        board_stats["OccupiedCells"] /
        (BOARD_SIZE * BOARD_SIZE)
    )

    wind_dependency = (
        hand_stats["WindShapes"] *
        board_stats["MovableEnemies"]
    ) / 4

    objective_pressure = (
        board_stats["Enemies"] +
        board_stats["Symbols"]
    ) / 4

    planning_pressure = (
        avg_interaction *
        avg_punishment
    )

    return {
        "TotalValidPlacements": total_valid,
        "TotalUsefulPlacements": total_useful,
        "DeadRatio": dead_ratio,

        "AvgFreedom": avg_freedom,
        "Ambiguity": avg_ambiguity,
        "InteractionDensity": avg_interaction,
        "Punishment": avg_punishment,
        "ShapeAwkwardness": avg_awkwardness,
        "AvgPlacementScore": avg_score,

        "OccupiedRatio": occupied_ratio,
        "WindDependency": wind_dependency,
        "ObjectivePressure": objective_pressure,
        "PlanningPressure": planning_pressure
    }


# ----------------------------
# Difficulty formula
# ----------------------------

# learned weights
LEARNED_WEIGHTS = {
    "AvgFreedom": -2.8,
    "Ambiguity": 3.6,
    "InteractionDensity": 1.9,
    "Punishment": 2.7,
    "ShapeAwkwardness": 0.9,
    "DeadRatio": 2.4,
    "OccupiedRatio": 1.1,
    "WindDependency": 1.6,
    "ObjectivePressure": 1.5,
    "PlanningPressure": 2.1,
    "bias": 1.7
}

def compute_difficulty(metrics):

    ED = (
        metrics["AvgFreedom"] * LEARNED_WEIGHTS["AvgFreedom"] +
        metrics["Ambiguity"] * LEARNED_WEIGHTS["Ambiguity"] +
        metrics["InteractionDensity"] * LEARNED_WEIGHTS["InteractionDensity"] +
        metrics["Punishment"] * LEARNED_WEIGHTS["Punishment"] +
        metrics["ShapeAwkwardness"] * LEARNED_WEIGHTS["ShapeAwkwardness"] +
        metrics["DeadRatio"] * LEARNED_WEIGHTS["DeadRatio"] +
        metrics["OccupiedRatio"] * LEARNED_WEIGHTS["OccupiedRatio"] +
        metrics["WindDependency"] * LEARNED_WEIGHTS["WindDependency"] +
        metrics["ObjectivePressure"] * LEARNED_WEIGHTS["ObjectivePressure"] +
        metrics["PlanningPressure"] * LEARNED_WEIGHTS["PlanningPressure"] +
        LEARNED_WEIGHTS["bias"]
    )

    # rescale back to 0–10
    CD = max(0, min(10, round(ED * 10)))

    return {
        "ED": ED,
        "CD": CD
    }


# ----------------------------
# Weight optimization
# ----------------------------

FEATURE_COLUMNS = [
    "AvgFreedom",
    "Ambiguity",
    "InteractionDensity",
    "Punishment",
    "ShapeAwkwardness",
    "DeadRatio",
    "OccupiedRatio",
    "WindDependency",
    "ObjectivePressure",
    "PlanningPressure"
]


def fit_weights(results):

    rows = []
    targets = []

    # collect data
    for r in results:

        if r.get("PlayerDifficulty", "") == "":
            continue

        rows.append([
            r[c] for c in FEATURE_COLUMNS
        ])

        # normalize to 0–1
        targets.append(float(r["PlayerDifficulty"]) / 10.0)

    if len(rows) < 5:
        return None

    X = np.array(rows, dtype=float)
    y = np.array(targets, dtype=float)

    # ----------------------------
    # feature normalization (IMPORTANT)
    # ----------------------------
    X_mean = X.mean(axis=0)
    X_std = X.std(axis=0) + 1e-8

    X_norm = (X - X_mean) / X_std

    # add bias
    X_norm = np.column_stack([X_norm, np.ones(len(X_norm))])

    # least squares
    weights, *_ = np.linalg.lstsq(X_norm, y, rcond=None)

    learned = {
        FEATURE_COLUMNS[i]: float(weights[i] / X_std[i])
        for i in range(len(FEATURE_COLUMNS))
    }

    learned["bias"] = float(weights[-1])

    return learned


# ----------------------------
# Level analysis
# ----------------------------

def analyze_level(level_data):

    board = level_data["board"]
    hand = level_data["hand"]

    piece_stats = [
        analyze_piece(board, p)
        for p in hand
    ]

    board_stats = count_board(board)
    hand_stats = count_hand(hand)

    metrics = compute_metrics(
        piece_stats,
        board_stats,
        hand_stats
    )

    difficulty = compute_difficulty(metrics)

    return {
        **board_stats,
        **hand_stats,
        **metrics,
        **difficulty
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
        filetypes=[("JSON files", "*.json")]
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
# CSV columns
# ----------------------------

OUTPUT_COLUMNS = [

    "Level",

    "Enemies",
    "Symbols",
    "Rocks",
    "MovableEnemies",
    "OccupiedCells",

    "WindShapes",
    "ShapeSizeAvg",

    "AvgFreedom",
    "Ambiguity",
    "InteractionDensity",
    "Punishment",
    "ShapeAwkwardness",
    "AvgPlacementScore",
    "TotalValidPlacements",
    "TotalUsefulPlacements",

    "PlanningPressure",
    "WindDependency",
    "ObjectivePressure",

    "DeadRatio",
    "OccupiedRatio",

    "TacticalComplexity",
    "InteractionComplexity",
    "PlanningDepth",
    "Fragility",

    "ED",
    "CD",

    "PlayerDifficulty"
]


# ----------------------------
# Table printing
# ----------------------------

def print_table(results, columns=None):

    if not results:
        return

    if columns is None:
        columns = OUTPUT_COLUMNS

    for r in results:
        for col in columns:
            if col not in r:
                r[col] = ""

    col_widths = {}

    for col in columns:
        max_len = max(len(str(r[col])) for r in results)
        col_widths[col] = max(max_len, len(col)) + 2

    header = "".join(
        col.ljust(col_widths[col])
        for col in columns
    )

    print("\n" + header)
    print("-" * len(header))

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


def excel_col(index):
    """
    Convert 0-based column index to Excel column letters.
    Example:
        0 -> A
        1 -> B
        26 -> AA
    """

    result = ""

    while index >= 0:
        result = chr(index % 26 + ord('A')) + result
        index = index // 26 - 1

    return result

def save_results_to_csv(results, filepath, columns=None):

    if columns is None:
        columns = OUTPUT_COLUMNS

    # columns that should remain RAW VALUES
    raw_columns = {

        "Level",

        "Enemies",
        "Symbols",
        "Rocks",
        "MovableEnemies",
        "OccupiedCells",

        "WindShapes",
        "ShapeSizeAvg",

        "TotalValidPlacements",
        "TotalUsefulPlacements",

        "AvgFreedom",
        "Ambiguity",
        "InteractionDensity",
        "Punishment",
        "ShapeAwkwardness",
        "AvgPlacementScore",

        "PlayerDifficulty"
    }

    with open(filepath, "w", newline="") as f:

        writer = csv.DictWriter(
            f,
            fieldnames=columns
        )

        writer.writeheader()

        for row_index, r in enumerate(results, start=2):

            row = deepcopy(r)

            # ---------------------------------
            # Excel column references
            # ---------------------------------

            col = {
                name: excel_col(i)
                for i, name in enumerate(columns)
            }

            # ---------------------------------
            # Formula fields
            # ---------------------------------

            # DeadRatio
            row["DeadRatio"] = (
                f"=("
                f"{col['TotalValidPlacements']}{row_index}-"
                f"{col['TotalUsefulPlacements']}{row_index}"
                f")/"
                f"MAX(1,{col['TotalValidPlacements']}{row_index})"
            )

            # OccupiedRatio
            row["OccupiedRatio"] = (
                f"={col['OccupiedCells']}{row_index}/16"
            )

            # WindDependency
            row["WindDependency"] = (
                f"=("
                f"{col['WindShapes']}{row_index}*"
                f"{col['MovableEnemies']}{row_index}"
                f")/4"
            )

            # ObjectivePressure
            row["ObjectivePressure"] = (
                f"=("
                f"{col['Enemies']}{row_index}+"
                f"{col['Symbols']}{row_index}"
                f")/4"
            )

            # PlanningPressure
            row["PlanningPressure"] = (
                f"="
                f"{col['InteractionDensity']}{row_index}*"
                f"{col['Punishment']}{row_index}"
            )

            # TacticalComplexity
            row["TacticalComplexity"] = (
                f"=("
                f"(1-{col['AvgFreedom']}{row_index})*3+"
                f"{col['Ambiguity']}{row_index}*4+"
                f"{col['ShapeAwkwardness']}{row_index}*0.7"
                f")"
            )

            # InteractionComplexity
            row["InteractionComplexity"] = (
                f"=("
                f"{col['InteractionDensity']}{row_index}*2+"
                f"{col['WindDependency']}{row_index}*2+"
                f"{col['ObjectivePressure']}{row_index}*1.5"
                f")"
            )

            # PlanningDepth
            row["PlanningDepth"] = (
                f"=("
                f"{col['PlanningPressure']}{row_index}*2+"
                f"{col['Punishment']}{row_index}*1.5"
                f")"
            )

            # Fragility
            row["Fragility"] = (
                f"=("
                f"{col['Punishment']}{row_index}*2+"
                f"{col['DeadRatio']}{row_index}"
                f")"
            )

            # ED
            row["ED"] = (
                f"=("
                f"{col['TacticalComplexity']}{row_index}*0.30+"
                f"{col['InteractionComplexity']}{row_index}*0.30+"
                f"{col['PlanningDepth']}{row_index}*0.25+"
                f"{col['Fragility']}{row_index}*0.15"
                f")"
            )

            # CD
            row["CD"] = (
                f"=MAX(1,MIN(10,ROUND({col['ED']}{row_index},0)))"
            )

            # ---------------------------------
            # Write row
            # ---------------------------------

            for key in row:

                if key not in raw_columns:

                    # keep formulas as strings
                    if not isinstance(row[key], str):
                        row[key] = str(row[key])

            writer.writerow(row)


# ----------------------------
# Main
# ----------------------------

if __name__ == "__main__":

    import sys
    from tkinter import messagebox

    filepaths = pick_input_files()

    if not filepaths:
        print("No files selected.")
        sys.exit(0)

    levels = load_levels_from_files(filepaths)

    results = []

    for i, lvl in enumerate(levels, start=1):

        res = analyze_level(lvl)

        res["Level"] = i

        res["PlayerDifficulty"] = lvl.get(
            "difficulty",
            ""
        )

        results.append(res)
    
    ##Update weights based on player difficulty data
    learned = fit_weights(results)
    if learned:
        LEARNED_WEIGHTS.update(learned)
        print("\nLEARNED WEIGHTS:\n")
        for k, v in learned.items():
            print(f'{k}: {round(v, 4)}')
        # recompute after learning
        for r in results:
            difficulty = compute_difficulty(r)
            r["ED"] = difficulty["ED"]
            r["CD"] = difficulty["CD"]

    SORT_BY = "Level"

    results.sort(
        key=lambda x: x.get(SORT_BY, 0)
    )

    print_table(results)

    if messagebox.askyesno(
        "Export",
        "Save results to CSV?"
    ):

        out_path = pick_save_file()

        if not out_path:
            print("Save cancelled.")
            sys.exit(0)

        save_results_to_csv(
            results,
            out_path
        )

        print(f"Saved to {out_path}")