import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import threading
import os
import time
import random
from datetime import datetime
import json

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from webdriver_manager.chrome import ChromeDriverManager
import openpyxl

class YouTubeShortsScraper:
    """
    Kelas ini bertanggung jawab untuk logika scraping YouTube Shorts.
    """
    def __init__(self, output_folder, log_callback, progress_callback, status_callback, config):
        """
        Inisialisasi scraper.

        Args:
            output_folder (str): Lokasi folder untuk menyimpan output.
            log_callback (function): Fungsi callback untuk logging ke GUI.
            progress_callback (function): Fungsi callback untuk memperbarui progress bar di GUI.
            status_callback (function): Fungsi callback untuk memperbarui status di GUI.
            config (dict): Konfigurasi scraping dari GUI.
        """
        self.output_folder = output_folder
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.status_callback = status_callback
        self.config = config
        self.driver = None
        self.scraped_data = []
        self.stop_scraping_flag = threading.Event() # Event untuk menghentikan scraping
        self.start_time = None
        self.scroll_count = 0
        self.no_new_urls_consecutive_scrolls = 0 # Counter untuk mendeteksi potensi blocking

    def _log(self, message):
        """
        Mencatat pesan ke log GUI dan file log.
        Setiap entri log mencakup timestamp.

        Args:
            message (str): Pesan yang akan dicatat.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        self.log_callback(log_message)
        # Pastikan folder output ada sebelum mencoba menulis file log
        os.makedirs(self.output_folder, exist_ok=True)
        with open(os.path.join(self.output_folder, "scraping_log.txt"), "a", encoding="utf-8") as f:
            f.write(log_message + "\n")

    def _initialize_webdriver(self):
        """
        Menginisialisasi Selenium WebDriver dengan opsi yang dikonfigurasi.
        """
        self._log("Menginisialisasi WebDriver...")
        options = Options()

        # Konfigurasi opsi browser dari GUI
        if self.config["headless_mode"]:
            options.add_argument("--headless=new")
        if self.config["disable_sandbox"]:
            options.add_argument("--no-sandbox")
        if self.config["disable_dev_shm_usage"]:
            options.add_argument("--disable-dev-shm-usage")
        if self.config["disable_notifications"]:
            options.add_argument("--disable-notifications")
        if self.config["disable_extensions"]:
            options.add_argument("--disable-extensions")
        if self.config["disable_gpu"]:
            options.add_argument("--disable-gpu")
        if self.config["enable_webgl"]:
            options.add_argument("--enable-webgl")
        if self.config["enable_smooth_scrolling"]:
            options.add_argument("--enable-smooth-scrolling")
        if self.config["set_language_en_us"]:
            options.add_argument("--lang=en-US")
        if self.config["start_maximized"]:
            options.add_argument("--start-maximized")

        # Random User-Agent
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.113 Mobile Safari/537.36"
        ]
        options.add_argument(f"user-agent={random.choice(user_agents)}")

        # Konfigurasi Proxy
        if self.config["proxy_input"]:
            options.add_argument(f"--proxy-server={self.config['proxy_input']}")
            self._log(f"Menggunakan proxy: {self.config['proxy_input']}")

        try:
            # Menggunakan ChromeDriverManager untuk mengelola ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(30) # Set timeout untuk loading halaman
            self._log("WebDriver berhasil diinisialisasi.")
        except WebDriverException as e:
            self._log(f"Error saat menginisialisasi WebDriver: {e}")
            self.status_callback("Error: Gagal menginisialisasi browser. Pastikan Chrome terinstall dan up-to-date.")
            self.driver = None # Pastikan driver None jika gagal inisialisasi
            raise

    def _scrape_shorts_data(self):
        """
        Melakukan scraping data URL dan judul Shorts dari halaman YouTube.
        """
        self.scraped_data = []
        urls_found = set() # Menggunakan set untuk menghindari duplikasi URL
        previous_urls_count = 0 # Untuk deteksi URL baru setelah scroll

        self.start_time = time.time()
        self.scroll_count = 0
        self.no_new_urls_consecutive_scrolls = 0 # Reset counter
        last_height = self.driver.execute_script("return document.documentElement.scrollHeight")

        # Inisialisasi progress bar sebagai indeterminate jika tidak ada target URL
        if self.config["target_url_count"] == 0:
            self.progress_callback(0, 0) # Mode indeterminate

        while True:
            if self.stop_scraping_flag.is_set():
                self._log("Proses scraping dibatalkan oleh pengguna.")
                self.status_callback("Scraping Dibatalkan.")
                break

            self.scroll_count += 1
            self.status_callback(f"Melakukan scroll ke-{self.scroll_count}...")
            self._log(f"Melakukan scroll ke-{self.scroll_count}...")

            # Implementasi metode scrolling
            if self.config["scrolling_method"] == "Send END Key":
                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
            elif self.config["scrolling_method"] == "Scroll to Bottom (JS)":
                self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            elif self.config["scrolling_method"] == "Scroll by Viewport (JS)":
                # Scroll 90% dari tinggi viewport
                self.driver.execute_script("window.scrollBy(0, window.innerHeight * 0.9);")

            # Random delay
            # Menggunakan random.randint karena scroll delay sekarang bilangan bulat
            delay = random.randint(1, self.config["scroll_delay"]) # Min 1 detik, Max = Scroll Delay
            self._log(f"Menunggu {delay} detik (random delay).")
            time.sleep(delay)

            try:
                # Mencari elemen video Shorts berdasarkan struktur HTML yang diberikan.
                # Kami mencari tag 'a' yang memiliki class yang sesuai dan '/shorts/' dalam href-nya.
                video_elements = self.driver.find_elements(By.CSS_SELECTOR,
                    "a.shortsLockupViewModelHostEndpoint.reel-item-endpoint[href*='/shorts/'], " +
                    "a.shortsLockupViewModelHostEndpoint.shortsLockupViewModelHostOutsideMetadataEndpoint[href*='/shorts/']"
                )

                # Dapatkan URL yang sudah ada sebelum penambahan di iterasi ini
                num_urls_before_current_scan = len(urls_found)

                for element in video_elements:
                    href = element.get_attribute("href")
                    title = ""

                    # Mencoba mendapatkan judul. Ada dua kemungkinan lokasi judul:
                    # 1. Dari atribut 'title' pada tag <a> itu sendiri.
                    # 2. Dari teks di dalam tag <span> yang merupakan anak dari tag <a>,
                    #    terutama untuk a.shortsLockupViewModelHostOutsideMetadataEndpoint.
                    if element.get_attribute("title"):
                        title = element.get_attribute("title").strip()
                    else:
                        # Mencoba menemukan span di dalam elemen a untuk mendapatkan judul teks
                        try:
                            title_span = element.find_element(By.CSS_SELECTOR, "span.yt-core-attributed-string")
                            title = title_span.text.strip()
                        except NoSuchElementException:
                            pass # Tidak ada span judul yang ditemukan, biarkan title kosong

                    if href and "/shorts/" in href:
                        # Pastikan URL lengkap dan tidak relatif
                        if not href.startswith("http"):
                            # Perbaiki URL relatif ke URL absolut YouTube
                            if href.startswith("/"):
                                href = f"https://www.youtube.com{href}"
                            else:
                                # Fallback jika format URL relatif tidak terduga, coba gabungkan dengan base URL
                                # Namun, disarankan URL yang dimasukkan pengguna sudah channel URL lengkap
                                try:
                                    from urllib.parse import urljoin
                                    base_url = self.config['channel_url'].split('/shorts')[0] # Ambil bagian dasar URL channel
                                    href = urljoin(base_url, href)
                                    self._log(f"URL relatif dikonversi ke absolut: {href}")
                                except Exception as url_err:
                                    self._log(f"Peringatan: Gagal mengonversi URL relatif '{href}' ke absolut. Error: {url_err}")
                                    # Lanjutkan saja dengan URL relatif, mungkin YouTube bisa menanganinya
                                    pass


                        if href not in urls_found:
                            self.scraped_data.append({"URL Video": href, "Title": title})
                            urls_found.add(href)
                            self._log(f"Ditemukan: {title} ({href})")

                # Cek apakah ada URL baru yang ditemukan di scroll ini
                if len(urls_found) > num_urls_before_current_scan:
                    self.no_new_urls_consecutive_scrolls = 0 # Reset counter jika ada URL baru
                else:
                    self.no_new_urls_consecutive_scrolls += 1 # Increment jika tidak ada URL baru

                self._log(f"Total URL unik ditemukan: {len(urls_found)}")
                self.progress_callback(len(urls_found), self.config["target_url_count"])

                if self.config["target_url_count"] > 0 and len(urls_found) >= self.config["target_url_count"]:
                    self._log(f"Jumlah URL target ({self.config['target_url_count']}) tercapai.")
                    self.status_callback("Jumlah URL target tercapai.")
                    break

                new_height = self.driver.execute_script("return document.documentElement.scrollHeight")
                if new_height == last_height:
                    self._log("Tidak ada konten baru yang bisa di-scroll (mencapai akhir halaman atau tidak ada konten baru dimuat). Mengakhiri scraping.")
                    self.status_callback("Tidak ada konten baru yang bisa di-scroll.")
                    break
                last_height = new_height

                # Deteksi potensi pemblokiran: Jika tidak ada URL baru ditemukan setelah beberapa scroll berturut-turut
                # Meskipun halaman masih bisa discroll ke bawah, ini bisa menjadi indikasi masalah
                if self.no_new_urls_consecutive_scrolls >= 5: # Misalnya, 5 scroll tanpa URL baru
                    self._log("Peringatan: Tidak ada URL Shorts baru yang ditemukan setelah beberapa scroll berturut-turut.")
                    self._log("Ini mungkin mengindikasikan potensi rate limiting, pemblokiran, atau tidak ada lagi Shorts baru.")
                    self.status_callback("Peringatan: Potensi pemblokiran terdeteksi. Melanjutkan dengan hati-hati.")
                    # Kita bisa memilih untuk menghentikan atau melanjutkan
                    # Untuk saat ini, kita akan teruskan, tapi log ini akan muncul
                    # Jika counter terus bertambah, kemungkinan besar memang tidak ada konten baru.
                    if self.no_new_urls_consecutive_scrolls >= 10: # Hentikan jika terlalu lama tidak ada URL baru
                        self._log("Menghentikan scraping karena terlalu banyak scroll tanpa menemukan URL baru.")
                        self.status_callback("Dihentikan: Tidak ada URL baru ditemukan setelah banyak scroll.")
                        break

            except Exception as e:
                self._log(f"Error saat mencari elemen video atau memproses data: {e}")
                self.status_callback(f"Error: {e}")
                break

        self.status_callback("Scraping selesai.")
        self._log("Proses scraping selesai.")

    def run_scraper(self):
        """
        Menjalankan seluruh proses scraping, termasuk inisialisasi browser, scraping,
        dan penanganan retry.
        """
        for retry_attempt in range(self.config["number_of_retries"]):
            if self.stop_scraping_flag.is_set():
                break

            self._log(f"Memulai percobaan scraping ke-{retry_attempt + 1} dari {self.config['number_of_retries']}...")
            self.status_callback(f"Memulai percobaan scraping ke-{retry_attempt + 1}...")
            self.scraped_data = [] # Reset data untuk setiap percobaan
            self.scroll_count = 0 # Reset scroll count untuk setiap percobaan
            self.start_time = None # Reset start time
            self.no_new_urls_consecutive_scrolls = 0 # Reset counter

            try:
                self._initialize_webdriver()
                if not self.driver: # Jika inisialisasi driver gagal, lewati percobaan ini
                    continue

                self.driver.get(self.config["channel_url"])
                # Tunggu hingga elemen body atau elemen penting lainnya muncul
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                self._log(f"Berhasil membuka URL: {self.config['channel_url']}")
                self.status_callback("Membuka URL channel...")

                self._scrape_shorts_data()

                if len(self.scraped_data) > 0:
                    self._log("Scraping berhasil pada percobaan ini.")
                    break # Berhasil, keluar dari loop retry
                else:
                    self._log("Tidak ada URL Shorts ditemukan pada percobaan ini. Mengulang...")
                    self.status_callback("Tidak ada URL ditemukan. Mengulang...")

            except TimeoutException:
                self._log("Timeout saat memuat halaman atau mencari elemen.")
                self.status_callback("Error: Timeout saat memuat halaman. Coba lagi...")
            except WebDriverException as e:
                self._log(f"Kesalahan WebDriver: {e}")
                self.status_callback(f"Error WebDriver: {e}. Coba lagi...")
            except Exception as e:
                self._log(f"Terjadi kesalahan tak terduga: {e}")
                self.status_callback(f"Error tak terduga: {e}. Coba lagi...")
            finally:
                self._quit_driver() # Pastikan driver ditutup setiap kali setelah percobaan

        # Tampilkan statistik akhir setelah semua percobaan selesai
        self._display_final_stats()

    def _display_final_stats(self):
        """
        Menampilkan statistik akhir proses scraping.
        """
        total_time = "N/A"
        if self.start_time:
            total_time_seconds = time.time() - self.start_time
            total_time = f"{total_time_seconds:.2f} detik"

        self._log(f"\n--- Statistik Akhir ---")
        self._log(f"Jumlah URL berhasil dikumpulkan: {len(self.scraped_data)}")
        self._log(f"Waktu proses total: {total_time}")
        self._log(f"Jumlah scroll dilakukan: {self.scroll_count}")
        self._log(f"Lokasi folder output: {os.path.abspath(self.output_folder)}")
        self._log(f"----------------------")

        self.status_callback(f"Selesai! {len(self.scraped_data)} URL terkumpul.")
        self.progress_callback(len(self.scraped_data), len(self.scraped_data)) # Selesaikan progress bar

        if len(self.scraped_data) > 0:
            self._save_results()
            messagebox.showinfo("Scraping Selesai",
                                f"Scraping selesai!\n"
                                f"Jumlah URL berhasil dikumpulkan: {len(self.scraped_data)}\n"
                                f"Waktu proses total: {total_time}\n"
                                f"Hasil disimpan di: {os.path.abspath(self.output_folder)}")
        else:
            messagebox.showwarning("Scraping Selesai",
                                   "Scraping selesai, namun tidak ada URL Shorts yang ditemukan.")


    def _save_results(self):
        """
        Menyimpan hasil scraping ke file TXT dan XLSX.
        """
        self._log("Menyimpan hasil scraping...")
        # Pastikan folder output ada
        os.makedirs(self.output_folder, exist_ok=True)

        # Simpan ke TXT
        txt_path = os.path.join(self.output_folder, "scraped_urls.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            for item in self.scraped_data:
                f.write(item["URL Video"] + "\n")
        self._log(f"URL berhasil disimpan ke: {txt_path}")

        # Simpan ke Excel
        xlsx_path = os.path.join(self.output_folder, "YouTube_Shorts_Scraped_Details.xlsx")
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "YouTube Shorts"

        sheet.append(["URL Video", "Title"])
        for item in self.scraped_data:
            sheet.append([item["URL Video"], item["Title"]])
        workbook.save(xlsx_path)
        self._log(f"Detail berhasil disimpan ke: {xlsx_path}")
        self.status_callback("Hasil disimpan ke file.")


    def _quit_driver(self):
        """
        Menutup browser Selenium jika sedang berjalan.
        """
        if self.driver:
            self._log("Menutup browser Selenium...")
            try:
                self.driver.quit()
                self._log("Browser berhasil ditutup.")
            except WebDriverException as e:
                self._log(f"Error saat menutup browser: {e}")
            finally:
                self.driver = None

    def stop_scraping(self):
        """
        Mengatur flag untuk menghentikan proses scraping.
        """
        self._log("Permintaan untuk menghentikan scraping diterima.")
        self.stop_scraping_flag.set()
        self._quit_driver()


class ScrapingApp(tk.Tk):
    """
    Kelas ini mewakili aplikasi GUI utama untuk bot scraping.
    """
    def __init__(self):
        """
        Inisialisasi aplikasi GUI.
        """
        super().__init__()
        self.title("YouTube Shorts Scraper Bot")
        self.geometry("800x800") # Tinggi sedikit ditingkatkan untuk area log dan random delay
        self.scraper = None
        self.scraping_thread = None

        self._create_widgets()
        self._load_saved_settings()

    def _create_widgets(self):
        """
        Membuat semua elemen GUI.
        """
        main_frame = ttk.Frame(self)
        main_frame.pack(pady=10, padx=10, expand=True, fill="both")

        # Input Fields Frame
        input_frame = ttk.LabelFrame(main_frame, text="Pengaturan Umum")
        input_frame.pack(padx=5, pady=5, fill="x") # Padding disesuaikan

        # Output Folder
        ttk.Label(input_frame, text="Folder Output:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.output_folder_var = tk.StringVar(value=os.path.join(os.getcwd(), "scraped_results"))
        ttk.Entry(input_frame, textvariable=self.output_folder_var, width=50).grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        ttk.Button(input_frame, text="Browse", command=self._browse_output_folder).grid(row=0, column=2, padx=5, pady=2)

        # Channel URL
        ttk.Label(input_frame, text="URL Channel Shorts:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.channel_url_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.channel_url_var, width=50).grid(row=1, column=1, columnspan=2, padx=5, pady=2, sticky="ew")

        # Jumlah URL Target
        ttk.Label(input_frame, text="Jumlah URL Video yang Ingin Dikumpulkan (0 = Semua):").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.target_url_count_var = tk.IntVar(value=0)
        ttk.Entry(input_frame, textvariable=self.target_url_count_var, width=10).grid(row=2, column=1, padx=5, pady=2, sticky="w")

        # Scroll Delay (Kembali ke satu input bilangan bulat)
        ttk.Label(input_frame, text="Scroll Delay (detik, akan dirandom dari 1 hingga nilai ini):").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.scroll_delay_var = tk.IntVar(value=5) # Default 5 detik
        ttk.Entry(input_frame, textvariable=self.scroll_delay_var, width=10).grid(row=3, column=1, padx=5, pady=2, sticky="w")

        # Number of Retries
        ttk.Label(input_frame, text="Jumlah Percobaan Penuh Scraping:").grid(row=4, column=0, padx=5, pady=2, sticky="w")
        self.num_retries_var = tk.IntVar(value=1)
        ttk.Entry(input_frame, textvariable=self.num_retries_var, width=10).grid(row=4, column=1, padx=5, pady=2, sticky="w")

        # Proxy Input
        ttk.Label(input_frame, text="Proxy (opsional, ip:port atau user:pass@ip:port):").grid(row=5, column=0, padx=5, pady=2, sticky="w")
        self.proxy_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.proxy_var, width=50).grid(row=5, column=1, columnspan=2, padx=5, pady=2, sticky="ew")

        input_frame.grid_columnconfigure(1, weight=1)

        # Selenium Browser Options Frame
        browser_options_frame = ttk.LabelFrame(main_frame, text="Opsi Browser Selenium")
        browser_options_frame.pack(padx=5, pady=5, fill="x") # Padding disesuaikan

        self.headless_mode_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(browser_options_frame, text="Headless Mode", variable=self.headless_mode_var).grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.disable_sandbox_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(browser_options_frame, text="Disable Sandbox", variable=self.disable_sandbox_var).grid(row=0, column=1, padx=5, pady=2, sticky="w")
        self.disable_dev_shm_usage_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(browser_options_frame, text="Disable /dev/shm Usage", variable=self.disable_dev_shm_usage_var).grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.disable_notifications_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(browser_options_frame, text="Disable Notifications", variable=self.disable_notifications_var).grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.disable_extensions_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(browser_options_frame, text="Disable Extensions", variable=self.disable_extensions_var).grid(row=1, column=1, padx=5, pady=2, sticky="w")
        self.disable_gpu_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(browser_options_frame, text="Disable GPU", variable=self.disable_gpu_var).grid(row=1, column=2, padx=5, pady=2, sticky="w")
        self.enable_webgl_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(browser_options_frame, text="Enable WebGL", variable=self.enable_webgl_var).grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.enable_smooth_scrolling_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(browser_options_frame, text="Enable Smooth Scrolling", variable=self.enable_smooth_scrolling_var).grid(row=2, column=1, padx=5, pady=2, sticky="w")
        self.set_language_en_us_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(browser_options_frame, text="Set Language ke English (US)", variable=self.set_language_en_us_var).grid(row=2, column=2, padx=5, pady=2, sticky="w")
        self.start_maximized_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(browser_options_frame, text="Start Browser in Maximized Mode", variable=self.start_maximized_var).grid(row=3, column=0, padx=5, pady=2, sticky="w")

        # Scrolling Method Dropdown
        ttk.Label(browser_options_frame, text="Metode Scrolling:").grid(row=4, column=0, padx=5, pady=2, sticky="w")
        self.scrolling_method_var = tk.StringVar(value="Send END Key")
        self.scrolling_method_dropdown = ttk.Combobox(browser_options_frame, textvariable=self.scrolling_method_var,
                                                    values=["Send END Key", "Scroll to Bottom (JS)", "Scroll by Viewport (JS)"])
        self.scrolling_method_dropdown.grid(row=4, column=1, padx=5, pady=2, sticky="ew")
        self.scrolling_method_dropdown.set("Send END Key") # Default value

        for i in range(3):
            browser_options_frame.grid_columnconfigure(i, weight=1)

        # Action Buttons (Dipindahkan ke atas log)
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10, fill="x") # Menggunakan fill="x" agar tombol memanjang

        self.start_button = ttk.Button(button_frame, text="Mulai Scraping", command=self._start_scraping)
        self.start_button.pack(side=tk.LEFT, expand=True, fill="both", padx=5) # Responsive
        self.cancel_button = ttk.Button(button_frame, text="Batal/Hentikan", command=self._cancel_scraping, state="disabled")
        self.cancel_button.pack(side=tk.LEFT, expand=True, fill="both", padx=5) # Responsive
        self.reset_button = ttk.Button(button_frame, text="Reset", command=self._reset_gui)
        self.reset_button.pack(side=tk.LEFT, expand=True, fill="both", padx=5) # Responsive
        self.open_output_button = ttk.Button(button_frame, text="Buka Folder Output", command=self._open_output_folder)
        self.open_output_button.pack(side=tk.LEFT, expand=True, fill="both", padx=5) # Responsive

        # Log Area (dipindahkan ke bawah tombol aksi)
        ttk.Label(main_frame, text="Log Proses:").pack(pady=5, padx=10, fill="x")
        self.log_area = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=15, state="disabled") # Tinggi disesuaikan
        self.log_area.pack(pady=5, padx=10, expand=True, fill="both")

        # Progress Bar & Status Area (tetap di bawah log)
        self.progress_bar_label = ttk.Label(main_frame, text="Progress: 0%")
        self.progress_bar_label.pack(pady=5, padx=10, fill="x")
        self.progress_bar = ttk.Progressbar(main_frame, orient="horizontal", length=600, mode="determinate")
        self.progress_bar.pack(pady=5, padx=10, fill="x")

        self.status_label = ttk.Label(main_frame, text="Status: Siap", anchor="w")
        self.status_label.pack(pady=5, padx=10, fill="x")

        # Handle window close event
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _browse_output_folder(self):
        """
        Membuka dialog untuk memilih folder output.
        """
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.output_folder_var.set(folder_selected)

    def _log_to_gui(self, message):
        """
        Menulis pesan ke area log GUI.
        """
        self.log_area.config(state="normal")
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state="disabled")
        self.update_idletasks() # Perbarui GUI segera

    def _update_progress(self, current, total):
        """
        Memperbarui progress bar dan label persentase.

        Args:
            current (int): Jumlah URL yang sudah terkumpul.
            total (int): Jumlah URL target (0 jika tidak ada target).
        """
        if total > 0:
            percentage = (current / total) * 100
            self.progress_bar.config(mode="determinate", value=percentage)
            self.progress_bar_label.config(text=f"Progress: {percentage:.2f}% ({current}/{total} URL)")
        else:
            # Mode indeterminate jika tidak ada target, hanya tampilkan jumlah URL terkumpul
            self.progress_bar.config(mode="indeterminate")
            if self.progress_bar.cget("mode") == "indeterminate" and self.progress_bar["value"] == 0:
                self.progress_bar.start() # Start animation for indeterminate mode only if not already started
            self.progress_bar_label.config(text=f"Progress: Menemukan {current} URL...")
        self.update_idletasks()

    def _update_status(self, message):
        """
        Memperbarui label status di GUI.
        """
        self.status_label.config(text=f"Status: {message}")
        self.update_idletasks()

    def _start_scraping(self):
        """
        Memulai proses scraping dalam thread terpisah.
        """
        # Validasi input
        channel_url = self.channel_url_var.get().strip()
        if not channel_url:
            messagebox.showerror("Input Error", "URL Channel Shorts tidak boleh kosong.")
            return
        if not channel_url.startswith("http"):
            messagebox.showerror("Input Error", "URL Channel Shorts tidak valid. Harus dimulai dengan http:// atau https://")
            return

        try:
            target_url_count = int(self.target_url_count_var.get())
            if target_url_count < 0:
                raise ValueError("Jumlah URL tidak boleh negatif.")
        except ValueError:
            messagebox.showerror("Input Error", "Jumlah URL Video yang Ingin Dikumpulkan harus berupa angka non-negatif.")
            return

        try:
            # Scroll Delay kini bilangan bulat
            scroll_delay = int(self.scroll_delay_var.get())
            if scroll_delay <= 0:
                raise ValueError("Scroll Delay harus berupa bilangan bulat positif.")
        except ValueError as e:
            messagebox.showerror("Input Error", f"Kesalahan pada Scroll Delay: {e}\nPastikan nilai adalah bilangan bulat positif.")
            return

        try:
            num_retries = int(self.num_retries_var.get())
            if num_retries < 1:
                raise ValueError("Jumlah percobaan harus minimal 1.")
        except ValueError:
            messagebox.showerror("Input Error", "Jumlah Percobaan Penuh Scraping harus berupa angka positif.")
            return

        output_folder = self.output_folder_var.get()
        if not os.path.exists(output_folder):
            try:
                os.makedirs(output_folder)
                self._log_to_gui(f"Folder output '{output_folder}' berhasil dibuat.")
            except OSError as e:
                messagebox.showerror("Folder Error", f"Gagal membuat folder output: {e}")
                return

        self._save_settings() # Simpan pengaturan saat ini

        # Nonaktifkan tombol Start, aktifkan tombol Cancel
        self.start_button.config(state="disabled")
        self.cancel_button.config(state="normal")
        self.reset_button.config(state="disabled")
        self.open_output_button.config(state="disabled")

        # Reset log area dan progress bar
        self.log_area.config(state="normal")
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state="disabled")
        self.progress_bar.config(value=0) # Reset value to 0
        if target_url_count == 0:
            self.progress_bar.config(mode="indeterminate")
            self.progress_bar.start()
        else:
            self.progress_bar.config(mode="determinate")

        self.progress_bar_label.config(text="Progress: 0%")
        self.status_label.config(text="Status: Memulai...")

        # Kumpulkan konfigurasi untuk scraper
        config = {
            "output_folder": output_folder,
            "channel_url": channel_url,
            "target_url_count": target_url_count,
            "scroll_delay": scroll_delay, # Menggunakan satu nilai scroll delay
            "number_of_retries": num_retries,
            "proxy_input": self.proxy_var.get().strip(),
            "headless_mode": self.headless_mode_var.get(),
            "disable_sandbox": self.disable_sandbox_var.get(),
            "disable_dev_shm_usage": self.disable_dev_shm_usage_var.get(),
            "disable_notifications": self.disable_notifications_var.get(),
            "disable_extensions": self.disable_extensions_var.get(),
            "disable_gpu": self.disable_gpu_var.get(),
            "enable_webgl": self.enable_webgl_var.get(),
            "enable_smooth_scrolling": self.enable_smooth_scrolling_var.get(),
            "set_language_en_us": self.set_language_en_us_var.get(),
            "start_maximized": self.start_maximized_var.get(),
            "scrolling_method": self.scrolling_method_var.get()
        }

        self.scraper = YouTubeShortsScraper(output_folder, self._log_to_gui, self._update_progress, self._update_status, config)
        self.scraping_thread = threading.Thread(target=self.scraper.run_scraper)
        self.scraping_thread.daemon = True # Biarkan thread berhenti saat aplikasi ditutup
        self.scraping_thread.start()

        self._update_status("Scraping sedang berjalan...")

        # Monitor thread selesai untuk mengaktifkan kembali tombol
        self.after(100, self._check_scraping_completion)

    def _check_scraping_completion(self):
        """
        Memeriksa apakah thread scraping sudah selesai dan mengaktifkan kembali tombol.
        """
        if self.scraping_thread and not self.scraping_thread.is_alive():
            self._enable_buttons()
            self.progress_bar.stop() # Pastikan progress bar indeterminate berhenti
        else:
            self.after(100, self._check_scraping_completion)


    def _cancel_scraping(self):
        """
        Menghentikan proses scraping.
        """
        if self.scraper:
            self.scraper.stop_scraping()
            self._log_to_gui("Membatalkan proses scraping...")
            self._update_status("Scraping dibatalkan.")
        self._enable_buttons()
        self.progress_bar.stop() # Pastikan progress bar indeterminate berhenti

    def _reset_gui(self):
        """
        Mengatur ulang semua input field ke nilai default.
        """
        self.output_folder_var.set(os.path.join(os.getcwd(), "scraped_results"))
        self.channel_url_var.set("")
        self.target_url_count_var.set(0)
        self.scroll_delay_var.set(5) # Default 5 detik (integer)
        self.num_retries_var.set(1)
        self.proxy_var.set("")
        self.headless_mode_var.set(True)
        self.disable_sandbox_var.set(True)
        self.disable_dev_shm_usage_var.set(False)
        self.disable_notifications_var.set(True)
        self.disable_extensions_var.set(True)
        self.disable_gpu_var.set(True)
        self.enable_webgl_var.set(False)
        self.enable_smooth_scrolling_var.set(True)
        self.set_language_en_us_var.set(True)
        self.start_maximized_var.set(False)
        self.scrolling_method_var.set("Send END Key")

        self.log_area.config(state="normal")
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state="disabled")
        self.progress_bar.config(value=0, mode="determinate")
        self.progress_bar.stop()
        self.progress_bar_label.config(text="Progress: 0%")
        self.status_label.config(text="Status: Siap")

        self._enable_buttons()
        self._log_to_gui("GUI telah direset ke pengaturan default.")

    def _open_output_folder(self):
        """
        Membuka folder output di file explorer sistem.
        """
        output_folder = self.output_folder_var.get()
        if os.path.exists(output_folder):
            try:
                # Periksa OS untuk menjalankan perintah yang sesuai
                if os.name == 'nt':  # Windows
                    os.startfile(output_folder)
                elif os.name == 'posix': # macOS, Linux, Unix
                    import subprocess
                    subprocess.call(['xdg-open', output_folder]) # Umum untuk Linux
                else:
                    messagebox.showerror("Error", "Sistem operasi tidak didukung untuk membuka folder secara otomatis. Harap buka secara manual.")
            except Exception as e:
                messagebox.showerror("Error", f"Gagal membuka folder: {e}\nHarap buka secara manual: {output_folder}")
        else:
            messagebox.showerror("Error", "Folder output tidak ditemukan. Pastikan sudah ada atau proses scraping sudah selesai.")

    def _enable_buttons(self):
        """
        Mengaktifkan kembali tombol Start dan Reset, menonaktifkan tombol Cancel.
        """
        self.start_button.config(state="normal")
        self.cancel_button.config(state="disabled")
        self.reset_button.config(state="normal")
        self.open_output_button.config(state="normal")

    def _save_settings(self):
        """
        Menyimpan pengaturan GUI ke file JSON.
        """
        settings = {
            "output_folder": self.output_folder_var.get(),
            "channel_url": self.channel_url_var.get(),
            "target_url_count": self.target_url_count_var.get(),
            "scroll_delay": self.scroll_delay_var.get(), # Hanya satu nilai
            "num_retries": self.num_retries_var.get(),
            "proxy_input": self.proxy_var.get(),
            "headless_mode": self.headless_mode_var.get(),
            "disable_sandbox": self.disable_sandbox_var.get(),
            "disable_dev_shm_usage": self.disable_dev_shm_usage_var.get(),
            "disable_notifications": self.disable_notifications_var.get(),
            "disable_extensions": self.disable_extensions_var.get(),
            "disable_gpu": self.disable_gpu_var.get(),
            "enable_webgl": self.enable_webgl_var.get(),
            "enable_smooth_scrolling": self.enable_smooth_scrolling_var.get(),
            "set_language_en_us": self.set_language_en_us_var.get(),
            "start_maximized": self.start_maximized_var.get(),
            "scrolling_method": self.scrolling_method_var.get()
        }
        try:
            with open("scraper_settings.json", "w") as f:
                json.dump(settings, f, indent=4)
            self._log_to_gui("Pengaturan berhasil disimpan.")
        except Exception as e:
            self._log_to_gui(f"Error menyimpan pengaturan: {e}")

    def _load_saved_settings(self):
        """
        Memuat pengaturan GUI dari file JSON.
        """
        try:
            if os.path.exists("scraper_settings.json"):
                with open("scraper_settings.json", "r") as f:
                    settings = json.load(f)
                self.output_folder_var.set(settings.get("output_folder", os.path.join(os.getcwd(), "scraped_results")))
                self.channel_url_var.set(settings.get("channel_url", ""))
                self.target_url_count_var.set(settings.get("target_url_count", 0))
                # Ambil nilai default jika tidak ada di settings.json atau jika dulu ada min/max
                self.scroll_delay_var.set(int(settings.get("scroll_delay", settings.get("max_scroll_delay", 5)))) # Konversi ke int
                self.num_retries_var.set(settings.get("num_retries", 1))
                self.proxy_var.set(settings.get("proxy_input", ""))
                self.headless_mode_var.set(settings.get("headless_mode", True))
                self.disable_sandbox_var.set(settings.get("disable_sandbox", True))
                self.disable_dev_shm_usage_var.set(settings.get("disable_dev_shm_usage", False))
                self.disable_notifications_var.set(settings.get("disable_notifications", True))
                self.disable_extensions_var.set(settings.get("disable_extensions", True))
                self.disable_gpu_var.set(settings.get("disable_gpu", True))
                self.enable_webgl_var.set(settings.get("enable_webgl", False))
                self.enable_smooth_scrolling_var.set(settings.get("enable_smooth_scrolling", True))
                self.set_language_en_us_var.set(settings.get("set_language_en_us", True))
                self.start_maximized_var.set(settings.get("start_maximized", False))
                self.scrolling_method_var.set(settings.get("scrolling_method", "Send END Key"))
                self._log_to_gui("Pengaturan sebelumnya berhasil dimuat.")
            else:
                self._log_to_gui("File pengaturan tidak ditemukan. Menggunakan nilai default.")
        except Exception as e:
            self._log_to_gui(f"Error memuat pengaturan: {e}. Menggunakan nilai default.")

    def _on_closing(self):
        """
        Menangani event penutupan jendela GUI.
        """
        if self.scraping_thread and self.scraping_thread.is_alive():
            if messagebox.askyesno("Keluar Aplikasi", "Scraping sedang berjalan. Apakah Anda yakin ingin keluar? Ini akan menghentikan proses scraping."):
                self._cancel_scraping() # Hentikan scraping jika sedang berjalan
                self.destroy()
        else:
            self.destroy()

if __name__ == "__main__":
    app = ScrapingApp()
    app.mainloop()
