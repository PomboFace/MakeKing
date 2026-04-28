import pygame
import sys
import random
import json
import datetime
import copy
import os
import math
from game_common import *
import asyncio

# -----------------
# GLOBAL VARIABLES
# -----------------

# CONFIG
SAVE_MESSAGE = ""
SAVE_MESSAGE_TIME = 0
PRESET_MESSAGE_DURATION = 2000

# CONSTANTS
CLICK_TIME = 200  # ms
MOVE_THRESHOLD = 5  # pixels

# STATE
board: list = []
hand: list = []
game_won = False
used_indices = set()
turn_count = 0
start_entities = 0
score = 0
initial_board = None
initial_hand = None
dragging = None
dragging_index = None
placements = []
mouse_down_pos = None
mouse_down_index = None
mouse_down_time = 0
scrolled = False
running = True

# SPRITES
SPRITE_CACHE = {}

#LEVELS
LEVELS = []
LEVEL_MENU_OPEN = False
LEVEL_SCROLL = 0
LEVEL_SCROLL_SPEED = 30

# ANIMATIONS
wind_animations = []  # List of (from_pos, to_pos, entity, start_time, duration)
ANIM_DURATION = 150  # milliseconds
resolving = False  # Flag to track if we're waiting for wind animations to complete

# MAIN OBJECTS (initialized later)
renderer = None
input_handler = None

# -----------------
# Pygame
# -----------------

class Renderer:
    def __init__(self, width, height, title):
        pygame.init()
        pygame.mixer.quit()  # Disable sound to prevent audio lag on some systems
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption(title)

        # fonts belong to rendering layer
        self.font = pygame.font.Font(None, 26)
        self.big_font = pygame.font.Font(None, 40)

    def clear(self, color): 
        self.screen.fill(color)

    
    def create_rect(self, x, y, w, h):
        return pygame.Rect(x, y, w, h)

    def draw_rect(self, color, rect, width=0, radius=0):
        pygame.draw.rect(self.screen, color, rect, width, border_radius=radius)

    def text(self, text, color, center=None, big=False):
        font = self.big_font if big else self.font
        surf = font.render(text, True, color)

        if center:
            self.screen.blit(surf, surf.get_rect(center=center))

    def blit(self, surf, rect):
        self.screen.blit(surf, rect)

    def draw_line(self, color, start, end, width=1):
        pygame.draw.line(self.screen, color, start, end, width)

    def draw_circle(self, color, pos, radius):
        pygame.draw.circle(self.screen, color, pos, radius)

    def present(self):
        pygame.display.flip()

    def overlay(self, size, alpha, color):
        surf = pygame.Surface(size)
        surf.set_alpha(alpha)
        surf.fill(color)
        self.screen.blit(surf, (0, 0))

    def load_image(self, path, alpha=True):
        img = pygame.image.load(path)
        return img.convert_alpha() if alpha else img.convert()

    def scale(self, surf, size):
        return pygame.transform.smoothscale(surf, size)

    def tint(self, surface, color):
        tinted = surface.copy()
        tinted.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
        tinted.fill(color + (0,), special_flags=pygame.BLEND_RGBA_ADD)
        return tinted

