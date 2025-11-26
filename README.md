# 🎮 AI Pathfinding Game: Thief vs Police

Simulasi game berbasis AI yang mendemonstrasikan algoritma **A* Pathfinding**, **Predictive Movement**, dan **Strategic Interception** dalam skenario pengejaran polisi dan pencuri.

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
![Pygame](https://img.shields.io/badge/Pygame-2.0+-green.svg)

## 📋 Deskripsi

Game ini mensimulasikan pengejaran cerdas antara satu pencuri dan dua polisi dalam maze dinamis. Setiap karakter menggunakan algoritma AI yang berbeda:

- **Pencuri (Biru)**: Menggunakan **Weighted A*** dengan safety heatmap untuk menghindari zona bahaya polisi
- **Polisi 1 - Chaser (Merah)**: Menggunakan **A* murni** untuk mengejar posisi pencuri secara langsung
- **Polisi 2 - Interceptor (Merah Tua)**: Menggunakan **Predictive A*** untuk memotong jalur pencuri di masa depan

## ✨ Fitur Utama

### 🧠 Algoritma AI
- **A* Pathfinding**: Pencarian jalur optimal dengan heuristik Manhattan Distance
- **Weighted A***: Pathfinding dengan cost map dinamis untuk penghindaran bahaya
- **Predictive Movement**: Prediksi 5 langkah ke depan berdasarkan vektor kecepatan
- **Safety Heatmap**: Sistem pembobotan area berbahaya dengan fungsi eksponensial

### 🎯 Gameplay
- **Tujuan Pencuri**: Ambil uang → Kabur ke Exit
- **Tujuan Polisi**: Tangkap pencuri sebelum sampai Exit
- **Dynamic Maze**: Maze acak 20x20 dengan 50% wall density
- **Real-time Visualization**: Visualisasi jalur AI secara real-time

### 🛡️ Safety Mechanism
- Anti-stuck system dengan random restart
- Spawn protection untuk area karakter
- Fallback behavior saat pathfinding gagal

## 🚀 Instalasi

### Requirements
```bash
Python 3.7+
pygame 2.0+
```

### Install Dependencies
```bash
pip install pygame
```

### Jalankan Game
```bash
python Pursuit-Evasion.py
```

## 🎮 Kontrol

| Tombol | Fungsi |
|--------|--------|
| `R` | Reset game (mulai baru) |
| `Q` | Quit (keluar dari game) |

## 📊 Struktur Kode

```
├── BAGIAN 1: KONSTANTA & PENGATURAN
│   ├── Grid Configuration (20x20)
│   ├── Color Definitions
│   └── Game States
│
├── BAGIAN 2: STRUKTUR DATA
│   └── Class Node (untuk A* Algorithm)
│
└── BAGIAN 3: LOGIKA UTAMA
    ├── Game Initialization
    ├── Maze Generation
    ├── A* Pathfinding
    ├── Safety Map Creation
    ├── AI Updates (Thief & Police)
    └── Rendering System
```

## 🧮 Cara Kerja Algoritma

### 1. A* Pathfinding
```python
F(n) = G(n) + H(n)
```
- **G(n)**: Jarak riil dari start ke node n
- **H(n)**: Estimasi jarak dari node n ke goal (Manhattan Distance)
- **F(n)**: Total cost (prioritas node)

### 2. Safety Heatmap
```python
Cost = Base + (Radius - Distance)² × Multiplier
```
- Kotak dekat polisi = cost tinggi (mahal)
- Kotak jauh dari polisi = cost rendah (murah)
- A* otomatis memilih jalur "termurah"

### 3. Predictive Interception
```python
PredictedPos = CurrentPos + (Velocity × Steps)
```
- Hitung vektor kecepatan pencuri
- Prediksi 5 langkah ke depan
- Polisi interceptor menuju posisi prediksi

## 🎨 Visualisasi

| Warna | Representasi |
|-------|-------------|
| 🟦 **Biru** | Pencuri |
| 🟥 **Merah** | Polisi 1 (Chaser) |
| 🟫 **Merah Tua** | Polisi 2 (Interceptor) |
| 🟨 **Kuning** | Uang |
| 🟩 **Hijau** | Exit |
| ⬛ **Hitam** | Tembok |
| 🟦 **Biru Muda** | Jalur Pencuri |
| 🟥 **Merah Muda** | Jalur Polisi 1 |
| 🟫 **Merah Gelap** | Jalur Polisi 2 |

## ⚙️ Konfigurasi

Anda dapat menyesuaikan parameter game di bagian `KONSTANTA`:

```python
GRID_SIZE = 20        # Ukuran map (20x20)
CELL_SIZE = 50        # Ukuran cell dalam pixel
FPS = 10              # Frame rate normal
wall_density = 0.50   # 50% wall coverage

# Safety Heatmap Parameters
danger_radius = 6          # Radius zona bahaya polisi
base_danger_cost = 50      # Cost dasar zona bahaya
multiplier = 100           # Pengali cost eksponensial
```

## 🎯 Strategi AI

### Pencuri (Defensive)
1. ✅ Prioritas: Keselamatan > Kecepatan
2. 📊 Analisis safety heatmap setiap frame
3. 🔄 Pilih jalur dengan cost terendah (paling aman)
4. 🏃 Bergerak menghindari zona polisi

### Polisi 1 - Chaser (Aggressive)
1. 🎯 Target: Posisi pencuri SAAT INI
2. ⚡ Taktik: Direct pursuit
3. 💪 Peran: Pressure dari belakang

### Polisi 2 - Interceptor (Tactical)
1. 🔮 Target: Posisi pencuri DI MASA DEPAN
2. 🧠 Taktik: Path prediction
3. ✂️ Peran: Cut off dari depan

## 🏆 Kondisi Kemenangan

### Pencuri Menang
- ✅ Ambil uang
- ✅ Sampai ke Exit tanpa tertangkap

### Polisi Menang
- ✅ Salah satu polisi menyentuh pencuri
- ✅ Pencuri sudah ambil uang

## 🔧 Troubleshooting

**Q: Game terlalu lambat/cepat?**
```python
FPS = 10  # Ubah nilai ini (lebih tinggi = lebih cepat)
```

**Q: Terlalu banyak tembok?**
```python
wall_count = int(GRID_SIZE * GRID_SIZE * 0.30)  # Ubah 0.50 jadi 0.30
```

**Q: Polisi terlalu kuat/lemah?**
```python
danger_radius = 4  # Kurangi radius untuk memudahkan pencuri
multiplier = 50    # Kurangi multiplier untuk zona bahaya lebih kecil
```

## 📚 Pembelajaran

Project ini cocok untuk mempelajari:
- ✅ Algoritma A* dan variasinya
- ✅ Game AI pathfinding
- ✅ Predictive movement
- ✅ Priority Queue (heapq)
- ✅ Heuristic functions
- ✅ Cost-based pathfinding
- ✅ Multi-agent coordination
