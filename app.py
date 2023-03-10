from py1337x import py1337x
import transmissionrpc
from rich.console import Console
from rich.table import Table
import json
import time
from db import DownloadHistory
from urllib.parse import urlparse, parse_qs
import threading
import logging
import sys
import os

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
# create a logger object
logger = logging.getLogger('my_logger')

# create a py1337x object
p = py1337x()
tc = transmissionrpc.Client(os.environ['TRANSMISSION_IP'], port=int(os.environ['TRANSMISSION_PORT']))
download_history_db = "1337x_download_history.db"

def get_remote_free_space(tc):
    # Get the amount of free space available on the storage directory
    free_space = tc.free_space('/downloads')
    # return in bytes
    return free_space

def get_magnet_from_link(link):
    return p.info(link)['magnetLink']

def get_name_from_magnet(magnet_link):
    url_components = urlparse(magnet_link)
    query_params = parse_qs(url_components.query)
    torrent_name = query_params.get('dn', [''])[0]
    return torrent_name

def mprint(torrent):
    print(torrent['name'], torrent['time'], torrent['seeders'], torrent['size'])

def download_magnet(magnet, download_history):
    torrent_name = get_name_from_magnet(magnet)
    # Check if the torrent has already been downloaded
    if torrent_name in download_history.get_all():
        logger.info(f"{torrent_name} has already been downloaded")
        return

    freespace = get_remote_free_space(tc)
    _torrent = tc.add_torrent(magnet)
    torrent_size_bytes = tc.get_torrent(_torrent.id).totalSize # in bytes

    # Check if there is enough space on the remote server to download the torrent
    if torrent_size_bytes > freespace:
        tc.remove_torrent(_torrent.id)
        raise Exception("Not enough space on the remote server")
    else:
        # Record the download timestamp and torrent name in the download history table
        # download_history.insert(torrent_name)
        # not recording the download history here because it will be recorded when the torrent is completed
        logger.info(f"Download started: {torrent_name}")

def view_download_progress():
    _torrents = tc.get_torrents()
    for torrent in _torrents:
        print(f"{torrent.name}: {torrent.progress * 100:.2f}% downloaded")

def get_table(torrents = p.top(category='xxx')):
    table = Table(show_header=True, header_style="bold magenta")

    # add columns to the table
    table.add_column("Name")
    table.add_column("Time")
    table.add_column("Seeders")
    table.add_column("Size")

    # add rows to the table
    for torrent in torrents['items']:
        table.add_row(torrent['name'], torrent['time'], torrent['seeders'], torrent['size'])
    return table

def check_and_download_torrents():
    download_history = DownloadHistory(download_history_db)
    while True:
        # categories = movies, tv, games, music, apps, anime, xxx, other
        # p.trending(category='anime')
        torrents = p.top(category='xxx')
        for torrent in torrents['items']:
            magnet = get_magnet_from_link(torrent['link'])
            try:
                download_magnet(magnet, download_history)
            except Exception as e:
                if "duplicate torrent" not in str(e):
                    logger.info(f"Error downloading {magnet}: {str(e)}")
            time.sleep(5)

def remove_by_name(torrent_name):
    torrents = tc.get_torrents()
    for torrent in torrents:
        if torrent.name == torrent_name:
            tc.remove_torrent(torrent.id, delete_data=True)

def delete_old_torrents():
    download_history = DownloadHistory(download_history_db)
    while True:
        # Remove torrents that were downloaded more than a week ago and delete their records from the download history
        one_week_ago = time.time() - (7 * 24 * 60 * 60)  # One week ago in seconds
        for download_info in download_history.get_all():
            if download_info['timestamp'] < one_week_ago:
                remove_by_name(download_info['name'])
                # tc.remove_torrent(download_info['name'], delete_data=True)
                download_history.remove(download_info['name'])
        time.sleep(120) # sleep for a day before checking again         

def insert_completed_torrents():
    download_history = DownloadHistory(download_history_db)
    while True:
        # Get all active torrents
        _torrents = tc.get_torrents()

        # Check if any torrents have completed downloading
        for torrent in _torrents:
            if torrent.progress == 1.0 or torrent.status == "seeding":
                # Check if the torrent has already been added to the download history
                if not download_history.contains(torrent.name):
                    # Insert the torrent name into the download history
                    download_history.insert(torrent.name)
                    logger.info(f"{torrent.name} has finished downloading and has been added to the download history.")

        # Wait for 30 seconds before checking again
        time.sleep(30)   

def main():

    # Create the threads and pass the appropriate DownloadHistory object to each one
    download_thread = threading.Thread(target=check_and_download_torrents)
    delete_thread = threading.Thread(target=delete_old_torrents)
    insert_thread = threading.Thread(target=insert_completed_torrents)


    # start both threads
    download_thread.start()
    delete_thread.start()
    insert_thread.start()

    # wait for both threads to finish before exiting
    download_thread.join()
    delete_thread.join()
    insert_thread.join()
if __name__ == "__main__":
    main()