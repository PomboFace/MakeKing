# puzzle_analyzer.py

from math import exp
from copy import deepcopy
from statistics import mean
import json
import csv
import numpy as np
import string
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

BOARD_SIZE = 4

# ----------------------------
# MODEL STORAGE
# ----------------------------

MODEL = {
    "mean": None,
    "std": None,
    "weights": None,
    "bias": None
}
# ----------------------------
# FEATURE SET
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

# ----------------------------
# ROUNDING HELPER
# ----------------------------

def round(x):
    """safe rounding for all numeric outputs"""
    try:
        return round(float(x), 4)
    except:
        return x
    

# ----------------------------
# EXCEL COLUMN NAME (A, B, ..., Z, AA, AB...)
# ----------------------------

def excel_col(n):
    name = ""
    while n >= 0:
        name = chr(n % 26 + 65) + name
        n = n // 26 - 1
    return name
# ----------------------------
# SHAPE UTILITIES
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
# PLACEMENT LOGIC
# ----------------------------

def get_shape_bounds(shape):
    return (
        max(x for x, y in shape),
        max(y for x, y in shape)
    )


def get_valid_placements(shape):
    placements = []
    max_x, max_y = get_shape_bounds(shape)

    for x in range(BOARD_SIZE - max_x):
        for y in range(BOARD_SIZE - max_y):
            placements.append([(x + dx, y + dy) for dx, dy in shape])

    return placements


def inside_board(x, y):
    return 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE


# ----------------------------
# SHAPE COMPLEXITY
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

    return waste * 1.0 + rotations * 0.6 + thinness * 0.8


# ----------------------------
# PLACEMENT EVALUATION
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

        if piece["element"] == "wind":

            if cell["kind"] == "enemy":

                if not cell.get("immovable", False):

                    score += 3
                    interactions += 2

                    dx, dy = piece["direction"]
                    nx, ny = x + dx, y + dy

                    if inside_board(nx, ny):
                        next_cell = board[ny][nx]

                        if next_cell is not None:
                            score += 4
                            interactions += 3

                            if next_cell["kind"] == "symbol":
                                punishment += 2
                else:
                    score -= 0.5

        else:

            if cell["kind"] == "enemy":

                if cell["element"] == piece["element"] or cell["element"] == "rock":
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
# PIECE ANALYSIS
# ----------------------------

def analyze_piece(board, piece):

    rotations = get_unique_rotations(piece["pattern"])

    valid = 0
    useful = 0
    optimal = 0

    scores = []
    punishments = []
    interactions = []

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

    return {
        "valid": valid,
        "useful": useful,
        "dead": valid - useful,
        "freedom": useful / valid if valid else 0,
        "avg_score": mean(scores) if scores else 0,
        "best_score": best_score,
        "ambiguity": optimal / max(1, useful),
        "avg_punishment": mean(punishments) if punishments else 0,
        "interaction_density": mean(interactions) if interactions else 0,
        "shape_awkwardness": compute_shape_awkwardness(piece)
    }


# ----------------------------
# BOARD STATS
# ----------------------------

def count_board(board):

    enemies = symbols = rocks = movable = occupied = 0

    for row in board:
        for cell in row:

            if not cell:
                continue

            occupied += 1

            if cell["kind"] == "enemy":
                enemies += 1
                if cell.get("element") == "rock":
                    rocks += 1
                if not cell.get("immovable", False):
                    movable += 1

            elif cell["kind"] == "symbol":
                symbols += 1

    return {
        "Enemies": enemies,
        "Symbols": symbols,
        "Rocks": rocks,
        "MovableEnemies": movable,
        "OccupiedCells": occupied
    }


def count_hand(hand):

    wind = 0
    total = 0

    for p in hand:
        total += len(p["pattern"])
        if p["element"] == "wind":
            wind += 1

    return {
        "WindShapes": wind,
        "ShapeSizeAvg": total / len(hand)
    }


# ----------------------------
# METRICS
# ----------------------------

def compute_metrics(piece_stats, board_stats, hand_stats):

    avg_freedom = mean(p["freedom"] for p in piece_stats)
    avg_ambiguity = mean(p["ambiguity"] for p in piece_stats)
    avg_interaction = mean(p["interaction_density"] for p in piece_stats)
    avg_punishment = mean(p["avg_punishment"] for p in piece_stats)
    avg_awkwardness = mean(p["shape_awkwardness"] for p in piece_stats)

    total_valid = sum(p["valid"] for p in piece_stats)
    total_useful = sum(p["useful"] for p in piece_stats)
    total_dead = sum(p["dead"] for p in piece_stats)

    return {
        "AvgFreedom": avg_freedom,
        "Ambiguity": avg_ambiguity,
        "InteractionDensity": avg_interaction,
        "Punishment": avg_punishment,
        "ShapeAwkwardness": avg_awkwardness,

        "DeadRatio": total_dead / max(1, total_valid),
        "OccupiedRatio": board_stats["OccupiedCells"] / 16,

        "WindDependency": hand_stats["WindShapes"] * board_stats["MovableEnemies"] / 4,
        "ObjectivePressure": (board_stats["Enemies"] + board_stats["Symbols"]) / 4,
        "PlanningPressure": avg_interaction * avg_punishment
    }


