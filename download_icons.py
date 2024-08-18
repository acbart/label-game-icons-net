"""
Simple command line tool to download icons from game-icons.net as a zip file, and unpack them into the icons/ directory.
Reports on any newly added icons, and any errors that occurred during the download or unpacking process, which gets appended
to the logs/icons.log file.
"""
import csv
import datetime
import os
import requests
import json
import logging
import argparse
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DEFAULT_ICON_URL = "https://game-icons.net/archives/png/zip/000000/ffffff/game-icons.net.png.zip"
# The directory to save the icons to, defaults to ./ because the zip file contains a directory called "icons" already
OUTPUT_DIRECTORY = "./"
LOG_FILE = "logs/icons.log"
CSV_OUTPUT_PATH = "icons/all_icons.csv"

# Set up additional logging to another file
def setup_file_logger(log_file_path: str):
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

def download_icons(icon_url: str, output_dir: str, csv_path: str, force: bool = False):
    """
    Download the icons from the specified URL and save them to the output directory.
    """
    # Make the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Download the zip file
    logger.info(f"Downloading icons from {icon_url}...")
    response = requests.get(icon_url)
    response.raise_for_status()
    
    # Save the zip file
    zip_path = os.path.join(output_dir, "icons.zip")
    with open(zip_path, 'wb') as f:
        f.write(response.content)
    logger.info("Icons downloaded successfully.")
    
    # Check if this is the first time, based on there being a license.txt file in the icons directory
    is_first_time = not os.path.exists(os.path.join(output_dir, "icons/license.txt"))
    if is_first_time:
        logger.info("First time downloading icons; unpacking all icons.")
        
    # Iterate through the zip file and make a list of the icons
    # Compare this list to the existing icons to see if there are any new, deleted, or modified icons
    do_unpack = True
    if is_first_time:
        all_icons = set()
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for file in zip_ref.namelist():
                icon = file.split('/')[-1]
                all_icons.add(icon)
        logger.info(f"All icons downloaded ({len(all_icons)} icons).")
    else:
        all_icons = set()
        new_icons = set()
        deleted_icons = set()
        modified_icons = set()
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for file in zip_ref.namelist():
                icon = file.split('/')[-1]
                all_icons.add(icon)
                icon_path = os.path.join(output_dir, file)
                if os.path.exists(icon_path):
                    if os.path.getsize(icon_path) != zip_ref.getinfo(file).file_size:
                        modified_icons.add(icon)
                else:
                    new_icons.add(icon)
        # Update the log with the new, deleted, and modified icons (also log to logger)
        if new_icons:
            logger.info(f"New icons: {new_icons}")
        if deleted_icons:
            logger.info(f"Deleted icons: {deleted_icons}")
        if modified_icons:
            logger.info(f"Modified icons: {modified_icons}")
        if not new_icons and not deleted_icons and not modified_icons:
            logger.info("No changes to icons; skipping unpacking.")
            do_unpack = False
    
    
    # Unpack the zip file
    if do_unpack or force:
        logger.info(f"Unpacking icons to {output_dir}...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(output_dir)
    
    # Remove the zip file
    os.remove(zip_path)
    
    logger.info("Icons downloaded and unpacked successfully.")
    
    # Generate a flat CSV file with the icon names and their paths
    logger.info(f"Generating CSV file with icon names and paths: {csv_path}")
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["icon", "path"])
        # Iterate through all directories looking for png files
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                if file.endswith(".png"):
                    icon = file
                    # Force linux style style line endings
                    path = Path(os.path.join(root, file)).as_posix()
                    # Remove the extension from the icon name
                    icon = Path(icon).stem
                    writer.writerow([icon, path])
    
    
    
def main():
    parser = argparse.ArgumentParser(description="Download icons from game-icons.net.")
    parser.add_argument('--icon_url', type=str, default=DEFAULT_ICON_URL,
                        help=f"The URL to download the icons from. Defaults to {DEFAULT_ICON_URL}")
    parser.add_argument('--output_dir', type=str, default=OUTPUT_DIRECTORY,
                        help=f"The directory to save the icons to. Defaults to {OUTPUT_DIRECTORY}, because the zip file contains a directory called 'icons'.")
    parser.add_argument('--csv_output_path', type=str, default=CSV_OUTPUT_PATH,
                        help=f"The path to save the CSV file with the icon names and paths. Defaults to {CSV_OUTPUT_PATH}")
    parser.add_argument('--log_file', type=str, default=LOG_FILE, 
                        help=f"The log file to write to. Defaults to {LOG_FILE}")
    parser.add_argument('--force', action='store_true', help="Force download and unpacking of icons.")
    
    args = parser.parse_args()
    
    setup_file_logger(LOG_FILE)
    
    download_icons(args.icon_url, args.output_dir, args.csv_output_path, args.force)

if __name__ == "__main__":
    main()