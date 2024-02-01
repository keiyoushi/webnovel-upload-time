import time
import traceback
from typing import Optional
from urllib.parse import urlencode

import requests
from discord_webhook import DiscordWebhook
from requests import Response
from tqdm.auto import tqdm


class WebNovel:
    __BASE_URL: str = "https://www.webnovel.com/go/pcm"
    __MAX_RETRIES: int = 2
    __HEADERS: dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0)"
    }

    def __init__(self, proxy_url: Optional[str], webhook_url: Optional[str]):
        self.__proxy_url = proxy_url
        self.__webhook: Optional[DiscordWebhook] = None
        if webhook_url:
            self.__webhook = DiscordWebhook(url=webhook_url)

        # Content contains ZERO WIDTH NON-JOINER (U+200C) characters to stop discord from trimming '\n'.
        self.__send_webhook("‌\n‌\n‌\nSTARTING SESSION\n‌")

    def __send_webhook(
        self, content: str, embed_description: Optional[str] = None
    ) -> None:
        if self.__webhook is None:
            return

        self.__webhook.set_content(content=content)
        if embed_description is not None:
            self.__webhook.add_embed({"description": embed_description})
        self.__webhook.execute(remove_embeds=True)

    def __request(self, path: str, payload: Optional[dict] = None) -> Response:
        attempt: int = 0
        while attempt < self.__MAX_RETRIES:
            attempt += 1
            response: Optional[Response] = None
            try:
                url_params = urlencode(payload) if payload else ""
                url = f"{self.__BASE_URL}{path}?{url_params}"
                if self.__proxy_url is not None:
                    url = f"{self.__proxy_url}?{urlencode({'u': url})}"

                response = requests.get(url=url, headers=self.__HEADERS)
                response.raise_for_status()

                return response
            except requests.RequestException:
                if response is not None and response.status_code == 429:
                    message = "RATE LIMITED. Sleeping for a minute and retrying"
                    self.__send_webhook(f":warning: {message}")
                    tqdm.write(message)
                    time.sleep(60)
                else:
                    if response is not None:
                        message = (
                            f"Request failed with HTTP error {response.status_code}"
                        )
                        embed_description = None
                    else:
                        message = f"Request failed with error"
                        embed_description = "```py\n" + traceback.format_exc() + "```"

                    sleep_time: Optional[int] = None
                    if attempt < self.__MAX_RETRIES:
                        sleep_time: Optional[int] = 2**attempt

                    message += f"\nAttempt {attempt}/{self.__MAX_RETRIES}"

                    if sleep_time is not None:
                        message += f"\nRetrying in {sleep_time} seconds"

                    self.__send_webhook(
                        content=f":warning: {message}",
                        embed_description=embed_description,
                    )
                    tqdm.write(message)

                    if sleep_time is not None:
                        time.sleep(sleep_time)

        message = f"Failed to get response after {self.__MAX_RETRIES} tries"
        self.__send_webhook(f":warning::warning::warning: {message} @everyone")
        raise Exception(message)

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
