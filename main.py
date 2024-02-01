import json
import os
from pathlib import Path

from tqdm.auto import tqdm

from database import Database
from webnovel import WebNovel

CWD = Path().cwd()
DATA_FOLDER = CWD.joinpath("data")
DATA_FOLDER.mkdir(parents=True, exist_ok=True)
BUILD_FOLDER = CWD.joinpath("build")
BUILD_FOLDER.mkdir(parents=True, exist_ok=True)

MAX_WORKERS = 10
PROXY_URL = os.getenv("PROXY_URL")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")


def main():
    database = Database(DATA_FOLDER.joinpath("database.sqlite3"))
    webnovel = WebNovel(PROXY_URL, WEBHOOK_URL)
    page_item_count, total_item = webnovel.get_pagination_info()
    last_page = -(-total_item // page_item_count)

    tqdm.write(f"Getting comic ids")
    comic_ids: set[int] = set()
    for page_index in tqdm(range(last_page)):
        comic_ids.update(webnovel.get_comic_ids(page_index + 1))

    tqdm.write("Getting chapter ids for comics")
    comic_chapter_ids: set[tuple[int, int]] = set()
    for comic_id in tqdm(comic_ids):
        for chapter_id in webnovel.get_chapter_ids(comic_id):
            if database.has_chapter_upload_time(comic_id, chapter_id):
                continue

            comic_chapter_ids.add((comic_id, chapter_id))

    tqdm.write("Inserting new chapters upload time to db")
    for comic_id, chapter_id in tqdm(comic_chapter_ids):
        upload_time = webnovel.get_chapter_upload_time(comic_id, chapter_id)
        database.insert_chapter_upload_time(comic_id, chapter_id, upload_time)

    tqdm.write("Generating json files")
    for comic_id in database.get_comic_ids():
        with open(BUILD_FOLDER.joinpath(f"{comic_id}.json"), "w") as json_file:
            json_string = json.dumps(database.get_chapter_data(comic_id), separators=(",", ":"))
            json_file.write(json_string + "\n")


if __name__ == "__main__":
    main()
