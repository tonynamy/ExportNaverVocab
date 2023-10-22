import csv
import inquirer

from naver_session import NaverSession
from naver_vocab import NaverVocab
from naver_vocab_book import NaverVocabBook


def inquire_is_session_load() -> bool:
    questions = [inquirer.Confirm("is_session_load", message="세션을 불러오시겠습니까?")]
    answers = inquirer.prompt(questions)
    return answers["is_session_load"]


def inquire_is_session_save() -> bool:
    questions = [inquirer.Confirm("is_session_save", message="세션을 저장하시겠습니까?")]
    answers = inquirer.prompt(questions)
    return answers["is_session_save"]


def inquire_sesion_file_path() -> str:
    questions = [inquirer.Path("session_file_path", message="세션 파일 경로를 입력하세요")]
    answers = inquirer.prompt(questions)
    return answers["session_file_path"]


def inquire_username_and_password() -> tuple[str, str]:
    questions = [
        inquirer.Text("username", message="네이버 아이디를 입력하세요"),
        inquirer.Password("password", message="네이버 비밀번호를 입력하세요"),
    ]
    answers = inquirer.prompt(questions)
    return answers["username"], answers["password"]


def inquire_book_type() -> NaverVocabBook.Type:
    questions = [
        inquirer.List(
            "book_type",
            message="사전을 선택하세요",
            choices=[
                ("일한사전", NaverVocabBook.Type.JAKO),
                ("중한사전", NaverVocabBook.Type.ZHKO),
            ],
        ),
    ]
    answers = inquirer.prompt(questions)
    return NaverVocabBook.Type(answers["book_type"])


def inquire_book_id(books: list[NaverVocabBook]) -> str:
    questions = [
        inquirer.List(
            "book_id",
            message="단어장을 선택하세요",
            choices=[(book.book_name, book.book_id) for book in books],
        ),
    ]
    answers = inquirer.prompt(questions)
    return answers["book_id"]


def inquire_csv_file_path() -> str:
    questions = [inquirer.Path("csv_file_path", message="CSV 파일 경로를 입력하세요")]
    answers = inquirer.prompt(questions)
    return answers["csv_file_path"]


def inquire_quit() -> bool:
    questions = [inquirer.Confirm("quit", message="종료하시겠습니까?")]
    answers = inquirer.prompt(questions)
    return answers["quit"]


def get_session():
    try:
        if inquire_is_session_load():
            session_file_path = inquire_sesion_file_path()
            return NaverSession.from_file(session_file_path)

    except FileNotFoundError:
        print("세션 파일을 찾지 못했습니다. 로그인을 진행합니다.")

    if inquire_is_session_save():
        session_file = inquire_sesion_file_path()

    username, password = inquire_username_and_password()
    session = NaverSession.login(username, password)
    session.save(session_file)

    return session


def _get_front_and_back(
    book_type: NaverVocabBook.Type, vocab: NaverVocab
) -> tuple[str, str]:
    match book_type:
        case NaverVocabBook.Type.JAKO:
            return (vocab.word, f"{vocab.pron}<br/>{vocab.meaning}")

        case NaverVocabBook.Type.ZHKO:
            return (vocab.word, f"{vocab.pron}<br/>{vocab.meaning}")

        case _:
            raise NotImplementedError


def main():
    session = get_session()

    while True:
        book_type = inquire_book_type()

        books = NaverVocabBook.get_book_list(session, book_type)

        book_id = inquire_book_id(books)

        selected_book = NaverVocabBook.get_book_from_id(session, book_id, book_type)
        selected_book.load_vocabs(session)

        csv_file_path = inquire_csv_file_path()

        with open(csv_file_path, "w", encoding="utf8") as f:
            vocabs = selected_book.vocabs
            assert vocabs

            wr = csv.writer(f)

            for vocab in vocabs:
                wr.writerow(_get_front_and_back(book_type, vocab))

        print(f"{len(vocabs)}개 단어를 {csv_file_path}에 저장했습니다.")

        if inquire_quit():
            break


if __name__ == "__main__":
    main()
