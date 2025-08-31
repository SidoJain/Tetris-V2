import sys
import random
import pygame
import requests
import os
import numpy as np
import threading
from dotenv import load_dotenv
load_dotenv()

COLS, ROWS = 10, 20
BLOCK = 30
GRID_W, GRID_H = COLS * BLOCK, ROWS * BLOCK
SIDE_W = 200
WIN_W, WIN_H = GRID_W + SIDE_W, GRID_H

FPS = 60
MIN_FPS = 30
MAX_FPS = 240
FPS_STEP = 5
FALL_INTERVAL_MS = 500
BASE_INTERVAL_MS = 650
MIN_INTERVAL_MS = 90
FAST_DROP_MS = 50

SIDEBAR_BG = (18, 18, 18)
PANEL_BG = (25, 25, 25)
PANEL_BORDER = (60, 60, 60)
PANEL_PAD = 12
PREVIEW_BG = (32, 32, 32)

SERVER_URL = os.getenv("TETRIS_SERVER_URL", "https://localhost:5000/api")

BLACK = (0, 0, 0)
GRAY = (30, 30, 30)
GRID_LINE = (45, 45, 45)
WHITE = (240, 240, 240)
CYAN = (48, 207, 208)
YELLOW = (255, 214, 10)
PURPLE = (155, 89, 182)
GREEN = (46, 204, 113)
RED = (231, 76, 60)
BLUE = (52, 152, 219)
ORANGE = (243, 156, 18)

PIECES = {
    "I": {
        "color": CYAN,
        "rotation": [
            [(0, 1), (1, 1), (2, 1), (3, 1)],
            [(2, 0), (2, 1), (2, 2), (2, 3)],
            [(0, 2), (1, 2), (2, 2), (3, 2)],
            [(1, 0), (1, 1), (1, 2), (1, 3)],
        ],
        "spawn_x": 3,
        "spawn_y": -2,
    },
    "O": {
        "color": YELLOW,
        "rotation": [
            [(1, 1), (2, 1), (1, 2), (2, 2)],
        ],
        "spawn_x": 4,
        "spawn_y": -2,
    },
    "T": {
        "color": PURPLE,
        "rotation": [
            [(1, 1), (0, 1), (2, 1), (1, 2)],
            [(1, 1), (1, 0), (1, 2), (2, 1)],
            [(1, 1), (0, 1), (2, 1), (1, 0)],
            [(1, 1), (1, 0), (1, 2), (0, 1)],
        ],
        "spawn_x": 3,
        "spawn_y": -2,
    },
    "S": {
        "color": GREEN,
        "rotation": [
            [(1, 1), (2, 1), (0, 2), (1, 2)],
            [(1, 0), (1, 1), (2, 1), (2, 2)],
            [(1, 1), (2, 1), (0, 2), (1, 2)],
            [(1, 0), (1, 1), (2, 1), (2, 2)],
        ],
        "spawn_x": 3,
        "spawn_y": -2,
    },
    "Z": {
        "color": RED,
        "rotation": [
            [(0, 1), (1, 1), (1, 2), (2, 2)],
            [(2, 0), (1, 1), (2, 1), (1, 2)],
            [(0, 1), (1, 1), (1, 2), (2, 2)],
            [(2, 0), (1, 1), (2, 1), (1, 2)],
        ],
        "spawn_x": 3,
        "spawn_y": -2,
    },
    "J": {
        "color": BLUE,
        "rotation": [
            [(0, 1), (1, 1), (2, 1), (2, 2)],
            [(1, 0), (1, 1), (1, 2), (2, 0)],
            [(0, 0), (0, 1), (1, 1), (2, 1)],
            [(0, 2), (1, 0), (1, 1), (1, 2)],
        ],
        "spawn_x": 3,
        "spawn_y": -2,
    },
    "L": {
        "color": ORANGE,
        "rotation": [
            [(0, 1), (1, 1), (2, 1), (0, 2)],
            [(1, 0), (1, 1), (1, 2), (2, 2)],
            [(0, 1), (1, 1), (2, 1), (2, 0)],
            [(0, 0), (1, 0), (1, 1), (1, 2)],
        ],
        "spawn_x": 3,
        "spawn_y": -2,
    },
}

BAG = list(PIECES.keys())

