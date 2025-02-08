import os
import sqlite3
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
import time
import logging

# Load environment variables
load_dotenv()

# Configuration from .env
RADARR_URL = os.getenv("RADARR_URL").split(",")
RADARR_API_KEY = os.getenv("RADARR_API_KEY").split(",")
SONARR_URL = os.getenv("SONARR_URL").split(",")
SONARR_API_KEY = os.getenv("SONARR_API_KEY").split(",")
LIDARR_URL = os.getenv("LIDARR_URL").split(",")
LIDARR_API_KEY = os.getenv("LIDARR_API_KEY").split(",")
READARR_URL = os.getenv("READARR_URL").split(",")
READARR_API_KEY = os.getenv("READARR_API_KEY").split(",")
STALLED_TIMEOUT = int(os.getenv("STALLED_TIMEOUT", 3600))
STALLED_ACTION = os.getenv("STALLED_ACTION", "BLOCKLIST_AND_SEARCH").upper()
VERBOSE = os.getenv("VERBOSE", "false").lower() == "true"
RUN_INTERVAL = int(os.getenv("RUN_INTERVAL", 300))  # Default to 300 seconds
COUNT_DOWNLOADING_METADATA_AS_STALLED = os.getenv("COUNT_DOWNLOADING_METADATA_AS_STALLED", "false").lower() == "true"

DB_FILE = "stalled_downloads.db"

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if VERBOSE else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

def initialize_database():
    """Initialize the SQLite database for tracking stalled downloads."""
    if STALLED_TIMEOUT == 0:
        return  # Skip DB initialization if timeout is 0

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Create the table with the new schema
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stalled_downloads (
            download_id TEXT,
            first_detected TIMESTAMP NOT NULL,
            arr_service TEXT NOT NULL,
            PRIMARY KEY (download_id, arr_service)
        )
    """)

    conn.commit()
    conn.close()

def get_stalled_downloads_from_db(arr_service):
    """Retrieve stalled downloads for a specific service from the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Fetch all records for the specific service
    cursor.execute("SELECT download_id, first_detected FROM stalled_downloads WHERE arr_service = ?", (arr_service,))
    rows = cursor.fetchall()
    conn.close()

    # Convert download_id to string and timestamps to datetime
    return {str(row[0]): datetime.fromisoformat(row[1]) for row in rows}

def add_stalled_download_to_db(download_id, first_detected, arr_service):
    """Add a stalled download to the database if it does not already exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Insert only if the (download_id, arr_service) pair does not already exist
    cursor.execute("""
        INSERT OR IGNORE INTO stalled_downloads (download_id, first_detected, arr_service)
        VALUES (?, ?, ?)
    """, (str(download_id), first_detected.isoformat(), arr_service))

    added = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return added

def remove_stalled_download_from_db(download_id, arr_service):
    """Remove a stalled download entry from the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Delete the record for the specific service
    cursor.execute("DELETE FROM stalled_downloads WHERE download_id = ? AND arr_service = ?", (download_id, arr_service))

    conn.commit()
    conn.close()

def query_api(url, headers, params=None):
    """Query an API endpoint and return the JSON response."""
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"API Request Error: {e}")
        return None

def post_api(url, headers, data=None):
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        logging.debug(f"Successfully performed POST action on {url} with data {data}.")
    except requests.RequestException as e:
        logging.error(f"API POST Error: {e}")

def delete_api(url, headers, params=None):
    try:
        response = requests.delete(url, headers=headers, params=params)
        response.raise_for_status()
        logging.debug(f"Successfully performed DELETE action on {url} with params {params}.")
    except requests.RequestException as e:
        logging.error(f"API DELETE Error: {e}")