class InputHandler:
    def __init__(self):
        self.events = []
        self.mouse_pos_value = (0, 0)

        self.mouse_down_pos = None
        self.mouse_down_time = 0

        self.mouse_down = False
        self.mouse_up = False
        self.mouse_motion = False

    def update(self):
        self.events = pygame.event.get()
        self.mouse_pos_value = pygame.mouse.get_pos()

        self.mouse_down = False
        self.mouse_up = False
        self.mouse_motion = False
        self.scrolled = False

        for e in self.events:
            if e.type == pygame.MOUSEBUTTONDOWN:
                self.mouse_down = True
                self.mouse_down_pos = self.mouse_pos_value
                self.mouse_down_time = self.time()

            elif e.type == pygame.MOUSEBUTTONUP:
                self.mouse_down = False
                self.mouse_up = True

            elif e.type == pygame.MOUSEMOTION:
                self.mouse_motion = True
            
            elif e.type == pygame.MOUSEWHEEL:
                self.mouse_down = False
                self.scrolled = True
                
    def time(self):
        return pygame.time.get_ticks()

    def mouse_pos(self):
        return self.mouse_pos_value

    def quit_requested(self):
        return any(e.type == pygame.QUIT for e in self.events)

    def get_events(self):
        return self.events

    def is_click(self):
        if self.scrolled:
            return False

        if self.mouse_down_pos and self.mouse_up:
            dt = self.time() - self.mouse_down_time
            dx = abs(self.mouse_pos_value[0] - self.mouse_down_pos[0])
            dy = abs(self.mouse_pos_value[1] - self.mouse_down_pos[1])
            return dt < CLICK_TIME and dx < MOVE_THRESHOLD and dy < MOVE_THRESHOLD
        return False

    def get_card_at_position(self, pos):
        """Returns card index if position is over a hand card, None otherwise"""
        if not hand:
            return None
        
        mx, my = pos
        spacing = WIDTH / len(hand)
        
        for i, shape in enumerate(hand):
            x = int(spacing * i + spacing / 2 - CARD_W / 2)
            rect = pygame.Rect(x, HAND_Y, CARD_W, CARD_H)
            if rect.collidepoint(mx, my):
                return i
        return None

    def get_placement_at_position(self, pos):
        """Returns placement index if position is over a placement, None otherwise"""
        mx, my = pos
        gx, gy = mx // CELL_SIZE, my // CELL_SIZE
        
        for i in range(len(placements) - 1, -1, -1):
            s, o, idx = placements[i]
            if (gx, gy) in get_cells(s, o):
                return i
        return None

    def get_button_at_position(self, pos, btn_rect, load_btn_rect, save_btn_rect=None):
        """Returns which button was clicked: 'main', 'load', 'save', or None"""
        mx, my = pos
        if btn_rect.collidepoint(mx, my):
            return 'main'
        elif load_btn_rect.collidepoint(mx, my):
            return 'load'
        elif save_btn_rect and save_btn_rect.collidepoint(mx, my):
            return 'save'
        return None

    def get_level_button_at_position(self, pos, level_buttons):
        """Returns level index if position is over a level button, None otherwise"""
        mx, my = pos
        for i, rect in enumerate(level_buttons):
            if rect.collidepoint(mx, my):
                return i
        return None

    def handle_mouse_down(self):
        """Process mouse down: return card index if card clicked, or None"""
        if not self.mouse_down:
            return None
        
        card_index = self.get_card_at_position(self.mouse_pos_value)
        if card_index is not None and card_index not in used_indices:
            return card_index
        return None

    def handle_drag(self):
        """Check if we've moved far enough to count as a drag"""
        if self.mouse_down_pos and self.mouse_motion:
            dx = abs(self.mouse_pos_value[0] - self.mouse_down_pos[0])
            dy = abs(self.mouse_pos_value[1] - self.mouse_down_pos[1])
            return dx > MOVE_THRESHOLD or dy > MOVE_THRESHOLD
        return False


# -----------------
# SHAPES / ELEMENTS
# -----------------

def set_status_message(text):
    global SAVE_MESSAGE, SAVE_MESSAGE_TIME
    SAVE_MESSAGE = text
    SAVE_MESSAGE_TIME = pygame.time.get_ticks()


def serialize_board_state(board_state=None):
    if board_state is None:
        board_state = board

    return [
        [
            None if cell is None else {
                "kind": cell.kind,
                "element": cell.element,
                "immovable": cell.immovable,
                "active": cell.active,
            }
            for cell in row
        ]
        for row in board_state
    ]


def deserialize_board_state(data):
    board[:] = [
        [
            None if cell is None else _deserialize_entity(cell)
            for cell in row
        ]
        for row in data
    ]


def _deserialize_entity(data):
    entity = Entity(data["kind"], data.get("element"), data.get("immovable", False))
    entity.active = data.get("active", False)
    return entity


