#!/usr/bin/python
# -*- coding: utf-8 -*-

import csv

import getpass

import json

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from urllib.parse import unquote

import requests

import re

# as per recommendation from @freylis, compile once only
RE_HTML = re.compile(r'<.*?>')
RE_PARENTHESIS = re.compile(r'\((?:[^)(]|\([^)(]*\))*\)')
RE_BRACKET = re.compile(r'\[(?:[^\]\[]|\[[^\]\[]*\])*\]')
RE_PARENTHESIS_HANGUL = re.compile(r'\(([ㄱ-ㅎ가-힣ㅏ-ㅣ\s]+)\)')
RE_HANGUL = re.compile(r'[가-힣]+')

RE_KANJI = re.compile(u'[\u4E00-\u9FFF\s]+')
RE_HIRA = re.compile(u'[\u3040-\u309Fー\s]+')
RE_KATA = re.compile(u'[\u30A0-\u30FF\s]+')
RE_JAPANESE = re.compile(u'[\u3040-\u30FF\u30A0-\u30FFー\s]+')
RE_HIRA_KATA = re.compile(u'[\u3040-\u30FFー\s]+')

def clean_html(raw):
  cleantext = re.sub(RE_HTML, '', raw)
  return cleantext

def clean_parenthesis(raw):

    while True:
        output = re.sub(RE_PARENTHESIS, '', raw)
        if output == raw:
            break
        raw = output

    while True:
        output = re.sub(RE_BRACKET, '', raw)
        if output == raw:
            break
        raw = output

    output = output.replace('\'', '')
    output = output.replace('\"', '')
    output = output.replace('‘', '')
    output = output.replace('’', '')

    return output

def clean_parenthesis_hangul(raw) :
    cleantext = re.sub(RE_PARENTHESIS_HANGUL , '', raw)
    return cleantext

def get_only_hangul(raw) :
    return ''.join(re.findall(RE_HANGUL, raw))

def get_only_hira_kata(raw) :
    return ''.join(re.findall(RE_HIRA_KATA, raw))

def get_only_japanese(raw) :
    return ''.join(re.findall(RE_JAPANESE, raw))

def get_first_item(raw) :
    return raw.split(';')[0].split(",")[0].split(".")[0].split("·")[0].strip()


def get_naver_login_session(username, password, session_save, session_load) :

    if not session_load :
        driver = webdriver.Chrome('./chromedriver/chromedriver.exe')
        driver.get('https://nid.naver.com/nidlogin.login')

        timeout = 5
        try:
            element_present = EC.presence_of_element_located((By.ID, 'id'))
            WebDriverWait(driver, timeout).until(element_present)
        except TimeoutException:
            print
            "Timed out waiting for page to load"

        driver.find_element(By.ID, 'id').send_keys(username)
        driver.find_element(By.ID, 'pw').send_keys(password)
        driver.find_element(By.ID, 'log.login').click()

        wait = WebDriverWait(driver, 600)
        wait.until(lambda driver: "https://nid.naver.com/" not in driver.current_url)

        cookies = driver.get_cookies()

        if session_save :

            with open('session_info', mode='w') as f :

                f.write(json.dumps(cookies))
    else :

        with open('session_info', mode='r') as f:

            cookies = json.loads(f.read())

    s = requests.Session()

    for cookie in cookies:
        s.cookies.set(cookie['name'], cookie['value'])

    return s

def get_vocab_lists(session, page, page_size=100) :

    vocab_lists_text = session.get(f"https://learn.dict.naver.com/gateway-api/jakodict/mywordbook/wordbook/list.dict?page={page}&page_size={page_size}&st=0&domain=naver")

    result = json.loads(vocab_lists_text.text)

    if result['meta']['status'] != 1 :
        raise Exception("단어장 목록 받아오기 실패")

    vocab_lists = result['data']['m_items']

    vocab_list_dict = {}

    for vocab_list in vocab_lists :

        vocab_list_dict[vocab_list['name']] = (vocab_list['id'], vocab_list['wordCount'])

    return vocab_list_dict


def get_vocabs(session, vocab_list_id, start, count, search_size=100):

    words = {}

    fisrt_page = start//100
    if fisrt_page == 0: fisrt_page = 1

    total_page = (start+count+100)//100
    if total_page == 0 : total_page = 1

    page = fisrt_page
    cursor = ""

    vocab_count = 0

    while page <= total_page :

        if page == 1 :
            link = f'https://learn.dict.naver.com/gateway-api/jakodict/mywordbook/word/list/search?wbId={vocab_list_id}&qt=0&st=0&page_size={search_size}&domain=naver'
        else :
            link = f'https://learn.dict.naver.com/gateway-api/jakodict/mywordbook/word/list/search?wbId={vocab_list_id}&qt=0&st=0&cursor={cursor}&page_size={search_size}&domain=naver'

        result = json.loads(session.get(link).text)

        if result['meta']['status'] != 1:
            raise Exception("단어장 목록 받아오기 실패")

        vocabs = result['data']['m_items']
        cursor = result['data']['next_cursor']

        for vocab in vocabs :

            vocab_count += 1

            if vocab_count < start : continue

            word, meaning = process_vocab(vocab)

            if word == None or meaning == None : continue

            words[word] = meaning

            if vocab_count >= count + start - 1: break

        if vocab_count >= count + start - 1: break

        page += 1

    return words

