# main.py

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import threading
import os
import time
import random
from datetime import datetime
import json
import subprocess # To run yt-dlp
from urllib.parse import urljoin, urlparse

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
    This class handles the logic for scraping and downloading YouTube Shorts.
    """
    def __init__(self, output_folder, log_callback, progress_callback, status_callback, config):
        """
        Initializes the scraper.

        Args:
            output_folder (str): Output folder location.
            log_callback (function): Callback function for logging to GUI.
            progress_callback (function): Callback function for updating GUI progress bar.
            status_callback (function): Callback function for updating GUI status.
            config (dict): Scraping and download configuration from GUI.
        """
        self.output_folder = output_folder
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.status_callback = status_callback
        self.config = config
        self.driver = None
        self.scraped_data = [] # List to store {'URL': ..., 'Title': ..., 'Description': ..., 'Download_Status': ...}
        self.stop_scraping_flag = threading.Event() # Event to stop scraping
        self.start_time = None
        self.scroll_count = 0
        self.no_new_urls_consecutive_scrolls = 0 # Counter for potential blocking detection
        self.download_errors = [] # List to store video URLs that failed to download

    def _log(self, message):
        """
        Logs messages to the GUI log area and a log file.
        Each log entry includes a timestamp.

        Args:
            message (str): Message to log.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        self.log_callback(log_message)
        # Ensure the output folder exists before writing the log file
        os.makedirs(self.output_folder, exist_ok=True)
        with open(os.path.join(self.output_folder, "scraping_log.txt"), "a", encoding="utf-8") as f:
            f.write(log_message + "\n")

    def _initialize_webdriver(self):
        """
        Initializes the Selenium WebDriver with configured options.
        """
        self._log("Initializing WebDriver...")
        options = Options()

        # Configure browser options from GUI
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

        # Proxy Configuration
        if self.config["proxy_input"]:
            options.add_argument(f"--proxy-server={self.config['proxy_input']}")
            self._log(f"Using proxy: {self.config['proxy_input']}")

        try:
            # Use ChromeDriverManager to manage ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(30) # Set timeout for page loading
            self._log("WebDriver initialized successfully.")
        except WebDriverException as e:
            self._log(f"Error initializing WebDriver: {e}")
            self.status_callback("Error: Failed to initialize browser. Make sure Chrome is installed and up-to-date.")
            self.driver = None # Ensure driver is None if initialization fails
            raise

    def _get_video_description(self, video_url):
        """
        Visits individual video URL to get the description.
        """
        try:
            self._log(f"Visiting {video_url} to get description...")
            self.driver.get(video_url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-watch-flexy, ytm-single-column-watch-next-results")) # Wait for video page to load
            )

            # Try to click "more" or "show more" button if available
            try:
                # Common selector for "show more" button
                more_button = self.driver.find_element(By.CSS_SELECTOR, "tp-yt-paper-button[aria-label*='show more'], ytd-text-inline-expander button")
                if more_button.is_displayed() and more_button.is_enabled():
                    self.driver.execute_script("arguments[0].click();", more_button) # Use JS click for robustness
                    time.sleep(1) # Give time for description to expand
            except NoSuchElementException:
                pass # No 'more' button found

            # Find description element (selectors may vary between Shorts and regular videos)
            description_element = None
            try:
                # Selector for description in ytd-watch-flexy (regular videos)
                description_element = self.driver.find_element(By.CSS_SELECTOR, "ytd-expander #description-inline-expander, #description-inline-expander div.ytd-text-inline-expander")
            except NoSuchElementException:
                try:
                    # Selector for description in Shorts (might be simple text or in a particular div)
                    description_element = self.driver.find_element(By.CSS_SELECTOR, "ytd-reel-player-overlay-renderer #description-text, ytm-autonav-renderer #description-text")
                except NoSuchElementException:
                    pass

            if description_element:
                description = description_element.text.strip()
                self._log(f"Description found: {description[:50]}...") # Log first 50 characters
                return description
            else:
                self._log("Description not found for this video.")
                return ""
        except Exception as e:
            self._log(f"Error getting description from {video_url}: {e}")
            return ""

    def _scrape_shorts_data_phase(self):
        """
        Performs the scraping phase: collecting URLs, Titles, and Descriptions.
        """
        self.scraped_data = []
        urls_found_set = set()
        previous_urls_count = 0
        self.scroll_count = 0
        self.no_new_urls_consecutive_scrolls = 0
        
        # Store initial URL to return to (used if navigating away for description)
        # initial_channel_url = self.driver.current_url # Not used directly in loop, just for context

        try:
            self._log(f"Starting scraping phase for: {self.config['channel_url']}")
            self.driver.get(self.config["channel_url"])
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            self.status_callback("Scraping: Opening channel URL...")

            last_height = self.driver.execute_script("return document.documentElement.scrollHeight")

            if self.config["target_video_count"] == 0:
                self.progress_callback(0, 0) # Indeterminate mode

            while True:
                if self.stop_scraping_flag.is_set():
                    self._log("Scraping process cancelled by user.")
                    self.status_callback("Scraping Cancelled.")
                    return False # Indicate scraping was not successful

                self.scroll_count += 1
                self.status_callback(f"Scraping: Scrolling {self.scroll_count}...")
                self._log(f"Scrolling {self.scroll_count}...")

                # Scrolling method implementation
                if self.config["scrolling_method"] == "Send END Key":
                    self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
                elif self.config["scrolling_method"] == "Scroll to Bottom (JS)":
                    self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                elif self.config["scrolling_method"] == "Scroll by Viewport (JS)":
                    self.driver.execute_script("window.scrollBy(0, window.innerHeight * 0.9);")

                time.sleep(self.config["scroll_delay"]) # Fixed delay

                video_elements = self.driver.find_elements(By.CSS_SELECTOR,
                    "a.shortsLockupViewModelHostEndpoint.reel-item-endpoint[href*='/shorts/'], " +
                    "a.shortsLockupViewModelHostEndpoint.shortsLockupViewModelHostOutsideMetadataEndpoint[href*='/shorts/']"
                )

                num_urls_before_current_scan = len(urls_found_set)

                for element in video_elements:
                    href = element.get_attribute("href")
                    title = ""

                    if element.get_attribute("title"):
                        title = element.get_attribute("title").strip()
                    else:
                        try:
                            title_span = element.find_element(By.CSS_SELECTOR, "span.yt-core-attributed-string")
                            title = title_span.text.strip()
                        except NoSuchElementException:
                            pass

                    if href and "/shorts/" in href:
                        # Ensure URL is absolute
                        if not href.startswith("http"):
                            href = urljoin(self.config['channel_url'], href)

                        if href not in urls_found_set:
                            self.scraped_data.append({"URL Video": href, "Title": title, "Description": "", "Download_Status": "N"})
                            urls_found_set.add(href)
                            self._log(f"Found Shorts (URL): {title} ({href})")

                if len(urls_found_set) > num_urls_before_current_scan:
                    self.no_new_urls_consecutive_scrolls = 0
                else:
                    self.no_new_urls_consecutive_scrolls += 1

                self._log(f"Total unique URLs found during scraping: {len(urls_found_set)}")
                self.progress_callback(len(urls_found_set), self.config["target_video_count"])

                if self.config["target_video_count"] > 0 and len(urls_found_set) >= self.config["target_video_count"]:
                    self._log(f"Target video count ({self.config['target_video_count']}) reached. Stopping scraping.")
                    self.status_callback("Target video count reached. Stopping scraping.")
                    break

                new_height = self.driver.execute_script("return document.documentElement.scrollHeight")
                if new_height == last_height:
                    self._log("No new content to scroll (reached end of page or no new content loaded). Ending scraping.")
                    self.status_callback("No new content to scroll. Stopping scraping.")
                    break
                last_height = new_height

                if self.no_new_urls_consecutive_scrolls >= 5:
                    self._log("Warning: No new Shorts URLs found after several consecutive scrolls.")
                    self._log("This might indicate potential rate limiting, blocking, or no more new Shorts.")
                    self.status_callback("Warning: Potential blocking detected. Proceeding cautiously.")
                    if self.no_new_urls_consecutive_scrolls >= 10:
                        self._log("Stopping scraping due to too many scrolls without finding new URLs.")
                        self.status_callback("Stopped: No new URLs found after many scrolls.")
                        break

            self._log("Scraping phase completed.")
            self.status_callback("Scraping phase completed.")
            return True # Indicate scraping was successful

        except Exception as e:
            self._log(f"Error during scraping phase: {e}")
            self.status_callback(f"Error during scraping: {e}")
            return False # Indicate scraping failed

        finally:
            # The driver will be quit by the run_full_process method, not here
            pass 

    def _get_descriptions_phase(self):
        """
        Visits each scraped video URL to get its description.
        """
        if not self.scraped_data:
            self._log("No videos scraped to get descriptions for.")
            self.status_callback("No videos for description retrieval.")
            return False

        self._log("Starting video description retrieval phase...")
        self.status_callback("Retrieving video descriptions...")
        
        # Re-initialize driver for description retrieval
        try:
            self._initialize_webdriver()
            if not self.driver:
                self._log("Failed to re-initialize WebDriver for description retrieval.")
                return False
        except Exception as e:
            self._log(f"Failed to re-initialize WebDriver for description retrieval: {e}")
            self.status_callback("Error: Cannot get descriptions (browser issue).")
            return False

        # Keep track of the original window handle
        original_window_handle = self.driver.current_window_handle

        for i, item in enumerate(self.scraped_data):
            if self.stop_scraping_flag.is_set():
                self._log("Description retrieval cancelled.")
                self.status_callback("Description retrieval cancelled.")
                self.driver.quit() # Ensure driver is closed if cancelled here
                return False

            self.status_callback(f"Getting description {i+1}/{len(self.scraped_data)} for {item['Title']}...")
            self._log(f"Getting description for: {item['URL Video']}")
            
            # Navigate to the video URL to get description
            try:
                item["Description"] = self._get_video_description(item["URL Video"])
            except Exception as e:
                self._log(f"Failed to get description for {item['URL Video']}: {e}")
                item["Description"] = "" # Set to empty if error

            # After getting description, try to close any new tabs opened and return to original
            # This is important if YouTube opens video in a new tab/window which happens rarely
            if len(self.driver.window_handles) > 1:
                for handle in self.driver.window_handles:
                    if handle != original_window_handle:
                        self.driver.switch_to.window(handle)
                        self.driver.close()
                self.driver.switch_to.window(original_window_handle)
            
            # Add a small delay between description fetches
            time.sleep(random.uniform(1, 3)) # Random delay for description fetching

        self._log("Video description retrieval completed.")
        self.status_callback("Video description retrieval completed.")
        self._quit_driver() # Quit driver after description phase
        return True

    def _download_videos(self):
        """
        Downloads Shorts videos using yt-dlp.
        """
        if not self.scraped_data:
            self._log("No videos to download.")
            self.status_callback("No videos to download.")
            return

        self._log("Starting video download process...")
        self.status_callback("Starting download process...")
        self.download_errors = [] # Reset error list for this download attempt

        batch_size = self.config["batch_size"]
        total_videos = len(self.scraped_data)
        
        # Ensure 'Download_Status' is reset to 'N' for any video that was not previously downloaded
        # or for retries to ensure they are marked 'N' before attempting 'D' or 'E'
        for item in self.scraped_data:
            if item["Download_Status"] != "D": # Only reset if not already downloaded
                item["Download_Status"] = "N"

        for retry_attempt in range(self.config["download_retries"] + 1): # +1 for initial attempt
            if self.stop_scraping_flag.is_set():
                self._log("Download process cancelled by user during retry loop.")
                self.status_callback("Download Cancelled.")
                break

            self._log(f"Starting download attempt {retry_attempt + 1}...")
            # Filter videos that are not yet successfully downloaded
            videos_to_download_in_this_attempt = [
                item for item in self.scraped_data if item["Download_Status"] == "N" or item["Download_Status"] == "E"
            ]

            if not videos_to_download_in_this_attempt:
                self._log("All specified videos have been successfully downloaded or no new videos to attempt.")
                break # All done or no new videos to process

            current_batch_num = 1
            
            for i in range(0, len(videos_to_download_in_this_attempt), batch_size):
                if self.stop_scraping_flag.is_set():
                    self._log("Download process cancelled by user during batch loop.")
                    self.status_callback("Download Cancelled.")
                    break

                batch_videos = videos_to_download_in_this_attempt[i : i + batch_size]
                # Use current timestamp for batch folder to avoid conflicts if retrying
                batch_folder_name = os.path.join(self.output_folder, f"batch_{current_batch_num}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                os.makedirs(batch_folder_name, exist_ok=True)
                self._log(f"Starting download for batch {current_batch_num} to folder: {batch_folder_name}")
                self.status_callback(f"Downloading batch {current_batch_num} (Attempt {retry_attempt + 1})...")

                for video_data in batch_videos:
                    if self.stop_scraping_flag.is_set():
                        break

                    video_url = video_data["URL Video"]
                    video_title = video_data["Title"] if video_data["Title"] else f"Untitled Video {int(time.time())}"
                    # Sanitize title for filename
                    sanitized_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '.', '_', '-')).strip()
                    sanitized_title = sanitized_title.replace(" ", "_") # Replace spaces with underscores
                    if not sanitized_title:
                        sanitized_title = f"Untitled_Video_{hash(video_url) % 100000}" # Fallback if title is empty/invalid
                    sanitized_title = sanitized_title[:100] # Limit filename length

                    self.status_callback(f"Downloading '{sanitized_title}'...")
                    self._log(f"Attempting to download: {video_url} - {sanitized_title}")

                    download_command = ["yt-dlp"]
                    
                    # Add cookies file path if provided
                    if self.config["cookies_file_path"]:
                        # Validate cookies file exists before adding to command
                        if os.path.exists(self.config["cookies_file_path"]):
                            download_command.extend(["--cookies", self.config["cookies_file_path"]])
                            self._log(f"Using cookies from: {self.config['cookies_file_path']}")
                        else:
                            self._log(f"Warning: Cookies file not found at {self.config['cookies_file_path']}. Proceeding without cookies.")


                    # Add quality/format options
                    quality_map = {
                        "Best Quality": "bestvideo+bestaudio/best",
                        "Best Quality format mp4": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
                        "Best Quality format mkv": "bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=mkv]",
                        "1080p format mp4": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]",
                        "1080p format mkv": "bestvideo[height<=1080][ext=webm]+bestaudio[ext=webm]/best[height<=1080][ext=mkv]",
                        "720p format mp4": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]",
                        "720p format mkv": "bestvideo[height<=720][ext=webm]+bestaudio[ext=webm]/best[height<=720][ext=mkv]"
                    }
                    download_format_string = quality_map.get(self.config["download_quality"], "best")
                    download_command.extend(["-f", download_format_string])
                    
                    download_command.extend(["--output", os.path.join(batch_folder_name, f"{sanitized_title}.%(ext)s"), video_url])
                    download_command.append("--no-playlist") # Ensure only single video is downloaded
                    download_command.append("--retries") # Add retries for individual download attempts
                    download_command.append("5") # Example: 5 retries for each video

                    try:
                        # Execute yt-dlp
                        result = subprocess.run(
                            download_command,
                            capture_output=True,
                            text=False, # Important: Read raw bytes
                            check=True,
                            timeout=self.config["download_delay"] * 5, # Timeout is 5x download delay
                            encoding=None # Ensure no automatic decoding here
                        )
                        self._log(f"Successfully downloaded: {video_url}")
                        # Decode stdout with error handling for logging
                        self._log(f"yt-dlp Output: {result.stdout.decode(errors='ignore').strip()}") 
                        video_data["Download_Status"] = "D" # Downloaded

                    except subprocess.CalledProcessError as e:
                        # Decode stderr with error handling, handle None case
                        err_msg = e.stderr.decode(errors='ignore').strip() if e.stderr else "No error message"
                        self._log(f"Error downloading {video_url}: {err_msg}")
                        self.download_errors.append(f"URL: {video_url}\nTitle: {video_title}\nError: {err_msg}\n")
                        video_data["Download_Status"] = "E" # Error
                    except FileNotFoundError:
                        self._log("Error: yt-dlp (or youtube-dl) not found. Make sure it is installed and in your system PATH.")
                        self.status_callback("Error: Downloader not found. Download halted.")
                        self.download_errors.append(f"URL: {video_url}\nTitle: {video_title}\nError: Downloader not found (yt-dlp or youtube-dl).\n")
                        self.stop_scraping_flag.set() # Stop process if downloader is missing
                        break # Exit inner loop
                    except TimeoutError:
                        self._log(f"Download timed out for {video_url}.")
                        self.download_errors.append(f"URL: {video_url}\nTitle: {video_title}\nError: Download timed out.\n")
                        video_data["Download_Status"] = "E"
                    except Exception as e:
                        self._log(f"Unexpected error while downloading {video_url}: {e}")
                        self.download_errors.append(f"URL: {video_url}\nTitle: {video_title}\nError: {e}\n")
                        video_data["Download_Status"] = "E"

                    # Random delay between downloads
                    if self.config["download_delay"] > 0 and not self.stop_scraping_flag.is_set():
                        dl_delay = random.randint(1, self.config["download_delay"])
                        self._log(f"Waiting {dl_delay} seconds (random delay before next download).")
                        time.sleep(dl_delay)

                current_batch_num += 1
                if self.stop_scraping_flag.is_set():
                    break # Exit batch loop if cancellation requested

            if self.stop_scraping_flag.is_set():
                break # Exit retry loop if cancellation requested

            # If all videos were successfully downloaded in this attempt, break out of retry loop
            if all(item["Download_Status"] == "D" for item in self.scraped_data):
                 self._log("All videos successfully downloaded across all retries.")
                 break
            else:
                self._log(f"Download attempt {retry_attempt + 1} finished. Remaining videos to download: {sum(1 for item in self.scraped_data if item['Download_Status'] != 'D')}")
                if retry_attempt < self.config["download_retries"]: # Changed from -1 to just < download_retries
                    self._log("Waiting before next download retry...")
                    time.sleep(self.config["download_delay"] * 2) # Longer delay between full retries

        self._log("Video download process completed.")
        self.status_callback("Download completed.")

    # --- Renamed from run_scraper to run_full_process ---
    def run_full_process(self):
        """
        Runs the entire process: scraping, description retrieval, and downloading.
        This method is called from the GUI thread.
        """
        self.start_time = time.time() # Start global timer

        # Phase 1: Scraping
        scraping_successful = False
        # Allow 1 initial attempt + X retries for scraping/driver init
        # Use config["download_retries"] for the number of retries, meaning total attempts = retries + 1
        for retry_attempt in range(self.config["download_retries"] + 1): 
            if self.stop_scraping_flag.is_set():
                break
            
            self._log(f"Attempting to start browser and scrape (Trial {retry_attempt + 1})...")
            self.status_callback(f"Starting browser & scraping (Trial {retry_attempt + 1})...")
            
            try:
                # Initialize driver here, so each retry gets a fresh driver
                self._initialize_webdriver() 
                if not self.driver: # Check if driver failed to initialize
                    self._log("WebDriver initialization failed. Retrying...")
                    time.sleep(self.config["scroll_delay"] * 2) # Add a delay before retrying driver init
                    continue # Skip to next retry attempt

                # If driver initialized, proceed with scraping
                scraping_successful = self._scrape_shorts_data_phase()
                if scraping_successful:
                    self._log("Scraping phase completed successfully.")
                    break # Exit retry loop if scraping succeeded
                else:
                    self._log("Scraping phase failed or yielded no data. Retrying...")
                    # The _scrape_shorts_data_phase itself handles closing the driver.
                    time.sleep(self.config["scroll_delay"] * 2) # Delay before retrying scraping

            except Exception as e:
                self._log(f"An unexpected error occurred during scraping phase setup or execution: {e}")
                self.status_callback(f"Error during scraping setup: {e}. Retrying...")
                time.sleep(self.config["scroll_delay"] * 2) # Delay before retrying after an exception
            finally:
                # Ensure driver is always quit if it was initialized, before the next retry
                if self.driver:
                    self._quit_driver()
        
        # After the retry loop, check if scraping was successful
        if not scraping_successful or self.stop_scraping_flag.is_set():
            self._log("Scraping phase failed after all retries or was cancelled.")
            self._display_final_stats() # Show stats even if scraping failed or cancelled
            return # Exit if scraping failed or cancelled

        # Phase 2: Description Retrieval
        self.status_callback("Starting description retrieval phase...")
        description_successful = self._get_descriptions_phase()

        if not description_successful or self.stop_scraping_flag.is_set():
            self._display_final_stats() # Show stats even if description retrieval failed or cancelled
            return # Exit if description retrieval failed or cancelled

        # Phase 3: Download (with retries)
        if self.scraped_data:
            self._download_videos()
        else:
            self._log("No videos to download after scraping and description retrieval phases.")

        # Save final results and display stats
        self._save_final_results()
        self._display_final_stats()


    def _save_final_results(self):
        """
        Saves all final results to a comprehensive TXT file, batch Excel files, and download error file.
        """
        self._log("Saving final scraping and download results...")
        os.makedirs(self.output_folder, exist_ok=True)

        # Save all_scraped_details.txt
        all_details_txt_path = os.path.join(self.output_folder, "all_scraped_details.txt")
        with open(all_details_txt_path, "w", encoding="utf-8") as f:
            for item in self.scraped_data:
                # Ensure no None values for output
                url_val = item.get("URL Video", "")
                title_val = item.get("Title", "")
                desc_val = item.get("Description", "")
                f.write(f"{url_val} | {title_val} | {desc_val}\n")
        self._log(f"All URL, Title, Description details saved to: {all_details_txt_path}")

        # Save batch Excel files
        batch_size = self.config["batch_size"]
        total_videos = len(self.scraped_data)
        current_batch_num = 1
        for i in range(0, total_videos, batch_size):
            batch_videos = self.scraped_data[i : i + batch_size]
            # Use current timestamp for batch folder to avoid conflicts if retrying
            batch_folder_name = os.path.join(self.output_folder, f"batch_{current_batch_num}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            os.makedirs(batch_folder_name, exist_ok=True) # Ensure batch folder exists
            xlsx_path = os.path.join(batch_folder_name, f"YouTube_Shorts_Batch_{current_batch_num}.xlsx")
            
            workbook = openpyxl.Workbook()
            sheet = workbook.active
            sheet.title = f"Batch {current_batch_num} Shorts"
            sheet.append(["Video URL", "Title", "Description", "Download Status (D/N/E)"])
            for item in batch_videos:
                # Ensure no None values for output
                url_val = item.get("URL Video", "")
                title_val = item.get("Title", "")
                desc_val = item.get("Description", "")
                status_val = item.get("Download_Status", "N") # Default to Not Downloaded
                sheet.append([url_val, title_val, desc_val, status_val])
            workbook.save(xlsx_path)
            self._log(f"Batch {current_batch_num} details saved to: {xlsx_path}")
            current_batch_num += 1

        # Save error file
        if self.download_errors:
            error_file_path = os.path.join(self.output_folder, "download_errors.txt")
            with open(error_file_path, "w", encoding="utf-8") as f:
                for error_entry in self.download_errors:
                    f.write(error_entry + "\n" + "="*50 + "\n")
            self._log(f"Download error details saved to: {error_file_path}")
        else:
            self._log("No download errors recorded.")

        self._log("Final results saving completed.")


    def _display_final_stats(self):
        """
        Displays final statistics of the scraping and downloading process.
        """
        total_time = "N/A"
        if self.start_time:
            total_time_seconds = time.time() - self.start_time
            total_time = f"{total_time_seconds:.2f} seconds"

        downloaded_count = sum(1 for item in self.scraped_data if item["Download_Status"] == "D")
        not_downloaded_count = sum(1 for item in self.scraped_data if item["Download_Status"] == "N")
        error_download_count = sum(1 for item in self.scraped_data if item["Download_Status"] == "E")

        self._log(f"\n--- Final Statistics ---")
        self._log(f"Total Shorts URLs found: {len(self.scraped_data)}")
        self._log(f"Successfully Downloaded Videos: {downloaded_count}")
        self._log(f"Videos Not Downloaded (cancelled/not attempted): {not_downloaded_count}")
        self._log(f"Videos Failed to Download (Error): {error_download_count}")
        self._log(f"Total Process Time: {total_time}")
        self._log(f"Total scrolls performed: {self.scroll_count}")
        self._log(f"Output folder location: {os.path.abspath(self.output_folder)}")
        self._log(f"----------------------")

        self.status_callback(f"Process Complete! {downloaded_count} videos downloaded. {error_download_count} errors.")
        self.progress_callback(len(self.scraped_data), len(self.scraped_data)) # Finalize progress bar

        messagebox.showinfo("Process Complete",
                            f"Scraping & Download Process Complete!\n"
                            f"Total URLs Found: {len(self.scraped_data)}\n"
                            f"Videos Successfully Downloaded: {downloaded_count}\n"
                            f"Videos Failed to Download: {error_download_count}\n"
                            f"Total Time: {total_time}\n"
                            f"Results and Logs are in: {os.path.abspath(self.output_folder)}")


    def _quit_driver(self):
        """
        Closes the Selenium browser if it's running.
        """
        if self.driver:
            self._log("Closing Selenium browser...")
            try:
                self.driver.quit()
                self._log("Browser closed successfully.")
            except WebDriverException as e:
                self._log(f"Error closing browser: {e}")
            finally:
                self.driver = None

    def stop_scraping(self):
        """
        Sets the flag to stop the scraping/downloading process.
        """
        self._log("Request to stop process (scraping/download) received.")
        self.stop_scraping_flag.set()
        self._quit_driver()


class ScrapingApp(tk.Tk):
    """
    This class represents the main GUI application for the YouTube Shorts scraper and downloader.
    """
    def __init__(self):
        """
        Initializes the GUI application.
        """
        super().__init__()
        self.title("YouTube Shorts Scraper & Downloader Bot")
        self.geometry("850x880") # Adjusted height for new cookies input
        self.scraper = None
        self.scraping_thread = None

        self._create_widgets()
        self._load_saved_settings()

    def _create_widgets(self):
        """
        Creates all GUI elements.
        """
        main_frame = ttk.Frame(self)
        main_frame.pack(pady=10, padx=10, expand=True, fill="both")

        # Input Fields Frame
        input_frame = ttk.LabelFrame(main_frame, text="General Settings")
        input_frame.pack(padx=5, pady=5, fill="x")

        # Output Folder
        ttk.Label(input_frame, text="Output Folder:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.output_folder_var = tk.StringVar(value=os.path.join(os.getcwd(), "scraped_results"))
        ttk.Entry(input_frame, textvariable=self.output_folder_var, width=50).grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        ttk.Button(input_frame, text="Browse", command=self._browse_output_folder).grid(row=0, column=2, padx=5, pady=2)

        # Channel URL
        ttk.Label(input_frame, text="YouTube Channel URL:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.channel_url_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.channel_url_var, width=50).grid(row=1, column=1, columnspan=2, padx=5, pady=2, sticky="ew")

        # Target Video Count
        ttk.Label(input_frame, text="Target Video Count (0 = All):").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.target_video_count_var = tk.IntVar(value=0)
        ttk.Entry(input_frame, textvariable=self.target_video_count_var, width=10).grid(row=2, column=1, padx=5, pady=2, sticky="w")

        # Scroll Delay
        ttk.Label(input_frame, text="Scroll Delay (seconds):").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.scroll_delay_var = tk.IntVar(value=5) # Default 5 seconds
        ttk.Entry(input_frame, textvariable=self.scroll_delay_var, width=10).grid(row=3, column=1, padx=5, pady=2, sticky="w")

        # Download Delay
        ttk.Label(input_frame, text="Download Delay (seconds):").grid(row=4, column=0, padx=5, pady=2, sticky="w")
        self.download_delay_var = tk.IntVar(value=5) # Default 5 seconds
        ttk.Entry(input_frame, textvariable=self.download_delay_var, width=10).grid(row=4, column=1, padx=5, pady=2, sticky="w")

        # Download Retries
        ttk.Label(input_frame, text="Download Retries:").grid(row=5, column=0, padx=5, pady=2, sticky="w")
        self.download_retries_var = tk.IntVar(value=3) # Default 3 retries
        ttk.Entry(input_frame, textvariable=self.download_retries_var, width=10).grid(row=5, column=1, padx=5, pady=2, sticky="w")
        
        # Download Batch Size
        ttk.Label(input_frame, text="Download Batch Size:").grid(row=6, column=0, padx=5, pady=2, sticky="w")
        self.batch_size_var = tk.IntVar(value=20) # Default 20 videos per batch
        ttk.Entry(input_frame, textvariable=self.batch_size_var, width=10).grid(row=6, column=1, padx=5, pady=2, sticky="w")

        # Proxy Input
        ttk.Label(input_frame, text="Proxy (optional):").grid(row=7, column=0, padx=5, pady=2, sticky="w")
        self.proxy_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.proxy_var, width=50).grid(row=7, column=1, columnspan=2, padx=5, pady=2, sticky="ew")

        # Cookies File Path Input
        ttk.Label(input_frame, text="Cookies File (.txt) Path (optional):").grid(row=8, column=0, padx=5, pady=2, sticky="w")
        self.cookies_file_path_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.cookies_file_path_var, width=50).grid(row=8, column=1, padx=5, pady=2, sticky="ew")
        ttk.Button(input_frame, text="Browse", command=self._browse_cookies_file).grid(row=8, column=2, padx=5, pady=2)


        input_frame.grid_columnconfigure(1, weight=1)

        # Selenium Browser Options Frame
        browser_options_frame = ttk.LabelFrame(main_frame, text="Browser Options")
        browser_options_frame.pack(padx=5, pady=5, fill="x")

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
        ttk.Checkbutton(browser_options_frame, text="Set Language to English (US)", variable=self.set_language_en_us_var).grid(row=2, column=2, padx=5, pady=2, sticky="w")
        self.start_maximized_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(browser_options_frame, text="Start Browser in Maximized Mode", variable=self.start_maximized_var).grid(row=3, column=0, padx=5, pady=2, sticky="w")

        # Scrolling Method Dropdown
        ttk.Label(browser_options_frame, text="Scrolling Method:").grid(row=4, column=0, padx=5, pady=2, sticky="w")
        self.scrolling_method_var = tk.StringVar(value="Send END Key")
        self.scrolling_method_dropdown = ttk.Combobox(browser_options_frame, textvariable=self.scrolling_method_var,
                                                    values=["Send END Key", "Scroll to Bottom (JS)", "Scroll by Viewport (JS)"])
        self.scrolling_method_dropdown.grid(row=4, column=1, padx=5, pady=2, sticky="ew")
        self.scrolling_method_dropdown.set("Send END Key")

        # Download Quality Dropdown
        ttk.Label(browser_options_frame, text="Download Quality & Format:").grid(row=5, column=0, padx=5, pady=2, sticky="w")
        self.download_quality_var = tk.StringVar(value="Best Quality")
        self.download_quality_dropdown = ttk.Combobox(browser_options_frame, textvariable=self.download_quality_var,
                                                    values=[
                                                        "Best Quality",
                                                        "Best Quality format mp4",
                                                        "Best Quality format mkv",
                                                        "1080p format mp4",
                                                        "1080p format mkv",
                                                        "720p format mp4",
                                                        "720p format mkv"
                                                    ])
        self.download_quality_dropdown.grid(row=5, column=1, padx=5, pady=2, sticky="ew")
        self.download_quality_dropdown.set("Best Quality")

        for i in range(3):
            browser_options_frame.grid_columnconfigure(i, weight=1)

        # Action Buttons (Moved above log)
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10, fill="x")

        self.start_button = ttk.Button(button_frame, text="Start Scraping & Download", command=self._start_scraping)
        self.start_button.pack(side=tk.LEFT, expand=True, fill="both", padx=5, ipadx=10, ipady=5)
        self.cancel_button = ttk.Button(button_frame, text="Cancel/Stop", command=self._cancel_scraping, state="disabled")
        self.cancel_button.pack(side=tk.LEFT, expand=True, fill="both", padx=5, ipadx=10, ipady=5)
        self.reset_button = ttk.Button(button_frame, text="Reset", command=self._reset_gui)
        self.reset_button.pack(side=tk.LEFT, expand=True, fill="both", padx=5, ipadx=10, ipady=5)
        self.open_output_button = ttk.Button(button_frame, text="Open Output Folder", command=self._open_output_folder)
        self.open_output_button.pack(side=tk.LEFT, expand=True, fill="both", padx=5, ipadx=10, ipady=5)

        # Log Area (moved below action buttons)
        ttk.Label(main_frame, text="Process Log:").pack(pady=5, padx=10, fill="x")
        self.log_area = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=15, state="disabled")
        self.log_area.pack(pady=5, padx=10, expand=True, fill="both")

        # Progress Bar & Status Area (below log)
        self.progress_bar_label = ttk.Label(main_frame, text="Progress: 0%")
        self.progress_bar_label.pack(pady=5, padx=10, fill="x")
        self.progress_bar = ttk.Progressbar(main_frame, orient="horizontal", length=600, mode="determinate")
        self.progress_bar.pack(pady=5, padx=10, fill="x")

        self.status_label = ttk.Label(main_frame, text="Status: Ready", anchor="w")
        self.status_label.pack(pady=5, padx=10, fill="x")

        # Handle window close event
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _browse_output_folder(self):
        """
        Opens a dialog to select the output folder.
        """
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.output_folder_var.set(folder_selected)

    def _browse_cookies_file(self):
        """
        Opens a file dialog to select the cookies .txt file.
        """
        file_selected = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if file_selected:
            self.cookies_file_path_var.set(file_selected)

    def _log_to_gui(self, message):
        """
        Writes messages to the GUI log area.
        """
        self.log_area.config(state="normal")
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state="disabled")
        self.update_idletasks() # Update GUI immediately

    def _update_progress(self, current, total):
        """
        Updates the progress bar and percentage label.

        Args:
            current (int): Number of URLs collected so far.
            total (int): Target number of URLs (0 if no target).
        """
        if total > 0:
            percentage = (current / total) * 100
            self.progress_bar.config(mode="determinate", value=percentage)
            self.progress_bar_label.config(text=f"Progress: {percentage:.2f}% ({current}/{total} URLs)")
        else:
            # Indeterminate mode if no target, just show current URL count
            self.progress_bar.config(mode="indeterminate")
            if self.progress_bar.cget("mode") == "indeterminate" and self.progress_bar["value"] == 0:
                self.progress_bar.start() # Start animation for indeterminate mode only if not already started
            self.progress_bar_label.config(text=f"Progress: Found {current} URLs...")
        self.update_idletasks()

    def _update_status(self, message):
        """
        Updates the status label in the GUI.
        """
        self.status_label.config(text=f"Status: {message}")
        self.update_idletasks()

    def _start_scraping(self):
        """
        Starts the scraping and downloading process in a separate thread.
        """
        # Input Validation
        channel_url = self.channel_url_var.get().strip()
        if not channel_url:
            messagebox.showerror("Input Error", "YouTube Channel URL cannot be empty.")
            return
        if not channel_url.startswith("http"):
            messagebox.showerror("Input Error", "YouTube Channel URL is invalid. Must start with http:// or https://")
            return

        try:
            target_video_count = int(self.target_video_count_var.get())
            if target_video_count < 0:
                raise ValueError("Target Video Count cannot be negative.")
        except ValueError:
            messagebox.showerror("Input Error", "Target Video Count must be a non-negative integer.")
            return

        try:
            scroll_delay = int(self.scroll_delay_var.get())
            if scroll_delay <= 0:
                raise ValueError("Scroll Delay must be a positive integer.")
        except ValueError as e:
            messagebox.showerror("Input Error", f"Scroll Delay error: {e}\nPlease ensure it's a positive integer.")
            return

        try:
            download_delay = int(self.download_delay_var.get())
            if download_delay < 0: # Can be 0 for no download delay
                raise ValueError("Download Delay cannot be negative.")
        except ValueError as e:
            messagebox.showerror("Input Error", f"Download Delay error: {e}\nPlease ensure it's a non-negative integer.")
            return

        try:
            download_retries = int(self.download_retries_var.get())
            if download_retries < 0: # 0 retries means only one attempt
                raise ValueError("Download Retries cannot be negative.")
        except ValueError:
            messagebox.showerror("Input Error", "Download Retries must be a non-negative integer.")
            return
        
        try:
            batch_size = int(self.batch_size_var.get())
            if batch_size <= 0:
                raise ValueError("Download Batch Size must be greater than 0.")
        except ValueError:
            messagebox.showerror("Input Error", "Download Batch Size must be a positive integer.")
            return

        output_folder = self.output_folder_var.get()
        if not os.path.exists(output_folder):
            try:
                os.makedirs(output_folder)
                self._log_to_gui(f"Output folder '{output_folder}' created successfully.")
            except OSError as e:
                messagebox.showerror("Folder Error", f"Failed to create output folder: {e}")
                return

        cookies_file_path = self.cookies_file_path_var.get().strip()
        if cookies_file_path and not os.path.exists(cookies_file_path):
            messagebox.showwarning("File Warning", f"Cookies file not found at: {cookies_file_path}\nProceeding without cookies for yt-dlp.")
            cookies_file_path = "" # Clear invalid path

        self._save_settings() # Save current settings

        # Disable Start button, enable Cancel
        self.start_button.config(state="disabled")
        self.cancel_button.config(state="normal")
        self.reset_button.config(state="disabled")
        self.open_output_button.config(state="disabled")

        # Reset log area and progress bar
        self.log_area.config(state="normal")
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state="disabled")
        self.progress_bar.config(value=0) # Reset value to 0
        if target_video_count == 0:
            self.progress_bar.config(mode="indeterminate")
            self.progress_bar.start()
        else:
            self.progress_bar.config(mode="determinate")

        self.progress_bar_label.config(text="Progress: 0%")
        self.status_label.config(text="Status: Starting...")

        # Collect configuration for scraper
        config = {
            "output_folder": output_folder,
            "channel_url": channel_url,
            "target_video_count": target_video_count,
            "scroll_delay": scroll_delay,
            "download_delay": download_delay,
            "download_retries": download_retries,
            "batch_size": batch_size,
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
            "scrolling_method": self.scrolling_method_var.get(),
            "download_quality": self.download_quality_var.get(),
            "cookies_file_path": cookies_file_path # Pass cookies file path to scraper
        }

        self.scraper = YouTubeShortsScraper(output_folder, self._log_to_gui, self._update_progress, self._update_status, config)
        # --- PERBAIKAN DI SINI: Panggil run_full_process ---
        self.scraping_thread = threading.Thread(target=self.scraper.run_full_process)
        self.scraping_thread.daemon = True # Allow thread to exit when app closes
        self.scraping_thread.start()

        self._update_status("Process is running...")

        # Monitor thread completion to re-enable buttons
        self.after(100, self._check_scraping_completion)

    def _check_scraping_completion(self):
        """
        Checks if the scraping thread has finished and re-enables buttons.
        """
        if self.scraping_thread and not self.scraping_thread.is_alive():
            self._enable_buttons()
            self.progress_bar.stop() # Ensure indeterminate progress bar stops
        else:
            self.after(100, self._check_scraping_completion)

    def _cancel_scraping(self):
        """
        Stops the scraping process.
        """
        if self.scraper:
            self.scraper.stop_scraping()
            self._log_to_gui("Process cancelled...")
            self._update_status("Process cancelled.")
        self._enable_buttons()
        self.progress_bar.stop() # Ensure indeterminate progress bar stops

    def _reset_gui(self):
        """
        Resets all input fields to their default values.
        """
        self.output_folder_var.set(os.path.join(os.getcwd(), "scraped_results"))
        self.channel_url_var.set("")
        self.target_video_count_var.set(0)
        self.scroll_delay_var.set(5)
        self.download_delay_var.set(5)
        self.download_retries_var.set(3)
        self.batch_size_var.set(20)
        self.proxy_var.set("")
        self.cookies_file_path_var.set("") # Reset cookies path
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
        self.download_quality_var.set("Best Quality")

        self.log_area.config(state="normal")
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state="disabled")
        self.progress_bar.config(value=0, mode="determinate")
        self.progress_bar.stop()
        self.progress_bar_label.config(text="Progress: 0%")
        self.status_label.config(text="Status: Ready")

        self._enable_buttons()
        self._log_to_gui("GUI has been reset to default settings.")

    def _open_output_folder(self):
        """
        Opens the output folder in the system's file explorer.
        """
        output_folder = self.output_folder_var.get()
        if os.path.exists(output_folder):
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(output_folder)
                elif os.name == 'posix': # macOS, Linux, Unix
                    import subprocess
                    subprocess.call(['xdg-open', output_folder]) # Common for Linux
                else:
                    messagebox.showerror("Error", "Operating system not supported for automatic folder opening. Please open manually.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open folder: {e}\nPlease open manually: {output_folder}")
        else:
            messagebox.showerror("Error", "Output folder not found. Ensure it exists or the process has completed.")

    def _enable_buttons(self):
        """
        Re-enables Start and Reset buttons, disables Cancel button.
        """
        self.start_button.config(state="normal")
        self.cancel_button.config(state="disabled")
        self.reset_button.config(state="normal")
        self.open_output_button.config(state="normal")

    def _save_settings(self):
        """
        Saves GUI settings to a JSON file.
        """
        settings = {
            "output_folder": self.output_folder_var.get(),
            "channel_url": self.channel_url_var.get(),
            "target_video_count": self.target_video_count_var.get(),
            "scroll_delay": self.scroll_delay_var.get(),
            "download_delay": self.download_delay_var.get(),
            "download_retries": self.download_retries_var.get(),
            "batch_size": self.batch_size_var.get(),
            "proxy_input": self.proxy_var.get(),
            "cookies_file_path": self.cookies_file_path_var.get(), # Save cookies path
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
            "scrolling_method": self.scrolling_method_var.get(),
            "download_quality": self.download_quality_var.get()
        }
        try:
            with open("scraper_settings.json", "w") as f:
                json.dump(settings, f, indent=4)
            self._log_to_gui("Settings saved successfully.")
        except Exception as e:
            self._log_to_gui(f"Error saving settings: {e}")

    def _load_saved_settings(self):
        """
        Loads GUI settings from a JSON file.
        """
        try:
            if os.path.exists("scraper_settings.json"):
                with open("scraper_settings.json", "r") as f:
                    settings = json.load(f)
                self.output_folder_var.set(settings.get("output_folder", os.path.join(os.getcwd(), "scraped_results")))
                self.channel_url_var.set(settings.get("channel_url", ""))
                self.target_video_count_var.set(settings.get("target_video_count", 0))
                self.scroll_delay_var.set(int(settings.get("scroll_delay", 5)))
                self.download_delay_var.set(int(settings.get("download_delay", 5)))
                self.download_retries_var.set(int(settings.get("download_retries", 3)))
                self.batch_size_var.set(settings.get("batch_size", 20))
                self.proxy_var.set(settings.get("proxy_input", ""))
                self.cookies_file_path_var.set(settings.get("cookies_file_path", "")) # Load cookies path
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
                self.download_quality_var.set(settings.get("download_quality", "Best Quality"))
                self._log_to_gui("Previous settings loaded successfully.")
            else:
                self._log_to_gui("Settings file not found. Using default values.")
        except Exception as e:
            self._log_to_gui(f"Error loading settings: {e}. Using default values.")

    def _on_closing(self):
        """
        Handles the GUI window close event.
        """
        if self.scraping_thread and self.scraping_thread.is_alive():
            if messagebox.askyesno("Exit Application", "Process is running. Are you sure you want to exit? This will stop the process."):
                self._cancel_scraping() # Stop process if running
                self.destroy()
        else:
            self.destroy()

if __name__ == "__main__":
    app = ScrapingApp()
    app.mainloop()