def serialize_hand_state(hand_state=None):
    if hand_state is None:
        hand_state = hand

    return [
        {
            "pattern": [[x, y] for x, y in shape.pattern],
            "element": shape.element,
            "direction": list(shape.direction) if shape.direction is not None else None,
        }
        for shape in hand_state
    ]


def deserialize_hand_state(data):
    return [
        Shape(
            pattern=[(item[0], item[1]) for item in shape_data["pattern"]],
            element=shape_data["element"],
            direction=tuple(shape_data["direction"]) if shape_data.get("direction") is not None else None,
        )
        for shape_data in data
    ]


def save_preset(name=None):
    payload = {
        "board": serialize_board_state(initial_board if initial_board is not None else board),
        "hand": serialize_hand_state(initial_hand if initial_hand is not None else hand),
    }

    path = save_json_preset(payload, name)
    set_status_message(f"Saved preset: {os.path.basename(path)}")
    return os.path.basename(path)



def load_preset_path(path):
    if not os.path.exists(path):
        set_status_message("Preset not found")
        return False

    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    deserialize_board_state(payload.get("board", []))
    hand[:] = deserialize_hand_state(payload.get("hand", []))

    global start_entities, turn_count, score, placements, used_indices, game_won
    start_entities = sum(1 for row in board for cell in row if cell is not None)
    turn_count = 0
    score = 0
    placements.clear()
    used_indices.clear()
    game_won = False
    capture_initial_state()

    set_status_message(f"Loaded preset: {os.path.basename(path)}")
    return True


def load_preset(filename):
    return load_preset_path(get_preset_path(filename))

def prompt_load_preset():
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        set_status_message("Tkinter unavailable")
        return False

    root = tk.Tk()
    root.withdraw()
    initial_dir = ensure_preset_dir()
    path = filedialog.askopenfilename(
        title="Select preset to load",
        initialdir=initial_dir,
        filetypes=[("JSON preset", "*.json"), ("All files", "*")],
    )
    root.destroy()

    if not path:
        return False

    return load_preset_path(path)


def load_latest_preset():
    presets = get_preset_files()
    if not presets:
        set_status_message("No presets available")
        return False
    return load_preset(presets[0])

# -----------------
# SPRITES
# -----------------

def tint_surface(surface, color):
    tinted = surface.copy()
    
    # Zero out RGB (keep alpha)
    tinted.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
    
    # Add target color
    tinted.fill(color + (0,), special_flags=pygame.BLEND_RGBA_ADD)
    
    return tinted

def lighten(color, f):
    r, g, b = color
    return (
        int(r + (255 - r) * f),
        int(g + (255 - g) * f),
        int(b + (255 - b) * f),
    )

def load_sprite(sprite_name, size = CELL_SIZE):
    if sprite_name in SPRITE_CACHE:
        return SPRITE_CACHE[sprite_name]
    path = f"assets/sprites/{sprite_name}.png"
     # Check file exists first
    if not os.path.exists(path):
        print(f"[WARN] Missing sprite: {path}")
        return missing_texture(int(size))  # Return a fallback surface
    base = pygame.image.load(path).convert_alpha()  
    size = int(size)
    img = pygame.transform.smoothscale(base, (size, size))
    SPRITE_CACHE[sprite_name] = img
    return img

def missing_texture(size):
    surf = pygame.Surface((size, size))
    surf.fill((255, 0, 255))  # bright magenta = easy debug
    return surf

def preload_sprites():
    for e in ELEMENTS:
        load_sprite("enemy_" + e)
        load_sprite("tile_" + e)
        load_sprite("shape_" + e, size=15)   

    load_sprite("floor_active")
    load_sprite("floor_inactive")
    load_sprite("tile_active")
    load_sprite("arrow", size=20)
        
# -----------------
# HELPERS
# -----------------
def is_executable():
    if getattr(sys, 'frozen', False):
        running_as_exe = True
    else:
        running_as_exe = False
    return running_as_exe


