# main.py
import pygame
import constrants
from character import Character
from constrants import SCREEN_WIDTH, SCREEN_HEIGHT
from game_logic import (
    move_player, undo_move, get_player_rc,
    get_map, get_revealed, get_inventory, get_log_tail,
    is_game_over, reset_game, process_command
)

pygame.init()

# Screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Dungeon Crawler")
clock = pygame.time.Clock()

# -------- Layout --------
HUD_W = 260               # right sidebar width
PADDING = 12              # outer padding
BTN_AREA_H = 70           # space under grid for buttons + input
INPUT_H = 28              # input box height
BG = constrants.BACKGROUND_COLOUR

# Grid size from logic
GRID = get_map()
ROWS, COLS = len(GRID), len(GRID[0])

# Compute tile so grid fits (leaving space for HUD & button area)
avail_w = SCREEN_WIDTH - HUD_W - PADDING * 3
avail_h = SCREEN_HEIGHT - PADDING * 2 - BTN_AREA_H
TILE = max(12, min(avail_w // COLS, avail_h // ROWS))

GRID_W, GRID_H = COLS * TILE, ROWS * TILE
GRID_X = PADDING
GRID_Y = PADDING + (avail_h - GRID_H) // 2  # vertically centered in available area

# HUD rect
HUD_X = GRID_X + GRID_W + PADDING
HUD_Y = PADDING
HUD_H = SCREEN_HEIGHT - PADDING * 2
HUD_RECT = pygame.Rect(HUD_X, HUD_Y, HUD_W, HUD_H)

# Buttons row (below grid)
BTN_Y = GRID_Y + GRID_H + 10
BTN_W, BTN_H, GAP = 120, 36, 10
btn_undo  = pygame.Rect(GRID_X,                  BTN_Y, BTN_W, BTN_H)
btn_play  = pygame.Rect(GRID_X + BTN_W + GAP,    BTN_Y, BTN_W, BTN_H)
btn_exit  = pygame.Rect(GRID_X + 2*(BTN_W+GAP),  BTN_Y, BTN_W, BTN_H)

# Text input (under buttons)
INPUT_Y = BTN_Y + BTN_H + 8
input_rect = pygame.Rect(GRID_X, INPUT_Y, GRID_W, INPUT_H)

# ----- assets -----
def scale_image(image, scale: float) -> pygame.Surface:
    w, h = image.get_width(), image.get_height()
    return pygame.transform.scale(image, (int(w * scale), int(h * scale)))

# Use raw string / forward slashes for Windows paths
player_image = pygame.image.load(r"assets/character_0/img1.png").convert_alpha()
player_image = scale_image(player_image, constrants.SCALE)
character = Character(100, 100, player_image)

# Fonts
font_small = pygame.font.SysFont(None, 20)
font_med = pygame.font.SysFont(None, 22)

# Command input state
command_active = False
cmd_buffer = ""
feedback_text = ""  # optional one-line feedback

# snap sprite to logic position with origin offsets
def snap_sprite_to_grid():
    r, c = get_player_rc()
    character.rect.center = (
        GRID_X + c * TILE + TILE // 2,
        GRID_Y + r * TILE + TILE // 2
    )

snap_sprite_to_grid()

# ---- drawing helpers ----
def draw_grid(surface):
    grid = get_map()
    vis = get_revealed()
    # soft backdrop around grid
    pygame.draw.rect(surface, (235, 235, 235), (GRID_X-1, GRID_Y-1, GRID_W+2, GRID_H+2))
    for rr, row in enumerate(grid):
        for cc, cell in enumerate(row):
            x = GRID_X + cc * TILE
            y = GRID_Y + rr * TILE
            if not vis[rr][cc]:
                pygame.draw.rect(surface, (220, 220, 220), (x, y, TILE, TILE))
                pygame.draw.rect(surface, (200, 200, 200), (x, y, TILE, TILE), 1)
                continue
            color = {
                ".": (245, 245, 245),
                "#": (80, 80, 80),
                "I": (255, 215, 0),
                "M": (200, 80, 80),
                "S": (180, 220, 255),
                "E": (120, 200, 120),
            }.get(cell, (245, 245, 245))
            pygame.draw.rect(surface, color, (x, y, TILE, TILE))
            pygame.draw.rect(surface, (200, 200, 200), (x, y, TILE, TILE), 1)

def draw_hud(surface):
    pygame.draw.rect(surface, (245, 245, 245), HUD_RECT, border_radius=6)
    pygame.draw.rect(surface, (200, 200, 200), HUD_RECT, 1, border_radius=6)

    # Inventory
    title = font_med.render("Inventory", True, (0, 0, 0))
    surface.blit(title, (HUD_X + 10, HUD_Y + 8))
    inv = ", ".join(get_inventory()) or "(empty)"
    inv_img = font_small.render(inv, True, (30, 30, 30))
    surface.blit(inv_img, (HUD_X + 10, HUD_Y + 34))

    # Log
    y = HUD_Y + 68
    log_title = font_med.render("Recent Log", True, (0, 0, 0))
    surface.blit(log_title, (HUD_X + 10, y))
    y += 6
    for line in get_log_tail(9):
        y += 20
        img = font_small.render(line, True, (40, 40, 40))
        surface.blit(img, (HUD_X + 10, y))

def draw_button(surface, rect, label, disabled=False):
    bg = (235,235,235) if not disabled else (215,215,215)
    border = (160,160,160)
    txt_col = (0,0,0) if not disabled else (120,120,120)
    pygame.draw.rect(surface, bg, rect, border_radius=6)
    pygame.draw.rect(surface, border, rect, 1, border_radius=6)
    img = font_small.render(label, True, txt_col)
    surface.blit(img, (rect.x + (rect.w-img.get_width())//2,
                       rect.y + (rect.h-img.get_height())//2))

# ---- main loop ----
running = True
while running:
    clock.tick(constrants.FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # ----- mouse: buttons & input focus -----
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if btn_exit.collidepoint(event.pos):
                running = False
            elif btn_play.collidepoint(event.pos):
                reset_game()
                snap_sprite_to_grid()
            elif btn_undo.collidepoint(event.pos):
                if not is_game_over():
                    undo_move()
                    snap_sprite_to_grid()
            # focus input when clicking the box
            command_active = input_rect.collidepoint(event.pos)

        # ----- keyboard: arrows vs typing -----
        if event.type == pygame.KEYDOWN and not command_active:
            # arrow keys still work
            if event.key == pygame.K_LEFT:
                move_player(-1, 0)
            elif event.key == pygame.K_RIGHT:
                move_player(1, 0)
            elif event.key == pygame.K_UP:
                move_player(0, -1)
            elif event.key == pygame.K_DOWN:
                move_player(0, 1)
            elif event.key == pygame.K_u:
                undo_move()
            elif event.key == pygame.K_TAB:
                command_active = True
                cmd_buffer = ""
            snap_sprite_to_grid()

        elif event.type == pygame.KEYDOWN and command_active:
            if event.key == pygame.K_RETURN:
                feedback_text = process_command(cmd_buffer)
                cmd_buffer = ""
                command_active = False
                snap_sprite_to_grid()
            elif event.key == pygame.K_ESCAPE:
                command_active = False
            elif event.key == pygame.K_BACKSPACE:
                cmd_buffer = cmd_buffer[:-1]
            else:
                if event.unicode and event.unicode.isprintable():
                    cmd_buffer += event.unicode

    # ---- draw ----
    screen.fill(BG)
    draw_grid(screen)
    character.draw(screen)
    draw_hud(screen)

    # Buttons
    draw_button(screen, btn_undo, "Undo", disabled=is_game_over())
    draw_button(screen, btn_play, "Play Again")
    draw_button(screen, btn_exit, "Exit")

    # Input box (click to type)
    pygame.draw.rect(screen, (255,255,255), input_rect, border_radius=6)
    pygame.draw.rect(screen, (170,170,170), input_rect, 1, border_radius=6)
    prompt = ("> " + cmd_buffer) if command_active else "> (click here to type commands)"
    img = font_small.render(prompt, True, (0,0,0))
    screen.blit(img, (input_rect.x + 8, input_rect.y + 6))

    # Optional one-line feedback above the input
    if feedback_text:
        fb = font_small.render(feedback_text, True, (40,40,40))
        screen.blit(fb, (input_rect.x, input_rect.y - 22))

    pygame.display.update()

pygame.quit()