# ----------------------------
# MODEL TRAINING
# ----------------------------

def fit_weights(results):

    rows, targets = [], []

    for r in results:
        if r.get("PlayerDifficulty") == "":
            continue

        rows.append([r[c] for c in FEATURE_COLUMNS])
        targets.append(float(r["PlayerDifficulty"]) / 10.0)

    if len(rows) < 10:
        return False

    X = np.array(rows, dtype=float)
    y = np.clip(np.array(targets, dtype=float), 0, 1)

    mean = X.mean(axis=0)
    std = X.std(axis=0) + 1e-8

    Xs = (X - mean) / std

    model = Ridge(alpha=2.0)
    model.fit(Xs, y)

    MODEL["mean"] = mean
    MODEL["std"] = std
    MODEL["weights"] = model.coef_
    MODEL["bias"] = model.intercept_

    print("\nTraining MAE:", np.mean(np.abs(model.predict(Xs) - y)))

    return True


# ----------------------------
# PREDICTION
# ----------------------------

def compute_difficulty(metrics):

    if MODEL["mean"] is None:
        return {"ED": 0, "CD": 0}

    x = np.array([metrics[c] for c in FEATURE_COLUMNS], dtype=float)

    # standardize using stored stats
    x = (x - MODEL["mean"]) / MODEL["std"]

    # linear model
    ed = float(np.dot(MODEL["weights"], x) + MODEL["bias"])

    return {
        "ED": ed,
        "CD": max(0, min(10, round(ed * 10)))
    }


# ----------------------------
# LEVEL ANALYSIS
# ----------------------------

def analyze_level(level_data):

    board = level_data["board"]
    hand = level_data["hand"]

    piece_stats = [analyze_piece(board, p) for p in hand]

    board_stats = count_board(board)
    hand_stats = count_hand(hand)

    metrics = compute_metrics(piece_stats, board_stats, hand_stats)
    difficulty = compute_difficulty(metrics)

    return {
        **board_stats,
        **hand_stats,
        **metrics,
        **difficulty
    }


# ----------------------------
# CSV EXPORT (MODEL ONLY)
# ----------------------------

def save_results_to_csv(results, filepath):

    FEATURE_INPUTS = [
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

    INPUT_COLUMNS = [
        "Level",
        "PlayerDifficulty"
    ] + FEATURE_INPUTS

    OUTPUT_COLUMNS = [
        "ED",
        "CD"
    ]

    cols = INPUT_COLUMNS + OUTPUT_COLUMNS

    mean = MODEL["mean"]
    std = MODEL["std"]
    weights = MODEL["weights"]
    bias = MODEL["bias"]

    with open(filepath, "w", newline="") as f:

        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()

        for row_i, rdata in enumerate(results, start=2):

            row = {}

            # ----------------------------
            # INPUTS (rounded)
            # ----------------------------
            row["Level"] = round(rdata.get("Level"))
            row["PlayerDifficulty"] = round(rdata.get("PlayerDifficulty"))

            for c in FEATURE_INPUTS:
                row[c] = round(rdata.get(c))

            # ----------------------------
            # COLUMN LETTER MAP
            # ----------------------------
            col_map = {name: excel_col(i) for i, name in enumerate(cols)}

            # ----------------------------
            # EXCEL NORMALIZATION FORMULA
            # ----------------------------
            def norm(col):
                idx = FEATURE_INPUTS.index(col)
                letter = col_map[col]
                return f"(({letter}{row_i}-{mean[idx]})/{std[idx]})"

            # ----------------------------
            # ED FORMULA (MODEL)
            # ----------------------------
            ed_terms = [
                f"{weights[i]}*{norm(col)}"
                for i, col in enumerate(FEATURE_INPUTS)
            ]

            row["ED"] = "=" + "+".join(ed_terms) + f"+({bias})"

            # ----------------------------
            # CD FORMULA
            # ----------------------------
            row["CD"] = f"=MAX(0,MIN(10,ROUND(({row['ED']})*10,0)))"

            writer.writerow(row)

# ----------------------------
# MAIN
# ----------------------------

if __name__ == "__main__":

    import sys
    from tkinter import Tk, filedialog, messagebox

    root = Tk()
    root.withdraw()

    files = filedialog.askopenfilenames(filetypes=[("JSON", "*.json")])
    if not files:
        sys.exit()

    levels = []
    for f in files:
        data = json.load(open(f))
        levels.extend(data if isinstance(data, list) else [data])

    results = []

    for i, lvl in enumerate(levels, 1):

        r = analyze_level(lvl)
        r["Level"] = i
        r["PlayerDifficulty"] = lvl.get("difficulty", "")

        results.append(r)

    if fit_weights(results):
        for r in results:
            d = compute_difficulty(r)
            r["ED"] = d["ED"]
            r["CD"] = d["CD"]

    results.sort(key=lambda x: x["Level"])

    print("\nDONE")

    if messagebox.askyesno("Export", "Save CSV?"):
        path = filedialog.asksaveasfilename(defaultextension=".csv")
        save_results_to_csv(results, path)
        print("Saved:", path)