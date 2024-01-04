import sqlite3
from os import PathLike
from typing import Union


class Database:
    def __init__(self, database: Union[str, bytes, PathLike[str], PathLike[bytes]]):
        self.__connection = sqlite3.connect(database)
        self.__connection.row_factory = sqlite3.Row
        self.__migrate()

    def __migrate(self):
        version = self.__connection.execute("PRAGMA user_version").fetchone()[
            "user_version"
        ]
        if version < 1:
            self.__connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chapter_upload_time(
                    comic_id INTEGER NOT NULL,
                    chapter_id INTEGER NOT NULL,
                    upload_time INTEGER NOT NULL,
                    PRIMARY KEY (comic_id, chapter_id)
                )
                """
            )
            self.__connection.commit()
            self.__set_version(1)

    def __set_version(self, version: int):
        self.__connection.execute("PRAGMA user_version = {v:d}".format(v=version))
        self.__connection.commit()

    def has_chapter_upload_time(self, comic_id: int, chapter_id: int) -> bool:
        return (
            self.__connection.execute(
                """
                    SELECT * FROM chapter_upload_time WHERE comic_id = :comic_id AND chapter_id = :chapter_id LIMIT 1
                    """,
                {"comic_id": comic_id, "chapter_id": chapter_id},
            ).fetchone()
            is not None
        )

    def insert_chapter_upload_time(
        self, comic_id: int, chapter_id: int, upload_time: int
    ):
        self.__connection.execute(
            """
            INSERT INTO chapter_upload_time(comic_id, chapter_id, upload_time)
            VALUES(:comic_id, :chapter_id, :upload_time)
            """,
            {
                "comic_id": comic_id,
                "chapter_id": chapter_id,
                "upload_time": upload_time,
            },
        )
        self.__connection.commit()

    def get_comic_ids(self) -> list[int]:
        comic_ids_result = self.__connection.execute(
            "SELECT DISTINCT comic_id FROM chapter_upload_time"
        ).fetchall()
        return [row["comic_id"] for row in comic_ids_result]

    def get_chapter_data(self, comic_id: int) -> dict[int, int]:
        result = self.__connection.execute(
            "SELECT chapter_id, upload_time FROM chapter_upload_time WHERE comic_id = :comic_id",
            {"comic_id": comic_id},
        ).fetchall()
        return {row["chapter_id"]: row["upload_time"] for row in result}
