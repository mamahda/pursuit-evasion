import pygame
import heapq
import random
import urllib.request
import os
import sys
import io

pygame.init()

# ==============================================================================
# KONSTANTA & PENGATURAN
# ==============================================================================

GRID_SIZE = 17
CELL_SIZE = 43
WINDOW_SIZE = GRID_SIZE * CELL_SIZE
FPS = 60

# Warna
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)
RED = (255, 0, 0)
DARK_RED = (139, 0, 0)
BLUE = (0, 100, 255)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)

GRADIENT_TOP = (10, 10, 50)
GRADIENT_BOTTOM = (30, 30, 100)
TEXT_COLOR = (255, 255, 255)
SELECTED_COLOR_START = (255, 100, 0)
SELECTED_COLOR_END = (255, 200, 50)
TITLE_COLOR = (255, 20, 20)

FONT_PATH = "./assets/upheavtt.ttf"

# Status Game
MENU = -1
PLAYING = 0
THIEF_WIN = 1
POLICE_WIN = 2

INTERCEPT_DISTANCE_THRESHOLD = 5
POLICE_PATH = 1

LEVEL_CONFIG = {
    1: {"grid_size": 17, "walls": 0.25, "police_speed": 300, "name": "Easy"},
    2: {"grid_size": 17, "walls": 0.30, "police_speed": 200, "name": "Normal"},
    3: {"grid_size": 17, "walls": 0.35, "police_speed": 180, "name": "Hard"},
    4: {"grid_size": 17, "walls": 0.30, "police_speed": 160, "name": "Expert"},
    5: {"grid_size": 17, "walls": 0.35, "police_speed": 130, "name": "Impossible"},
}

# size font
title_size = 64
subtitle_size = 32
menu_size = 24

