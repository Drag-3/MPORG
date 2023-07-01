import argparse
import concurrent.futures
import multiprocessing
import queue
import threading
from pathlib import Path
from queue import Queue

import api

SUPPORTED_FILETYPES = [".mp3", ".wav", ".flac", ".ogg", ".wma", ".m4a", ".oga"]
end_of_search = threading.Event()

def search_lyrics_single(args):
    if args.method == 'name_artist':
        result = api.search_lyrics_by_name_artist(args.track_name, args.track_artist)
    elif args.method == 'spotify_url':
        result = api.search_lyrics_by_spotify_url(args.spotify_url)
    elif args.method == 'spotify_track_id':
        result = api.search_lyrics_by_spotify_track_id(args.spotify_track_id)
    elif args.method == 'file':
        result = api.search_lyrics_by_file(Path(args.file))
    else:
        print(f"Invalid search method: {args.method}")
        return

    print(result)


def search_files(search_path: Path, file_queue: Queue):
    for filetype in SUPPORTED_FILETYPES:
        music_files = search_path.rglob(f"*{filetype}")
        for music_file in music_files:
            file_queue.put(music_file)
    print("Finished Scanning")
    end_of_search.set()


def process_file_queue(file_queue: Queue[Path]):
    while True:
        try:
            music_file = file_queue.get(timeout=5)
            if music_file is None:
                # Reached the end of file search, exit the thread
                if end_of_search.is_set():
                    file_queue.task_done()
                    print("Thread Done")
                    break
            else:
                api.search_lyrics_by_file(music_file)
            #file_queue.task_done()
        except queue.Empty:
            if end_of_search.is_set():
                file_queue.task_done()
                print("Empty -Exp Thread Done")
                break
        except Exception as e:
            print("Exception", e)
        finally:
            file_queue.task_done()


def search_lyrics_batch(args):
    search_path = Path(args.search_path)

    if not search_path.is_dir():
        print(f"Invalid search path: {search_path}")
        return

    music_files_queue = Queue()

    file_search_thread = threading.Thread(target=search_files, args=(search_path, music_files_queue))
    file_search_thread.start()

    num_threads = min(6, multiprocessing.cpu_count() // 2)  # Number of threads in the thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        # Start worker threads to process the file queue
        for _ in range(num_threads):
            executor.submit(process_file_queue, music_files_queue)

    # Wait for the file search thread to finish
    file_search_thread.join()

    # Wait for all files to be processed
    music_files_queue.join()


def parse_args():
    parser = argparse.ArgumentParser(description='Lyrics Search CLI')
    subparsers = parser.add_subparsers(dest='mode', help='Mode')

    # Single mode subcommand
    single_parser = subparsers.add_parser('single', help='Single mode')
    single_subparsers = single_parser.add_subparsers(dest='method', help='Search method')

    # Metadata subcommand
    metadata_parser = single_subparsers.add_parser('metadata', help='Search lyrics by track metadata')
    metadata_parser.add_argument('track_name', type=str, help='Track name')
    metadata_parser.add_argument('track_artist', type=str, help='Track artist')
    metadata_parser.add_argument('album_name', type=str, help='Album name')

    # Name/artist subcommand
    name_artist_parser = single_subparsers.add_parser('name_artist', help='Search lyrics by track name and artist')
    name_artist_parser.add_argument('track_name', type=str, help='Track name')
    name_artist_parser.add_argument('track_artist', type=str, help='Track artist')

    # Spotify URL subcommand
    spotify_url_parser = single_subparsers.add_parser('spotify_url', help='Search lyrics by Spotify URL')
    spotify_url_parser.add_argument('spotify_url', type=str, help='Spotify URL')

    # Spotify track ID subcommand
    spotify_track_id_parser = single_subparsers.add_parser('spotify_track_id', help='Search lyrics by Spotify track ID')
    spotify_track_id_parser.add_argument('spotify_track_id', type=str, help='Spotify track ID')

    spotify_track_id_parser = single_subparsers.add_parser('file', help='Search lyrics by the path to an audio file')
    spotify_track_id_parser.add_argument('file', type=str, help='Path to file')

    # Batch mode subcommand
    batch_parser = subparsers.add_parser('batch', help='Batch mode')
    batch_parser.add_argument('search_path', type=str, help='Search path')

    return parser.parse_args()


def main():
    args = parse_args()

    if args.mode == 'single':
        search_lyrics_single(args)
    elif args.mode == 'batch':
        search_lyrics_batch(args)
    else:
        print(f"Invalid mode: {args.mode}")


if __name__ == '__main__':
    main()
