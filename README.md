# Smart Traffic Management Kota Chicago

**Project Analisis Big Data - Kelompok 5 - S1 Sains Data, Institut Teknologi Sepuluh Nopember (ITS), 2026**

Proyek ini mengimplementasikan integrasi data perkotaan Chicago untuk mendukung analisis lalu lintas, kecelakaan, kriminalitas, dan kualitas udara. Proyek memiliki dua jalur pemrosesan data, yaitu **Batch ETL** dan **Streaming ETL**, serta dashboard analitik berbasis Streamlit.

> Dashboard menggunakan **data hasil Batch ETL**. Dashboard tidak menggunakan aliran pesan Kafka sebagai sumber datanya. Streaming ETL merupakan jalur pemrosesan terpisah yang dibangun dan dievaluasi sebagai bagian dari proyek.

## Daftar Isi

- [Latar Belakang dan Tujuan](#latar-belakang-dan-tujuan)
- [Cakupan Data](#cakupan-data)
- [Arsitektur Sistem](#arsitektur-sistem)
- [Teknologi](#teknologi)
- [Struktur Proyek](#struktur-proyek)
- [Pipeline Batch ETL](#pipeline-batch-etl)
- [Pipeline Streaming ETL](#pipeline-streaming-etl)
- [Dashboard Analitik](#dashboard-analitik)
- [Persiapan dan Menjalankan Proyek](#persiapan-dan-menjalankan-proyek)
- [Keterbatasan dan Interpretasi](#keterbatasan-dan-interpretasi)
- [Troubleshooting](#troubleshooting)

## Latar Belakang dan Tujuan

Data perkotaan berasal dari sumber yang berbeda dan memiliki struktur, format, cakupan, serta kualitas yang tidak selalu seragam. Proyek ini mengintegrasikan beberapa domain data Chicago melalui pipeline ETL agar data lebih terstruktur dan dapat digunakan dalam dashboard analitik.

Tujuan proyek:

1. Mengidentifikasi karakteristik dan permasalahan kualitas data perkotaan Chicago.
2. Membangun pipeline Batch ETL dan Streaming ETL.
3. Melakukan profiling, standardisasi atribut, konversi tipe data, deduplikasi, dan pemuatan data.
4. Menggunakan Apache Airflow, PySpark, Apache Kafka, dan PostgreSQL dalam alur pengolahan data.
5. Menyajikan data terintegrasi melalui dashboard untuk eksplorasi kondisi lalu lintas dan keselamatan perkotaan.

## Cakupan Data

Proyek mengolah empat kelompok data utama.

| Domain | File sumber batch | Informasi yang dianalisis |
|---|---|---|
| Traffic | `data/macet.csv` | Volume kendaraan pada segmen jalan serta atribut lokasi dan waktu yang tersedia |
| Accident | `data/kecelakaan.csv` | Catatan kecelakaan, waktu, kondisi kejadian, dan atribut terkait yang tersedia |
| Crime | `data/kriminalitas.csv` | Kejadian kriminalitas, waktu, lokasi, dan kategori kejadian yang tersedia |
| Pollution | `data/polusi_udara.csv` | Pengukuran kualitas udara dan atribut lingkungan yang tersedia |

Data batas wilayah komunitas Chicago disediakan dalam file `Boundaries_-_Community_Areas_20260921.geojson`. Data geografis ini mendukung visualisasi dan pengaitan record dengan *Community Areas*, selama koordinat dan geometri yang diperlukan valid.

### Sumber dan cakupan data

- Data traffic batch diambil dari Chicago Data Portal melalui Socrata Open Data API.
- Dataset accident, crime, dan pollution pada pipeline batch dibaca dari file CSV lokal yang disertakan dalam proyek.
- File CSV lokal merupakan snapshot dengan cakupan terbatas. File tersebut tidak boleh dianggap mewakili seluruh data yang tersedia pada Chicago Data Portal.
- Pada konfigurasi batch yang diperiksa, ekstraksi traffic dibatasi hingga maksimal **1.000 record per eksekusi**.

## Arsitektur Sistem

Proyek memiliki dua jalur ETL. Keduanya menyiapkan data untuk analisis, tetapi memiliki mekanisme pemrosesan dan pemuatan yang berbeda.

```text
                  Chicago Data Portal / Socrata API
                               |
                 +-------------+-------------+
                 |                           |
                 v                           v
           BATCH ETL                    STREAMING ETL
                 |                           |
       Apache Airflow DAG              API polling producer
                 |                           |
       Fetch traffic API                     v
                 |                      Apache Kafka
       Profiling dan transformasi            |
          menggunakan PySpark                v
                 |                       Processor
          Apache Parquet                     |
                 |                           v
                 v                    PostgreSQL (upsert)
          PostgreSQL
                 |
                 v
       Data batch untuk dashboard
                 |
                 v
        Streamlit Dashboard
```

**Pemisahan sumber dashboard:** Diagram menunjukkan peran kedua jalur ETL dalam proyek secara keseluruhan. Dashboard yang didokumentasikan menggunakan data batch; jalur streaming Kafka tidak menjadi sumber langsung dashboard.

## Teknologi

| Teknologi | Peran |
|---|---|
| Python | Bahasa pemrograman untuk ETL dan dashboard |
| Docker / Docker Compose | Menjalankan komponen sistem dalam container |
| Apache Airflow | Orkestrasi dan penjadwalan pipeline Batch ETL |
| PySpark | Profiling dan transformasi data batch |
| Apache Parquet | Penyimpanan hasil transformasi batch |
| Apache Kafka | Perantara pesan pada pipeline Streaming ETL |
| PostgreSQL | Penyimpanan data hasil pemuatan |
| Streamlit | Antarmuka dashboard analitik |
| Pandas / Plotly | Pengolahan data dan visualisasi |
| GeoJSON | Representasi geometri batas wilayah komunitas |

## Struktur Proyek

Struktur utama proyek:

```text
Project_Bigdat_Kel5/
├── dashboard/
│   ├── app.py
│   ├── requirements.txt
│   ├── .streamlit/
│   │   └── config.toml
│   └── Boundaries_-_Community_Areas_20260921.geojson
│
├── metropolia-traffic-etl/
│   ├── dags/
│   │   └── metropolia_traffic_etl.py
│   ├── scripts/
│   │   ├── etch_traffic_api.py
│   │   ├── profiling.py
│   │   ├── transform.py
│   │   ├── load.py
│   │   └── test_api.py
│   ├── data/
│   │   ├── macet.csv
│   │   ├── kecelakaan.csv
│   │   ├── kriminalitas.csv
│   │   ├── polusi_udara.csv
│   │   ├── Boundaries_-_Community_Areas_20260921.geojson
│   │   └── processed/
│   ├── sql/
│   └── docker-compose.yml
│
└── README.md
```

Pipeline Streaming ETL berada pada arsip/folder terpisah bernama `chicago-stream-etl`. Folder tersebut berisi implementasi producer, Kafka, dan processor. Pipeline streaming bukan sumber data dashboard pada konfigurasi yang dijelaskan README ini.

## Pipeline Batch ETL

Batch ETL diorkestrasi oleh DAG Airflow bernama `metropolia_traffic_etl`, dengan jadwal setiap **15 menit** dan `catchup=False`.

### Tahapan Batch ETL

1. **`fetch_traffic_api` — Extract**
   - Mengambil snapshot data traffic dari Socrata API.
   - Menyimpan data traffic ke `data/macet.csv`.
   - Konfigurasi yang diperiksa membatasi pengambilan hingga maksimal 1.000 record per eksekusi.

2. **`profiling` — Data profiling**
   - Memeriksa struktur dan skema data.
   - Menampilkan jumlah baris dan kolom, nilai kosong, duplikasi, sampel data, serta ringkasan statistik sesuai implementasi skrip.

3. **`transformation` — Transform**
   - Membaca dataset CSV dengan PySpark.
   - Memilih dan menyesuaikan atribut yang diperlukan.
   - Mengonversi tipe data tertentu.
   - Menghapus duplikasi sesuai aturan dalam skrip.
   - Menyimpan hasil transformasi dalam format Parquet.

4. **`load` — Load**
   - Membaca keluaran Parquet.
   - Memuat data ke tabel PostgreSQL untuk domain traffic, accident, crime, dan pollution.
   - Menggunakan mekanisme **full refresh**: tabel tujuan dibuat ulang sebelum data dimasukkan kembali.

### Karakteristik Batch ETL

- Berorientasi pada pemrosesan kumpulan data secara terjadwal.
- Hasil transformasi disimpan ke Parquet sebelum tahap pemuatan.
- Full refresh berarti tabel tujuan mengikuti hasil eksekusi terakhir; riwayat dari eksekusi sebelumnya tidak otomatis dipertahankan.
- Jadwal 15 menit menunjukkan frekuensi pemicu batch, bukan pemrosesan streaming secara kontinu.

## Pipeline Streaming ETL

Streaming ETL merupakan jalur terpisah yang menggunakan API polling, Apache Kafka, processor, dan PostgreSQL.

### Alur Streaming ETL

1. **Producer**
   - Mengambil data dari Socrata Open Data API melalui polling.
   - Konfigurasi yang didokumentasikan menggunakan interval polling 2 detik per dataset.
   - Menggunakan watermark untuk melanjutkan pengambilan data dari posisi terakhir yang tercatat.
   - Menerbitkan pesan ke topik Kafka berdasarkan domain data.

2. **Apache Kafka**
   - Menjadi perantara antara producer dan processor.
   - Topik data yang didokumentasikan:
     - `chi.crime.raw`
     - `chi.accident.raw`
     - `chi.traffic.raw`
     - `chi.pollution.raw`
   - Topik `chi.dlq` disediakan untuk pesan yang gagal diproses (*dead-letter queue*).

3. **Processor**
   - Membaca pesan dari Kafka.
   - Memproses payload JSON dan menyesuaikan tipe data.
   - Memeriksa kolom wajib dan melakukan deduplikasi sesuai implementasi.
   - Mengarahkan pesan yang gagal ke DLQ.
   - Memuat data valid ke PostgreSQL dengan mekanisme **upsert**.

4. **PostgreSQL**
   - Upsert menambahkan record baru atau memperbarui record dengan kunci yang sama.
   - Offset Kafka dikonfirmasi setelah transaksi basis data berhasil, sesuai alur yang dirancang.

### Perbedaan Batch dan Streaming

| Aspek | Batch ETL | Streaming ETL |
|---|---|---|
| Orkestrasi / alur | Apache Airflow DAG | Producer → Kafka → Processor |
| Pengambilan data | Snapshot traffic API dan CSV lokal untuk domain lainnya | Polling Socrata API |
| Pemrosesan | PySpark | Processor pesan |
| Perantara / penyimpanan antara | Parquet | Apache Kafka |
| Mekanisme pemuatan | Full refresh | Upsert |
| Tujuan | Pemrosesan kumpulan data secara terjadwal | Pemrosesan pesan secara berkelanjutan berdasarkan polling API |
| Hubungan dengan dashboard | Sumber data dashboard pada konfigurasi yang didokumentasikan | Jalur terpisah, bukan sumber langsung dashboard |

> Polling API bukanlah langganan terhadap event stream native dari portal data. Keberhasilan producer mengambil data juga tidak otomatis membuktikan semua record berhasil diterbitkan ke Kafka, diproses, dan dimuat ke PostgreSQL.

## Dashboard Analitik

Dashboard dibangun menggunakan Streamlit untuk menyajikan informasi deskriptif melalui indikator, grafik, dan visualisasi wilayah. Dashboard terdiri atas delapan halaman analitik.

| Tab | Fungsi |
|---|---|
| **Overview** | Ringkasan indikator utama dari domain data yang tersedia |
| **Live Traffic** | Eksplorasi volume kendaraan berdasarkan segmen jalan yang tersedia |
| **Incidents** | Eksplorasi data kecelakaan dan kriminalitas |
| **Area Intelligence** | Perbandingan indikator antar-*Community Areas* |
| **Environment** | Eksplorasi data kualitas udara dan variabel lingkungan |
| **Traffic Analytics** | Analisis pola dan distribusi volume traffic |
| **Crash Forecast** | Baseline perkiraan kecelakaan menggunakan rata-rata historis berdasarkan hari dan jam |
| **Signal Simulator** | Simulasi skenario pengaturan sinyal berdasarkan asumsi dan parameter masukan |

### Sumber data dashboard

Dashboard menggunakan **data hasil Batch ETL**, bukan pesan yang dibaca langsung dari Kafka. Dalam pemeriksaan yang dicatat pada laporan, dashboard menggunakan Parquet sebagai sumber cadangan (*fallback*), dengan waktu ingest terakhir yang ditampilkan sebesar **4 Oktober 2026**.

Pastikan hasil transformasi batch tersedia sebelum menjalankan dashboard. Jika aplikasi mengambil data dari lokasi fallback, file Parquet harus berada pada path yang sesuai dengan konfigurasi dan struktur direktori proyek. Jangan menyimpulkan bahwa dashboard telah membaca data PostgreSQL terbaru hanya karena tabel PostgreSQL tersedia; sumber yang benar-benar digunakan perlu diverifikasi melalui konfigurasi dan log aplikasi.

### Catatan interpretasi dashboard

- **Live Traffic:** data menunjukkan volume kendaraan pada segmen yang tersedia, bukan kecepatan kendaraan atau waktu tempuh. Kategori Normal, Moderate, High, dan Severe merupakan klasifikasi relatif, bukan ukuran langsung kemacetan.
- **Area Intelligence:** hasil pemetaan bergantung pada validitas koordinat, kesesuaian sistem koordinat, dan geometri batas komunitas.
- **Risk score:** skor risiko merupakan indeks relatif yang dibentuk berdasarkan peringkat persentil kepadatan kriminalitas dan kecelakaan. Skor ini bukan indeks resmi dan tidak mewakili seluruh dimensi risiko wilayah.
- **Crash Forecast:** menggunakan baseline rata-rata historis berdasarkan hari dan jam, bukan model machine learning. Nilai evaluasi hanya berlaku untuk periode pengujian yang digunakan.
- **Signal Simulator:** hasilnya bersifat ilustratif dan tidak menggantikan analisis rekayasa lalu lintas berbasis data persimpangan aktual.

## Persiapan dan Menjalankan Proyek

### Prasyarat

- Docker Desktop dan Docker Compose.
- Python yang kompatibel dengan `dashboard/requirements.txt`.
- Koneksi internet untuk pengambilan data melalui Socrata API.
- File CSV sumber untuk batch ETL.
- File GeoJSON batas wilayah Chicago.

### A. Menjalankan Batch ETL

1. Buka terminal dan masuk ke folder ETL:

   ```bash
   cd Project_Bigdat_Kel5/metropolia-traffic-etl
   ```

2. Jalankan container:

   ```bash
   docker compose up -d
   ```

3. Periksa status layanan:

   ```bash
   docker compose ps
   ```

4. Buka Airflow pada alamat dan port yang dikonfigurasi di `docker-compose.yml`. Pada konfigurasi proyek, antarmuka Airflow tersedia di:

   ```text
   http://localhost:8081
   ```

5. Cari DAG `metropolia_traffic_etl`, lalu aktifkan atau trigger DAG tersebut.

6. Pastikan task `fetch_traffic_api`, `profiling`, `transformation`, dan `load` selesai sesuai harapan. Periksa log setiap task untuk memvalidasi hasil eksekusi.

Keluaran Parquet diharapkan tersedia di direktori `metropolia-traffic-etl/data/processed/` untuk dataset traffic, accident, crime, dan pollution. Direktori keluaran Spark dapat berisi beberapa file `part-*.parquet` serta penanda `_SUCCESS`.

### B. Menjalankan Dashboard

1. Buka terminal lain dan masuk ke folder dashboard:

   ```bash
   cd Project_Bigdat_Kel5/dashboard
   ```

2. Buat dan aktifkan virtual environment (disarankan).

   **Windows PowerShell:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   **macOS/Linux:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Instal dependensi:

   ```bash
   pip install -r requirements.txt
   ```

4. Konfirmasikan konfigurasi sumber data pada `app.py` dan pastikan keluaran Parquet batch tersedia pada lokasi yang diharapkan oleh aplikasi. Jika aplikasi memerlukan koneksi PostgreSQL, sesuaikan konfigurasi koneksinya dengan pengaturan lokal dan verifikasi sumber data yang benar-benar dipakai.

5. Jalankan dashboard:

   ```bash
   streamlit run app.py
   ```

6. Buka URL lokal yang ditampilkan Streamlit, biasanya:

   ```text
   http://localhost:8501
   ```

### Konfigurasi dan keamanan

- Periksa `docker-compose.yml` untuk nama layanan, port, database, dan kredensial lokal yang sebenarnya.
- Jangan mengasumsikan kredensial, port, atau nama service sama di semua lingkungan.
- Jangan commit password, token API, atau file secrets ke repository.
- Untuk deployment, gunakan environment variable atau mekanisme secrets yang sesuai.

## Keterbatasan dan Interpretasi

Hasil proyek perlu dibaca dengan memperhatikan batasan berikut:

1. **Cakupan data:** CSV yang disertakan merupakan snapshot lokal dengan jumlah record terbatas; ekstraksi traffic batch dibatasi maksimal 1.000 record per eksekusi.
2. **Validasi eksekusi:** keberadaan skrip, konfigurasi, atau keluaran Parquet dalam arsip tidak dengan sendirinya membuktikan keberhasilan eksekusi ulang. Jumlah record, durasi proses, dan kegagalan perlu diverifikasi dari log dan query hasil eksekusi tertentu.
3. **Pemuatan batch:** full refresh tidak otomatis menyimpan riwayat data dari eksekusi sebelumnya.
4. **Ketergantungan streaming:** hasil streaming bergantung pada query API, watermark, batas penggunaan API, ketersediaan layanan, dan penanganan pesan gagal.
5. **Interpretasi traffic:** volume kendaraan tidak sama dengan kecepatan atau waktu tempuh.
6. **Analisis spasial:** tidak semua record dijamin berhasil dipetakan ke *Community Areas*.
7. **Risk score:** indeks buatan tim, bukan indikator resmi.
8. **Forecast kecelakaan:** baseline historis, bukan model machine learning; perlu pengujian pada periode lain.
9. **Simulasi sinyal:** hasil berbasis asumsi dan perlu validasi rekayasa lalu lintas sebelum digunakan untuk keputusan operasional.
10. **Sumber dashboard:** sumber data yang benar-benar dipakai aplikasi harus diverifikasi melalui konfigurasi dan log. Pada pemeriksaan yang dicatat dalam laporan, dashboard menggunakan Parquet sebagai sumber cadangan.

## Troubleshooting

### Airflow tidak dapat dibuka

```bash
docker compose ps
docker compose logs --tail=100
```

Pastikan container aktif dan port yang ditetapkan pada `docker-compose.yml` tidak digunakan aplikasi lain.

### Batch ETL gagal membaca CSV

- Pastikan file CSV tersedia di `metropolia-traffic-etl/data/`.
- Periksa nama kolom sumber karena skrip transformasi mengandalkan kolom yang ditentukan di kode.
- Periksa log task Airflow untuk menemukan file, kolom, atau tipe data yang menyebabkan kegagalan.

### Pengambilan API gagal

- Pastikan koneksi internet tersedia.
- Periksa endpoint, query, dan respons Socrata API.
- Periksa log task atau producer.
- Perhatikan batas permintaan API dan konfigurasi pagination.

### Dashboard tidak menampilkan data

- Pastikan Batch ETL telah dijalankan dan keluaran Parquet tersedia.
- Periksa path data yang dirujuk dalam `dashboard/app.py`.
- Periksa apakah nama kolom pada hasil transformasi sesuai dengan nama kolom yang dipakai dashboard.
- Jika aplikasi menggunakan PostgreSQL untuk pembacaan tertentu, verifikasi koneksi, nama tabel, dan status pemuatan.
- Restart aplikasi atau bersihkan cache bila dashboard masih menampilkan hasil lama.

### Streaming ETL bermasalah

- Periksa status container producer, Kafka, processor, dan PostgreSQL.
- Periksa log producer dan processor.
- Verifikasi topik Kafka, offset, watermark, dan pesan pada `chi.dlq`.
- Periksa jumlah record yang masuk, diperbarui, atau gagal melalui log dan query PostgreSQL.

---
## Perancang:
- Naomy Athaya Jovany - 5052241002
- Amelia Widiastuti - 5052241007
- Marvelio Jonathan W. - 5052241017
- M. Razan Thariq A. - 5052241025
- Aqila Ikhza K. - 5052241032
- Inessa Regina Angelica Munda - 5052241037



## Referensi Sumber Data dan Dokumentasi

- City of Chicago — [Chicago Data Portal](https://data.cityofchicago.org/)
- Socrata — [Socrata Open Data API (SODA) Documentation](https://dev.socrata.com/docs/)
