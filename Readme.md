# YT-Shorts-Bulk-Downloader-GUI

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![GUI](https://img.shields.io/badge/GUI-Tkinter-blue?style=for-the-badge)
![Web Scraping](https://img.shields.io/badge/Web%20Scraping-Selenium-green?style=for-the-badge&logo=selenium)
[![GitHub followers](https://img.shields.io/github/followers/MuchoRio?style=social)](https://github.com/MuchoRio)
[![GitHub stars](https://img.shields.io/github/stars/MuchoRio/YT-Shorts-Bulk-Downloader-GUI?style=social)](https://github.com/MuchoRio/YT-Shorts-Bulk-Downloader-GUI)

---

## English

This is a powerful and user-friendly Python application with a Graphical User Interface (GUI) designed to **bulk scrape YouTube Shorts video URLs and their comprehensive metadata (Title, Description)** from any specified YouTube channel, and then **efficiently download these videos in configurable batches**. It leverages Selenium for robust URL collection and `yt-dlp` for high-quality downloading and metadata extraction.

**Important Note:** Downloading content from YouTube may violate YouTube's Terms of Service. The use of this tool is entirely at your own risk. Please use this tool responsibly and adhere to all applicable laws and copyright regulations.

### Features

* Intuitive GUI: Built with Tkinter for an easy-to-navigate and user-friendly experience.
* Comprehensive Data Collection:
    * Automated URL Scraping: Uses Selenium with intelligent scrolling logic to fetch all available YouTube Shorts URLs from a given channel.
    * Rich Metadata Extraction: Navigates to individual video pages using Selenium to obtain accurate video descriptions, in addition to titles.
* Flexible Download Management:
    * Bulk Downloading: Efficiently downloads multiple Shorts videos in configurable batches.
    * Targeted Processing: Option to limit the number of videos to process (e.g., download only the latest 100 Shorts).
    * Configurable Download Quality & Format: Select your preferred video quality and format (e.g., Best Quality, 1080p MP4, 720p MKV, etc.).
    * Randomized Delays: Incorporates customizable, random delays between downloads to mimic human behavior and reduce detection risk.
    * Retry Mechanism: Automatically retries failed downloads for improved reliability.
* Advanced Browser & Network Options:
    * Selenium Customization: Configure headless mode, disable sandbox, notifications, GPU, and more for optimized scraping performance and stealth.
    * Multiple Scrolling Methods: Choose between "Send END Key", "Scroll to Bottom (JS)", or "Scroll by Viewport (JS)" for robust content loading on YouTube.
    * Proxy Support: Option to use a proxy for both Selenium scraping and `yt-dlp` downloads, enhancing privacy and potentially bypassing geo-restrictions or IP blocks.
    * Random User-Agent Rotation: Uses a rotating list of User-Agents for both Selenium and `yt-dlp` to further evade bot detection.
* Detailed Output & Error Handling:
    * Batch-wise Output: Organizes downloaded videos and their corresponding metadata (in .xlsx format) into separate, numbered batch folders.
    * Comprehensive Status Tracking: Maintains an overall download status (URL Video, Title, Description, Download_Status) saved as a master Excel file, indicating 'D' (Downloaded), 'N' (Not Downloaded/Not Attempted), or 'E' (Error).
    * Error Logging: Automatically saves URLs of failed downloads to a dedicated download_errors.txt file within the main output folder for easy review.
* Process Control: Real-time progress bar and detailed status updates within the GUI, along with a "Cancel/Stop" button to gracefully halt ongoing operations.
* Persistent Settings: Saves and loads your last-used GUI configurations (output folder, channel URL, options) for convenience.

### Installation

1.  Ensure Python is installed: Python 3.6 or higher is required.
2.  Clone the repository:
    ```bash
    git clone https://github.com/MuchoRio/YT-Shorts-Bulk-Downloader-GUI.git
    cd YT-Shorts-Bulk-Downloader-GUI
    ```
3.  Create a virtual environment (highly recommended):
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
4.  Install the required Python libraries:
    ```bash
    pip install -r requirements.txt
    ```
    (Note: `tkinter` is typically included with standard Python installations, but `openpyxl` is required by `pandas` for `.xlsx` file handling, and `yt-dlp`, `selenium`, `webdriver-manager` are crucial for functionality. Ensure `yt-dlp` is installed and accessible from your system's PATH.)

### Usage

1.  Run the application:
    ```bash
    python downloader.py
    ```
2.  Configure Settings in the GUI:
    * Output Folder: Click "Browse" to choose the primary directory where batch folders (e.g., `batch_1`, `batch_2`), log files, and the master status file will be created.
    * YouTube Channel URL: Input the full URL of the YouTube channel whose Shorts you wish to process (e.g., `https://www.youtube.com/@NamaChannel`). The script will attempt to navigate to the Shorts section of that channel.
    * Target Video Count (0 = All): Enter the maximum number of Shorts you want to scrape and download. Leave it as `0` to process all Shorts found on the channel.
    * Scroll Delay (seconds): Specify the fixed delay (in seconds) between scrolls during the initial scraping phase.
    * Download Delay (seconds): Set the maximum delay (in seconds) between individual video downloads. The script will apply a random delay between 1 second and this value.
    * Download Retries: Define how many times `yt-dlp` should retry a failed download for a single video.
    * Download Batch Size: Set the number of videos to be grouped into each batch folder for downloading.
    * Proxy (optional): Enter your proxy details (e.g., `http://host:port` or `user:pass@ip:port`) if you want to use one for both scraping and downloading.
    * Browser Options: Tick the checkboxes for various Selenium browser options like `Headless Mode` (runs the browser without a visible window), `Disable Sandbox`, `Disable Notifications`, etc., to customize browser behavior and improve stealth.
    * Scrolling Method: Select the method Selenium will use to scroll the YouTube Shorts page to load more content. "Send END Key" is often most effective.
    * Download Quality & Format: Choose your desired video quality and file format from the dropdown menu.
3.  Start the Process: Click the **"Start Scraping & Download"** button to begin the scraping and downloading.
4.  Monitor Progress: Observe the real-time `Process Log` area, `Progress` bar, and `Status` label in the GUI for detailed updates on the process, including current step, batch information, and video counts.
5.  Cancel: Click the **"Cancel/Stop"** button at any time to gracefully halt the ongoing operations.
6.  Review Output: Once the process is complete (or cancelled), click **"Open Output Folder"** to quickly access your chosen main output directory and find the organized batch folders, log files, and the master status Excel file.

### Output Structure

Within the main output folder you selected, the script will create:

* Numbered Batch Subfolders: (e.g., `batch_1`, `batch_2`, etc.)
    * Each subfolder will contain:
        * An Excel file (`YouTube_Shorts_Batch_X.xlsx`) with `Video URL`, `Title`, `Description`, and `Download Status (D/N/E)` for all Shorts in that batch.
        * The downloaded Shorts video files (e.g., `Amazing_Shorts_Title.mp4`).
* `scraping_log.txt`: A comprehensive log file detailing all actions, successful finds, and errors encountered during the entire process.
* `download_errors.txt`: A dedicated text file (if errors occurred) listing the URLs and error messages for any videos that failed to download.
* `scraper_settings.json`: A JSON file that saves your last-used GUI settings for quick reloading.

### Advanced Configuration (within `downloader.py`)

You can fine-tune several core parameters by modifying the `downloader.py` script directly if needed:

* `_get_video_description` function: You can adjust the `WebDriverWait` timeouts or CSS selectors if YouTube's HTML structure for descriptions changes.
* `_scrape_shorts_data_phase` function:
    * `no_new_urls_consecutive_scrolls` threshold (default `5` and `10`): Controls how many consecutive scrolls without new URLs will trigger warnings or stop the scraping.
    * CSS selectors for Shorts video elements.
* `_download_videos` function:
    * `subprocess.run` timeout (default `self.config["download_delay"] * 5`): Adjusts the maximum time `yt-dlp` is allowed to run for a single video.
    * `quality_map`: Defines the mapping from user-friendly quality names in the GUI to `yt-dlp`'s format strings.

### Support Me

If you find this script useful, please consider giving it a star ⭐️ on GitHub! Your support encourages me to create more open-source tools.

### License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
