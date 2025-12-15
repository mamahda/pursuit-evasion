import pygame
import heapq
import random
import urllib.request
import os

pygame.init()
try:
    pygame.mixer.init()
except Exception:
    print("[WARNING] pygame.mixer failed to initialize; sound disabled.")

# ==============================================================================
# CONSTANTS
# ==============================================================================
GRID_SIZE = 17
CELL_SIZE = 43
WINDOW_SIZE = GRID_SIZE * CELL_SIZE
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)

# Game States
MENU, PLAYING, THIEF_WIN, POLICE_WIN = -1, 0, 1, 2

# Game Settings
INTERCEPT_DISTANCE = 5
MOVE_DELAY = 150

LEVEL_CONFIG = {
    1: {"walls": 0.25, "police_speed": 300, "name": "Easy"},
    2: {"walls": 0.30, "police_speed": 200, "name": "Normal"},
    3: {"walls": 0.35, "police_speed": 180, "name": "Hard"},
    4: {"walls": 0.35, "police_speed": 150, "name": "Expert"},
    5: {"walls": 0.40, "police_speed": 120, "name": "Impossible"},
}

# ==============================================================================
# ASSET LOADER
# ==============================================================================
class AssetLoader:
    def __init__(self):
        self.assets = {}
        self.asset_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        os.makedirs(self.asset_dir, exist_ok=True)
        self.load_assets()
    
    def load_assets(self):
        """Load all game assets"""
        self.assets['thief'] = self.load_or_create('thief.png', (255, 0, 255))
        self.assets['police1'] = self.load_or_create('police1.png', (0, 0, 255))
        self.assets['police2'] = self.load_or_create('police2.png', (0, 100, 255))
        self.assets['money'] = self.load_or_create('money.png', (255, 215, 0))
        self.assets['exit'] = self.create_exit_sprite()
        self.assets['wall'] = self.create_wall_sprite()
        self.assets['floor'] = self.create_floor_sprite()
        # Load running sound (played when thief is chased)
        self.assets['running'] = self.load_sound('running.mp3')
        # Load before sound (played before money is collected)
        self.assets['before'] = self.load_sound('before.mp3')
        # Load win sound (played when thief escapes)
        self.assets['win'] = self.load_sound('win.mp3')
        # Load lose sound (played when thief is caught)
        self.assets['lose'] = self.load_sound('lose.mp3')
    
    def load_or_create(self, filename, fallback_color):
        """Load image or create colored square as fallback"""
        filepath = os.path.join(self.asset_dir, filename)
        try:
            img = pygame.image.load(filepath)
            return pygame.transform.scale(img, (CELL_SIZE, CELL_SIZE))
        except:
            surf = pygame.Surface((CELL_SIZE, CELL_SIZE))
            surf.fill(fallback_color)
            return surf
    
    def create_exit_sprite(self):
        surf = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
        pygame.draw.rect(surf, (101, 67, 33), (5, 0, CELL_SIZE - 10, CELL_SIZE))
        pygame.draw.rect(surf, (70, 130, 70), (8, 3, CELL_SIZE - 16, CELL_SIZE - 6))
        pygame.draw.circle(surf, YELLOW, (CELL_SIZE - 15, CELL_SIZE // 2), 4)
        return surf

    def load_sound(self, filename):
        filepath = os.path.join(self.asset_dir, filename)
        try:
            sound = pygame.mixer.Sound(filepath)
            return sound
        except Exception as e:
            print(f"[WARNING] Sound {filename} failed to load: {e}")
            return None
    
    def create_wall_sprite(self):
        surf = pygame.Surface((CELL_SIZE, CELL_SIZE))
        surf.fill((90, 90, 90))
        for y in range(0, CELL_SIZE, 15):
            offset = 0 if (y // 15) % 2 == 0 else 20
            for x in range(-20 + offset, CELL_SIZE, 40):
                pygame.draw.rect(surf, (60, 60, 60), (x, y, 38, 13))
        return surf
    
    def create_floor_sprite(self):
        surf = pygame.Surface((CELL_SIZE, CELL_SIZE))
        surf.fill((200, 200, 200))
        pygame.draw.rect(surf, (180, 180, 180), (0, 0, CELL_SIZE//2, CELL_SIZE//2))
        pygame.draw.rect(surf, (180, 180, 180), (CELL_SIZE//2, CELL_SIZE//2, CELL_SIZE//2, CELL_SIZE//2))
        return surf

# ==============================================================================
# A* NODE
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
# GAME
# ==============================================================================
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
        pygame.display.set_caption("Museum Heist - Escape the Police!")
        self.clock = pygame.time.Clock()
        
        # Load fonts
        font_path = "./assets/upheavtt.ttf"
        try:
            self.title_font = pygame.font.Font(font_path, 64)
            self.subtitle_font = pygame.font.Font(None, 32)
            self.font = pygame.font.Font(None, 24)
        except:
            print(f"[WARNING] Custom font {font_path} failed. Using default.")
            self.title_font = pygame.font.Font(None, 64)
            self.subtitle_font = pygame.font.Font(None, 32)
            self.font = pygame.font.Font(None, 24)
        
        self.assets = AssetLoader()
        self.game_state = MENU
        self.selected_level = 1
        self.reset_timers()

    def reset_timers(self):
        """Reset all timing variables"""
        self.last_move_time = 0
        self.last_police_move = 0
        self.start_time = 0
        self.elapsed_time = 0
        self.timer_started = False
        self.running_sound_playing = False
        self.before_sound_playing = False
        self.win_sound_playing = False
        self.lose_sound_playing = False

    def play_running_sound(self):
        """Play the running sound in loop when chase starts"""
        sound = None
        try:
            sound = self.assets.assets.get('running')
        except Exception:
            return
        if sound and not getattr(self, 'running_sound_playing', False):
            try:
                sound.set_volume(0.5)
                sound.play(-1)
                self.running_sound_playing = True
            except Exception:
                pass

    def stop_running_sound(self):
        """Stop the running sound"""
        try:
            sound = self.assets.assets.get('running')
        except Exception:
            sound = None
        if sound:
            try:
                sound.stop()
            except Exception:
                pass
        self.running_sound_playing = False

    def play_before_sound(self):
        """Play the before sound in loop before money is collected"""
        sound = None
        try:
            sound = self.assets.assets.get('before')
        except Exception:
            return
        if sound and not getattr(self, 'before_sound_playing', False):
            try:
                sound.play(-1)
                self.before_sound_playing = True
            except Exception:
                pass

    def stop_before_sound(self):
        """Stop the before sound"""
        try:
            sound = self.assets.assets.get('before')
        except Exception:
            sound = None
        if sound:
            try:
                sound.stop()
            except Exception:
                pass
        self.before_sound_playing = False

    def play_win_sound(self):
        """Play the win sound when thief escapes"""
        sound = None
        try:
            sound = self.assets.assets.get('win')
        except Exception:
            return
        if sound and not getattr(self, 'win_sound_playing', False):
            try:
                sound.play(0)
                self.win_sound_playing = True
            except Exception:
                pass

    def stop_win_sound(self):
        """Stop the win sound"""
        try:
            sound = self.assets.assets.get('win')
        except Exception:
            sound = None
        if sound:
            try:
                sound.stop()
            except Exception:
                pass
        self.win_sound_playing = False

    def play_lose_sound(self):
        """Play the lose sound when thief is caught"""
        sound = None
        try:
            sound = self.assets.assets.get('lose')
        except Exception:
            return
        if sound and not getattr(self, 'lose_sound_playing', False):
            try:
                sound.play(0)
                self.lose_sound_playing = True
            except Exception:
                pass

    def stop_lose_sound(self):
        """Stop the lose sound"""
        try:
            sound = self.assets.assets.get('lose')
        except Exception:
            sound = None
        if sound:
            try:
                sound.stop()
            except Exception:
                pass
        self.lose_sound_playing = False

    def get_random_position(self, exclude=[], min_distance=1):
        """
        Get random free position on grid, ensuring it has a Manhattan distance 
        greater than or equal to min_distance from all positions in the exclude list.
        """
        # Meningkatkan iterasi untuk peluang yang lebih baik
        for _ in range(10000): 
            x, y = random.randint(1, GRID_SIZE - 2), random.randint(1, GRID_SIZE - 2)
            current_pos = [x, y]
            
            # Pengecekan 1: Pastikan bukan dinding
            if self.grid[y][x] == 0:
                # Pengecekan 2: Pastikan jarak Manhattan >= min_distance dari SEMUA excluded_pos
                is_far_enough = all(self.manhattan_distance(current_pos, pos) >= min_distance 
                                    for pos in exclude)
                
                if is_far_enough:
                    return current_pos
                    
        # Fallback: Jika gagal, kembalikan posisi tengah (berisiko melanggar jarak minimum)
        return [GRID_SIZE // 2, GRID_SIZE // 2]

    def clear_area(self, positions):
        """Clear walls around important positions"""
        for pos in positions:
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    ny, nx = pos[1] + dy, pos[0] + dx
                    if 0 <= ny < GRID_SIZE and 0 <= nx < GRID_SIZE:
                        self.grid[ny][nx] = 0

    def reset_game(self):
        """Initialize new game"""
        self.current_level = self.selected_level
        config = LEVEL_CONFIG[self.current_level]
        # ensure any sounds are stopped when starting/resetting
        try:
            self.stop_running_sound()
            self.stop_before_sound()
        except Exception:
            pass
        
        # start before sound for pre-heist phase
        try:
            self.play_before_sound()
        except Exception:
            pass
        
        # Create grid with walls
        self.grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
        wall_count = int(GRID_SIZE * GRID_SIZE * config["walls"])
        for _ in range(wall_count):
            self.grid[random.randint(1, GRID_SIZE-2)][random.randint(1, GRID_SIZE-2)] = 1
        
        # Place game elements
        self.money_pos = self.get_random_position()
        self.exit_pos = self.get_random_position([self.money_pos], min_distance=10)
        self.thief_pos = list(self.exit_pos)
        self.thief_prev_pos = list(self.exit_pos)
        self.police_positions = [
            self.get_random_position([self.money_pos, self.exit_pos], min_distance=5),
            self.get_random_position([self.money_pos, self.exit_pos], min_distance=5)
        ]
        
        self.clear_area([self.thief_pos, self.money_pos, self.exit_pos] + self.police_positions)
        
        # Game state
        self.police_paths = [[], []]
        self.police_move_delay = config["police_speed"]
        self.money_collected = False
        self.interceptor_mode = "intercept"
        self.game_state = PLAYING
        self.reset_timers()

    def manhattan_distance(self, pos1, pos2):
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def get_neighbors(self, pos):
        """Get valid neighboring cells"""
        neighbors = []
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nx, ny = pos[0] + dx, pos[1] + dy
            if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE and self.grid[ny][nx] == 0:
                neighbors.append([nx, ny])
        return neighbors

    def a_star(self, start, goal):
        """A* pathfinding algorithm"""
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

                tentative_g = current.g + 1
                if neighbor_tuple not in g_scores or tentative_g < g_scores[neighbor_tuple]:
                    g_scores[neighbor_tuple] = tentative_g
                    h = self.manhattan_distance(neighbor, goal)
                    heapq.heappush(open_list, Node(neighbor_tuple, tentative_g, h, current))

        return []

    def get_intercept_target(self):
        """Predict thief's future position"""
        dx = self.thief_pos[0] - self.thief_prev_pos[0]
        dy = self.thief_pos[1] - self.thief_prev_pos[1]
        
        for step in range(5, 0, -1):
            tx, ty = self.thief_pos[0] + dx * step, self.thief_pos[1] + dy * step
            if 0 <= tx < GRID_SIZE and 0 <= ty < GRID_SIZE and self.grid[ty][tx] == 0:
                return [tx, ty]
        return self.thief_pos

    def evaluate_position(self, police_pos, thief_pos, depth):
        """Evaluate position score for minimax (lower is better for police)"""
        distance = self.manhattan_distance(police_pos, thief_pos)
        # Closer distance = higher score (better for police)
        return -distance + depth * 2

    def minimax(self, police_pos, thief_pos, depth, is_maximizing):
        """Minimax algorithm to evaluate best police move
        Maximizing: thief tries to maximize distance
        Minimizing: police tries to minimize distance
        """
        if depth == 0:
            return self.evaluate_position(police_pos, thief_pos, depth), police_pos
        
        if is_maximizing:  # Thief's turn (worst case for police)
            max_eval = float('-inf')
            best_pos = police_pos
            for neighbor in self.get_neighbors(thief_pos):
                eval_score, _ = self.minimax(police_pos, neighbor, depth - 1, False)
                if eval_score > max_eval:
                    max_eval = eval_score
                    best_pos = neighbor
            return max_eval, best_pos
        else:  # Police's turn (best case for police)
            min_eval = float('inf')
            best_pos = police_pos
            for neighbor in self.get_neighbors(police_pos):
                eval_score, _ = self.minimax(neighbor, thief_pos, depth - 1, True)
                if eval_score < min_eval:
                    min_eval = eval_score
                    best_pos = neighbor
            return min_eval, best_pos

    def get_best_police_move(self, police_pos, thief_pos, depth=2):
        """Get best move for police using minimax"""
        _, best_target = self.minimax(police_pos, thief_pos, depth, False)
        return best_target if best_target != police_pos else None

    def handle_input(self):
        """Handle keyboard input based on game state"""
        keys = pygame.key.get_pressed()
        current_time = pygame.time.get_ticks()
        
        if self.game_state == MENU:
            if current_time - self.last_move_time < 150:
                return
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                self.selected_level = max(1, self.selected_level - 1)
                self.last_move_time = current_time
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.selected_level = min(len(LEVEL_CONFIG), self.selected_level + 1)
                self.last_move_time = current_time
        
        elif self.game_state == PLAYING:
            if current_time - self.last_move_time < MOVE_DELAY:
                return
            
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
            
            if moved and 0 <= new_pos[0] < GRID_SIZE and 0 <= new_pos[1] < GRID_SIZE:
                if self.grid[new_pos[1]][new_pos[0]] == 0:
                    if not self.timer_started:
                        self.timer_started = True
                        self.start_time = current_time
                    
                    self.thief_prev_pos = list(self.thief_pos)
                    self.thief_pos = new_pos
                    self.last_move_time = current_time
                    
                    # Check money collection
                    if self.thief_pos == self.money_pos:
                        self.money_collected = True
                        # stop before sound and start running sound when thief takes the money
                        try:
                            self.stop_before_sound()
                            self.play_running_sound()
                        except Exception:
                            pass
                    
                    # Check win condition
                    if self.thief_pos == self.exit_pos and self.money_collected:
                        self.game_state = THIEF_WIN
                        self.elapsed_time = (current_time - self.start_time) / 1000.0
                        try:
                            self.stop_running_sound()
                            self.stop_before_sound()
                            self.play_win_sound()
                        except Exception:
                            pass

    def update_police(self):
        """Update police positions"""
        if self.game_state != PLAYING or not self.money_collected:
            return
        
        current_time = pygame.time.get_ticks()
        if current_time - self.last_police_move < self.police_move_delay:
            return
        
        self.last_police_move = current_time

        # Police 1: Direct chaser
        path = self.a_star(self.police_positions[0], self.thief_pos)
        self.police_paths[0] = path
        if path:
            self.police_positions[0] = path[0]

        # Police 2: Interceptor
        distance = self.manhattan_distance(self.police_positions[1], self.thief_pos)
        self.interceptor_mode = "chase" if distance <= INTERCEPT_DISTANCE else "intercept"
        target = self.thief_pos if self.interceptor_mode == "chase" else self.get_intercept_target()
        
        path = self.a_star(self.police_positions[1], target)
        self.police_paths[1] = path
        if path:
            self.police_positions[1] = path[0]

        # Check capture
        if self.thief_pos in self.police_positions:
            self.game_state = POLICE_WIN
            self.elapsed_time = (current_time - self.start_time) / 1000.0
            try:
                self.stop_running_sound()
                self.stop_before_sound()
                self.play_lose_sound()
            except Exception:
                pass

    def draw_menu(self):
        """Draw menu screen"""
        # Draw gradient background
        for y in range(WINDOW_SIZE):
            t = y / WINDOW_SIZE
            r = int(10 * (1 - t) + 30 * t)
            g = int(10 * (1 - t) + 30 * t)
            b = int(50 * (1 - t) + 100 * t)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (WINDOW_SIZE, y))
        
        title = self.title_font.render("MUSEUM HEIST", True, RED)
        self.screen.blit(title, (WINDOW_SIZE//2 - title.get_width()//2, 40))
        
        subtitle = self.subtitle_font.render("Pilih Level:", True, WHITE)
        self.screen.blit(subtitle, (WINDOW_SIZE//2 - subtitle.get_width()//2, 150))
        
        y = 200
        for level, config in LEVEL_CONFIG.items():
            color = ORANGE if level == self.selected_level else WHITE
            text = self.font.render(f"Level {level}: {config['name']}", True, color)
            self.screen.blit(text, (200, y))
            if level == self.selected_level:
                pygame.draw.circle(self.screen, color, (180, y + 12), 5)
            y += 40
        
        info = self.font.render("ENTER to Start", True, (150, 150, 150))
        self.screen.blit(info, (WINDOW_SIZE//2 - info.get_width()//2, WINDOW_SIZE - 60))

    def draw_game(self):
        """Draw game screen"""
        self.screen.fill(WHITE)

        # Draw grid
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                sprite = self.assets.assets['wall'] if self.grid[y][x] == 1 else self.assets.assets['floor']
                self.screen.blit(sprite, (x * CELL_SIZE, y * CELL_SIZE))

        # Draw police paths
        if self.money_collected:
            for i, path in enumerate(self.police_paths):
                alpha = 100 if i == 0 else 80
                color = (255, 200, 200, alpha) if i == 0 else (200, 100, 100, alpha)
                for pos in path[:5]:
                    s = pygame.Surface((CELL_SIZE-20, CELL_SIZE-20), pygame.SRCALPHA)
                    s.fill(color)
                    self.screen.blit(s, (pos[0]*CELL_SIZE+10, pos[1]*CELL_SIZE+10))

        # Draw game elements
        self.screen.blit(self.assets.assets['exit'], (self.exit_pos[0]*CELL_SIZE, self.exit_pos[1]*CELL_SIZE))
        if not self.money_collected:
            self.screen.blit(self.assets.assets['money'], (self.money_pos[0]*CELL_SIZE, self.money_pos[1]*CELL_SIZE))
        self.screen.blit(self.assets.assets['thief'], (self.thief_pos[0]*CELL_SIZE, self.thief_pos[1]*CELL_SIZE))
        self.screen.blit(self.assets.assets['police1'], (self.police_positions[0][0]*CELL_SIZE, self.police_positions[0][1]*CELL_SIZE))
        self.screen.blit(self.assets.assets['police2'], (self.police_positions[1][0]*CELL_SIZE, self.police_positions[1][1]*CELL_SIZE))

        # Draw HUD
        status = "Steal the Diamond!" if not self.money_collected else "ESCAPE! Police chasing!"
        color = ORANGE if not self.money_collected else RED
        self.draw_hud_text(status, color, 10, 5, self.subtitle_font)
        
        if self.game_state == PLAYING:
           elapsed = (pygame.time.get_ticks() - self.start_time) / 1000.0 if self.timer_started else 0
        else :
           elapsed = self.elapsed_time
        self.draw_hud_text(f"Time: {elapsed:.1f}s", BLACK, 10, 40, self.font)
        
        config = LEVEL_CONFIG[self.current_level]
        self.draw_hud_text(f"Level {self.current_level}: {config['name']}", BLACK, 10, 65, self.font)
        
        if self.money_collected:
            self.draw_hud_text(f"Chaser | Interceptor ({self.interceptor_mode.upper()})", BLACK, 10, 90, self.font)

        # Draw game over
        if self.game_state != PLAYING:
            overlay = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE))
            overlay.fill(BLACK)
            overlay.set_alpha(150)
            self.screen.blit(overlay, (0, 0))
            
            if self.game_state == THIEF_WIN:
                msg, color = "YOU ESCAPED!", GREEN
                action = "Press N for Next | R for Menu | Q to Quit" if self.current_level < len(LEVEL_CONFIG) else "Press R for Menu | Q to Quit"
            else:
                msg, color = "CAUGHT!", RED
                action = "Press R for Menu | Q to Quit"
            
            text = self.title_font.render(msg, True, color)
            score = self.subtitle_font.render(f"Time: {self.elapsed_time:.1f}s", True, WHITE)
            restart = self.font.render(action, True, WHITE)
            
            cx, cy = WINDOW_SIZE // 2, WINDOW_SIZE // 2
            self.screen.blit(text, (cx - text.get_width()//2, cy - 60))
            self.screen.blit(score, (cx - score.get_width()//2, cy+10))
            self.screen.blit(restart, (cx - restart.get_width()//2, cy + 300))

    def draw_hud_text(self, text, color, x, y, font=None):
        """Draw HUD text with background"""
        if font is None:
            font = self.font
        rendered = font.render(text, True, color)
        bg = pygame.Surface((rendered.get_width() + 10, rendered.get_height() + 5))
        bg.fill(WHITE)
        bg.set_alpha(200)
        self.screen.blit(bg, (x - 5, y))
        self.screen.blit(rendered, (x, y + 2))

    def draw(self):
        """Main draw function"""
        if self.game_state == MENU:
            self.draw_menu()
        else:
            self.draw_game()
        pygame.display.flip()

    def run(self):
        """Main game loop"""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        running = False if self.game_state == MENU else None
                        self.game_state = MENU if self.game_state != MENU else self.game_state
                    elif event.key == pygame.K_RETURN and self.game_state == MENU:
                        self.reset_game()
                    elif event.key == pygame.K_r and self.game_state != MENU:
                        self.game_state = MENU
                    elif event.key == pygame.K_n:
                        if self.game_state == THIEF_WIN and self.current_level < len(LEVEL_CONFIG):
                            self.selected_level = self.current_level + 1
                            self.reset_game()

            self.handle_input()
            self.update_police()
            # ensure sounds are stopped when returning to menu
            if self.game_state == MENU:
                try:
                    self.stop_running_sound()
                    self.stop_before_sound()
                    self.stop_win_sound()
                    self.stop_lose_sound()
                except Exception:
                    pass
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()

if __name__ == "__main__":
    Game().run()
