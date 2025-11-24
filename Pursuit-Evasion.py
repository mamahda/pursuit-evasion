import pygame
import heapq
import random

# Inisialisasi library Pygame
pygame.init()

# --- KONSTANTA (PENGATURAN STYLE LAMA) ---
GRID_SIZE = 20       # Jumlah kotak (20x20)
CELL_SIZE = 50       # Ukuran per kotak (Sesuai kode terakhir Anda)
WINDOW_SIZE = GRID_SIZE * CELL_SIZE
FPS = 5              # Kecepatan game

# --- DEFINISI WARNA (RGB) ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)       # Tembok
RED = (255, 0, 0)       # Polisi
BLUE = (0, 100, 255)    # Pencuri
GREEN = (0, 255, 0)     # Pintu Keluar
YELLOW = (255, 255, 0)  # Uang
GRAY = (100, 100, 100)  # Garis Grid
ORANGE = (255, 165, 0)  # Status teks

# --- STATUS PERMAINAN ---
PLAYING = 0
THIEF_WIN = 1
POLICE_WIN = 2

class Node:
    def __init__(self, pos, g=0, h=0, parent=None):
        self.pos = pos
        self.g = g
        self.h = h
        self.f = g + h
        self.parent = parent

    def __lt__(self, other):
        return self.f < other.f

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
        pygame.display.set_caption("Smart Thief - Logic: Wait & Avoid")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.reset_game()

    def reset_game(self):
        # 1. Reset Grid
        self.grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        
        # 2. Set Posisi
        self.thief_pos = [1, 1]
        self.police_pos = [GRID_SIZE - 2, 1]
        self.money_pos = [GRID_SIZE // 2, GRID_SIZE // 2]
        self.exit_pos = [GRID_SIZE - 2, 1] # Exit di pojok kanan atas (dekat spawn polisi)

        # 3. Generate Walls
        self.generate_walls()

        # 4. Status
        self.money_collected = False
        self.game_state = PLAYING
        self.is_retreating = False # (Variable ini hanya untuk status text, logicnya sudah di A*)
        
        self.thief_path = []
        self.police_path = []

    def generate_walls(self):
        wall_count = int(GRID_SIZE * GRID_SIZE * 0.30) # 30% Tembok
        for _ in range(wall_count):
            x = random.randint(1, GRID_SIZE - 2)
            y = random.randint(1, GRID_SIZE - 2)
            self.grid[y][x] = 1

        # Bersihkan area spawn
        for pos in [self.thief_pos, self.police_pos, self.money_pos, self.exit_pos]:
            cx, cy = pos
            for dy in range(-1, 2):
                for dx in range(-1, 2):
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

                # --- LOGIKA COST DINAMIS ---
                # A* akan menghindari node dengan move_cost tinggi
                move_cost = cost_grid[neighbor[1]][neighbor[0]]
                tentative_g = current.g + move_cost

                if neighbor_tuple not in g_scores or tentative_g < g_scores[neighbor_tuple]:
                    g_scores[neighbor_tuple] = tentative_g
                    h = self.manhattan_distance(neighbor, goal)
                    neighbor_node = Node(neighbor_tuple, tentative_g, h, current)
                    heapq.heappush(open_list, neighbor_node)

        return []

    def create_safety_map(self):
        """
        LOGIKA RETREAT OTOMATIS:
        Membuat peta bobot di mana area dekat polisi memiliki biaya sangat mahal.
        Semakin dekat (radius mengecil) -> Biaya makin besar.
        """
        cost_grid = [[1 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

        # Tembok = Infinity
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                if self.grid[y][x] == 1:
                    cost_grid[y][x] = float('inf')

        # Jika uang belum diambil, polisi dianggap tembok diam (agar tidak ditabrak)
        if not self.money_collected:
            px, py = self.police_pos
            cost_grid[py][px] = float('inf')
            return cost_grid

        # --- LOGIKA BOBOT GRADASI ---
        # Area sekitar polisi diberi bobot tinggi
        danger_radius = 6
        base_danger_cost = 50 
        multiplier = 100

        for dy in range(-danger_radius, danger_radius + 1):
            for dx in range(-danger_radius, danger_radius + 1):
                py = self.police_pos[1] + dy
                px = self.police_pos[0] + dx
                
                if 0 <= py < GRID_SIZE and 0 <= px < GRID_SIZE:
                    if self.grid[py][px] == 0:
                        distance = abs(dx) + abs(dy)
                        
                        if distance <= danger_radius:
                            # FORMULA: Semakin dekat jaraknya, semakin besar cost tambahannya
                            # (danger_radius - distance) akan besar jika distance kecil
                            added_cost = (danger_radius - distance) ** 2 * multiplier
                            cost_grid[py][px] = base_danger_cost + added_cost

        return cost_grid

    def update_thief(self):
        if self.game_state != PLAYING:
            return

        # 1. Tentukan Target
        target = self.money_pos if not self.money_collected else self.exit_pos

        # 2. Buat Peta Bobot (Ini yang bikin pencuri menghindari polisi)
        cost_grid = self.create_safety_map()

        # 3. Cari Jalan (Weighted A*)
        self.thief_path = self.a_star(self.thief_pos, target, cost_grid)

        # 4. Gerak
        if self.thief_path:
            self.thief_pos = self.thief_path.pop(0)

        # Logic Game Loop
        if self.thief_pos == self.money_pos and not self.money_collected:
            self.money_collected = True
        
        if self.thief_pos == self.exit_pos and self.money_collected:
            self.game_state = THIEF_WIN

    def update_police(self):
        if self.game_state != PLAYING:
            return

        # --- LOGIKA BARU: POLISI DIAM JIKA UANG BELUM DIAMBIL ---
        if not self.money_collected:
            return 
        
        # Polisi mengejar (A* Biasa, dia tidak peduli safety map)
        self.police_path = self.a_star(self.police_pos, self.thief_pos)

        if self.police_path:
            self.police_pos = self.police_path.pop(0)

        if self.police_pos == self.thief_pos:
            self.game_state = POLICE_WIN

    def draw(self):
        self.screen.fill(WHITE) # Layar Putih

        # --- STYLE GRID LAMA (RESTORED) ---
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)

                if self.grid[y][x] == 1:
                    pygame.draw.rect(self.screen, BLACK, rect) # Tembok Hitam Full
                else:
                    pygame.draw.rect(self.screen, GRAY, rect, 1) # Jalan Garis Abu (Outline)

        # Visualisasi Path (Kotak kecil di dalam cell)
        for pos in self.thief_path:
            rect = pygame.Rect(pos[0] * CELL_SIZE + 5, pos[1] * CELL_SIZE + 5, 
                               CELL_SIZE - 10, CELL_SIZE - 10)
            pygame.draw.rect(self.screen, (173, 216, 230), rect) # Biru Muda

        for pos in self.police_path:
            rect = pygame.Rect(pos[0] * CELL_SIZE + 5, pos[1] * CELL_SIZE + 5,
                               CELL_SIZE - 10, CELL_SIZE - 10)
            pygame.draw.rect(self.screen, (255, 200, 200), rect) # Merah Muda

        # Gambar Exit (Hijau)
        exit_rect = pygame.Rect(self.exit_pos[0] * CELL_SIZE, self.exit_pos[1] * CELL_SIZE,
                                CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(self.screen, GREEN, exit_rect)

        # Gambar Uang (Kuning)
        if not self.money_collected:
            money_rect = pygame.Rect(self.money_pos[0] * CELL_SIZE, self.money_pos[1] * CELL_SIZE,
                                     CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(self.screen, YELLOW, money_rect)

        # Gambar Karakter (Lingkaran)
        thief_center = (self.thief_pos[0] * CELL_SIZE + CELL_SIZE // 2,
                        self.thief_pos[1] * CELL_SIZE + CELL_SIZE // 2)
        pygame.draw.circle(self.screen, BLUE, thief_center, CELL_SIZE // 3)

        police_center = (self.police_pos[0] * CELL_SIZE + CELL_SIZE // 2,
                         self.police_pos[1] * CELL_SIZE + CELL_SIZE // 2)
        pygame.draw.circle(self.screen, RED, police_center, CELL_SIZE // 3)

        # Info Jarak
        distance = self.manhattan_distance(self.thief_pos, self.police_pos)
        distance_text = self.font.render(f"Jarak: {distance}", True, BLACK)
        self.screen.blit(distance_text, (10, 10))

        # Status Teks
        status = "AMBIL UANG (Polisi Diam)" if not self.money_collected else "LARI!! (Polisi Kejar)"
        color = ORANGE if not self.money_collected else RED
        status_text = self.font.render(status, True, color)
        self.screen.blit(status_text, (10, 40))

        # Game Over Message
        if self.game_state == THIEF_WIN:
            text = self.font.render("PENCURI MENANG! (Tekan R)", True, BLUE)
            text_bg = pygame.Surface((text.get_width()+10, text.get_height()+10))
            text_bg.fill(WHITE)
            self.screen.blit(text_bg, (WINDOW_SIZE//2 - text.get_width()//2 - 5, WINDOW_SIZE//2 - text.get_height()//2 - 5))
            self.screen.blit(text, (WINDOW_SIZE//2 - text.get_width()//2, WINDOW_SIZE//2 - text.get_height()//2))
        elif self.game_state == POLICE_WIN:
            text = self.font.render("TERTANGKAP! (Tekan R)", True, RED)
            text_bg = pygame.Surface((text.get_width()+10, text.get_height()+10))
            text_bg.fill(WHITE)
            self.screen.blit(text_bg, (WINDOW_SIZE//2 - text.get_width()//2 - 5, WINDOW_SIZE//2 - text.get_height()//2 - 5))
            self.screen.blit(text, (WINDOW_SIZE//2 - text.get_width()//2, WINDOW_SIZE//2 - text.get_height()//2))

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
                    elif event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                        running = False

            self.update_thief()
            self.update_police()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()

if __name__ == "__main__":
    Game().run()