class Piece:
    def __init__(self, kind: str) -> None:
        self.kind = kind
        self.rot_idx = 0
        self.x = PIECES[kind]["spawn_x"]
        self.y = PIECES[kind]["spawn_y"]
        self.color = PIECES[kind]["color"]

    def blocks(self) -> list[tuple[int, int]]:
        return [(self.x + cx, self.y + cy) for (cx, cy) in PIECES[self.kind]["rotation"][self.rot_idx]]

    def rotated(self, dir: int=1) -> 'Piece':
        p = Piece(self.kind)
        p.x, p.y = self.x, self.y
        p.rot_idx = (self.rot_idx + dir) % len(PIECES[self.kind]["rotation"])
        return p

    def moved(self, dx: int=0, dy: int=0) -> 'Piece':
        p = Piece(self.kind)
        p.x, p.y = self.x + dx, self.y + dy
        p.rot_idx = self.rot_idx
        return p

def new_bag() -> list[str]:
    b = BAG[:]
    random.shuffle(b)
    return b

def spawn_piece(queue: list[str]) -> Piece:
    if not queue:
        queue.extend(new_bag())
    return Piece(queue.pop(0))

def create_board() -> np.ndarray:
    return np.zeros((ROWS, COLS), dtype=object)

def valid(board: np.ndarray, piece: Piece) -> bool:
    for x, y in piece.blocks():
        if x < 0 or x >= COLS or y >= ROWS:
            return False
        if y >= 0 and board[y, x] != 0:
            return False
    return True

def lock_piece(board: np.ndarray, piece: Piece) -> None:
    for x, y in piece.blocks():
        if 0 <= y < ROWS:
            board[y, x] = piece.color

def clear_lines(board: np.ndarray) -> tuple[np.ndarray, int]:
    full_rows = np.where(np.all(board != 0, axis=1))[0]
    num_cleared = len(full_rows)
    if num_cleared > 0:
        board = np.delete(board, full_rows, axis=0)
        new_rows = np.zeros((num_cleared, board.shape[1]), dtype=board.dtype)
        board = np.vstack([new_rows, board])
    return board, num_cleared

def score_for_lines(n: int) -> int:
    return {1: 100, 2: 300, 3: 500, 4: 800}.get(n, 0)

def draw_grid(surf: pygame.surface.Surface) -> None:
    for x in range(COLS + 1):
        pygame.draw.line(surf, GRID_LINE, (x * BLOCK, 0), (x * BLOCK, GRID_H), 1)
    for y in range(ROWS + 1):
        pygame.draw.line(surf, GRID_LINE, (0, y * BLOCK), (GRID_W, y * BLOCK), 1)

def draw_board(surf: pygame.surface.Surface, board) -> None:
    for y in range(ROWS):
        for x in range(COLS):
            if board[y, x] != 0:
                pygame.draw.rect(surf, board[y, x], pygame.Rect(x * BLOCK + 1, y * BLOCK + 1, BLOCK - 2, BLOCK - 2))

def draw_piece(surf: pygame.surface.Surface, piece: Piece) -> None:
    for x, y in piece.blocks():
        if y >= 0:
            pygame.draw.rect(surf, piece.color, pygame.Rect(x * BLOCK + 1, y * BLOCK + 1, BLOCK - 2, BLOCK - 2))

def fetch_highscore() -> int:
    try:
        req = requests.get(f"{SERVER_URL}/highscore", timeout=2)
        if req.ok:
            return int(req.json().get("highscore", 0))
    except Exception:
        pass
    return 0

def update_highscore(score: int) -> int | None:
    try:
        req = requests.post(f"{SERVER_URL}/highscore", json={"score": int(score)}, timeout=2)
        if req.ok:
            return int(req.json().get("highscore", 0))
    except Exception:
        pass
    return None

def fetch_highscore_async(result_container: dict) -> None:
    result_container["highscore"] = fetch_highscore()

