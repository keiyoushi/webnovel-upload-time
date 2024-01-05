import concurrent.futures
import json
import os
from pathlib import Path

from tqdm.auto import tqdm
from tqdm.contrib.concurrent import thread_map

from database import Database
from webnovel import WebNovel

CWD = Path().cwd()
DATA_FOLDER = CWD.joinpath("data")
DATA_FOLDER.mkdir(parents=True, exist_ok=True)
BUILD_FOLDER = CWD.joinpath("build")
BUILD_FOLDER.mkdir(parents=True, exist_ok=True)

if os.getenv("CI") is not None:
    print("CI is enabled")
    MAX_WORKERS = 10
else:
    MAX_WORKERS = 25


def main():
    database = Database(DATA_FOLDER.joinpath("database.sqlite3"))
    webnovel = WebNovel()
    page_item_count, total_item = webnovel.get_pagination_info()
    last_page = -(-total_item // page_item_count)

    tqdm.write(f"Getting comic ids")
    comic_ids_results = thread_map(
        lambda i: webnovel.get_comic_ids(i + 1),
        range(last_page),
        max_workers=MAX_WORKERS,
    )
    comic_ids = sorted(
        {comic_id for result in comic_ids_results for comic_id in result}
    )

    tqdm.write("Getting chapter ids for comics")
    comic_chapter_ids = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        tasks = []
        for comic_id in comic_ids:
            task = executor.submit(webnovel.get_chapter_ids, comic_id)
            tasks.append((comic_id, task))

        for comic_id, task in tqdm(tasks):
            chapter_ids = task.result()
            for chapter_id in chapter_ids:
                comic_chapter_ids.append((comic_id, chapter_id))

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        tasks = []
        tqdm.write("Submitting chapters to fetch upload time")
        for comic_id, chapter_id in tqdm(comic_chapter_ids):
            if database.has_chapter_upload_time(comic_id, chapter_id):
                continue

            task = executor.submit(
                webnovel.get_chapter_upload_time, comic_id, chapter_id
            )
            tasks.append((comic_id, chapter_id, task))
        tqdm.write("Inserting new chapters upload time to db")
        for comic_id, chapter_id, task in tqdm(tasks):
            try:
                upload_time = task.result()
            except Exception as e:
                _ = e
                continue
            database.insert_chapter_upload_time(comic_id, chapter_id, upload_time)

    tqdm.write("Generating json files")
    for comic_id in database.get_comic_ids():
        with open(BUILD_FOLDER.joinpath(f"{comic_id}.json"), "w") as json_file:
            json.dump(database.get_chapter_data(comic_id), json_file)


if __name__ == "__main__":
    main()
