#!/usr/bin/env python3
# dependencies = [
#   "selenium>=4.10.0",
#   "dateparser",
#   "tzdata"
# ]
#
import time
import traceback
import logging
import argparse
from datetime import datetime, timedelta
import dateparser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def setup_logging(verbose=False):
    """Configures logging to write to output.log if verbose is True."""
    if verbose:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='output.log', filemode='w')
    else:
        logging.basicConfig(level=logging.CRITICAL, format='%(message)s')

def get_recent_video_info(driver, channel_url):
    """Optimized function to check for recent videos.
    Only navigates to the video page if the upload date is recent.
    """
    wait = WebDriverWait(driver, 20)
    try:
        logging.info(f"Checking channel: {channel_url}/videos")
        driver.get(f"{channel_url}/videos")

        # Find the first video container on the /videos page
        first_video_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-rich-grid-media")))

        # Extract metadata directly from the grid view
        title_element = first_video_container.find_element(By.ID, "video-title-link")
        title = title_element.get_attribute("title")
        video_url = title_element.get_attribute("href")

        # Metadata line contains views and date
        metadata_line = first_video_container.find_element(By.ID, "metadata-line").find_elements(By.TAG_NAME, "span")
        date_str = metadata_line[1].text # The date is typically the second span

        # Use dateparser with a timezone-aware setting
        upload_date = dateparser.parse(date_str, settings={'RETURN_AS_TIMEZONE_AWARE': True})
        if not upload_date:
            logging.warning(f"Could not parse date string '{date_str}' for {channel_url}")
            return None

        # Make current time timezone-aware for comparison
        now_aware = datetime.now(upload_date.tzinfo)

        # --- Conditional Navigation ---
        # Only proceed if the video is recent
        if (now_aware - upload_date) < timedelta(hours=1):
            logging.info(f"RECENT VIDEO FOUND: '{title}'. Navigating to page for description.")
            driver.get(video_url)

            # Now on the video page, get the uploader name and description
            uploader = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "ytd-channel-name #text"))).text
            wait.until(EC.element_to_be_clickable((By.ID, "expand"))).click()
            description_container = wait.until(EC.visibility_of_element_located((By.ID, "description-inline-expander")))
            description_text = description_container.text
            logging.info(f"--- Video Description ---
{description_text}")

            return uploader, title, date_str, video_url
        else:
            logging.info(f"Video for {channel_url} is older than 1 hour ({date_str}). Skipping page load.")
            return None

    except Exception as e:
        logging.error(f"an error occurred while processing {channel_url}: {e}
{traceback.format_exc()}")
        return None

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='extract recent video info from youtube channels.')
    parser.add_argument('-v', '--verbose', action='store_true', help='enable detailed logging to output.log')
    args = parser.parse_args()
    setup_logging(args.verbose)

    youtubers_to_check = (
        "https://www.youtube.com/@mrbeast",
        "https://www.youtube.com/@linustechtips",
    )

    options = Options()
    options.add_argument("--headless")
    driver = None

    try:
        driver = webdriver.Firefox(options=options)
        # Handle consent once at the beginning
        try:
            driver.get("https://www.youtube.com")
            # Using a more specific selector for the consent button
            accept_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//button[.//span[contains(text(), "Accept all")]]'))
            )
            accept_button.click()
            logging.info("Clicked the 'Accept all' consent button.")
        except Exception:
            logging.warning("Consent button not found or not clickable, continuing...")

        for channel_url in youtubers_to_check:
            video_info = get_recent_video_info(driver, channel_url)
            if video_info:
                youtuber, title, release_date, link = video_info
                print(f"{youtuber} - {title}
{release_date}
Link: {link}")
    finally:
        if driver:
            logging.info("Quitting webdriver.")
            driver.quit()
