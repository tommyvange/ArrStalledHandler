# ArrStalledHandler

ArrStalledHandler is a Python-based script designed to handle stalled downloads in [Radarr](https://radarr.video/), [Sonarr](https://sonarr.tv/), [Lidarr](https://lidarr.audio/) and [Readarr](https://readarr.com/) by taking actions such as removing, blocklisting, or blocklisting and re-searching for the affected items. It supports configuration through a `.env` file, logging for visibility, and is deployable via Docker for ease of use.

This repository is licensed under the **[GNU General Public License v3.0 (GPLv3)](LICENSE)**.

Created by **[Tommy Vange Rød](https://github.com/tommyvange)**. You can see the full list of credits [here](#credits).

This project is available on [GitHub](https://github.com/tommyvange/ArrStalledHandler), [Docker Hub](https://hub.docker.com/r/tommythebeast/arrstalledhandler) and the [Unraid Community App store](#unraid-deployment). 

[![Publish Docker image](https://github.com/tommyvange/ArrStalledHandler/actions/workflows/publish-docker-image.yml/badge.svg)](https://github.com/tommyvange/ArrStalledHandler/actions/workflows/publish-docker-image.yml)
[![Check docker build](https://github.com/tommyvange/ArrStalledHandler/actions/workflows/check-docker-image.yml/badge.svg?branch=main)](https://github.com/tommyvange/ArrStalledHandler/actions/workflows/check-docker-image.yml)

----------

## Features

-   **Automatic Handling of Stalled Downloads**:
    -   Detect stalled downloads based on error messages from Radarr/Sonarr/Lidarr/Readarr queues.
    - Detect download stuck on "Downloading Metadata" in qBittorrent and treat them as stalled.
    -   Perform configurable actions such as:
        -   Remove the stalled download.
        -   Blocklist the stalled download.
        -   Blocklist and re-trigger a search for the movie or episodes.
-   **Database Tracking**:
    -   Tracks stalled downloads in a SQLite database to ensure actions are only taken after a specified timeout period.
-   **Logging**:
    -   Verbose and informative logging controlled via configuration.
-   **Docker Support**:
    -   Easily deployable with Docker and customizable run intervals.

----------


## Configuration

The script is fully configurable using environment variables specified in a `.env` file. Below is a description of each configuration option:

### `.env` Variables

| Variable                                | Description                                                                                     | Default Value          |
|-----------------------------------------|-------------------------------------------------------------------------------------------------|------------------------|
| `RADARR_URL`                            | The base URL for Radarr's API. Example: `http://localhost:7878,http://otherhost:7878`.          | None (required)        |
| `RADARR_API_KEY`                        | The API key for Radarr (found in Radarr settings).                                              | None (required)        |
| `SONARR_URL`                            | The base URL for Sonarr's API. Example: `http://localhost:8989,http://otherhost:8989`.          | None (required)        |
| `SONARR_API_KEY`                        | The API key for Sonarr (found in Sonarr settings).                                              | None (required)        |
| `LIDARR_URL`                            | The base URL for Lidarr's API. Example: `http://localhost:8686,http://otherhost:8686`.          | None (required)        |
| `LIDARR_API_KEY`                        | The API key for Lidarr (found in Radarr settings).                                              | None (required)        |
| `READARR_URL`                           | The base URL for Readarr's API. Example: `http://localhost:8787,http://otherhost:8787`.         | None (required)        |
| `READARR_API_KEY`                       | The API key for Readarr (found in Sonarr settings).                                             | None (required)        |
| `STALLED_TIMEOUT`                       | Time (in seconds) a download must remain stalled before actions are taken.                      | `3600` (1 hour)        |
| `STALLED_ACTION`                        | Action to perform on stalled downloads: `REMOVE`, `BLOCKLIST`, or `BLOCKLIST_AND_SEARCH`.       | `BLOCKLIST_AND_SEARCH` |
| `VERBOSE`                               | Enable verbose logging for debugging (`true` or `false`).                                       | `false`                |
| `RUN_INTERVAL`                          | Time (in seconds) between script executions when running in Docker.                             | `300` (5 minutes)      |
| `COUNT_DOWNLOADING_METADATA_AS_STALLED` | Weather the script should count downloads with the status of "Downloading Metadata" as stalled. | `false`                |

To disable Radarr or Sonarr; leave the URL empty in the environment. If the service does not have a URL, then it is skipped. Multple services are allowed by using comma seperated values.

----------

## How It Works

### Script Workflow

1.  **Initialization**:
    
    -   The script initializes a SQLite database (`stalled_downloads.db`) to track stalled downloads.
    -   It fetches the current queue from Radarr and Sonarr APIs.
2.  **Detect Stalled Downloads**:
    
    -   The script identifies stalled downloads based on the error message: `"The download is stalled with no connections"`.
    -   [Optional] The script treats downloads with the error message `"qBittorrent is downloading metadata"` as stalled.
3.  **Timeout Check**:
    
    -   Downloads are only handled if they have been stalled longer than the configured `STALLED_TIMEOUT`.
4.  **Perform Configured Action**:
    
    -   Based on the `STALLED_ACTION` setting:
        -   **REMOVE**: Removes the stalled download.
        -   **BLOCKLIST**: Removes and blocklists the stalled download.
        -   **BLOCKLIST_AND_SEARCH**: Removes, blocklists, and re-triggers a search for the movie or episodes.
5.  **Logging**:
    
    -   Logs detailed information about each action for visibility.
6.  **Repeat**:
    
    -   When running in Docker, the script waits for the `RUN_INTERVAL` duration and repeats the process.

----------

## Deployment
### Unraid Deployment
![Picture of application in the Unraid Community App store](https://i.ibb.co/BNghTZN/image-png-fe1039ecc35d3aa9ffc37541edbd5e0d.jpg)
1. Install the Community Apps extension as documented in [this guide](https://forums.unraid.net/topic/38582-plug-in-community-applications/).
2. Go to the **Apps**-section in your Unraid web-ui.
3. Search for **ArrStalledHandler**.
4. Click **Install** on the application.
5. Fill out the variables according to the [Configuration](#configuration).
6. Click **Apply**.

Now the container should automatically start up and start handling your stalled downloads.

### Docker Deployment ([Docker Hub](https://hub.docker.com/r/tommythebeast/arrstalledhandler))

**Docker compose**

More info at [Docker Docs](https://docs.docker.com/compose/intro/compose-application-model/).
``` yaml
services:
  arr-stalled-handler:
    image: tommythebeast/arrstalledhandler:latest
    container_name: ArrStalledHandler
    restart: unless-stopped
    environment:
      RADARR_URL: "http://localhost:7878,http://otherhost:7878"
      RADARR_API_KEY: "your_radarr_api_key,your_2nd_radarr_api_key"
      SONARR_URL: "http://localhost:8989,http://otherhost:8989"
      SONARR_API_KEY: "your_sonarr_api_key,your_2nd_sonarr_api_key"
      LIDARR_URL: "http://localhost:8686,http://otherhost:8686"
      LIDARR_API_KEY: "your_lidarr_api_key,your_2nd_lidarr_api_key"
      READARR_URL: "http://localhost:8787,http://otherhost:8787"
      READARR_API_KEY: "your_readarr_api_key,our_2nd_readarr_api_key"
      STALLED_TIMEOUT: "3600"
      STALLED_ACTION: "BLOCKLIST_AND_SEARCH"
      VERBOSE: "false"
      RUN_INTERVAL: "300"
      COUNT_DOWNLOADING_METADATA_AS_STALLED: "false"
```

**Docker CLI**

More info at [Docker Docs](https://docs.docker.com/engine/containers/run/).

*Multi-line:*
``` bash
docker run -d \
  --name=ArrStalledHandler \
  -e RADARR_URL=http://localhost:7878,http://otherhost:7878 \
  -e RADARR_API_KEY=your_radarr_api_key,your_2nd_radarr_api_key \
  -e SONARR_URL=http://localhost:8989,http://otherhost:8989 \
  -e SONARR_API_KEY=your_sonarr_api_key,your_2nd_sonarr_api_key \
  -e LIDARR_URL=http://localhost:8686,http://otherhost:8686 \
  -e LIDARR_API_KEY=your_lidarr_api_key,your_2nd_lidarr_api_key \
  -e READARR_URL=http://localhost:8787,http://otherhost:8787 \
  -e READARR_API_KEY=your_readarr_api_key,our_2nd_readarr_api_key \
  -e STALLED_TIMEOUT=3600 \
  -e STALLED_ACTION=BLOCKLIST_AND_SEARCH \
  -e VERBOSE=false \
  -e RUN_INTERVAL=300 \
  -e COUNT_DOWNLOADING_METADATA_AS_STALLED=false \
  --restart unless-stopped \
  tommythebeast/arrstalledhandler:latest
```

*One line:*
``` bash
docker run -d --name=ArrStalledHandler -e RADARR_URL=http://localhost:7878,http://otherhost:7878 -e RADARR_API_KEY=your_radarr_api_key,your_2nd_radarr_api_key -e SONARR_URL=http://localhost:8989,http://otherhost:8989 -e SONARR_API_KEY=your_sonarr_api_key,your_2nd_sonarr_api_key -e LIDARR_URL=http://localhost:8686,http://otherhost:8686  -e LIDARR_API_KEY=your_lidarr_api_key,your_2nd_lidarr_api_key -e READARR_URL=http://localhost:8787,http://otherhost:8787 -e READARR_API_KEY=your_readarr_api_key,our_2nd_readarr_api_key -e STALLED_TIMEOUT=3600 -e STALLED_ACTION=BLOCKLIST_AND_SEARCH -e VERBOSE=false -e RUN_INTERVAL=300 -e COUNT_DOWNLOADING_METADATA_AS_STALLED=false --restart unless-stopped tommythebeast/arrstalledhandler:latest
```

### Docker Deployment (Manual)

1.  **Clone the Repository**:
    
    ``` bash
    git clone https://github.com/your-username/ArrStalledHandler.git
    cd ArrStalledHandler
    ```
    
2.  **Configure Environment**:
    
    Create a `.env` file and populate it with the required variables:
 
    ``` env
    RADARR_URL=http://localhost:7878,http://otherhost:7878
    RADARR_API_KEY=aaaabbbbcccc111122223333,xxxxyyyyzzzz777788889999
    SONARR_URL=http://localhost:8989,http://otherhost:8989
    SONARR_API_KEY=aaaabbbbcccc111122223333,xxxxyyyyzzzz777788889999
    LIDARR_URL=http://localhost:8686,http://otherhost:8686
    LIDARR_API_KEY=aaaabbbbcccc111122223333,xxxxyyyyzzzz777788889999
    READARR_URL=http://localhost:8787,http://otherhost:8787
    READARR_API_KEY=aaaabbbbcccc111122223333,xxxxyyyyzzzz777788889999
    STALLED_TIMEOUT=3600
    STALLED_ACTION=BLOCKLIST_AND_SEARCH
    VERBOSE=false
    RUN_INTERVAL=300
    COUNT_DOWNLOADING_METADATA_AS_STALLED=false
    ```

3.  **Build the Docker Image**:
    
    ``` bash
    docker-compose build .
    ```
    
4.  **Run the Docker Container**:
    
    ``` bash
    docker-compose up -d
    ```

### Local Installation

*Requires Python 3.13*

1.  **Clone the Repository**:
    
    ``` bash
    git clone https://github.com/your-username/ArrStalledHandler.git
    cd ArrStalledHandler
    ```
    
2.  **Install Dependencies**:
    ``` bash
    pip install -r requirements.txt
    ```
        
3.  **Configure Environment**:
    
    Create a `.env` file and populate it with the required variables:
 
    ``` env
    RADARR_URL=http://localhost:7878,http://otherhost:7878
    RADARR_API_KEY=aaaabbbbcccc111122223333,xxxxyyyyzzzz777788889999
    SONARR_URL=http://localhost:8989,http://otherhost:8989
    SONARR_API_KEY=aaaabbbbcccc111122223333,xxxxyyyyzzzz777788889999
    LIDARR_URL=http://localhost:8686,http://otherhost:8686
    LIDARR_API_KEY=aaaabbbbcccc111122223333,xxxxyyyyzzzz777788889999
    READARR_URL=http://localhost:8787,http://otherhost:8787
    READARR_API_KEY=aaaabbbbcccc111122223333,xxxxyyyyzzzz777788889999
    STALLED_TIMEOUT=3600
    STALLED_ACTION=BLOCKLIST_AND_SEARCH
    VERBOSE=false
    RUN_INTERVAL=300
    COUNT_DOWNLOADING_METADATA_AS_STALLED=false
    ```
        
4.  **Run the Script**:
    
    ``` bash
    python main.py
    ```

----------

## Logging

-   Logs are written to the console and are controlled by the `VERBOSE` environment variable.
-   If `VERBOSE` is set to `true`, debug-level logs are enabled. 

Example log output:
    
``` text
INFO: Checking stalled downloads in Radarr...
INFO: Handling Download ID 1462067687 in Radarr (elapsed time: 400 seconds).
INFO: Triggering search for Movie ID 770 in Radarr using Command API...
INFO: Script execution completed. Sleeping for 300 seconds...
```
    

----------

## Troubleshooting

1. **Script Not Executing Actions**:
    -   Check if `STALLED_TIMEOUT` is too high.
    -   Verify the stalled downloads are correctly detected via Radarr/Sonarr queues.

----------

## Credits

### Author

<!-- readme: tommyvange -start -->
<table>
	<tbody>
		<tr>
            <td align="center">
                <a href="https://github.com/tommyvange">
                    <img src="https://avatars.githubusercontent.com/u/28400191?v=4" width="100;" alt="tommyvange"/>
                    <br />
                    <sub><b>Tommy Vange Rød</b></sub>
                </a>
            </td>
		</tr>
	<tbody>
</table>
<!-- readme: tommyvange -end -->

You can find more of my work on my [GitHub profile](https://github.com/tommyvange) or connect with me on [LinkedIn](https://www.linkedin.com/in/tommyvange/).

### Contributors
Huge thanks to everyone who dedicates their valuable time to improving, perfecting, and supporting this project!

<!-- readme: contributors,tommyvange/- -start -->
<table>
	<tbody>
		<tr>
            <td align="center">
                <a href="https://github.com/supernovatroubling">
                    <img src="https://avatars.githubusercontent.com/u/58279766?v=4" width="100;" alt="supernovatroubling"/>
                    <br />
                    <sub><b>supernovatroubling</b></sub>
                </a>
            </td>
		</tr>
	<tbody>
</table>
<!-- readme: contributors,tommyvange/- -end -->

----------

# GNU General Public License v3.0 (GPLv3)

The  **GNU General Public License v3.0 (GPLv3)**  is a free, copyleft license for software and other creative works. It ensures your freedom to share, modify, and distribute all versions of a program, keeping it free software for everyone.

Full license can be read [here](LICENSE) or at [gnu.org](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text).

## Key Points:

1.  **Freedom to Share and Change:**
    
    -   You can distribute copies of GPLv3-licensed software.
    -   Access the source code.
    -   Modify the software.
    -   Create new free programs using parts of it.
2.  **Responsibilities:**
    
    -   If you distribute GPLv3 software, pass on the same freedoms to recipients.
    -   Provide the source code.
    -   Make recipients aware of their rights.
3.  **No Warranty:**
    
    -   No warranty for this free software.
    -   Developers protect your rights through copyright and this license.
4.  **Marking Modifications:**
    
    -   Clearly mark modified versions to avoid attributing problems to previous authors.
