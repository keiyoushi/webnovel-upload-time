import time
from typing import Optional
from urllib.parse import urlencode

import requests
from requests import Response
from tqdm.auto import tqdm


class WebNovel:
    __BASE_URL: str = "https://www.webnovel.com/go/pcm"
    __MAX_RETRIES: int = 3
    __BASE_DELAY: int = 1

    def __init__(self, proxy_url: str):
        self.__proxy_url = proxy_url

    def __request(self, path: str, payload: Optional[dict] = None) -> Response:
        for attempts in range(self.__MAX_RETRIES):
            response: Optional[Response] = None
            try:
                url_params = urlencode({"u": f"{self.__BASE_URL}{path}?{urlencode(payload) if payload else ''}"})
                response = requests.get(
                    url=f"{self.__proxy_url}?{url_params}",
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0)"
                    },
                )

                response.raise_for_status()
                return response
            except requests.RequestException as e:
                if response and response.status_code == 429:
                    tqdm.write(f"RATE LIMITED. Sleeping for a minute")
                    time.sleep(60)
                else:
                    if response:
                        tqdm.write(f"Request failed with HTTP error {response.status_code}")
                    else:
                        tqdm.write(f"Request failed with error")

                    tqdm.write(f"Failed to get response. Sleeping for a bit.")
                    time.sleep(2**attempts)

        raise Exception(f"Failed to get response after {self.__MAX_RETRIES} tries")

    def __category_request(self, page: Optional[int] = None) -> Response:
        payload: dict[str, int] = {
            "bookStatus": 0,
            "categoryId": 0,
            "categoryType": 2,
            "orderBy": 5,
        }
        if page is not None:
            payload["pageIndex"] = page

        return self.__request("/category/categoryAjax", payload)

    def get_pagination_info(self) -> tuple[int, int]:
        data: dict = self.__category_request().json()["data"]
        return len(data["items"]), data["total"]

    def get_comic_ids(self, page: int) -> list[int]:
        items: list[dict] = self.__category_request(page).json()["data"]["items"]
        return list(map(lambda item: int(item["bookId"]), items))

    def get_chapter_ids(self, comic_id: int) -> list[int]:
        response: dict = self.__request(
            "/comic/getChapterList", {"comicId": comic_id}
        ).json()
        return list(
            map(lambda item: int(item["chapterId"]), response["data"]["comicChapters"])
        )

    def get_chapter_upload_time(self, comic_id: int, chapter_id: int) -> int:
        response: dict = self.__request(
            "/comic/getContent", {"comicId": comic_id, "chapterId": chapter_id}
        ).json()
        return response["data"]["chapterInfo"]["publishTime"]
