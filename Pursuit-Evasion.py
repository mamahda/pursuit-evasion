import pygame   # Library utama untuk grafis, input pengguna, dan manajemen window game
import heapq    # Library untuk struktur data Priority Queue untuk optimasi Algoritma A*
import random   # Library untuk pengacakan (posisi tembok, gerakan random saat stuck)

pygame.init()

# ==============================================================================
# BAGIAN 1: KONSTANTA & PENGATURAN (CONFIGURATION)
# Variabel global yang bersifat statis (tidak berubah) untuk mengatur parameter game.
# ==============================================================================

# --- Pengaturan Grid (Peta) ---
GRID_SIZE = 20       # Ukuran map (20 baris x 20 kolom).
CELL_SIZE = 50       # Ukuran visual satu kotak dalam pixel.
WINDOW_SIZE = GRID_SIZE * CELL_SIZE # Total ukuran jendela aplikasi (20 * 50 = 1000px).
FPS = 10              # Frame Per Second. Diatur sangat rendah agar pergerakan AI terlihat 
                     # patah-patah, sehingga kita bisa mengamati logika pengambilan 
                     # keputusan mereka langkah demi langkah.

# --- Definisi Warna (Format: Red, Green, Blue) ---
WHITE = (255, 255, 255) # Background
BLACK = (0, 0, 0)       # Tembok
GRAY = (100, 100, 100)  # Garis pemisah grid
RED = (255, 0, 0)       # Polisi 1 (Chaser/Pengejar)
DARK_RED = (139, 0, 0)  # Polisi 2 (Interceptor/Pencegat)
BLUE = (0, 100, 255)    # Pencuri
GREEN = (0, 255, 0)     # Exit
YELLOW = (255, 255, 0)  # Uang
ORANGE = (255, 165, 0)  # Teks Status

# --- Status Game (State Management) ---
PLAYING = 0     # status game sedang berjalan.
THIEF_WIN = 1   # status kondisi kemenangan pencuri.
POLICE_WIN = 2  # status kondisi kemenangan polisi.

# ==============================================================================
# BAGIAN 2: STRUKTUR DATA (CLASS NODE)
# Elemen fundamental untuk Algoritma A* Pathfinding.
# ==============================================================================
class Node:
    """
    Representasi dari satu 'titik' atau 'kotak' dalam peta pencarian jalur.
    Objek ini menyimpan data matematis yang dibutuhkan algoritma A* untuk menilai
    apakah jalur yang melewatinya efisien atau tidak.
    """
    def __init__(self, pos, g=0, h=0, parent=None):
        """
        Inisialisasi Node baru.
        
        Args:
            pos (tuple): Koordinat (x, y) dari node ini di grid.
            g (int): 'Cost From Start'. Jarak langkah riil dari titik Awal ke titik ini.
            h (int): 'Heuristic Cost'. Estimasi jarak dari titik ini ke titik Tujuan 
                     (biasanya menggunakan Manhattan Distance).
            parent (Node): Referensi ke Node sebelumnya yang menuntun ke node ini. 
                           Digunakan untuk melacak mundur (backtracking) jalur akhir.
        """
        self.pos = pos
        self.g = g
        self.h = h
        self.f = g + h  # F-Score = G + H. Nilai total yang menentukan prioritas node.
        self.parent = parent

    def __lt__(self, other):
        """
        Logika perbandingan (Less Than).
        Fungsi ini dipanggil otomatis oleh Priority Queue (heapq) untuk mengurutkan antrian.
        
        Logika:
        Node dengan nilai F lebih kecil dianggap 'lebih baik' dan akan diproses duluan.
        """
        return self.f < other.f