def compute_drop_interval_ms(score: int, drop_fast: bool) -> int:
    base = int(BASE_INTERVAL_MS * (0.995 ** max(0, score // 10)))
    base = max(MIN_INTERVAL_MS, base)
    return FAST_DROP_MS if drop_fast else base

def draw_panel(surf: pygame.surface.Surface, rect: pygame.rect.Rect, title: str, font: pygame.font.Font) -> tuple[int, int]:
    pygame.draw.rect(surf, PANEL_BG, rect, border_radius=8)
    pygame.draw.rect(surf, PANEL_BORDER, rect, width=1, border_radius=8)
    title_surf = font.render(title, True, WHITE)
    title_pos = (rect.x + PANEL_PAD, rect.y + PANEL_PAD)
    surf.blit(title_surf, title_pos)
    content_x = rect.x + PANEL_PAD
    content_y = rect.y + PANEL_PAD + title_surf.get_height() + 8
    return content_x, content_y

def draw_sidebar(surf: pygame.surface.Surface, font: pygame.font.Font, small_font: pygame.font.Font, next_piece: Piece, score: int, highscore: int, fps_target: int, fps_actual: float, drop_ms: int) -> None:
    pygame.draw.rect(surf, SIDEBAR_BG, pygame.Rect(GRID_W, 0, SIDE_W, GRID_H))

    x_pad, y = GRID_W + PANEL_PAD, PANEL_PAD
    w = SIDE_W - 2 * PANEL_PAD

    next_rect = pygame.Rect(x_pad, y, w, 160)
    cx, cy = draw_panel(surf, next_rect, "Next", font)
    content_w = next_rect.w - 2 * PANEL_PAD
    available_h = next_rect.h - (cy - next_rect.y) - PANEL_PAD
    box_size = min(content_w, available_h)
    preview_rect = pygame.Rect(cx + (content_w - box_size) // 2, cy + (available_h - box_size) // 2, box_size, box_size)
    pygame.draw.rect(surf, PREVIEW_BG, preview_rect, border_radius=6)

    preview_surf = pygame.Surface((box_size, box_size), pygame.SRCALPHA)
    cell = box_size // 4

    cells = PIECES[next_piece.kind]["rotation"][0]
    min_x = min(cx0 for cx0, _ in cells)
    max_x = max(cx0 for cx0, _ in cells)
    min_y = min(cy0 for _, cy0 in cells)
    max_y = max(cy0 for _, cy0 in cells)
    width_cells = max_x - min_x + 1
    height_cells = max_y - min_y + 1

    start_x = -min_x * cell + (box_size - width_cells * cell) // 2
    start_y = -min_y * cell + (box_size - height_cells * cell) // 2

    for cx0, cy0 in cells:
        px = int(start_x + cx0 * cell)
        py = int(start_y + cy0 * cell)
        pygame.draw.rect(preview_surf, next_piece.color, pygame.Rect(px + 2, py + 2, cell - 4, cell - 4), border_radius=4)

    surf.blit(preview_surf, preview_rect.topleft)
    y += next_rect.height + PANEL_PAD

    stats_rect = pygame.Rect(x_pad, y, w, 160)
    sx, sy = draw_panel(surf, stats_rect, "Stats", font)
    line_h = 24
    items = [
        ("Score", str(score)),
        ("High", str(highscore)),
        ("FPS", f"{int(fps_actual)}/{int(fps_target)}"),
        ("Drop", f"{drop_ms} ms"),
    ]
    for i, (k, v) in enumerate(items):
        key_s = small_font.render(f"{k}:", True, WHITE)
        val_s = small_font.render(v, True, WHITE)
        surf.blit(key_s, (sx, sy + i * line_h))
        surf.blit(val_s, (sx + 80, sy + i * line_h))

    y += stats_rect.height + PANEL_PAD
    ctrls_rect = pygame.Rect(x_pad, y, w, 160)
    cx2, cy2 = draw_panel(surf, ctrls_rect, "Controls", font)
    controls = [
        "←/→: Move",
        "↑: Rotate",
        "↓: Soft drop",
        "Space: Hard drop",
        "+/-: FPS",
    ]
    for i, text in enumerate(controls):
        surf.blit(small_font.render(text, True, WHITE), (cx2, cy2 + i * 20))

def load_sounds() -> dict[str, pygame.mixer.Sound]:
    base_path = os.path.dirname(os.path.abspath(__file__))
    sound_folder = os.path.join(base_path, "..", "public")

    sounds = {
        "clear": pygame.mixer.Sound(os.path.join(sound_folder, "clear_line.wav")),
        "gameover": pygame.mixer.Sound(os.path.join(sound_folder, "game_over.wav")),
        "drop": pygame.mixer.Sound(os.path.join(sound_folder, "drop.wav")),
    }
    return sounds

def flash_lines(surf: pygame.Surface, lines: np.ndarray) -> None:
    flash_color = (255, 255, 255)
    flash_duration = 150
    end_time = pygame.time.get_ticks() + flash_duration
    while pygame.time.get_ticks() < end_time:
        for y in lines:
            for x in range(COLS):
                rect = pygame.Rect(x * BLOCK + 1, y * BLOCK + 1, BLOCK - 2, BLOCK - 2)
                pygame.draw.rect(surf, flash_color, rect)
        pygame.display.flip()

def game_over_animation(screen: pygame.surface.Surface, big_font: pygame.font.Font, font: pygame.font.Font) -> None:
    overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
    alpha = 0
    increment = 5
    while alpha <= 45:
        overlay.fill((0, 0, 0, alpha))
        screen.blit(overlay, (0, 0))
        msg1 = big_font.render("Game Over", True, WHITE)
        msg2 = font.render("Press R to Restart or ESC to Quit", True, WHITE)
        screen.blit(msg1, (GRID_W // 2 - msg1.get_width() // 2, GRID_H // 2 - 40))
        screen.blit(msg2, (GRID_W // 2 - msg2.get_width() // 2, GRID_H // 2 + 10))
        pygame.display.flip()
        alpha += increment
        pygame.time.wait(60)

def show_loading_screen(screen: pygame.Surface, font: pygame.font.Font) -> None:
    screen.fill(BLACK)
    loading_text = font.render("Connecting to server...", True, WHITE)
    text_rect = loading_text.get_rect(center=(WIN_W // 2, WIN_H // 2))
    screen.blit(loading_text, text_rect)
    pygame.display.flip()

def main() -> None:
    pygame.init()
    pygame.mixer.init()

    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Tetris")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("arial", 20, bold=True)
    big_font = pygame.font.SysFont("arial", 36, bold=True)
    small_font = pygame.font.SysFont("arial", 16)

    show_loading_screen(screen, font)
    result = {"highscore": None}
    thread = threading.Thread(target=fetch_highscore_async, args=(result,))
    thread.start()

    loading = True
    while loading:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)

        if not thread.is_alive():
            loading = False
        clock.tick(30)
    highscore = result["highscore"] if result["highscore"] else 0

    board = create_board()
    queue = []
    current = spawn_piece(queue)
    next_p = spawn_piece(queue)
    sounds = load_sounds()
    score = 0
    fall_timer = 0
    running = True
    drop_fast = False
    fps_target = FPS
    while running:
        dt = clock.tick(fps_target)
        fall_timer += dt
        fps_actual = clock.get_fps()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False

                elif event.key == pygame.K_LEFT:
                    moved = current.moved(dx=-1)
                    if valid(board, moved):
                        current = moved

                elif event.key == pygame.K_RIGHT:
                    moved = current.moved(dx=1)
                    if valid(board, moved):
                        current = moved

                elif event.key == pygame.K_DOWN:
                    drop_fast = True

                elif event.key == pygame.K_UP:
                    rotated = current.rotated(dir=1)
                    if valid(board, rotated):
                        current = rotated

                elif event.key == pygame.K_SPACE:
                    moved = current
                    while valid(board, moved.moved(dy=1)):
                        moved = moved.moved(dy=1)
                    sounds["drop"].play()
                    current = moved
                    lock_piece(board, current)
                    full_rows = np.where(np.all(board != 0, axis=1))[0]
                    board, cleared = clear_lines(board)
                    if cleared:
                        flash_lines(screen, full_rows)
                        sounds["clear"].play()
                        score += score_for_lines(cleared)
                    current = next_p
                    next_p = spawn_piece(queue)
                    if not valid(board, current):
                        sounds["gameover"].play()
                        break

                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    fps_target = max(MIN_FPS, fps_target - FPS_STEP)
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    fps_target = min(MAX_FPS, fps_target + FPS_STEP)

            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_DOWN:
                    drop_fast = False

        interval = compute_drop_interval_ms(score, drop_fast)
        if fall_timer >= interval:
            fall_timer = 0
            moved = current.moved(dy=1)
            if valid(board, moved):
                current = moved
            else:
                sounds["drop"].play()
                lock_piece(board, current)
                full_rows = np.where(np.all(board != 0, axis=1))[0]
                board, cleared = clear_lines(board)
                if cleared:
                    flash_lines(screen, full_rows)
                    sounds["clear"].play()
                    score += score_for_lines(cleared)
                current = next_p
                next_p = spawn_piece(queue)
                if not valid(board, current):
                    sounds["gameover"].play()
                    new_hs = update_highscore(score)
                    if isinstance(new_hs, int):
                        highscore = new_hs

                    game_over_animation(screen, big_font, font)
                    wait = True
                    while wait:
                        for e in pygame.event.get():
                            if e.type == pygame.QUIT:
                                pygame.quit()
                                sys.exit(0)
                            elif e.type == pygame.KEYDOWN:
                                if e.key == pygame.K_ESCAPE:
                                    pygame.quit()
                                    sys.exit(0)
                                elif e.key == pygame.K_r:
                                    board = create_board()
                                    queue = []
                                    current = spawn_piece(queue)
                                    next_p = spawn_piece(queue)
                                    score = 0
                                    highscore = fetch_highscore()
                                    fall_timer = 0
                                    drop_fast = False
                                    wait = False

        screen.fill(BLACK)
        pygame.draw.rect(screen, GRAY, pygame.Rect(0, 0, GRID_W, GRID_H))
        draw_board(screen, board)
        draw_piece(screen, current)
        draw_grid(screen)
        draw_sidebar(screen, font, small_font, next_p, score, highscore, fps_target, fps_actual, interval)

        pygame.display.flip()

    pygame.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()