def detect_stuck_metadata_downloads(base_url, api_key, service_name, api_version):
    """
    Detect downloads stuck at 'Downloading Metadata' and apply timeout logic.
    Controlled by COUNT_DOWNLOADING_METADATA_AS_STALLED environment variable.
    """
    count_metadata_as_stalled = os.getenv("COUNT_DOWNLOADING_METADATA_AS_STALLED", "false").lower() == "true"
    if not count_metadata_as_stalled:
        logging.debug(f"Skipping 'Downloading Metadata' detection for {service_name} (disabled).")
        return

    # Query parameters for metadata detection
    params = {
        "protocol": "torrent",
        "status": "queued",  # Only look for queued downloads
        "includeEpisode": "true" if service_name == "Sonarr" else "false"
    }

    logging.info(f"Checking for stuck downloads ('Downloading Metadata') in {service_name}...")
    headers = {"X-Api-Key": api_key}
    queue_url = f"{base_url}/api/{api_version}/queue"
    metadata_records = query_api_paginated(queue_url, headers, params, page_size=50)

    if not metadata_records:
        logging.info(f"No stuck downloads detected in {service_name}.")
        return

    # Get metadata downloads already detected and stored in the database
    detected_metadata_downloads = get_stalled_downloads_from_db(service_name)

    for item in metadata_records:
        if item.get("errorMessage", "").lower() == "qbittorrent is downloading metadata":
            download_id = str(item["id"])
            movie_id = item.get("movieId") if service_name == "Radarr" else None
            episode_ids = [item["episodeId"]] if service_name == "Sonarr" and "episodeId" in item else None

            # Check if this download ID is already tracked in the database
            if download_id in detected_metadata_downloads:
                first_detected = detected_metadata_downloads[download_id]
                elapsed_time = (datetime.now(timezone.utc) - first_detected).total_seconds()

                logging.debug(f"Download ID {download_id} first detected: {first_detected}, elapsed: {elapsed_time} seconds.")
                if elapsed_time > STALLED_TIMEOUT:
                    logging.info(f"Handling stuck metadata download ID {download_id} in {service_name} (elapsed time: {elapsed_time} seconds).")
                    perform_action(base_url, headers, download_id, movie_id, service_name, api_version, episode_ids)
                    remove_stalled_download_from_db(download_id, service_name)
                else:
                    logging.info(f"Metadata download ID {download_id} in {service_name} is within timeout period ({elapsed_time} seconds).")
            else:
                # Add this metadata download to the database with the current timestamp
                add_stalled_download_to_db(download_id, datetime.now(timezone.utc), service_name)
                logging.info(f"Added metadata download ID {download_id} in {service_name} to the database.")

def query_api_paginated(base_url, headers, params=None, page_size=50):
    """Query an API endpoint with pagination to retrieve all records."""
    all_records = []
    page = 1  # Start with the first page
    total_records = None  # Will be set from the API response

    while True:
        paginated_params = params.copy() if params else {}
        paginated_params.update({"page": page, "pageSize": page_size})

        logging.debug(f"Fetching page {page} with params: {paginated_params}")
        response = query_api(base_url, headers, paginated_params)

        if response is None:
            logging.error(f"API returned None for page {page}. Exiting pagination.")
            break

        if not isinstance(response, dict) or "records" not in response:
            logging.error(f"Unexpected response from API: {response}")
            break

        # Fetch the records and total number of records
        records = response.get("records", [])
        total_records = response.get("totalRecords", total_records)

        logging.debug(f"Page {page}: Retrieved {len(records)} records. Total so far: {len(all_records)} / {total_records}")

        if not records:
            logging.debug(f"No more records found on page {page}. Completed pagination.")
            break

        all_records.extend(records)

        # Exit if we have all records
        if total_records and len(all_records) >= total_records:
            logging.debug(f"Fetched all {total_records} records. Exiting pagination.")
            break

        # Move to the next page
        page += 1

    return all_records


    return all_records

def perform_action(base_url, headers, download_id, movie_id, service_name, api_version, episode_ids=None):
    # Define action descriptions for logging
    action_desc = {
        "REMOVE": f"remove (ID: {download_id})",
        "BLOCKLIST": f"blocklist (ID: {download_id})",
        "BLOCKLIST_AND_SEARCH": f"blocklist and search (ID: {download_id}, {'Episodes' if service_name == 'Sonarr' else 'Movie'}: {episode_ids if service_name == 'Sonarr' else movie_id})"
    }.get(STALLED_ACTION, "INVALID ACTION")

    if STALLED_ACTION == "REMOVE":
        action_url = f"{base_url}/api/{api_version}/queue/{download_id}"
        logging.info(f"Performing action: {action_desc} in {service_name}...")
        delete_api(action_url, headers)

    elif STALLED_ACTION == "BLOCKLIST":
        action_url = f"{base_url}/api/{api_version}/queue/{download_id}"
        params = {"blocklist": "true", "skipRedownload": "true"}
        logging.info(f"Performing action: {action_desc} in {service_name}...")
        delete_api(action_url, headers, params)

    elif STALLED_ACTION == "BLOCKLIST_AND_SEARCH":
        # Blocklist the item but allow redownload
        action_url = f"{base_url}/api/{api_version}/queue/{download_id}"
        params = {"blocklist": "true", "skipRedownload": "false"}
        logging.info(f"Performing action: {action_desc} in {service_name}...")
        delete_api(action_url, headers, params)

        # Trigger a search via the Command API
        if service_name == "Sonarr" and episode_ids:
            command_url = f"{base_url}/api/{api_version}/command"
            data = {"name": "EpisodeSearch", "episodeIds": episode_ids}
            logging.info(f"Triggering search for Episodes {episode_ids} in {service_name} using Command API...")
            post_api(command_url, headers, data)
        elif service_name == "Radarr" and movie_id:
            command_url = f"{base_url}/api/{api_version}/command"
            data = {"name": "MoviesSearch", "movieIds": [movie_id]}
            logging.info(f"Triggering search for Movie ID {movie_id} in {service_name} using Command API...")
            post_api(command_url, headers, data)
        else:
            logging.warning(f"No valid IDs found for download ID {download_id} in {service_name}, skipping search.")

    else:
        logging.error(f"Invalid STALLED_ACTION: {STALLED_ACTION}")