def in_bounds(x, y):
    return 0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE

def rotate(shape):
    return [(-y, x) for x, y in shape] # 90 degree clockwise rotation

def random_rotate(shape):
    for _ in range(random.randint(0, 3)): # rotate 0-3 times
        shape = rotate(shape)
    return shape

def get_cells(shape, origin):
    ox, oy = origin
    return [(ox + dx, oy + dy) for dx, dy in shape.pattern]


# -----------------
# ENTITIES
# -----------------

class Entity:
    def __init__(self, kind, element=None, immovable=False):
        self.kind = kind
        self.element = element
        self.immovable = immovable
        self.active = False


class Shape:
    def __init__(self, pattern, element, direction=None):
        self.pattern = pattern
        self.element = element
        self.direction = direction

# -----------------
# BOARD
# -----------------

def empty_cell():
    while True:
        x = random.randint(0, GRID_SIZE - 1)
        y = random.randint(0, GRID_SIZE - 1)
        if board[y][x] is None:
            return x, y


def setup_board():
    global start_entities

    board[:] = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

    enemy_count = random.randint(2, 4)
    symbol_count = random.randint(1, 3)

    for _ in range(enemy_count):
        x, y = empty_cell()
        element = random.choice([e for e in ELEMENTS if e != "wind"])
        board[y][x] = Entity("enemy", element, element == "rock") # type: ignore

    for _ in range(symbol_count):
        x, y = empty_cell()
        element = random.choice([e for e in ELEMENTS if e != "rock"])
        board[y][x] = Entity("symbol", element, True)

    start_entities = enemy_count + symbol_count

def get_useful_elements():
    useful = set()
    color_count: dict[str, int] = {}
    for row in board:
        for cell in row:
            if not cell or cell.element is None:
                continue

            # inactive symbols → add their element
            if cell.kind == "symbol" and not cell.active:
                useful.add(cell.element)
                color_count[cell.element] = color_count.get(cell.element, 0) + 1

            # enemies → add their weaknesses
            elif cell.kind == "enemy" and cell.element != "rock":
                for element in WEAKNESS.get(cell.element, []):
                    useful.add(element)
                    color_count[element] = color_count.get(element, 0) + 1

    # if no usefult types (i.e. all rocks), return one of each element
    if not useful:
        return [e for e in ELEMENTS if e != "rock"]
    return sorted(useful, key=lambda e: color_count[e], reverse=True)


def capture_initial_state():
    global initial_board, initial_hand
    initial_board = copy.deepcopy(board)
    initial_hand = copy.deepcopy(hand)


def start_new_game():
    setup_board()
    hand[:] = generate_hand(4)
    capture_initial_state()

# -----------------
# SHAPE SYSTEM
# -----------------

def random_shape(element=None):
    base = random.choice(SHAPES)
    pattern = random_rotate(base)

    if not element:
        element = random.choice([e for e in ELEMENTS if e != "rock"])

    direction = None
    if element == "wind":
        direction = random.choice([(1,0), (-1,0), (0,1), (0,-1)])

    return Shape(pattern, element, direction)


def generate_hand(size=4):
    base = [random_shape(e) for e in ["fire", "water", "wind"]] # ensure some element variety in hand
    common_color = get_useful_elements()[0]
    if common_color not in ["fire", "water", "wind"]:
        common_color = random.choice(["fire", "water", "wind"])
    hand = base + [random_shape(common_color) for _ in range(size - len(base))] #generate the rest randomly
    random.shuffle(hand)
    return hand


def occupied_cells():
    cells = set()
    for s, o, _ in placements:
        cells.update(get_cells(s, o))
    return cells


def is_valid(shape, origin):
    return all(
        in_bounds(x, y) and (x, y) not in occupied_cells()
        for x, y in get_cells(shape, origin)
    )

# -----------------
# DRAW BOARD
# -----------------

