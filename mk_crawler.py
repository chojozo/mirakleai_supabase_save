import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import os
import pytz
from supabase import create_client, Client
from dotenv import load_dotenv

import re

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException
import time


load_dotenv()

# --- 환경 변수 및 Supabase 설정 ---
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 465
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
RECIPIENT_EMAIL = os.environ.get('RECIPIENT_EMAIL')
URL = 'https://www.mk.co.kr/mirakleai'

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Supabase 클라이언트 초기화
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Supabase 클라이언트 초기화 성공")
except Exception as e:
    print(f"Supabase 클라이언트 초기화 실패: {e}")
    supabase = None

def crawl_article_content(url):
    """주어진 URL에서 기사 본문 내용을 Selenium을 사용하여 크롤링합니다."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = None

    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)
        
        # 페이지 로드를 위해 넉넉히 3초 대기
        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 1순위: 기사 본문 컨테이너를 직접 찾기
        content_div = soup.find('div', class_='view_txt')
        
        if content_div:
            # 컨테이너 내의 p 태그들을 모두 가져옴
            paragraphs = content_div.find_all('p')
            article_text = '\n'.join([p.get_text(strip=True) for p in paragraphs])
        else:
            # 2순위: 컨테이너를 못찾으면 body 전체에서 p 태그를 가져옴
            body = soup.find('body')
            if body:
                paragraphs = body.find_all('p')
                article_text = '\n'.join([p.get_text(strip=True) for p in paragraphs])
            else:
                return "기사 본문을 찾을 수 없습니다."

        # 간단한 후처리
        lines = [line.strip() for line in article_text.splitlines() if line.strip() and len(line.strip()) > 20]
        
        # 기자 정보, 저작권 등 확실한 패턴만 제거
        clean_lines = []
        for line in lines:
            if '기자' in line and '@' in line:
                continue
            if '저작권자' in line and '무단전재' in line:
                continue
            clean_lines.append(line)
        
        final_text = "\n".join(clean_lines)
        final_text = re.sub(r'\s+', ' ', final_text).strip()

        if not final_text:
            return "기사 본문을 찾을 수 없습니다."
            
        return final_text

    except Exception as e:
        return f"기사 본문 크롤링 중 오류 발생: {e}"
    finally:
        if driver:
            driver.quit()

def crawl_mirakleai():
    """미라클AI 기사 목록을 크롤링하고 최근 24시간 내 기사를 반환합니다."""
    print("DEBUG: crawl_mirakleai 함수 시작")
    print(f"DEBUG: SUPABASE_URL from .env: {os.environ.get('SUPABASE_URL')}")
    print(f"DEBUG: SUPABASE_KEY from .env: {os.environ.get('SUPABASE_KEY')[:5]}...")

    if not supabase:
        print("DEBUG: Supabase 클라이언트가 유효하지 않아 크롤링을 중단합니다.")
        return None

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        driver.get(URL)
        
        # 뉴스 목록 컨테이너가 로드될 때까지 최대 10초 대기
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ul#list_area li.news_node"))
            )
        except TimeoutException:
            print("DEBUG: 뉴스 목록 컨테이너 로드 시간 초과.")
            return None

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        articles = []
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        one_day_ago = now - timedelta(days=1)

        # Find the main news list container
        news_list_container = soup.find('ul', id='list_area')
        if not news_list_container:
            print("DEBUG: 뉴스 목록 컨테이너를 찾을 수 없습니다. (WebDriverWait 이후)")
            return None

        li_elements = news_list_container.find_all('li')

        for li_item in li_elements:
            news_item_link_tag = li_item.find('a', class_='news_item')
            if not news_item_link_tag:
                continue

            title_tag = news_item_link_tag.find('h3', class_='news_ttl')
            summary_tag = news_item_link_tag.find('p', class_='news_desc')
            date_tag = news_item_link_tag.find('p', class_='time_info')

            if title_tag and summary_tag and date_tag:
                title = title_tag.get_text(strip=True)
                link = news_item_link_tag['href']
                summary = summary_tag.get_text(strip=True)
                date_str = date_tag.get_text(strip=True)

                try:
                    # Handle "X시간 전" format
                    if "시간 전" in date_str:
                        hours_ago = int(re.search(r'(\d+)', date_str).group(1))
                        article_date = now - timedelta(hours=hours_ago)
                    elif "분 전" in date_str:
                        minutes_ago = int(re.search(r'(\d+)', date_str).group(1))
                        article_date = now - timedelta(minutes=minutes_ago)
                    else:
                        # Date format: 2025.07.27 12:57
                        article_date_naive = datetime.strptime(date_str, '%Y.%m.%d %H:%M')
                        article_date = kst.localize(article_date_naive)

                    if article_date > one_day_ago:
                        # 본문 크롤링 추가
                        full_content = crawl_article_content(link)

                        articles.append({
                            'title': title,
                            'link': link,
                            'summary': re.sub(r'\s+', ' ', summary),
                            'published_at': article_date.isoformat(),
                            'full_content': full_content # 본문 추가
                        })
                except ValueError as ve:
                    print(f"DEBUG: 날짜 파싱 오류: {date_str} - {ve}")
                    continue
        
        print(f"총 {len(articles)}개의 새 기사를 찾았습니다.")
        print("DEBUG: crawl_mirakleai 함수 종료 (성공)")
        return articles

    except Exception as e:
        print(f"DEBUG: 크롤링 중 오류 발생: {e}")
        print("DEBUG: crawl_mirakleai 함수 종료 (오류)")
        return None
    finally:
        if driver:
            driver.quit()

def save_to_supabase(articles):
    """크롤링한 기사를 Supabase DB에 저장합니다."""
    if not articles:
        print("DB에 저장할 새 기사가 없습니다.")
        return

    if not supabase:
        print("Supabase 클라이언트가 유효하지 않아 저장을 건너뜁니다.")
        return

    # Ensure uniqueness by link before upserting
    unique_articles = {}
    for article in articles:
        unique_articles[article['link']] = article
    articles_to_save = list(unique_articles.values())

    print(f"{len(articles_to_save)}개의 고유한 기사를 Supabase DB에 저장을 시도합니다.")
    
    # 디버그 출력: 저장될 기사들의 링크 확인
    print("DEBUG: Links of articles to save to Supabase:")
    for article in articles_to_save:
        article['source'] = 'Mirakle AI News' # Add source field
        print(f"  - {article['link']}")

    try:
        response = supabase.table('articles').upsert(articles_to_save, on_conflict='link').execute()
        print(f"Supabase 저장 응답: {response}")
        if response.data:
             print(f"Supabase 저장 완료: {len(response.data)}개 행이 처리되었습니다.")
        else:
             print(f"Supabase에 데이터가 저장되지 않았습니다. 응답을 확인하세요.")

    except Exception as e:
        print(f"Supabase 저장 중 오류 발생: {e}")
        if hasattr(e, 'details'):
            print(f"오류 상세: {e.details}")


def send_email(articles):
    """기사 목록을 HTML 형식으로 이메일 발송합니다."""
    if not articles:
        print("이메일로 발송할 새 기사가 없습니다.")
        return

    kst = pytz.timezone('Asia/Seoul')
    today_str = datetime.now(kst).strftime('%Y년 %m월 %d일')

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f'[{today_str}] 미라클AI 뉴스 요약'
    msg['From'] = SMTP_USER
    msg['To'] = RECIPIENT_EMAIL

    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: sans-serif; }}
            .article {{
                border-bottom: 1px solid #eee;
                padding-bottom: 15px;
                margin-bottom: 15px;
            }}
            .article:last-child {{
                border-bottom: none;
            }}
            h2 a {{ color: #0066cc; text-decoration: none; }}
            h2 a:hover {{ text-decoration: underline; }}
            p {{ color: #333; }}
            small {{ color: #888; }}
        </style>
    </head>
    <body>
        <h1>[{today_str}] 미라클AI 신규 기사</h1>
    """

    for article in articles:
        published_date = datetime.fromisoformat(article['published_at']).strftime('%Y-%m-%d %H:%M')
        html_body += f"""
        <div class="article">
            <h2><a href="{article['link']}">{article['title']}</a></h2>
            <p>{article['summary']}</p>
            <small>발행일: {published_date}</small>
        </div>
        """

    html_body += """
    </body>
    </html>
    """

    part1 = MIMEText(html_body, 'html')
    msg.attach(part1)

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, RECIPIENT_EMAIL, msg.as_string())
        print("이메일 발송 성공!")
    except Exception as e:
        print(f"이메일 발송 중 오류 발생: {e}")

if __name__ == "__main__":
    print("DEBUG: 메인 스크립트 시작")
    crawled_articles = crawl_mirakleai()
    
    if crawled_articles:
        print("DEBUG: Supabase 저장 함수 호출 전")
        save_to_supabase(crawled_articles)
        print("DEBUG: Supabase 저장 함수 호출 후")
        
        # print("DEBUG: 이메일 발송 함수 호출 전")
        # send_email(crawled_articles)
        # print("DEBUG: 이메일 발송 함수 호출 후")
    else:
        print("DEBUG: 크롤링된 기사가 없어 Supabase 저장 및 이메일 발송을 건너뜁니다.")
    print("DEBUG: 메인 스크립트 종료")
