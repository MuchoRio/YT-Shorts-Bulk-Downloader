# 🚀 YT-Shorts-Bulk-Scraper

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![GUI](https://img.shields.io/badge/GUI-Tkinter-blue?style=for-the-badge)
![Web Scraping](https://img.shields.io/badge/Web%20Scraping-Selenium-green?style=for-the-badge&logo=selenium)

---

## English

This is a powerful and user-friendly Python bot designed with a Graphical User Interface (GUI) to effortlessly scrape YouTube Shorts video URLs and their titles in bulk from any specified YouTube channel. It's built to automate your data collection needs, allowing you to easily gather information on Shorts content.

### ✨ Features

* **GUI-driven:** Easy-to-use interface built with Tkinter for seamless interaction.
* **Bulk & Targeted Scraping:** Scrape all available Shorts or specify a target number of URLs to collect.
* **Flexible Browser Options:** Configure headless mode, disable sandbox, notifications, GPU, and more for optimized scraping.
* **Multiple Scrolling Methods:** Choose between "Send END Key", "Scroll to Bottom (JS)", or "Scroll by Viewport (JS)" for robust content loading.
* **Randomized Delays:** Incorporates random delays between scrolls to mimic human behavior and reduce the risk of detection.
* **Proxy Support:** Option to use a proxy for enhanced privacy and to bypass potential IP blocking.
* **Retry Mechanism:** Automatically retries the scraping process if initial attempts fail.
* **Detailed Logging:** Provides real-time logs within the GUI and saves them to a file for review.
* **Output Formats:** Saves scraped data to both `.txt` (URLs only) and `.xlsx` (URLs and Titles) files.
* **Persistent Settings:** Saves and loads your last-used settings for convenience.

### ⚙️ Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/MuchoRio/YT-Shorts-Bulk-Scraper.git](https://github.com/MuchoRio/YT-Shorts-Bulk-Scraper.git)
    cd YT-Shorts-Bulk-Scraper
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    ```
    * On Windows:
        ```bash
        .\venv\Scripts\activate
        ```
    * On macOS/Linux:
        ```bash
        source venv/bin/activate
        ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### 🚀 Usage

1.  **Run the application:**
    ```bash
    python tus.py
    ```
2.  **Configure Settings:**
    * **Output Folder:** Choose where the scraped data will be saved.
    * **Channel URL:** Enter the full URL of the YouTube channel's Shorts section (e.g., `https://www.youtube.com/@YouTubeChannel/shorts`).
    * **Target URL Count:** Specify how many Shorts URLs you want to collect. Enter `0` to scrape all available Shorts.
    * **Scroll Delay:** Set the maximum delay (in seconds) between scrolls. The script will use a random delay between 1 second and this value.
    * **Number of Retries:** Define how many times the script should attempt a full scraping run if it encounters issues.
    * **Proxy (optional):** Enter your proxy details (e.g., `ip:port` or `user:pass@ip:port`).
    * **Selenium Browser Options:** Select desired browser behaviors like `Headless Mode` (runs without a visible browser window) or `Disable Notifications`.
    * **Scrolling Method:** Select the preferred method for scrolling the page.
3.  **Start Scraping:** Click the "Mulai Scraping" (Start Scraping) button.
4.  **Monitor Progress:** Observe the real-time logs, progress bar, and status updates within the GUI.
5.  **Stop/Cancel:** Use the "Batal/Hentikan" (Cancel/Stop) button to interrupt the process.
6.  **Open Output Folder:** Once completed, click "Buka Folder Output" to view your results.


### 🙏 Support Me

If you find this script useful, please consider giving it a star ⭐️ on GitHub! Your support encourages me to create more open-source tools.

### 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.

---

## Bahasa Indonesia

Ini adalah bot Python yang tangguh dan mudah digunakan yang dirancang dengan Antarmuka Pengguna Grafis (GUI) untuk dengan mudah melakukan scraping URL video YouTube Shorts dan judulnya secara massal dari saluran YouTube mana pun yang ditentukan. Ini dibangun untuk mengotomatiskan kebutuhan pengumpulan data Anda, memungkinkan Anda dengan mudah mengumpulkan informasi tentang konten Shorts.

### ✨ Fitur

* **Berbasis GUI:** Antarmuka yang mudah digunakan dibangun dengan Tkinter untuk interaksi yang mulus.
* **Scraping Massal & Bertarget:** Lakukan scraping semua Shorts yang tersedia atau tentukan jumlah URL target yang akan dikumpulkan.
* **Opsi Browser Fleksibel:** Konfigurasikan mode headless, nonaktifkan sandbox, notifikasi, GPU, dan lainnya untuk scraping yang optimal.
* **Beberapa Metode Scrolling:** Pilih antara "Send END Key", "Scroll to Bottom (JS)", atau "Scroll by Viewport (JS)" untuk pemuatan konten yang tangguh.
* **Penundaan Acak:** Menggabungkan penundaan acak antar scroll untuk meniru perilaku manusia dan mengurangi risiko deteksi.
* **Dukungan Proxy:** Opsi untuk menggunakan proxy untuk meningkatkan privasi dan melewati potensi pemblokiran IP.
* **Mekanisme Percobaan Ulang:** Secara otomatis mencoba kembali proses scraping jika percobaan awal gagal.
* **Logging Detail:** Menyediakan log waktu nyata dalam GUI dan menyimpannya ke file untuk ditinjau.
* **Format Output:** Menyimpan data yang di-scrape ke file `.txt` (hanya URL) dan `.xlsx` (URL dan Judul).
* **Pengaturan Persisten:** Menyimpan dan memuat pengaturan terakhir yang Anda gunakan untuk kenyamanan.

### ⚙️ Instalasi

1.  **Clone repositori:**
    ```bash
    git clone [https://github.com/MuchoRio/YT-Shorts-Bulk-Scraper.git](https://github.com/MuchoRio/YT-Shorts-Bulk-Scraper.git)
    cd YT-Shorts-Bulk-Scraper
    ```

2.  **Buat virtual environment (direkomendasikan):**
    ```bash
    python -m venv venv
    ```
    * Di Windows:
        ```bash
        .\venv\Scripts\activate
        ```
    * Di macOS/Linux:
        ```bash
        source venv/bin/activate
        ```

3.  **Instal dependensi yang diperlukan:**
    ```bash
    pip install -r requirements.txt
    ```

### 🚀 Penggunaan

1.  **Jalankan aplikasi:**
    ```bash
    python tus.py
    ```
2.  **Konfigurasi Pengaturan:**
    * **Output Folder:** Pilih di mana data yang di-scrape akan disimpan.
    * **URL Channel:** Masukkan URL lengkap bagian Shorts dari saluran YouTube (misalnya, `https://www.youtube.com/@YouTubeChannel/shorts`).
    * **Jumlah URL Target:** Tentukan berapa banyak URL Shorts yang ingin Anda kumpulkan. Masukkan `0` untuk melakukan scraping semua Shorts yang tersedia.
    * **Scroll Delay:** Tetapkan penundaan maksimum (dalam detik) antar scroll. Skrip akan menggunakan penundaan acak antara 1 detik dan nilai ini.
    * **Jumlah Percobaan:** Tentukan berapa kali skrip harus mencoba menjalankan scraping penuh jika mengalami masalah.
    * **Proxy (opsional):** Masukkan detail proxy Anda (misalnya, `ip:port` atau `user:pass@ip:port`).
    * **Opsi Browser Selenium:** Pilih perilaku browser yang diinginkan seperti `Headless Mode` (berjalan tanpa jendela browser yang terlihat) atau `Disable Notifications`.
    * **Metode Scrolling:** Pilih metode yang disukai untuk menggulir halaman.
3.  **Mulai Scraping:** Klik tombol "Mulai Scraping".
4.  **Pantau Progress:** Amati log waktu nyata, progress bar, dan pembaruan status di dalam GUI.
5.  **Berhenti/Batal:** Gunakan tombol "Batal/Hentikan" untuk menginterupsi proses.
6.  **Buka Folder Output:** Setelah selesai, klik "Buka Folder Output" untuk melihat hasil Anda.

### 🙏 Dukung Saya

Jika Anda merasa skrip ini bermanfaat, mohon pertimbangkan untuk memberikannya bintang ⭐️ di GitHub! Dukungan Anda mendorong saya untuk membuat lebih banyak alat `open-source`.

### 📄 Lisensi

Proyek ini dilisensikan di bawah Lisensi MIT - lihat file `LICENSE` untuk detailnya.
