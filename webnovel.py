from typing import Self, Optional
from urllib.parse import urlencode

import requests
from requests import Response


class WebNovel:
    __BASE_URL: str = "https://www.webnovel.com/go/pcm"

    def __request(self: Self, path: str, payload: Optional[dict] = None) -> Response:
        if payload is None:
            url_params: str = ""
        else:
            url_params: str = urlencode(payload)

        return requests.get(
            url=f"{self.__BASE_URL}{path}?{url_params}",
            headers={
                "User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0)"
            },
        )

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
