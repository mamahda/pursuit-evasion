import pygame
import heapq
import random
import urllib.request
import os
import sys
import io

# Ensure stdout/stderr use UTF-8 to avoid UnicodeEncodeError on Windows consoles
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

pygame.init()

# ==============================================================================
# KONSTANTA & PENGATURAN
# ==============================================================================

GRID_SIZE = 15
CELL_SIZE = 50
WINDOW_SIZE = GRID_SIZE * CELL_SIZE
FPS = 60  # Increased for smooth player movement

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

# Status Game
PLAYING = 0
THIEF_WIN = 1
POLICE_WIN = 2

# Threshold untuk mode switch Interceptor
INTERCEPT_DISTANCE_THRESHOLD = 5

# ==============================================================================
# ASSET LOADER
# ==============================================================================
class AssetLoader:
    """Load sprites dengan dukungan 4 arah (up, down, left, right)"""
    
    def __init__(self):
        self.assets = {}
        # Use script directory so assets load reliably when working dir differs
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.asset_dir = os.path.join(script_dir, "assets")

        # Create assets directory if not exists
        if not os.path.exists(self.asset_dir):
            os.makedirs(self.asset_dir)

        self.load_assets()
    
    def download_asset(self, url, filename):
        """Download asset from URL"""
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
        """Load or create all game assets"""
        
        # CARA 1: Load dari file lokal (letakkan file di folder 'assets/')
        # Uncomment baris di bawah dan comment fungsi create_* yang tidak dipakai
        
        self.assets['thief'] = self.load_image('thief.png')
        self.assets['police1'] = self.load_image('police1.png')
        self.assets['police2'] = self.load_image('police2.png')
        self.assets['money'] = self.load_image('money.png')
        # self.assets['exit'] = self.load_image('exit.png')
        # self.assets['wall'] = self.load_image('wall.png')
        # self.assets['floor'] = self.load_image('floor.png')
        
        # CARA 2: Gunakan sprite buatan sendiri (default)
        #self.assets['thief'] = self.create_thief_sprite()
        #self.assets['police1'] = self.create_police_sprite(RED)
        #self.assets['police2'] = self.create_police_sprite(DARK_RED)
        #self.assets['money'] = self.create_money_sprite()
        self.assets['exit'] = self.create_exit_sprite()
        self.assets['wall'] = self.create_wall_sprite()
        self.assets['floor'] = self.create_floor_sprite()
    
    def load_image(self, filename):
        """Load dan resize image dari folder assets"""
        try:
            filepath = os.path.join(self.asset_dir, filename)
            image = pygame.image.load(filepath)
            # Resize ke ukuran cell
            image = pygame.transform.scale(image, (CELL_SIZE, CELL_SIZE))
            return image
        except Exception as e:
            print(f"[WARNING] Tidak dapat load {filename}, menggunakan sprite default")
            # Fallback ke sprite default jika file tidak ditemukan
            surf = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            surf.fill((255, 0, 255))  # Magenta untuk menandai missing sprite
            return surf
    
    def create_exit_sprite(self):
        """Create exit door sprite"""
        surf = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
        
        # Door frame
        pygame.draw.rect(surf, (101, 67, 33), (5, 0, CELL_SIZE - 10, CELL_SIZE))
        
        # Door
        pygame.draw.rect(surf, (70, 130, 70), (8, 3, CELL_SIZE - 16, CELL_SIZE - 6))
        
        # Door handle
        pygame.draw.circle(surf, YELLOW, (CELL_SIZE - 15, CELL_SIZE // 2), 4)
        
        # Exit sign
        pygame.draw.rect(surf, GREEN, (10, 5, CELL_SIZE - 20, 8))
        
        return surf
    
    def create_wall_sprite(self):
        """Create wall tile sprite"""
        surf = pygame.Surface((CELL_SIZE, CELL_SIZE))
        surf.fill((80, 80, 80))
        
        # Brick pattern
        brick_color = (60, 60, 60)
        mortar_color = (90, 90, 90)
        
        surf.fill(mortar_color)
        
        # Draw bricks
        for y in range(0, CELL_SIZE, 15):
            offset = 0 if (y // 15) % 2 == 0 else 20
            for x in range(-20 + offset, CELL_SIZE, 40):
                pygame.draw.rect(surf, brick_color, (x, y, 38, 13))
        
        return surf
    
    def create_floor_sprite(self):
        """Create floor tile sprite"""
        surf = pygame.Surface((CELL_SIZE, CELL_SIZE))
        
        # Checkered floor
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
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        # Load assets
        self.assets = AssetLoader()
        
        # Player control variables
        self.move_delay = 150  # milliseconds between moves
        self.last_move_time = 0
        
        # Police mode tracking
        self.interceptor_mode = "intercept"  # "intercept" atau "chase"
        
        self.reset_game()

    def reset_game(self):
        self.grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        
        self.thief_pos = [1, 1]
        self.thief_prev_pos = [1, 1]
        
        self.money_pos = [GRID_SIZE // 2, GRID_SIZE // 2]
        self.exit_pos = [GRID_SIZE - 2, 1]

        self.police_positions = [
            [GRID_SIZE - 2, GRID_SIZE - 2],
            [GRID_SIZE - 2, 0]
        ]
        
        self.police_paths = [[], []]
        self.police_move_delay = 200
        self.last_police_move = 0

        self.generate_walls()
        
        self.money_collected = False
        self.game_state = PLAYING
        self.moves_count = 0
        self.interceptor_mode = "intercept"

    def generate_walls(self):
        wall_count = int(GRID_SIZE * GRID_SIZE * 0.30)
        for _ in range(wall_count):
            x = random.randint(1, GRID_SIZE - 2)
            y = random.randint(1, GRID_SIZE - 2)
            self.grid[y][x] = 1

        positions_to_clear = [self.thief_pos, self.money_pos, self.exit_pos] + self.police_positions
        
        for pos in positions_to_clear:
            cx, cy = pos
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < GRID_SIZE and 0 <= nx < GRID_SIZE:
                        self.grid[ny][nx] = 0

    def manhattan_distance(self, pos1, pos2):
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def get_neighbors(self, pos):
        neighbors = []
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        
        for dx, dy in directions:
            nx, ny = pos[0] + dx, pos[1] + dy
            if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                if self.grid[ny][nx] == 0:
                    neighbors.append([nx, ny])
        return neighbors

    def a_star(self, start, goal, cost_grid=None):
        if cost_grid is None:
            cost_grid = [[1 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

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

    def handle_player_input(self):
        """Handle keyboard input for player movement"""
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
            # Check if move is valid
            if (0 <= new_pos[0] < GRID_SIZE and 
                0 <= new_pos[1] < GRID_SIZE and 
                self.grid[new_pos[1]][new_pos[0]] == 0):
                
                self.thief_prev_pos = list(self.thief_pos)
                self.thief_pos = new_pos
                self.last_move_time = current_time
                self.moves_count += 1
                
                # Check objectives
                if self.thief_pos == self.money_pos and not self.money_collected:
                    self.money_collected = True
                
                if self.thief_pos == self.exit_pos and self.money_collected:
                    self.game_state = THIEF_WIN

    def get_intercept_target(self):
        """
        Prediksi posisi thief 5 langkah ke depan berdasarkan vektor geraknya.
        Hanya digunakan jika thief cukup jauh dari interceptor.
        """
        dx = self.thief_pos[0] - self.thief_prev_pos[0]
        dy = self.thief_pos[1] - self.thief_prev_pos[1]
        
        prediction_step = 5
        
        for step in range(prediction_step, 0, -1):
            tx = self.thief_pos[0] + (dx * step)
            ty = self.thief_pos[1] + (dy * step)
            
            if 0 <= tx < GRID_SIZE and 0 <= ty < GRID_SIZE:
                if self.grid[int(ty)][int(tx)] == 0:
                    return [int(tx), int(ty)]
        
        return self.thief_pos

    def update_police(self):
        if self.game_state != PLAYING or not self.money_collected:
            return
        
        current_time = pygame.time.get_ticks()
        if current_time - self.last_police_move < self.police_move_delay:
            return
        
        self.last_police_move = current_time

        # ==========================================
        # POLISI 1 (CHASER) - Selalu kejar langsung
        # ==========================================
        path_0 = self.a_star(self.police_positions[0], self.thief_pos)
        self.police_paths[0] = path_0
        
        if path_0:
            self.police_positions[0] = path_0.pop(0)
        else:
            neighbors = self.get_neighbors(self.police_positions[0])
            if neighbors:
                self.police_positions[0] = random.choice(neighbors)

        # ==========================================
        # POLISI 2 (INTERCEPTOR) - Mode Dinamis
        # ==========================================
        
        # Hitung jarak Manhattan ke thief
        distance_to_thief = self.manhattan_distance(self.police_positions[1], self.thief_pos)
        
        # LOGIKA SWITCH MODE:
        # - Jika jarak <= THRESHOLD (5 langkah): Mode CHASE (kejar langsung)
        # - Jika jarak > THRESHOLD: Mode INTERCEPT (prediksi 5 langkah ke depan)
        
        if distance_to_thief <= INTERCEPT_DISTANCE_THRESHOLD:
            # MODE CHASE: Terlalu dekat, kejar langsung untuk menghindari bug mundur
            self.interceptor_mode = "chase"
            target_pos = self.thief_pos
        else:
            # MODE INTERCEPT: Cukup jauh, gunakan prediksi
            self.interceptor_mode = "intercept"
            target_pos = self.get_intercept_target()
        
        path_1 = self.a_star(self.police_positions[1], target_pos)
        self.police_paths[1] = path_1

        if path_1:
            self.police_positions[1] = path_1.pop(0)
        else:
            # Fallback jika tidak ada path ke target
            path_fallback = self.a_star(self.police_positions[1], self.thief_pos)
            if path_fallback:
                self.police_positions[1] = path_fallback.pop(0)
            else:
                neighbors = self.get_neighbors(self.police_positions[1])
                if neighbors:
                    self.police_positions[1] = random.choice(neighbors)

        # Check capture
        for p_pos in self.police_positions:
            if p_pos == self.thief_pos:
                self.game_state = POLICE_WIN

    def draw(self):
        self.screen.fill(WHITE)

        # Draw map
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                if self.grid[y][x] == 1:
                    self.screen.blit(self.assets.assets['wall'], (x * CELL_SIZE, y * CELL_SIZE))
                else:
                    self.screen.blit(self.assets.assets['floor'], (x * CELL_SIZE, y * CELL_SIZE))

        # Draw police paths (only when money collected)
        if self.money_collected:
            for pos in self.police_paths[0][:5]:  # Show only next 5 steps
                rect = pygame.Rect(pos[0]*CELL_SIZE+10, pos[1]*CELL_SIZE+10, CELL_SIZE-20, CELL_SIZE-20)
                s = pygame.Surface((CELL_SIZE-20, CELL_SIZE-20), pygame.SRCALPHA)
                s.fill((255, 200, 200, 100))
                self.screen.blit(s, rect)

            for pos in self.police_paths[1][:5]:
                rect = pygame.Rect(pos[0]*CELL_SIZE+10, pos[1]*CELL_SIZE+10, CELL_SIZE-20, CELL_SIZE-20)
                s = pygame.Surface((CELL_SIZE-20, CELL_SIZE-20), pygame.SRCALPHA)
                s.fill((200, 100, 100, 100))
                self.screen.blit(s, rect)

        # Draw objects
        self.screen.blit(self.assets.assets['exit'], 
                        (self.exit_pos[0]*CELL_SIZE, self.exit_pos[1]*CELL_SIZE))
        
        if not self.money_collected:
            self.screen.blit(self.assets.assets['money'], 
                            (self.money_pos[0]*CELL_SIZE, self.money_pos[1]*CELL_SIZE))

        # Draw characters
        self.screen.blit(self.assets.assets['thief'], 
                        (self.thief_pos[0]*CELL_SIZE, self.thief_pos[1]*CELL_SIZE))
        
        if self.money_collected:
            self.screen.blit(self.assets.assets['police1'], 
                            (self.police_positions[0][0]*CELL_SIZE, self.police_positions[0][1]*CELL_SIZE))
            self.screen.blit(self.assets.assets['police2'], 
                            (self.police_positions[1][0]*CELL_SIZE, self.police_positions[1][1]*CELL_SIZE))

        # UI Text
        status = "Steal the Diamond! (Arrow Keys/WASD)" if not self.money_collected else "ESCAPE! Police are chasing you!"
        color = ORANGE if not self.money_collected else RED
        text = self.font.render(status, True, color)
        
        # Text background
        bg = pygame.Surface((text.get_width() + 10, text.get_height() + 5))
        bg.fill(WHITE)
        bg.set_alpha(200)
        self.screen.blit(bg, (5, 5))
        self.screen.blit(text, (10, 5))

        # Move counter
        moves_text = self.small_font.render(f"Moves: {self.moves_count}", True, BLACK)
        bg2 = pygame.Surface((moves_text.get_width() + 10, moves_text.get_height() + 5))
        bg2.fill(WHITE)
        bg2.set_alpha(200)
        self.screen.blit(bg2, (5, 45))
        self.screen.blit(moves_text, (10, 47))

        if self.money_collected:
            # Display police roles dan mode interceptor
            mode_text = f"Chaser | Interceptor ({self.interceptor_mode.upper()})"
            role_text = self.small_font.render(mode_text, True, BLACK)
            bg3 = pygame.Surface((role_text.get_width() + 10, role_text.get_height() + 5))
            bg3.fill(WHITE)
            bg3.set_alpha(200)
            self.screen.blit(bg3, (5, 75))
            self.screen.blit(role_text, (10, 77))

        # End screen
        if self.game_state != PLAYING:
            overlay = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE))
            overlay.fill(BLACK)
            overlay.set_alpha(150)
            self.screen.blit(overlay, (0, 0))
            
            msg = "YOU ESCAPED!" if self.game_state == THIEF_WIN else "CAUGHT!"
            score_msg = f"Moves: {self.moves_count}"
            
            color = GREEN if self.game_state == THIEF_WIN else RED
            text = self.font.render(msg, True, color)
            score = self.small_font.render(score_msg, True, WHITE)
            restart = self.small_font.render("Press R to Restart | Q to Quit", True, WHITE)
            
            center_x, center_y = WINDOW_SIZE // 2, WINDOW_SIZE // 2
            
            self.screen.blit(text, (center_x - text.get_width()//2, center_y - 40))
            self.screen.blit(score, (center_x - score.get_width()//2, center_y + 10))
            self.screen.blit(restart, (center_x - restart.get_width()//2, center_y + 40))

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.reset_game()
                    elif event.key == pygame.K_q:
                        running = False

            # Update
            self.handle_player_input()
            
            # Check if caught
            if self.thief_pos in self.police_positions:
                self.game_state = POLICE_WIN
            
            self.update_police()

            # Render
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()

if __name__ == "__main__":
    Game().run()