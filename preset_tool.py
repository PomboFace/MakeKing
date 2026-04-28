import datetime
import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox, Canvas
from game_common import (
    BOARD_CHOICES,
    HAND_ELEMENTS,
    HAND_SHAPE_PATTERNS,
    HAND_SHAPE_CHOICES,
    HAND_PATTERN_TO_NAME,
    DIRECTION_CHOICES,
    ensure_preset_dir,
    get_preset_path,
    get_preset_files,
    read_json_preset,
    save_json_preset,
    shape_choice_to_pattern,
    pattern_to_shape_choice,
)


def sample_board():
    return [
        [None, None, None, None],
        [None, None, None, None],
        [None, None, None, None],
        [None, None, None, None],
    ]


def sample_hand():
    return [
        {"pattern": [[0, 0], [1, 0], [0, 1]], "element": "fire", "direction": None},
        {"pattern": [[0, 0], [0, 1]], "element": "water", "direction": None},
        {"pattern": [[0, 0], [1, 0], [2, 0]], "element": "wind", "direction": [1, 0]},
        {"pattern": [[0, 0]], "element": "rock", "direction": None},
    ]


class PresetToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MakeKing Preset Manager")
        self.root.geometry("820x520")

        self.board_vars = [
            [tk.StringVar(value="Empty") for _ in range(4)]
            for _ in range(4)
        ]
        self.hand_vars = [tk.StringVar(value=HAND_ELEMENTS[i]) for i in range(4)]
        self.hand_shape_vars = [tk.StringVar(value=HAND_SHAPE_CHOICES[0]) for _ in range(4)]
        self.hand_dir_vars = [tk.StringVar(value="None") for _ in range(4)]

        self.build_ui()
        self.set_editor_sample()
        self.refresh_preset_list()

    def build_ui(self):
        left_frame = tk.Frame(self.root, padx=10, pady=10)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(left_frame, text="Presets", font=("Arial", 14, "bold")).pack(anchor=tk.W)
        self.preset_listbox = tk.Listbox(left_frame, width=40, height=20)
        self.preset_listbox.pack(fill=tk.Y, expand=True)
        self.preset_listbox.bind("<<ListboxSelect>>", self.on_preset_select)

        btn_frame = tk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=8)
        tk.Button(btn_frame, text="Refresh", command=self.refresh_preset_list, width=12).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="Open File", command=self.open_preset_file, width=12).pack(side=tk.LEFT, padx=6)

        right_frame = tk.Frame(self.root, padx=10, pady=10)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        editor_frame = tk.LabelFrame(right_frame, text="Board & Hand Editor", padx=10, pady=10)
        editor_frame.pack(fill=tk.X, pady=10)

        tk.Label(editor_frame, text="Board:", anchor=tk.W).pack(anchor=tk.W)
        for y in range(4):
            row_frame = tk.Frame(editor_frame)
            row_frame.pack(fill=tk.X)
            for x in range(4):
                opt = tk.OptionMenu(row_frame, self.board_vars[y][x], *BOARD_CHOICES)
                opt.config(width=12)
                opt.pack(side=tk.LEFT, padx=2, pady=2)

        tk.Label(editor_frame, text="Hand:", anchor=tk.W).pack(anchor=tk.W, pady=(8, 0))
        hand_frame = tk.Frame(editor_frame)
        hand_frame.pack(fill=tk.X)
        
        self.hand_canvases = []
        
        for i in range(4):
            slot_frame = tk.Frame(hand_frame, relief=tk.RIDGE, bd=1, padx=4, pady=4)
            slot_frame.pack(side=tk.LEFT, padx=4, fill=tk.BOTH, expand=True)
            
            tk.Label(slot_frame, text=f"Slot {i + 1}", font=("Arial", 10, "bold")).pack()
            
            # Visual preview canvas
            canvas = Canvas(slot_frame, width=80, height=80, bg="lightgray", relief=tk.SUNKEN, bd=1)
            canvas.pack(pady=4)
            self.hand_canvases.append(canvas)
            
            tk.Label(slot_frame, text="Element:").pack(anchor=tk.W)
            elem_menu = tk.OptionMenu(slot_frame, self.hand_vars[i], *HAND_ELEMENTS, command=lambda v, idx=i: self.update_hand_preview(idx))
            elem_menu.pack(fill=tk.X)
            
            tk.Label(slot_frame, text="Shape:").pack(anchor=tk.W)
            shape_menu = tk.OptionMenu(slot_frame, self.hand_shape_vars[i], *HAND_SHAPE_CHOICES, command=lambda v, idx=i: self.update_hand_preview(idx))
            shape_menu.pack(fill=tk.X)
            
            tk.Label(slot_frame, text="Direction:").pack(anchor=tk.W)
            dir_menu = tk.OptionMenu(slot_frame, self.hand_dir_vars[i], *DIRECTION_CHOICES, command=lambda v, idx=i: self.update_hand_preview(idx))
            dir_menu.pack(fill=tk.X)

        create_frame = tk.LabelFrame(right_frame, text="Save Preset", padx=10, pady=10)
        create_frame.pack(fill=tk.X, pady=10)

        action_row = tk.Frame(create_frame)
        action_row.pack(fill=tk.X, pady=6)
        tk.Button(action_row, text="Overwrite Selected File", command=self.overwrite_selected_file, width=22).pack(side=tk.LEFT)
        tk.Button(action_row, text="Save As New", command=self.save_as_new_file, width=15).pack(side=tk.LEFT, padx=4)

        self.status_label = tk.Label(self.root, text="Ready", anchor=tk.W)
        self.status_label.pack(fill=tk.X, padx=10, pady=(0, 10))

    def refresh_preset_list(self):
        self.preset_listbox.delete(0, tk.END)
        for preset in get_preset_files():
            self.preset_listbox.insert(tk.END, preset)
        self.status_label.config(text="Preset list refreshed.")

    def on_preset_select(self, event):
        selection = self.preset_listbox.curselection()
        if not selection:
            return
        filename = self.preset_listbox.get(selection[0])
        try:
            preset = read_json_preset(filename)
            self.update_editor_from_preset(preset)
            self.status_label.config(text=f"Loaded preset into editor: {filename}")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def open_preset_file(self):
        path = filedialog.askopenfilename(
            title="Open preset file",
            initialdir=ensure_preset_dir(),
            filetypes=[("JSON preset", "*.json"), ("All files", "*")],
        )
        if not path:
            return
        try:
            preset = read_json_preset(path)
            self.update_editor_from_preset(preset)
            self.status_label.config(text=f"Opened preset into editor: {os.path.basename(path)}")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def overwrite_selected_file(self):
        selection = self.preset_listbox.curselection()
        if not selection:
            messagebox.showwarning("No selection", "Select a preset file first.")
            return

        filename = self.preset_listbox.get(selection[0])
        path = os.path.join(ensure_preset_dir(), filename)
        board = self.editor_board_data()
        hand = self.editor_hand_data()
        payload = {"board": board, "hand": hand}

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            self.status_label.config(text=f"Overwrote preset: {filename}")
            self.refresh_preset_list()
            messagebox.showinfo("Saved", f"Preset overwritten: {path}")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def save_as_new_file(self):
        path = filedialog.asksaveasfilename(
            title="Save preset as",
            initialdir=ensure_preset_dir(),
            defaultextension=".json",
            filetypes=[("JSON preset", "*.json"), ("All files", "*")],
        )
        if not path:
            return

        board = self.editor_board_data()
        hand = self.editor_hand_data()
        payload = {"board": board, "hand": hand}

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            self.status_label.config(text=f"Saved preset: {os.path.basename(path)}")
            self.refresh_preset_list()
            messagebox.showinfo("Saved", f"Preset saved: {path}")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def choice_to_cell(self, choice):
        if choice == "Empty":
            return None
        if choice.startswith("Enemy "):
            element = choice.split(" ", 1)[1].lower()
            return {
                "kind": "enemy",
                "element": element,
                "immovable": element == "rock",
                "active": False,
            }
        if choice.startswith("Symbol "):
            element = choice.split(" ", 1)[1].lower()
            return {
                "kind": "symbol",
                "element": element,
                "immovable": True,
                "active": False,
            }
        return None

    def update_hand_preview(self, slot_index):
        """Draw a visual preview of the hand piece in the canvas."""
        canvas = self.hand_canvases[slot_index]
        canvas.delete("all")
        
        element = self.hand_vars[slot_index].get()
        shape_choice = self.hand_shape_vars[slot_index].get()
        direction_choice = self.hand_dir_vars[slot_index].get()
        
        pattern = shape_choice_to_pattern(shape_choice)
        
        # Color mapping for elements
        element_colors = {
            "fire": "#FF6B6B",
            "water": "#4ECDC4",
            "wind": "#FFE66D",
            "rock": "#95A5A6",
        }
        color = element_colors.get(element.lower(), "#999999")
        
        # Calculate bounds for centering
        if pattern:
            min_x = min(p[0] for p in pattern)
            max_x = max(p[0] for p in pattern)
            min_y = min(p[1] for p in pattern)
            max_y = max(p[1] for p in pattern)
            
            width = max_x - min_x + 1
            height = max_y - min_y + 1
            
            # Draw cells
            cell_size = min(60 // width, 60 // height) if width > 0 and height > 0 else 20
            start_x = 40 - (width * cell_size) // 2
            start_y = 30 - (height * cell_size) // 2
            
            for px, py in pattern:
                x = start_x + (px - min_x) * cell_size
                y = start_y + (py - min_y) * cell_size
                canvas.create_rectangle(x, y, x + cell_size, y + cell_size, fill=color, outline="black", width=2)
            
            # Draw wind direction arrow if applicable
            if element.lower() == "wind" and direction_choice != "None":
                center_x = 40
                center_y = 30
                
                dir_map = {"Right": (1, 0), "Left": (-1, 0), "Down": (0, 1), "Up": (0, -1)}
                dx, dy = dir_map.get(direction_choice, (0, 0))
                
                arrow_length = 20
                end_x = center_x + dx * arrow_length
                end_y = center_y + dy * arrow_length
                
                # Draw arrow line
                canvas.create_line(center_x, center_y, end_x, end_y, fill="#FF00FF", width=3)
                
                # Draw arrow head
                canvas.create_oval(end_x - 4, end_y - 4, end_x + 4, end_y + 4, fill="#FF00FF", outline="black", width=2)
                
                # Add direction label
                dir_labels = {"Right": "→", "Left": "←", "Down": "↓", "Up": "↑"}
                label = dir_labels.get(direction_choice, "")
                canvas.create_text(40, 65, text=label, font=("Arial", 16, "bold"), fill="#FF00FF")

    def update_editor_from_preset(self, preset):
        board = preset.get("board", [])
        hand = preset.get("hand", [])

        for y in range(4):
            for x in range(4):
                cell = None
                if y < len(board) and x < len(board[y]):
                    cell = board[y][x]
                self.board_vars[y][x].set(self.cell_to_choice(cell))

        for i in range(4):
            hand_data = hand[i] if i < len(hand) else None
            if hand_data:
                element = hand_data.get("element", HAND_ELEMENTS[i])
                self.hand_vars[i].set(element)
                self.hand_shape_vars[i].set(pattern_to_shape_choice(hand_data.get("pattern", [[0, 0]])))
                self.hand_dir_vars[i].set(self.vector_to_direction_choice(hand_data.get("direction")))
            else:
                self.hand_vars[i].set(HAND_ELEMENTS[i])
                self.hand_shape_vars[i].set(HAND_SHAPE_CHOICES[0])
                self.hand_dir_vars[i].set("None")
            
            self.update_hand_preview(i)

    def build_preset_summary(self, preset, filename):
        board = preset.get("board", [])
        hand = preset.get("hand", [])
        lines = [f"Preset: {filename}", "Board:"]
        for y in range(4):
            row = []
            for x in range(4):
                cell = board[y][x] if y < len(board) and x < len(board[y]) else None
                row.append(self.cell_to_choice(cell))
            lines.append("  " + ", ".join(row))
        lines.append("Hand:")
        for i in range(4):
            hand_data = hand[i] if i < len(hand) else {}
            lines.append(
                f"  Slot {i + 1}: {hand_data.get('element', 'fire')} | "
                f"shape={pattern_to_shape_choice(hand_data.get('pattern', [[0, 0]]))} | "
                f"dir={self.vector_to_direction_choice(hand_data.get('direction'))}"
            )
        return "\n".join(lines)

    def editor_board_data(self):
        return [
            [self.choice_to_cell(self.board_vars[y][x].get()) for x in range(4)]
            for y in range(4)
        ]

    def editor_hand_data(self):
        hand = []
        for i in range(4):
            element = self.hand_vars[i].get()
            shape_choice = self.hand_shape_vars[i].get()
            direction_choice = self.hand_dir_vars[i].get()
            pattern = shape_choice_to_pattern(shape_choice)
            direction = self.direction_choice_to_vector(direction_choice) if element == "wind" else None
            hand.append({"pattern": pattern, "element": element, "direction": direction})
        return hand

    def shape_choice_to_pattern(self, choice):
        return HAND_SHAPE_PATTERNS.get(choice, [[0, 0]])

    def direction_choice_to_vector(self, choice):
        return {
            "Right": [1, 0],
            "Left": [-1, 0],
            "Down": [0, 1],
            "Up": [0, -1],
        }.get(choice)

    def set_editor_sample(self):
        sample = sample_board()
        for y in range(4):
            for x in range(4):
                self.board_vars[y][x].set(self.cell_to_choice(sample[y][x]))
        sample_hand_data = sample_hand()
        for i, var in enumerate(self.hand_vars):
            hand_data = sample_hand_data[i]
            var.set(hand_data["element"])
            self.hand_shape_vars[i].set(self.pattern_to_shape_choice(hand_data["pattern"]))
            self.hand_dir_vars[i].set(self.vector_to_direction_choice(hand_data.get("direction")))

    def pattern_to_shape_choice(self, pattern):
        return pattern_to_shape_choice(pattern)

    def vector_to_direction_choice(self, vector):
        if vector is None:
            return "None"
        reverse = {
            (1, 0): "Right",
            (-1, 0): "Left",
            (0, 1): "Down",
            (0, -1): "Up",
        }
        return reverse.get(tuple(vector), "None")

    def cell_to_choice(self, cell):
        if not cell:
            return "Empty"
        if cell["kind"] == "enemy":
            return f"Enemy {cell['element'].capitalize()}"
        if cell["kind"] == "symbol":
            return f"Symbol {cell['element'].capitalize()}"
        return "Empty"


def main():
    root = tk.Tk()
    PresetToolApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
