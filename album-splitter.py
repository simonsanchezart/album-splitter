import concurrent.futures
import re
import argparse
import colorama
import os

from collections import namedtuple
from pathlib import Path
from glob import glob
from pydub import AudioSegment

parser = argparse.ArgumentParser(
    description="Splits .mp3's based on timestamps if a .txt with the same name of the .mp3 is found"
)
parser.add_argument(
    "-d",
    "--delete",
    type=bool,
    default=False,
    help="If True, deletes the original .mp3 after splitting",
    action=argparse.BooleanOptionalAction,
)
args = parser.parse_args()

colorama.init(autoreset=True)
TIMESTAMP_RE = r"((?:\d+:)+(?:\d{2}){1})"
Song = namedtuple("Song", ["title", "timestamp"])


def sanitize_title(title):
    return "".join(i for i in title if i not in r"\/:*?<>|")


# duration_specification = ["hours", "minutes", "seconds"]
def get_duration_in_ms(duration_specification):
    hours = int(duration_specification[0]) * 3.6e6
    minutes = int(duration_specification[1]) * 6e4
    seconds = int(duration_specification[2]) * 1000
    return hours + minutes + seconds


all_mp3s = [f for f in glob("*.mp3")]
all_txts = [f for f in glob("*.txt")]
if not all_mp3s or not all_txts:
    raise FileNotFoundError("No .mp3 or .txt files found")

albums = {}
for mp3 in all_mp3s:
    matching_txt = next((f for f in all_txts if Path(f).stem == Path(mp3).stem), None)
    if matching_txt:
        albums[mp3] = matching_txt


def export_song(song):
    print(f"\t{colorama.Fore.LIGHTCYAN_EX}Saving song '{song[0]}'\n")
    song[2].export(song[1], format="mp3")


for album_mp3, txt in albums.items():
    print(f"{colorama.Fore.GREEN}Processing {album_mp3}")

    songs = []
    with open(txt, "r", encoding="utf-8") as f:
        for song in f.readlines():
            song = re.sub(r"\n", "", song)
            song_timestamp = re.findall(TIMESTAMP_RE, song)

            if not song_timestamp:
                print(f"{colorama.Fore.RED}No timestamp found in '{song}'")
                continue

            song_title = song.replace(song_timestamp[0], "").strip()
            song_title = sanitize_title(song_title)

            song_timestamp = song_timestamp[0].split(":")
            if len(song_timestamp) < 3:
                song_timestamp.insert(0, "00")

            songs.append(Song(song_title, song_timestamp))
            print(
                f"\t{colorama.Fore.LIGHTGREEN_EX}Found song '{song_title}' with timestamp {":".join(song_timestamp)}"
            )

    print(f"\t{colorama.Fore.CYAN}Loading mp3 file")
    album_data = AudioSegment.from_mp3(album_mp3)
    album_dir = os.path.abspath(Path(album_mp3).stem)
    os.makedirs(album_dir, exist_ok=True)

    song_time_table = []

    for i, song in enumerate(songs):
        song_data = None
        song_save_path = os.path.join(album_dir, f"{i+1}- {song.title}.mp3")
        next_song = songs[i + 1] if i + 1 < len(songs) else None

        song_at = get_duration_in_ms(song.timestamp)
        if next_song:
            next_song_at = get_duration_in_ms(next_song.timestamp)
            song_time_table.append((song.title, song_save_path, album_data[song_at:next_song_at]))
        else:
            song_time_table.append((song.title, song_save_path, album_data[song_at:]))

    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(export_song, song_time_table)

    if args.delete:
        print(f"\t{colorama.Fore.RED}Removing {album_mp3}")
        os.remove(album_mp3)