def get_entry(element) :

    try :
        element = element['entry']
        lang = element['language']

        if lang == 'ja':  # 일어

            kanji, word = get_word(element['members'])
            meaning = get_mean(element['means'])

            return kanji, word, meaning

        return None,None,None

    except Exception as e:
        return None, None, None

def get_word(elements) :

    kanji = None
    entry_name = None

    for element in elements :

        entry_name = element['entry_name']
        entry_name = clean_parenthesis(entry_name)
        entry_name = clean_html(entry_name)
        entry_name = get_first_item(entry_name)
        entry_name = get_only_hira_kata(entry_name)

        kanji = element['kanji']
        kanji = clean_parenthesis(kanji)
        kanji = clean_html(kanji)
        kanji = get_first_item(kanji)

        if entry_name == "": entry_name = None
        if kanji == "": kanji = None

        if entry_name is not None : break

    return kanji, entry_name

def get_mean(elements) :

    mean = None

    for element in elements :

        mean = element['show_mean']
        mean = clean_parenthesis(mean)
        mean = clean_html(mean)
        mean = get_first_item(mean)

        if mean == "": mean = None

        if mean is not None : break

    return mean

def process_vocab(vocab) :

    if not isinstance(vocab, dict) :
        return None, None

    dic_type = vocab["dicType"]

    if dic_type == "jako" : #일한 사전

        kanji, word, meaning = get_entry(json.loads(unquote(vocab["content"])))

        if word is None or meaning is None : return None, None

        if kanji is not None :
            meaning = word + " " + meaning
            word = kanji

        return word, meaning

    elif dic_type == "koja" : # 한일 사전, 지원 X

        return None, None

def export_to_file(file_name, dict) :

    with open(file_name, 'w', newline='', encoding='utf-8-sig') as f:

        wr = csv.writer(f)

        for word, meaning in dict.items():
            wr.writerow([word, meaning])

        f.close()


def main() :

    username = input("네이버 아이디 : ")
    password = getpass.getpass("네이버 비밀번호 : ")

    session_load = input("세션을 불러올까요? (y or n) ")

    if session_load == "y" : session_load = True
    else : session_load = False

    session_save = False

    if not session_load :

        session_save = input("세션을 저장할까요? (y or n) ")

        if session_save == "y":
            session_save = True
        else:
            session_save = False

    session = get_naver_login_session(username, password, session_save, session_load)

    vocab_lists_page = 1
    vocab_lists_select = 0
    vocab_list_items = []

    while vocab_lists_select <= 0 :

        vocab_lists = get_vocab_lists(session, vocab_lists_page)

        vocab_list_items = list(vocab_lists.items())

        print()

        print(f"단어장 목록 {vocab_lists_page} 페이지")

        print()

        for idx, vocab_list_item in enumerate(vocab_list_items) :

            print(f"{idx+1} : {vocab_list_item[0]} ({vocab_list_item[1][1]}개 단어)")

        print()

        vocab_lists_select = int(input("단어장을 선택하거나 전 페이지를 검색하려면 -1, 다음 페이지를 검색하려면 0을 입력하십시오 : "))

        if vocab_lists_select == -1 :

            if vocab_lists_page <= 1 :

                print("이미 첫 페이지입니다.")

                vocab_lists_page = 1

            else :

                vocab_lists_page -= 1

        elif vocab_lists_select == 0 :

            vocab_lists_page += 1

        else : break

    print()
    print(f"선택한 단어장 : {vocab_list_items[vocab_lists_select-1][0]}  ({vocab_list_items[vocab_lists_select-1][1][1]}개 단어)")

    vocab_start_count = int(input("불러오기 시작할 단어의 개수를 입력하세요 : "))
    vocab_count = int(input("불러올 단어 개수를 입력하세요 : "))

    vocab_lists_id = vocab_list_items[vocab_lists_select-1][1][0]

    vocabs = get_vocabs(session, vocab_lists_id, vocab_start_count, vocab_count)
    print()

    print(f"{vocab_list_items[vocab_lists_select - 1][0]} 단어장에서 {vocab_start_count}번째 단어부터 {len(vocabs)}개를 불러왔습니다.")
    file_name = input("저장할 파일 이름을 입력하세요 (CSV) : ")
    export_to_file(file_name, vocabs)

    print(f"{file_name}에 {len(vocabs)}개의 단어를 저장했습니다.")


main()