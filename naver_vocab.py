from dataclasses import dataclass
import json
from typing import TYPE_CHECKING, TypedDict, cast

from naver_session import NaverSession
from naver_vocab_entry import get_entry_dict

if TYPE_CHECKING:
    from naver_vocab_book import NaverVocabBook


class NaverVocabResponse(TypedDict):
    id: str
    entryId: str
    wordbookId: str
    name: str
    content: str


class NaverVocabListDataResponse(TypedDict):
    m_total: int
    over_last_page: bool
    next_cursor: str
    m_items: list[NaverVocabResponse]


class NaverVocabListResponse(TypedDict):
    data: NaverVocabListDataResponse


SEARCH_SIZE = 100


@dataclass
class NaverVocab:
    word: str
    meaning: str
    pron: str
    remarks: str | None = None

    @staticmethod
    def get_words_response(
        naver_session: NaverSession,
        *,
        book: "NaverVocabBook",
        cursor: str | None = None,
    ):
        book_id = book.book_id

        if cursor is None:
            link = f"https://learn.dict.naver.com/gateway-api/{book.book_type}/mywordbook/word/list/search?wbId={book_id}&qt=0&st=0&page_size={SEARCH_SIZE}&domain=naver"
        else:
            link = f"https://learn.dict.naver.com/gateway-api/{book.book_type}/mywordbook/word/list/search?wbId={book_id}&qt=0&st=0&cursor={cursor}&page_size={SEARCH_SIZE}&domain=naver"

        vocabs_text = naver_session.session.get(link)

        return cast(NaverVocabListResponse, json.loads(vocabs_text.text))

    @staticmethod
    def get_vocabs(naver_session: NaverSession, book: "NaverVocabBook"):
        cursor = None
        words: list[NaverVocab] = []

        while (
            response := NaverVocab.get_words_response(
                naver_session, book=book, cursor=cursor
            )
        )["data"]["over_last_page"] is False:
            words += [
                NaverVocab(
                    **get_entry_dict(book.book_type, json.loads(item["content"])),
                )
                for item in response["data"]["m_items"]
            ]

            cursor = response["data"]["next_cursor"]

        return words