# ==============================================================================
# ASSET LOADER
# ==============================================================================
class AssetLoader:
    def __init__(self):
        self.assets = {}
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.asset_dir = os.path.join(script_dir, "assets")

        if not os.path.exists(self.asset_dir):
            os.makedirs(self.asset_dir)

        self.load_assets()
    
    def download_asset(self, url, filename):
        filepath = os.path.join(self.asset_dir, filename)
        if not os.path.exists(filepath):
            try:
                print(f"Downloading {filename}...")
                urllib.request.urlretrieve(url, filepath)
                return True
            except:
                print(f"Failed to download {filename}")
                return False
        return True
    
    def load_assets(self):
        self.assets['thief'] = self.load_image('thief.png')
        self.assets['police1'] = self.load_image('police1.png')
        self.assets['police2'] = self.load_image('police2.png')
        self.assets['money'] = self.load_image('money.png')
        
        self.assets['exit'] = self.create_exit_sprite()
        self.assets['wall'] = self.create_wall_sprite()
        self.assets['floor'] = self.create_floor_sprite()
    
    def load_image(self, filename):
        try:
            filepath = os.path.join(self.asset_dir, filename)
            image = pygame.image.load(filepath)
            image = pygame.transform.scale(image, (CELL_SIZE, CELL_SIZE))
            return image
        except Exception as e:
            print(f"[WARNING] Tidak dapat load {filename}, menggunakan sprite default")
            surf = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            surf.fill((255, 0, 255))
            return surf
    
    def create_exit_sprite(self):
        surf = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
        pygame.draw.rect(surf, (101, 67, 33), (5, 0, CELL_SIZE - 10, CELL_SIZE))
        pygame.draw.rect(surf, (70, 130, 70), (8, 3, CELL_SIZE - 16, CELL_SIZE - 6))
        pygame.draw.circle(surf, YELLOW, (CELL_SIZE - 15, CELL_SIZE // 2), 4)
        pygame.draw.rect(surf, GREEN, (10, 5, CELL_SIZE - 20, 8))
        return surf
    
    def create_wall_sprite(self):
        surf = pygame.Surface((CELL_SIZE, CELL_SIZE))
        surf.fill((80, 80, 80))
        
        brick_color = (60, 60, 60)
        mortar_color = (90, 90, 90)
        
        surf.fill(mortar_color)
        
        for y in range(0, CELL_SIZE, 15):
            offset = 0 if (y // 15) % 2 == 0 else 20
            for x in range(-20 + offset, CELL_SIZE, 40):
                pygame.draw.rect(surf, brick_color, (x, y, 38, 13))
        
        return surf
    
    def create_floor_sprite(self):
        surf = pygame.Surface((CELL_SIZE, CELL_SIZE))
        
        color1 = (200, 200, 200)
        color2 = (180, 180, 180)
        
        surf.fill(color1)
        pygame.draw.rect(surf, color2, (0, 0, CELL_SIZE//2, CELL_SIZE//2))
        pygame.draw.rect(surf, color2, (CELL_SIZE//2, CELL_SIZE//2, CELL_SIZE//2, CELL_SIZE//2))
        
        return surf

# ==============================================================================
# NODE CLASS
# ==============================================================================
class Node:
    def __init__(self, pos, g=0, h=0, parent=None):
        self.pos = pos
        self.g = g
        self.h = h
        self.f = g + h
        self.parent = parent

    def __lt__(self, other):
        return self.f < other.f

# ==============================================================================
# GAME CLASS
# ==============================================================================
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
        pygame.display.set_caption("Museum Heist - Escape the Police!")
        self.clock = pygame.time.Clock()

        try:
            self.font = pygame.font.Font(None, menu_size)
            self.subtitle_font = pygame.font.Font(None, subtitle_size)
            self.title_font = pygame.font.Font(FONT_PATH, title_size)
        except pygame.error:
            print(f"[WARNING] Font kustom {FONT_PATH} gagal dimuat. Menggunakan font default.")
            self.font = pygame.font.Font(None, 36)
            self.subtitle_font = pygame.font.Font(None, 24)
            self.title_font = pygame.font.Font(None, 64)

        self.assets = AssetLoader()
        self.move_delay = 150
        self.last_move_time = 0
        self.interceptor_mode = "intercept"
        self.current_level = 1
        self.game_state = MENU
        self.selected_level = 1
        
        # Timer variables
        self.timer_started = False
        self.start_time = 0
        self.elapsed_time = 0

    def get_random_free_position(self, exclude_positions=[]):
        """Mendapatkan posisi random yang tidak ada wall dan tidak ada di exclude_positions"""
        max_attempts = 1000
        for _ in range(max_attempts):
            x = random.randint(1, self.grid_size - 2)
            y = random.randint(1, self.grid_size - 2)
            pos = [x, y]
            
            # Cek apakah posisi kosong dan tidak ada di exclude_positions
            if self.grid[y][x] == 0 and pos not in exclude_positions:
                return pos
        
        # Fallback jika tidak menemukan posisi
        return [self.grid_size // 2, self.grid_size // 2]

    def reset_game(self):
        self.current_level = self.selected_level
        config = LEVEL_CONFIG[self.current_level]
        grid_size = config["grid_size"]
        
        if hasattr(self, 'screen'):
            new_size = grid_size * CELL_SIZE
            if new_size != WINDOW_SIZE:
                self.screen = pygame.display.set_mode((new_size, new_size))
        
        self.grid = [[0 for _ in range(grid_size)] for _ in range(grid_size)]
        self.grid_size = grid_size
        self.wall_ratio = config["walls"]
        
        # Generate walls terlebih dahulu
        self.generate_walls()
        
        # Posisi random untuk exit (thief start position)
        self.exit_pos = self.get_random_free_position([])
        
        # Thief mulai dari exit
        self.thief_pos = list(self.exit_pos)
        self.thief_prev_pos = list(self.exit_pos)
        
        # Posisi random untuk money
        self.money_pos = self.get_random_free_position([self.exit_pos])
        
        # Posisi random untuk police
        self.police_positions = [
            self.get_random_free_position([self.exit_pos, self.money_pos]),
            self.get_random_free_position([self.exit_pos, self.money_pos])
        ]
        
        # Clear area di sekitar posisi penting
        positions_to_clear = [self.thief_pos, self.money_pos, self.exit_pos] + self.police_positions
        for pos in positions_to_clear:
            cx, cy = pos
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < self.grid_size and 0 <= nx < self.grid_size:
                        self.grid[ny][nx] = 0
        
        self.police_paths = [[], []]
        self.police_move_delay = config["police_speed"]
        self.last_police_move = 0

        self.money_collected = False
        self.game_state = PLAYING
        self.moves_count = 0
        self.interceptor_mode = "intercept"
        
        # Reset timer
        self.timer_started = False
        self.start_time = 0
        self.elapsed_time = 0

    def generate_walls(self):
        wall_count = int(self.grid_size * self.grid_size * self.wall_ratio)
        for _ in range(wall_count):
            x = random.randint(1, self.grid_size - 2)
            y = random.randint(1, self.grid_size - 2)
            self.grid[y][x] = 1

    def manhattan_distance(self, pos1, pos2):
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def get_neighbors(self, pos):
        neighbors = []
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        
        for dx, dy in directions:
            nx, ny = pos[0] + dx, pos[1] + dy
            if 0 <= nx < self.grid_size and 0 <= ny < self.grid_size:
                if self.grid[ny][nx] == 0:
                    neighbors.append([nx, ny])
        return neighbors

    def a_star(self, start, goal, cost_grid=None):
        if cost_grid is None:
            cost_grid = [[1 for _ in range(self.grid_size)] for _ in range(self.grid_size)]

        start_node = Node(tuple(start), 0, self.manhattan_distance(start, goal))
        open_list = [start_node]
        closed_set = set()
        g_scores = {tuple(start): 0}

        while open_list:
            current = heapq.heappop(open_list)

            if current.pos == tuple(goal):
                path = []
                while current.parent:
                    path.append(list(current.pos))
                    current = current.parent
                return path[::-1]

            if current.pos in closed_set:
                continue
            closed_set.add(current.pos)

            for neighbor in self.get_neighbors(list(current.pos)):
                neighbor_tuple = tuple(neighbor)
                
                if neighbor_tuple in closed_set:
                    continue

                move_cost = cost_grid[neighbor[1]][neighbor[0]]
                tentative_g = current.g + move_cost

                if neighbor_tuple not in g_scores or tentative_g < g_scores[neighbor_tuple]:
                    g_scores[neighbor_tuple] = tentative_g
                    h = self.manhattan_distance(neighbor, goal)
                    neighbor_node = Node(neighbor_tuple, tentative_g, h, current)
                    heapq.heappush(open_list, neighbor_node)

        return []

    def handle_menu_input(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.selected_level = max(1, self.selected_level - 1)
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.selected_level = min(len(LEVEL_CONFIG), self.selected_level + 1)
        elif keys[pygame.K_RETURN]:
            self.reset_game()
            self.game_state = PLAYING

    def handle_player_input(self):
        if self.game_state != PLAYING:
            return
        
        current_time = pygame.time.get_ticks()
        if current_time - self.last_move_time < self.move_delay:
            return
        
        keys = pygame.key.get_pressed()
        new_pos = list(self.thief_pos)
        moved = False
        
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            new_pos[1] -= 1
            moved = True
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            new_pos[1] += 1
            moved = True
        elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
            new_pos[0] -= 1
            moved = True
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            new_pos[0] += 1
            moved = True
        
        if moved:
            if (0 <= new_pos[0] < self.grid_size and 
                0 <= new_pos[1] < self.grid_size and 
                self.grid[new_pos[1]][new_pos[0]] == 0):
                
                # Start timer saat gerakan pertama
                if not self.timer_started:
                    self.timer_started = True
                    self.start_time = current_time
                
                self.thief_prev_pos = list(self.thief_pos)
                self.thief_pos = new_pos
                self.last_move_time = current_time
                self.moves_count += 1
                
                if self.thief_pos == self.money_pos and not self.money_collected:
                    self.money_collected = True
                
                if self.thief_pos == self.exit_pos and self.money_collected:
                    self.game_state = THIEF_WIN
                    self.elapsed_time = (current_time - self.start_time) / 1000.0

    def get_intercept_target(self):
        dx = self.thief_pos[0] - self.thief_prev_pos[0]
        dy = self.thief_pos[1] - self.thief_prev_pos[1]
        
        prediction_step = 5
        for step in range(prediction_step, 0, -1):
            tx = self.thief_pos[0] + (dx * step)
            ty = self.thief_pos[1] + (dy * step)
            
            if 0 <= tx < self.grid_size and 0 <= ty < self.grid_size:
                if self.grid[int(ty)][int(tx)] == 0:
                    return [int(tx), int(ty)]
        
        return self.thief_pos

    def update_police(self):
        # Police hanya bergerak setelah money diambil
        if self.game_state != PLAYING or not self.money_collected:
            return
        
        current_time = pygame.time.get_ticks()
        if current_time - self.last_police_move < self.police_move_delay:
            return
        
        self.last_police_move = current_time

        path_0 = self.a_star(self.police_positions[0], self.thief_pos)
        self.police_paths[0] = path_0
        
        if path_0:
            self.police_positions[0] = path_0.pop(0)
        else:
            neighbors = self.get_neighbors(self.police_positions[0])
            if neighbors:
                self.police_positions[0] = random.choice(neighbors)

        distance_to_thief = self.manhattan_distance(self.police_positions[1], self.thief_pos)
        
        if distance_to_thief <= INTERCEPT_DISTANCE_THRESHOLD:
            self.interceptor_mode = "chase"
            target_pos = self.thief_pos
        else:
            self.interceptor_mode = "intercept"
            target_pos = self.get_intercept_target()
        
        path_1 = self.a_star(self.police_positions[1], target_pos)
        self.police_paths[1] = path_1

        if path_1:
            self.police_positions[1] = path_1.pop(0)
        else:
            path_fallback = self.a_star(self.police_positions[1], self.thief_pos)
            if path_fallback:
                self.police_positions[1] = path_fallback.pop(0)
            else:
                neighbors = self.get_neighbors(self.police_positions[1])
                if neighbors:
                    self.police_positions[1] = random.choice(neighbors)

        # Cek tangkapan hanya setelah money diambil
        for p_pos in self.police_positions:
            if p_pos == self.thief_pos:
                self.game_state = POLICE_WIN
                self.elapsed_time = (current_time - self.start_time) / 1000.0
                return;

    def draw_gradient_background(self, surface, top_color, bottom_color):
        """Menggambar latar belakang gradient vertikal sederhana."""
        width, height = surface.get_size()
        gradient_surface = pygame.Surface((1, height))
        
        for y in range(height):
            t = y / (height - 1)
            r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
            g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
            b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
            gradient_surface.set_at((0, y), (r, g, b))
            
        pygame.transform.scale(gradient_surface, (width, height), surface)

    def draw_menu(self):
        # Pastikan ukuran window konsisten di menu
        menu_size = 17 * CELL_SIZE
        current_size = self.screen.get_size()[0]
        
        if current_size != menu_size:
            self.screen = pygame.display.set_mode((menu_size, menu_size))
        
        window_width, window_height = menu_size, menu_size
        center_x = window_width // 2

        self.draw_gradient_background(self.screen, GRADIENT_TOP, GRADIENT_BOTTOM)
        
        title_text = "MUSEUM HEIST"
        title = self.title_font.render(title_text, True, TITLE_COLOR)
        self.screen.blit(title, (center_x - title.get_width() // 2, 40))
        
        subtitle_text = "Pilih Level:"
        subtitle = self.subtitle_font.render(subtitle_text, True, TEXT_COLOR)
        self.screen.blit(subtitle, (center_x - subtitle.get_width() // 2, 150))
        
        y_pos = 200
        for level in range(1, len(LEVEL_CONFIG) + 1):
            config = LEVEL_CONFIG[level]
            is_selected = level == self.selected_level
            
            level_name = config['name']
            text_content = f"Level {level}: {level_name}"
            
            if is_selected:
                color_r = int((SELECTED_COLOR_START[0] + SELECTED_COLOR_END[0]) / 2)
                color_g = int((SELECTED_COLOR_START[1] + SELECTED_COLOR_END[1]) / 2)
                color_b = int((SELECTED_COLOR_START[2] + SELECTED_COLOR_END[2]) / 2)
                text_color = (color_r, color_g, color_b)
                
                text_shadow = self.font.render(text_content, True, BLACK)
                # self.screen.blit(text_shadow, (center_x - text_shadow.get_width() // 2 + 2, y_pos + 2))
            else:
                text_color = TEXT_COLOR
            
            text = self.font.render(text_content, True, text_color)
            # self.screen.blit(text, (center_x - text.get_width() // 2, y_pos))
            self.screen.blit(text, (200, y_pos))
            
            if is_selected:
                indicator_size = 10
                # pygame.draw.circle(self.screen, text_color, 
                #                    (center_x - text.get_width() // 2 - 20, y_pos + text.get_height() // 2), 
                #                    indicator_size // 2)
                pygame.draw.circle(self.screen, text_color, 
                                   (180, y_pos + text.get_height() // 2), 
                                   indicator_size // 2)
            
            y_pos += 40
        
        info_text = "ENTER untuk Mulai"
        info = self.font.render(info_text, True, (150, 150, 150))
        self.screen.blit(info, (center_x - info.get_width() // 2, window_height - 60))
        
        pygame.display.flip()

    def draw(self):
        if self.game_state == MENU:
            self.draw_menu()
            return
        
        grid_size = self.grid_size
        window_size = grid_size * CELL_SIZE
        
        self.screen.fill(WHITE)

        for y in range(grid_size):
            for x in range(grid_size):
                if self.grid[y][x] == 1:
                    self.screen.blit(self.assets.assets['wall'], (x * CELL_SIZE, y * CELL_SIZE))
                else:
                    self.screen.blit(self.assets.assets['floor'], (x * CELL_SIZE, y * CELL_SIZE))

        if self.money_collected and POLICE_PATH:
            for pos in self.police_paths[0][:5]:
                rect = pygame.Rect(pos[0]*CELL_SIZE+10, pos[1]*CELL_SIZE+10, CELL_SIZE-20, CELL_SIZE-20)
                s = pygame.Surface((CELL_SIZE-20, CELL_SIZE-20), pygame.SRCALPHA)
                s.fill((255, 200, 200, 100))
                self.screen.blit(s, rect)

            for pos in self.police_paths[1][:5]:
                rect = pygame.Rect(pos[0]*CELL_SIZE+10, pos[1]*CELL_SIZE+10, CELL_SIZE-20, CELL_SIZE-20)
                s = pygame.Surface((CELL_SIZE-20, CELL_SIZE-20), pygame.SRCALPHA)
                s.fill((200, 100, 100, 100))
                self.screen.blit(s, rect)

        self.screen.blit(self.assets.assets['exit'], 
                        (self.exit_pos[0]*CELL_SIZE, self.exit_pos[1]*CELL_SIZE))
        
        if not self.money_collected:
            self.screen.blit(self.assets.assets['money'], 
                            (self.money_pos[0]*CELL_SIZE, self.money_pos[1]*CELL_SIZE))

        self.screen.blit(self.assets.assets['thief'], 
                        (self.thief_pos[0]*CELL_SIZE, self.thief_pos[1]*CELL_SIZE))
        
        # Police selalu ditampilkan
        self.screen.blit(self.assets.assets['police1'], 
                        (self.police_positions[0][0]*CELL_SIZE, self.police_positions[0][1]*CELL_SIZE))
        self.screen.blit(self.assets.assets['police2'], 
                        (self.police_positions[1][0]*CELL_SIZE, self.police_positions[1][1]*CELL_SIZE))

        config = LEVEL_CONFIG[self.current_level]
        status = "Steal the Diamond! (Arrow Keys/WASD)" if not self.money_collected else "ESCAPE! Police are chasing you!"
        color = ORANGE if not self.money_collected else RED
        text = self.font.render(status, True, color)
        
        bg = pygame.Surface((text.get_width() + 10, text.get_height() + 5))
        bg.fill(WHITE)
        bg.set_alpha(200)
        self.screen.blit(bg, (5, 5))
        self.screen.blit(text, (10, 5))

        # Tampilkan timer
        if self.timer_started and self.game_state == PLAYING:
            current_time = pygame.time.get_ticks()
            elapsed = (current_time - self.start_time) / 1000.0
            timer_text = self.subtitle_font.render(f"Time: {elapsed:.1f}s", True, BLACK)
        else:
            timer_text = self.subtitle_font.render(f"Time: 0.0s", True, BLACK)
        
        bg2 = pygame.Surface((timer_text.get_width() + 10, timer_text.get_height() + 5))
        bg2.fill(WHITE)
        bg2.set_alpha(200)
        self.screen.blit(bg2, (5, 45))
        self.screen.blit(timer_text, (10, 47))

        level_text = self.subtitle_font.render(f"Level {self.current_level}: {config['name']}", True, BLACK)
        bg_level = pygame.Surface((level_text.get_width() + 10, level_text.get_height() + 5))
        bg_level.fill(WHITE)
        bg_level.set_alpha(200)
        self.screen.blit(bg_level, (5, 75))
        self.screen.blit(level_text, (10, 77))

        if self.money_collected:
            mode_text = f"Chaser | Interceptor ({self.interceptor_mode.upper()})"
            role_text = self.subtitle_font.render(mode_text, True, BLACK)
            bg3 = pygame.Surface((role_text.get_width() + 10, role_text.get_height() + 5))
            bg3.fill(WHITE)
            bg3.set_alpha(200)
            self.screen.blit(bg3, (5, 105))
            self.screen.blit(role_text, (10, 107))

        if self.game_state != PLAYING:
            overlay = pygame.Surface((window_size, window_size))
            overlay.fill(BLACK)
            overlay.set_alpha(150)
            self.screen.blit(overlay, (0, 0))
            
            if self.game_state == THIEF_WIN:
                msg = "YOU ESCAPED!"
                next_action = "Press N for Next Level | R for Menu | Q to Quit" if self.current_level < len(LEVEL_CONFIG) else "Press R for Menu | Q to Quit"
                color = GREEN
            else:
                msg = "CAUGHT!"
                next_action = "Press R for Menu | Q to Quit"
                color = RED
            
            score_msg = f"Time: {self.elapsed_time:.2f}s"
            text = self.font.render(msg, True, color)
            score = self.subtitle_font.render(score_msg, True, WHITE)
            restart = self.subtitle_font.render(next_action, True, WHITE)
            
            center_x, center_y = window_size // 2, window_size // 2
            
            self.screen.blit(text, (center_x - text.get_width()//2, center_y - 40))
            self.screen.blit(score, (center_x - score.get_width()//2, center_y + 10))
            self.screen.blit(restart, (center_x - restart.get_width()//2, center_y + 40))

        pygame.display.flip()

    def run(self):
        running = True
        menu_input_delay = 0
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        if self.game_state == MENU:
                            running = False
                        else:
                            self.game_state = MENU
                    elif self.game_state == MENU:
                        if event.key == pygame.K_RETURN:
                            self.reset_game()
                            self.game_state = PLAYING
                    elif self.game_state != MENU:
                        if event.key == pygame.K_r:
                            self.game_state = MENU
                        elif event.key == pygame.K_n:
                            if self.game_state == THIEF_WIN and self.current_level < len(LEVEL_CONFIG):
                                self.selected_level = self.current_level + 1
                                self.reset_game()
                                self.game_state = PLAYING

            if self.game_state == MENU:
                current_time = pygame.time.get_ticks()
                if current_time - menu_input_delay > 150:
                    self.handle_menu_input()
                    menu_input_delay = current_time
            else:
                self.handle_player_input()
                
                # Cek tangkapan hanya setelah money diambil
                # if self.money_collected and self.thief_pos in self.police_positions:
                #     self.game_state = POLICE_WIN
                #     if self.timer_started:
                #         current_time = pygame.time.get_ticks()
                #         self.elapsed_time = (current_time - self.start_time) / 1000.0
                
                self.update_police()
            
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()

if __name__ == "__main__":
    Game().run()