def handle_stalled_downloads(base_url, api_key, service_name, api_version):
    """
    Handle downloads that are stalled (status=warning).
    """
    logging.info(f"Checking stalled downloads in {service_name}...")

    # Query parameters for stalled detection
    params = {
        "protocol": "torrent",
        "status": "warning",  # Only look for stalled downloads
        "includeEpisode": "true" if service_name == "Sonarr" else "false"
    }

    headers = {"X-Api-Key": api_key}
    queue_url = f"{base_url}/api/{api_version}/queue"
    queue_records = query_api_paginated(queue_url, headers, params, page_size=50)

    if not queue_records:
        logging.info(f"No stalled downloads found in {service_name}.")
        return

    # Existing logic for handling stalled downloads
    stalled_downloads = get_stalled_downloads_from_db(service_name)
    for item in queue_records:
        if item.get("errorMessage", "").lower() == "the download is stalled with no connections":
            download_id = str(item["id"])
            movie_id = item.get("movieId") if service_name == "Radarr" else None
            episode_ids = [item["episodeId"]] if service_name == "Sonarr" and "episodeId" in item else None

            if download_id in stalled_downloads:
                first_detected = stalled_downloads[download_id]
                elapsed_time = (datetime.now(timezone.utc) - first_detected).total_seconds()

                logging.debug(f"Download ID {download_id} first detected: {first_detected}, elapsed: {elapsed_time} seconds.")
                if elapsed_time > STALLED_TIMEOUT:
                    logging.info(f"Handling stalled Download ID {download_id} in {service_name} (elapsed time: {elapsed_time} seconds).")
                    perform_action(base_url, headers, download_id, movie_id, service_name, api_version, episode_ids)
                    remove_stalled_download_from_db(download_id, service_name)
                else:
                    logging.info(f"Download ID {download_id} in {service_name} is stalled but within timeout period ({elapsed_time} seconds).")
            else:
                add_stalled_download_to_db(download_id, datetime.now(timezone.utc), service_name)
                logging.info(f"Adding stalled download ID {download_id} in {service_name} to the database.")

if __name__ == "__main__":
    try:
        while True:
            initialize_database()

            #itterate through env variables for services
            for radarrCount in range(len(RADARR_URL)):
                handle_stalled_downloads(RADARR_URL[radarrCount], RADARR_API_KEY[radarrCount], "Radarr"+str(radarrCount), "v3")  # Handle regular stalled downloads
                detect_stuck_metadata_downloads(RADARR_URL[radarrCount], RADARR_API_KEY[radarrCount], "Radarr"+str(radarrCount), "v3")  # Detect stuck downloads at "Downloading Metadata"

            for sonarrCount in range(len(SONARR_URL)):
                handle_stalled_downloads(SONARR_URL[sonarrCount], SONARR_API_KEY[sonarrCount], "Sonarr"+str(sonarrCount), "v3")  # Handle regular stalled downloads
                detect_stuck_metadata_downloads(SONARR_URL[sonarrCount], SONARR_API_KEY[sonarrCount], "Sonarr"+str(sonarrCount), "v3")  # Detect stuck downloads at "Downloading Metadata"
            
            for lidarrCount in range(len(LIDARR_URL)):
                handle_stalled_downloads(LIDARR_URL[lidarrCount], LIDARR_API_KEY[lidarrCount], "lidarr"+str(lidarrCount), "v1")  # Handle regular stalled downloads
                detect_stuck_metadata_downloads(LIDARR_URL[lidarrCount], LIDARR_API_KEY[lidarrCount], "Lidarr"+str(lidarrCount), "v1")  # Detect stuck downloads at "Downloading Metadata"

            for readarrCount in range(len(READARR_URL)):
                handle_stalled_downloads(READARR_URL[readarrCount], READARR_API_KEY[readarrCount], "readarr"+str(readarrCount), "v1")  # Handle regular stalled downloads
                detect_stuck_metadata_downloads(READARR_URL[readarrCount], READARR_API_KEY[readarrCount], "Readarr"+str(readarrCount), "v1")  # Detect stuck downloads at "Downloading Metadata"

            logging.info(f"Script execution completed. Sleeping for {RUN_INTERVAL} seconds...")
            time.sleep(RUN_INTERVAL)
    except KeyboardInterrupt:
        logging.info("Script terminated by user.")
    except Exception as e:
        logging.exception(f"An error occurred: {e}")