def draw_board(renderer):
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            rect = renderer.create_rect(x*CELL_SIZE, y*CELL_SIZE, CELL_SIZE, CELL_SIZE)

            renderer.draw_rect(WHITE, rect)
            renderer.draw_rect(BLACK, rect, 2)

            entity = board[y][x]
            
            floor_sprite =  load_sprite("floor_" + ("active" if not entity or entity.active else "inactive"))
           
            if floor_sprite:
                sprite_rect = floor_sprite.get_rect(center=rect.center)
                renderer.blit(floor_sprite, sprite_rect)
            
            if not entity:
                continue

            if entity.kind == "enemy":
                sprite = load_sprite("enemy_" + entity.element)
                if sprite:
                    sprite_rect = sprite.get_rect(center=rect.center)
                    renderer.blit(sprite, sprite_rect)

            elif entity.kind == "symbol":
                if entity.active:
                    sprite = load_sprite("tile_active")
                else:
                    sprite = load_sprite("tile_" + entity.element)
                if sprite:
                    sprite_rect = sprite.get_rect(center=rect.center)
                    renderer.blit(sprite, sprite_rect)
               

# -----------------
# PLACEMENTS + GHOST
# -----------------

def draw_placements(renderer):
    for shape, (ox, oy), _ in placements:
        color = ELEMENT_COLORS.get(shape.element, YELLOW)
        for x, y in get_cells(shape, (ox, oy)):
            rect = renderer.create_rect(x*CELL_SIZE, y*CELL_SIZE, CELL_SIZE, CELL_SIZE)
            renderer.draw_rect(color, rect, 5)


def draw_ghost(renderer, input_handler):
    if not dragging:
        return

    mx, my = input_handler.mouse_pos()
    gx, gy = mx // CELL_SIZE, my // CELL_SIZE
    color = YELLOW if is_valid(dragging, (gx, gy)) else LIGHT_RED

    for x, y in get_cells(dragging, (gx, gy)):
        if in_bounds(x, y):
            rect = renderer.create_rect(x*CELL_SIZE, y*CELL_SIZE, CELL_SIZE, CELL_SIZE)
            renderer.draw_rect(color, rect, 6)

# -----------------
# HAND
# -----------------

def draw_hand(renderer):
    if not hand:
        return

    spacing = WIDTH / len(hand)


    for i, shape in enumerate(hand):
        x = int(spacing * i + spacing / 2 - CARD_W / 2)
        rect = renderer.create_rect(x, HAND_Y, CARD_W, CARD_H)

        renderer.draw_rect(DARK_TAN if i in used_indices else TAN, rect)
        renderer.draw_rect(BLACK, rect, 2)

        color = ELEMENT_COLORS.get(shape.element, GRAY)
        shape_sprite = load_sprite("shape_" + shape.element, size=15)

        min_x = min(p[0] for p in shape.pattern)
        min_y = min(p[1] for p in shape.pattern)
        max_x = max(p[0] for p in shape.pattern)
        max_y = max(p[1] for p in shape.pattern)

        shape_w = (max_x - min_x + 1) * 15
        shape_h = (max_y - min_y + 1) * 15

        offset_x = rect.centerx - shape_w // 2 - min_x * 15
        offset_y = rect.centery - shape_h // 2 - min_y * 15

        for dx, dy in shape.pattern:
            px = offset_x + dx * 15
            py = offset_y + dy * 15
            shape_rect = renderer.create_rect(px, py, 15, 15)
            if shape_sprite:
                sprite_rect = shape_sprite.get_rect(center=shape_rect.center)
                renderer.blit(shape_sprite, sprite_rect)
            else:
                # Fallback to colored square if sprite is not available
                renderer.draw_rect(color, shape_rect)

        if shape.element == "wind" and shape.direction:
            cx, cy = rect.center
            dx, dy = shape.direction
            
            # Calculate rotation angle based on direction
            # (1, 0) = right = 0°, (0, 1) = down = 90°, (-1, 0) = left = 180°, (0, -1) = up = 270°
            angle = (math.atan2(dy, dx) * 180 / math.pi) - 270
            
            # Rotate arrow sprite
            arrow_sprite = load_sprite("arrow", size=20)
            rotated_arrow = pygame.transform.rotate(arrow_sprite, -angle)
            arrow_rect = rotated_arrow.get_rect(center=(cx, cy))
            renderer.blit(rotated_arrow, arrow_rect)