# ==============================================================================
# BAGIAN 3: LOGIKA UTAMA GAME (CLASS GAME)
# Kelas ini membungkus seluruh logika, AI, dan rendering game.
# ==============================================================================
class Game:
    def __init__(self):
        """
        Konstruktor Utama.
        Menyiapkan jendela aplikasi, font, jam sistem, dan memanggil fungsi reset 
        untuk memulai sesi permainan baru.
        """
        self.screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
        pygame.display.set_caption("Global Optimal Search: Interception & Chasing")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.reset_game()

    def reset_game(self):
        """
        Menginisialisasi ulang (Reset) seluruh variabel permainan ke kondisi awal.
        
        Tujuan:
        1. Membersihkan peta dari permainan sebelumnya.
        2. Menentukan posisi awal karakter (Pencuri di kiri atas, Polisi di kanan).
        3. Membuat tembok acak baru.
        4. Mereset status kemenangan/kekalahan.
        """
        # Array 2D merepresentasikan peta: 0 = Jalan, 1 = Tembok
        self.grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        
        # Posisi Awal
        self.thief_pos = [1, 1]
        self.thief_prev_pos = [1, 1] # Variabel untuk menghitung vektor arah gerak pencuri
        
        self.money_pos = [GRID_SIZE // 2, GRID_SIZE // 2]
        self.exit_pos = [GRID_SIZE - 2, 1]

        # Posisi Polisi
        self.police_positions = [
            [GRID_SIZE - 2, GRID_SIZE - 2], # Index 0: Chaser
            [GRID_SIZE - 2, 1]              # Index 1: Interceptor
        ]
        
        self.police_paths = [[], []] # Menyimpan jalur visualisasi polisi
        self.thief_path = []         # Menyimpan jalur visualisasi pencuri

        self.generate_walls() # Panggil fungsi pembuat tembok
        
        self.money_collected = False
        self.game_state = PLAYING

    def generate_walls(self):
        """
        Algoritma Pembangkit Level Sederhana.
        
        Logika:
        1. Mengisi 30% dari total grid dengan tembok secara acak.
        2. SAFETY CHECK: Melakukan iterasi di sekitar posisi spawn karakter (Pencuri, 
           Polisi, Uang, Exit) dan menghapus tembok di sekitarnya.
           Ini mencegah bug "Spawn Kill" di mana karakter muncul terjebak di dalam tembok.
        """
        wall_count = int(GRID_SIZE * GRID_SIZE * 0.50)
        for _ in range(wall_count):
            x = random.randint(1, GRID_SIZE - 2)
            y = random.randint(1, GRID_SIZE - 2)
            self.grid[y][x] = 1

        # Area aman (Spawn Point Cleaning)
        positions_to_clear = [self.thief_pos, self.money_pos, self.exit_pos] + self.police_positions
        
        for pos in positions_to_clear:
            cx, cy = pos
            for dy in range(-1, 2):      # Hapus area 3x3 sekitar posisi penting
                for dx in range(-1, 2):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < GRID_SIZE and 0 <= nx < GRID_SIZE:
                        self.grid[ny][nx] = 0

    def manhattan_distance(self, pos1, pos2):
        """
        Fungsi Heuristik (H-Score).
        
        Tujuan:
        Menghitung estimasi jarak terdekat antara dua titik dalam sistem Grid.
        
        Logika:
        Menggunakan |x1 - x2| + |y1 - y2| karena karakter tidak bisa bergerak diagonal,
        melainkan harus menyusuri sumbu X dan Y (seperti taksi di blok kota).
        """
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def get_neighbors(self, pos):
        """
        Mencari tetangga yang valid untuk pergerakan karakter.
        
        Logika:
        1. Cek 4 arah mata angin (Atas, Bawah, Kiri, Kanan).
        2. Validasi Batas: Pastikan koordinat tidak keluar dari window game.
        3. Validasi Tembok: Pastikan koordinat grid bernilai 0 (Bukan Tembok).
        
        Return:
            List berisi koordinat [x, y] tetangga yang bisa dilewati.
        """
        neighbors = []
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        
        for dx, dy in directions:
            nx, ny = pos[0] + dx, pos[1] + dy
            if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                if self.grid[ny][nx] == 0:
                    neighbors.append([nx, ny])
        return neighbors

    def a_star(self, start, goal, cost_grid=None):
        """
        Implementasi Algoritma Pencarian Jalur A* (A-Star).
        
        Ini adalah otak navigasi dari game ini.
        
        Fitur Khusus 'Weighted Search':
        Fungsi ini menerima parameter opsional 'cost_grid'.
        - Jika cost_grid kosong: Berjalan sebagai A* standar (Shortest Path).
        - Jika cost_grid ada: Berjalan sebagai A* Berbobot (Cheapest Path). 
          Ini digunakan Pencuri untuk menghindari zona bahaya polisi.
          
        Cara Kerja:
        1. Masukkan node awal ke Priority Queue (Open List).
        2. Loop sampai Open List kosong atau Tujuan ditemukan.
        3. Ambil node dengan biaya F terendah.
        4. Eksplorasi tetangga, hitung G (biaya jalan) dan H (jarak sisa).
        5. Jika menemukan jalur lebih efisien ke tetangga, update jalurnya.
        6. Jika sampai tujuan, lakukan Backtracking (Parent -> Parent) untuk menyusun jalur.
        """
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
                return path[::-1] # Return jalur dari Start ke Goal

            if current.pos in closed_set:
                continue
            closed_set.add(current.pos)

            for neighbor in self.get_neighbors(list(current.pos)):
                neighbor_tuple = tuple(neighbor)
                
                if neighbor_tuple in closed_set:
                    continue

                # Ambil biaya langkah dari cost_grid (default 1 atau 500 jika dekat polisi)
                move_cost = cost_grid[neighbor[1]][neighbor[0]]
                tentative_g = current.g + move_cost

                if neighbor_tuple not in g_scores or tentative_g < g_scores[neighbor_tuple]:
                    g_scores[neighbor_tuple] = tentative_g
                    h = self.manhattan_distance(neighbor, goal)
                    neighbor_node = Node(neighbor_tuple, tentative_g, h, current)
                    heapq.heappush(open_list, neighbor_node)

        return [] # Return list kosong jika tidak ada jalur (terkurung)

    def create_safety_map(self):
        """
        Membangun 'Peta Keamanan' (Heatmap) untuk AI Pencuri.
        
        Tujuan:
        Memberikan "biaya" (cost) pada setiap kotak di grid.
        - Kotak biasa = Biaya 1.
        - Kotak dekat polisi = Biaya Tinggi (Mahal).
        
        Logika Matematika:
        Menggunakan fungsi eksponensial terbalik.
        Cost = Base + (Radius - Jarak)**2 * Multiplier
        Artinya: Semakin dekat jarak ke polisi, biaya akan melonjak drastis.
        A* akan melihat ini sebagai "jalan macet parah" dan otomatis mencari jalan memutar.
        """
        cost_grid = [[1 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

        # Set tembok jadi Infinity
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                if self.grid[y][x] == 1:
                    cost_grid[y][x] = float('inf')

        if not self.money_collected:
            for p_pos in self.police_positions:
                cost_grid[p_pos[1]][p_pos[0]] = float('inf')
            return cost_grid

        danger_radius = 6
        base_danger_cost = 50
        multiplier = 100

        for police_pos in self.police_positions:
            for dy in range(-danger_radius, danger_radius + 1):
                for dx in range(-danger_radius, danger_radius + 1):
                    py = police_pos[1] + dy
                    px = police_pos[0] + dx
                    
                    if 0 <= py < GRID_SIZE and 0 <= px < GRID_SIZE:
                        if self.grid[py][px] == 0:
                            distance = abs(dx) + abs(dy)
                            if distance <= danger_radius:
                                # Hitung biaya tambahan berdasarkan kedekatan
                                added_cost = (danger_radius - distance) ** 2 * multiplier
                                # Gunakan max() untuk mengambil risiko terbesar jika area tumpang tindih
                                current_cost = cost_grid[py][px]
                                new_cost = base_danger_cost + added_cost
                                cost_grid[py][px] = max(current_cost, new_cost)

        return cost_grid

    def update_thief(self):
        """
        Mengelola Kecerdasan Buatan (AI) Pencuri.
        Dijalankan setiap frame.
        
        Langkah-langkah:
        1. Simpan posisi saat ini ke 'prev_pos' (agar polisi bisa memprediksi arah geraknya).
        2. Tentukan Tujuan: Jika belum ada uang -> Ke Uang. Jika sudah -> Ke Exit.
        3. Buat Safety Map untuk mendeteksi bahaya.
        4. Jalankan A* dengan Safety Map tersebut (Weighted A*).
        5. Lakukan pergerakan.
        """
        if self.game_state != PLAYING:
            return

        self.thief_prev_pos = list(self.thief_pos)
        target = self.money_pos if not self.money_collected else self.exit_pos
        
        cost_grid = self.create_safety_map()
        self.thief_path = self.a_star(self.thief_pos, target, cost_grid)

        if self.thief_path:
            self.thief_pos = self.thief_path.pop(0)

        # Cek kondisi objektif
        if self.thief_pos == self.money_pos and not self.money_collected:
            self.money_collected = True
        
        if self.thief_pos == self.exit_pos and self.money_collected:
            self.game_state = THIEF_WIN

    def get_intercept_target(self):
        """
        Algoritma Prediksi Pergerakan (Predictive Logic).
        Digunakan KHUSUS oleh Polisi 2 (Interceptor).
        
        Logika:
        1. Hitung vektor arah gerak pencuri (Posisi Sekarang - Posisi Kemarin).
        2. Kalikan vektor itu dengan 5 (Prediksi 5 langkah ke depan).
        3. Cek apakah titik prediksi itu valid (bukan tembok).
        4. Jika tidak valid, kurangi jarak prediksi perlahan hingga menemukan titik valid.
        
        Return:
            Koordinat [x, y] tempat pencuri diperkirakan akan berada.
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
        """
        Mengelola Kecerdasan Buatan (AI) Kedua Polisi (Global Optimal Strategy).
        
        Strategi Polisi 1 (Chaser):
        - Menggunakan A* murni ke posisi pencuri SAAT INI.
        - Perilaku: Agresif, menekan dari belakang.
        
        Strategi Polisi 2 (Interceptor):
        - Menggunakan Predictive A* ke posisi pencuri DI MASA DEPAN (dari get_intercept_target).
        - Perilaku: Taktis, memotong jalan dari depan.
        
        Fitur Anti-Stuck (Random Restart):
        - Jika A* gagal menemukan jalan (misal karena target ada di dalam tembok tertutup),
          polisi akan melakukan gerakan acak 1 langkah ke tetangga.
        - Ini mencegah AI 'membeku' (freeze) saat menghadapi jalan buntu kalkulasi.
        """
        if self.game_state != PLAYING or not self.money_collected:
            return 

        # --- LOGIKA POLISI 1 (CHASER) ---
        path_0 = self.a_star(self.police_positions[0], self.thief_pos)
        self.police_paths[0] = path_0
        
        if path_0:
            self.police_positions[0] = path_0.pop(0)
        else:
            neighbors = self.get_neighbors(self.police_positions[0])
            if neighbors: self.police_positions[0] = random.choice(neighbors)

        # --- LOGIKA POLISI 2 (INTERCEPTOR) ---
        intercept_pos = self.get_intercept_target()
        path_1 = self.a_star(self.police_positions[1], intercept_pos)
        self.police_paths[1] = path_1

        if path_1:
            self.police_positions[1] = path_1.pop(0)
        else:
            # Fallback: Jika gagal intercept, kejar langsung
            path_fallback = self.a_star(self.police_positions[1], self.thief_pos)
            if path_fallback:
                self.police_positions[1] = path_fallback.pop(0)
            else:
                neighbors = self.get_neighbors(self.police_positions[1])
                if neighbors: self.police_positions[1] = random.choice(neighbors)

        # Cek Kondisi Menangkap
        for p_pos in self.police_positions:
            if p_pos == self.thief_pos:
                self.game_state = POLICE_WIN

    def draw(self):
        """
        Fungsi Rendering.
        Menggambar seluruh state permainan (Grid, Karakter, Jalur, Teks) ke layar komputer.
        Dipanggil setiap frame.
        """
        self.screen.fill(WHITE) # Bersihkan layar

        # Gambar Peta
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                if self.grid[y][x] == 1:
                    pygame.draw.rect(self.screen, BLACK, rect)
                else:
                    pygame.draw.rect(self.screen, GRAY, rect, 1)

        # Gambar Visualisasi Jalur AI (Debugging Visual)
        for pos in self.thief_path:
            rect = pygame.Rect(pos[0]*CELL_SIZE+5, pos[1]*CELL_SIZE+5, CELL_SIZE-10, CELL_SIZE-10)
            pygame.draw.rect(self.screen, (173, 216, 230), rect) # Biru Muda

        for pos in self.police_paths[0]:
            rect = pygame.Rect(pos[0]*CELL_SIZE+5, pos[1]*CELL_SIZE+5, CELL_SIZE-10, CELL_SIZE-10)
            pygame.draw.rect(self.screen, (255, 200, 200), rect) # Merah Muda

        for pos in self.police_paths[1]:
            rect = pygame.Rect(pos[0]*CELL_SIZE+5, pos[1]*CELL_SIZE+5, CELL_SIZE-10, CELL_SIZE-10)
            pygame.draw.rect(self.screen, (200, 100, 100), rect) # Merah Gelap Pucat

        # Gambar Objek
        pygame.draw.rect(self.screen, GREEN, (self.exit_pos[0]*CELL_SIZE, self.exit_pos[1]*CELL_SIZE, CELL_SIZE, CELL_SIZE))
        if not self.money_collected:
            pygame.draw.rect(self.screen, YELLOW, (self.money_pos[0]*CELL_SIZE, self.money_pos[1]*CELL_SIZE, CELL_SIZE, CELL_SIZE))

        # Gambar Karakter
        get_center = lambda pos: (pos[0]*CELL_SIZE + CELL_SIZE//2, pos[1]*CELL_SIZE + CELL_SIZE//2)
        pygame.draw.circle(self.screen, BLUE, get_center(self.thief_pos), CELL_SIZE//3)
        pygame.draw.circle(self.screen, RED, get_center(self.police_positions[0]), CELL_SIZE//3)
        pygame.draw.circle(self.screen, DARK_RED, get_center(self.police_positions[1]), CELL_SIZE//3)

        # UI Teks
        status = "Just a normal day in museum" if not self.money_collected else "Money has stolen, CHASE THE THIEF!"
        color = ORANGE if not self.money_collected else RED
        text = self.font.render(status, True, color)
        self.screen.blit(text, (10, 10))

        if self.money_collected:
            role_text = self.font.render("Merah: Chaser | Merah Tua: Interceptor", True, BLACK)
            role_text = pygame.transform.scale(role_text, (int(role_text.get_width()*0.6), int(role_text.get_height()*0.6)))
            self.screen.blit(role_text, (10, 40))

        # Layar Akhir (Win/Lose)
        if self.game_state != PLAYING:
            msg = "PENCURI MENANG!" if self.game_state == THIEF_WIN else "TERTANGKAP!"
            color = BLUE if self.game_state == THIEF_WIN else RED
            text = self.font.render(msg, True, color)
            bg = pygame.Surface((text.get_width()+20, text.get_height()+20))
            bg.fill(WHITE)
            center_x, center_y = WINDOW_SIZE//2, WINDOW_SIZE//2
            self.screen.blit(bg, (center_x - bg.get_width()//2, center_y - bg.get_height()//2))
            self.screen.blit(text, (center_x - text.get_width()//2, center_y - text.get_height()//2))

        pygame.display.flip()

    def run(self):
        """
        Game Loop (Jantung Permainan).
        Fungsi ini berjalan terus menerus (infinite loop) sampai user menutup aplikasi.
        Tugasnya: Menerima Input -> Update Logika -> Gambar ke Layar -> Ulangi.
        """
        running = True
        while running:
            # Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r: self.reset_game()
                    elif event.key == pygame.K_q: running = False

            current_FPS = FPS
            if self.money_collected:
                current_FPS = 3

            # Update AI
            self.update_thief()
            if self.thief_pos in self.police_positions:
                self.game_state = POLICE_WIN
            self.update_police()
            print("Chaser:", self.police_positions[0])
            print("Interceptor:", self.police_positions[1])
            print("Thief:", self.thief_pos)

            # Render
            self.draw()
            self.clock.tick(current_FPS)
            
        pygame.quit()

if __name__ == "__main__":
    Game().run()