# -----------------
# BUTTON + UI
# -----------------

def draw_button(renderer):
    rect = renderer.create_rect(WIDTH//2 - 60, HAND_Y + 90, 120, 45)

    label = "RESTART" if game_won else "EXECUTE"
    color = YELLOW if game_won else GREEN

    renderer.draw_rect(color, rect, radius=8)
    renderer.draw_rect(BLACK, rect, 2, radius=8)

    renderer.text(label, BLACK, center=rect.center)

    renderer.text(f"Turn: {turn_count}", WHITE,
                  center=(rect.right + 70, rect.centery))

    return rect


def draw_load_button(renderer):
    rect = renderer.create_rect(20, HAND_Y + 90, 80, 45)
    presets = get_preset_files()
    color = BLUE if presets else GRAY

    renderer.draw_rect(color, rect, radius=8)
    renderer.draw_rect(BLACK, rect, 2, radius=8)
    renderer.text("LEVELS", BLACK, center=rect.center)

    return rect


def draw_save_button(renderer):
    rect = renderer.create_rect(10, 10, 60, 35)

    renderer.draw_rect(BLUE, rect, radius=8)
    renderer.draw_rect(BLACK, rect, 2, radius=8)
    renderer.text("SAVE", BLACK, center=rect.center)

    return rect


def draw_status_message(renderer):
    global SAVE_MESSAGE
    if SAVE_MESSAGE and pygame.time.get_ticks() - SAVE_MESSAGE_TIME < PRESET_MESSAGE_DURATION:
        renderer.text(SAVE_MESSAGE, WHITE, center=(WIDTH//2, HAND_Y - 30))
    else:
        SAVE_MESSAGE = ""

def draw_level_menu(renderer, input_handler):
    global LEVEL_MENU_OPEN, LEVEL_SCROLL
    if not LEVEL_MENU_OPEN:
        return

    height = GRID_SIZE*CELL_SIZE + CARD_H + 20

    menu_rect = pygame.Rect(0, 0, WIDTH, height)

    renderer.overlay((WIDTH, height), 200, (0, 0, 0))
    renderer.screen.set_clip(menu_rect)
    renderer.text("Select Level", WHITE, center=(WIDTH//2, 60), big=True)

    mx, my = input_handler.mouse_pos()

    start_y = 120
    button_h = 40
    button_w = 300
    spacing = button_h + 10

    # scroll input (mouse wheel)
    for e in input_handler.get_events():
        if e.type == pygame.MOUSEWHEEL:
            LEVEL_SCROLL -= e.y * LEVEL_SCROLL_SPEED

    # clamp scroll
    max_scroll = max(0, len(LEVELS) * spacing - (height - start_y - 50))
    LEVEL_SCROLL = max(0, min(LEVEL_SCROLL, max_scroll))

    # visible range only (this is the key improvement)
    visible_top = start_y - LEVEL_SCROLL
    visible_bottom = height

    for i, (name, path) in enumerate(LEVELS):
        y = start_y + i * spacing - LEVEL_SCROLL

        rect = pygame.Rect(
            WIDTH//2 - button_w//2,
            y,
            button_w,
            button_h
        )

        # skip drawing off-screen buttons (performance + cleaner)
        if rect.bottom < visible_top or rect.top > visible_bottom:
            continue

        hover = rect.collidepoint(mx, my)
        color = (80, 80, 80) if not hover else (120, 120, 120)

        renderer.draw_rect(color, rect, radius=6)
        renderer.draw_rect(BLACK, rect, 2, radius=6)
        renderer.text(name, WHITE, center=rect.center)

        if input_handler.mouse_down and rect.collidepoint(mx, my):
            load_preset(path)
            LEVEL_MENU_OPEN = False
    renderer.screen.set_clip(None)

# -----------------
# GAME LOGIC
# -----------------

def resolve():
    global placements, used_indices, hand, turn_count, wind_animations, resolving

    turn_count += 1
    resolving = True  # Set flag to wait for animations

    wind_moves = []

    for shape, (ox, oy), _ in placements:
        if shape.element != "wind":
            continue

        dx, dy = shape.direction

        for x, y in get_cells(shape, (ox, oy)):
            if in_bounds(x, y):
                e = board[y][x]
                if e and not e.immovable:
                    nx, ny = x + dx, y + dy
                    if in_bounds(nx, ny):
                        wind_moves.append((x, y, nx, ny, e))

    # Create animations for wind moves instead of moving immediately
    start_time = pygame.time.get_ticks()
    for x, y, nx, ny, e in wind_moves:
        if board[y][x] == e:
            wind_animations.append(((x, y), (nx, ny), e, start_time, ANIM_DURATION))
            # Clear the original position (entity will be drawn during animation)
            board[y][x] = None

    # If no wind animations, resolve effects immediately
    if not wind_animations:
        resolve_effects()


def resolve_effects():
    global placements, used_indices, hand, resolving
    
    for shape, (ox, oy), _ in placements:
        for x, y in get_cells(shape, (ox, oy)):
            if not in_bounds(x, y):
                continue

            e = board[y][x]
            if not e:
                continue

            if e.kind == "symbol":
                e.active = (shape.element == e.element)

            elif e.kind == "enemy":
                if shape.element in WEAKNESS.get(e.element, []):
                    board[y][x] = None

    placements.clear()

    useful_elements = get_useful_elements()
    new_hand = []
    for i, h in enumerate(hand):
        if i in used_indices:
            if useful_elements:
                if random.random() < 0.6:
                    element = random.choice(useful_elements)
                    new_hand.append(random_shape(element))
                elif random.random() < 0.8:
                    new_hand.append(random_shape("wind"))
                else:
                    new_hand.append(random_shape())
            else:
                new_hand.append(random_shape())  # fallback
        else:
            new_hand.append(h)

    hand[:] = new_hand
    
    used_indices.clear()
    resolving = False  # Clear flag when done


def update_and_draw_wind_animations(renderer):
    global wind_animations, resolving
    current_time = pygame.time.get_ticks()
    completed = []
    
    for i, (from_pos, to_pos, entity, start_time, duration) in enumerate(wind_animations):
        elapsed = current_time - start_time
        progress = min(elapsed / duration, 1.0)
        
        if progress >= 1.0:
            # Animation complete - place entity at destination
            fx, fy = to_pos
            board[fy][fx] = entity
            completed.append(i)
        else:
            # Draw animated entity in motion
            fx, fy = from_pos
            tx, ty = to_pos
            
            # Interpolate position
            curr_x = fx + (tx - fx) * progress
            curr_y = fy + (ty - fy) * progress
            
            # Draw the entity at interpolated position
            rect = renderer.create_rect(
                int(curr_x * CELL_SIZE),
                int(curr_y * CELL_SIZE),
                CELL_SIZE,
                CELL_SIZE
            )
            
            if entity.kind == "enemy":
                sprite = load_sprite("enemy_" + entity.element)
                if sprite:
                    sprite_rect = sprite.get_rect(center=rect.center)
                    renderer.blit(sprite, sprite_rect)
            elif entity.kind == "symbol":
                sprite = load_sprite("tile_" + entity.element)
                if sprite:
                    sprite_rect = sprite.get_rect(center=rect.center)
                    renderer.blit(sprite, sprite_rect)
    
    # Remove completed animations
    for i in reversed(completed):
        wind_animations.pop(i)
    
    # If all animations are done and we're resolving, continue with effects
    if not wind_animations and resolving:
        resolve_effects()


def check_win():
    return all(
        cell is None or (cell.kind != "enemy" and (cell.kind != "symbol" or cell.active))
        for row in board for cell in row
    )

# -----------------
# MAIN LOOP
# -----------------
async def main():
    global dragging
    global mouse_down_pos
    global mouse_down_index
    global dragging_index
    global game_won
    global start_entities
    global turn_count
    
    await asyncio.sleep(0)  # Allow time for window to initialize

    renderer = Renderer(WIDTH, HEIGHT, "Puzzle Prototype")
    input_handler = InputHandler()

    await asyncio.sleep(0.016)
    preload_sprites()
    global  LEVELS
    LEVELS = preload_levels()
    
    start_new_game()

    running = True
    while running:
        input_handler.update()

        if input_handler.quit_requested():
            #pygame.quit()
            #sys.exit()
            running = False

        renderer.clear(BLACK)
        draw_board(renderer)
        draw_placements(renderer)
        draw_ghost(renderer, input_handler)
        draw_hand(renderer)
        update_and_draw_wind_animations(renderer)
        
        draw_level_menu(renderer, input_handler)

        # -----------------
        # WIN STATE
        # -----------------
        if check_win():
            game_won = True
            score = (start_entities / turn_count) if turn_count else 0

            renderer.overlay((WIDTH, HEIGHT), 180, (0, 0, 0))

            renderer.text("VICTORY!", GREEN,
                        center=(WIDTH//2, HEIGHT//2 - 160), big=True)

            renderer.text(f"Score: {score:.2f}", WHITE,
                        center=(WIDTH//2, HEIGHT//2 - 80), big=True)

        btn = draw_button(renderer)
        load_btn = draw_load_button(renderer)
        save_btn = draw_save_button(renderer) if game_won and not is_executable() else None
        draw_status_message(renderer)

        # -----------------
        # INPUT HANDLING
        # -----------------
        mx, my = input_handler.mouse_pos()

        if input_handler.mouse_down:
            # Try to pick up a card
            card_index = input_handler.handle_mouse_down()
            if card_index is not None:
                dragging = hand[card_index]
                dragging_index = card_index
                mouse_down_pos = (mx, my)
                mouse_down_index = card_index
                mouse_down_time = input_handler.time()
            
            # Try to remove a placement
            placement_index = input_handler.get_placement_at_position((mx, my))
            if placement_index is not None:
                _, _, card_index = placements[placement_index]
                placements.pop(placement_index)
                used_indices.discard(card_index)
            
            # Check button clicks
            button_clicked = input_handler.get_button_at_position((mx, my), btn, load_btn, save_btn)
            if button_clicked == 'main':
                if game_won:
                    turn_count = score = start_entities = 0
                    placements.clear()
                    start_new_game()
                    used_indices.clear()
                    game_won = False
                elif not wind_animations and not resolving:  # Only allow resolve if animations aren't running
                    resolve()
            elif button_clicked == 'load':
                global LEVEL_MENU_OPEN
                LEVEL_MENU_OPEN = not LEVEL_MENU_OPEN
            elif button_clicked == 'save':
                save_preset()

        

        # Handle drag detection
        if input_handler.handle_drag() and dragging and mouse_down_index is not None:
            mouse_down_index = None

        # Handle release
        if input_handler.mouse_up and dragging:
            if input_handler.is_click() and mouse_down_index is not None:
                # Rotate card on click
                shape = hand[mouse_down_index]
                shape.pattern = rotate(shape.pattern)
                if shape.element == "wind" and shape.direction:
                    dx, dy = shape.direction
                    shape.direction = (-dy, dx)
            else:
                # Try to place card on drag
                gx, gy = mx // CELL_SIZE, my // CELL_SIZE
                if is_valid(dragging, (gx, gy)):
                    placements.append((dragging, (gx, gy), dragging_index))
                    used_indices.add(dragging_index)
            
            dragging = dragging_index = None
            mouse_down_pos = None
            mouse_down_index = None

        renderer.present()
        await asyncio.sleep(0.016)

if __name__ == "__main__":
    asyncio.run(main())
