import schedule
import time
from bs4 import BeautifulSoup
import requests
import os
from datetime import datetime
import json
import logging
from typing import List, Dict
import html

class BeehiivNewsletterMonitor:
    def __init__(self, base_url="https://aibreakfast.beehiiv.com", media_name="aibreakfast"):
        self.base_url = base_url
        self.media_name = media_name
        self.base_dir = "news_data"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.processed_urls_file = os.path.join(self.base_dir, self.media_name, "processed_urls.json")
        self.setup_directories()
        self.setup_logging()
        self.load_processed_urls()

    def setup_directories(self):
        """디렉토리 구조 설정"""
        self.media_dir = os.path.join(self.base_dir, self.media_name)
        os.makedirs(self.media_dir, exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "logs"), exist_ok=True)

    def setup_logging(self):
        """로깅 설정"""
        log_file = os.path.join(self.base_dir, "logs", f"{self.media_name}_monitor.log")
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def load_processed_urls(self):
        """처리된 URL 목록 로드"""
        try:
            if os.path.exists(self.processed_urls_file):
                with open(self.processed_urls_file, 'r') as f:
                    self.processed_urls = set(json.load(f))
            else:
                self.processed_urls = set()
        except Exception as e:
            self.logger.error(f"Error loading processed URLs: {e}")
            self.processed_urls = set()

    def save_processed_urls(self):
        """처리된 URL 목록 저장"""
        try:
            with open(self.processed_urls_file, 'w') as f:
                json.dump(list(self.processed_urls), f)
        except Exception as e:
            self.logger.error(f"Error saving processed URLs: {e}")

    def clean_text(self, text: str) -> str:
        """텍스트 정규화 및 인코딩 처리"""
        try:
            text = html.unescape(text)
            replacements = {
                'â': "'",
                'â': '"',
                'â': '"',
                'â¦': '...',
                'â': '-',
                'â': "'",
                'â': '"',
                'â': '"',
                '\xa0': ' ',
            }
            for old, new in replacements.items():
                text = text.replace(old, new)
            return text
        except Exception as e:
            self.logger.error(f"Error cleaning text: {e}")
            return text

    def process_element(self, element):
        """HTML 요소를 텍스트로 처리"""
        try:
            if element.name in ['p', 'h2', 'h3']:
                return self.clean_text(element.text.strip())
            elif element.name == 'ul':
                items = element.find_all('li')
                return '\n'.join(['* ' + self.clean_text(item.text.strip()) for item in items])
            elif element.name == 'ol':
                items = element.find_all('li')
                return '\n'.join([f"{idx+1}. {self.clean_text(item.text.strip())}" for idx, item in enumerate(items)])
            return None
        except Exception as e:
            self.logger.error(f"Error processing element: {e}")
            return None

    def get_latest_articles(self) -> List[Dict]:
        """최신 뉴스레터 목록 가져오기"""
        try:
            response = requests.get(self.base_url, headers=self.headers)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = []
            
            # 각 기사 링크 찾기
            for article in soup.find_all('a', href=lambda x: x and '/p/' in x):
                url = article.get('href')
                if not url:
                    continue
                
                # 제목 찾기
                title_elem = article.find('h2')
                if not title_elem:
                    continue
                title = title_elem.text.strip()
                
                # 날짜 찾기
                time_elem = article.find('time')
                if not time_elem or 'datetime' not in time_elem.attrs:
                    continue
                    
                try:
                    # ISO 형식의 날짜를 파싱
                    date_str = time_elem['datetime']
                    date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    formatted_date = date.strftime("%y%m%d")  # YYMMDD 형식으로 변환
                    display_date = date.strftime("%B %d, %Y")  # 표시용 날짜
                except Exception as e:
                    self.logger.error(f"Error parsing date {date_str}: {e}")
                    continue
                
                full_url = url if url.startswith('http') else f"{self.base_url}{url}"
                
                articles.append({
                    'url': full_url,
                    'date': display_date,
                    'file_date': formatted_date,  # 파일명용 날짜 추가
                    'title': self.clean_text(title)
                })
            
            return articles
        except Exception as e:
            self.logger.error(f"Error fetching articles: {e}")
            return []

    def save_article(self, content: str, date_str: str, file_date: str) -> bool:
        """기사 저장"""
        try:
            filename = f"{file_date}.txt"  # YYMMDD.txt 형식으로 저장
            
            filepath = os.path.join(self.media_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(content)
                
            self.logger.info(f"Successfully saved article to: {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving article: {e}")
            return False

    def check_new_articles(self):
        """새로운 기사 확인 및 저장"""
        self.logger.info("Checking for new articles...")
        articles = self.get_latest_articles()
        
        for article in articles:
            try:
                if article['url'] not in self.processed_urls:
                    self.logger.info(f"Found new article: {article['title']}")
                    self.logger.info(f"Date: {article['date']}, File date: {article['file_date']}")
                    
                    content = self.get_article_content(article['url'])
                    
                    if content:
                        if self.save_article(content, article['date'], article['file_date']):
                            self.processed_urls.add(article['url'])
                            self.save_processed_urls()
                            self.logger.info(f"Successfully processed: {article['url']}")
                    else:
                        self.logger.error(f"Failed to get content for: {article['title']}")
                    
                    time.sleep(5)  # 너무 빠른 요청 방지
            except Exception as e:
                self.logger.error(f"Error processing article {article['title']}: {str(e)}")
                continue

    def get_article_content(self, url: str) -> str:
        """기사 내용 가져오기"""
        try:
            self.logger.info(f"Fetching article from URL: {url}")
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 기사 제목 찾기
            title = soup.find('h1', style=lambda x: x and 'font-size: 36px' in x if x else False)
            title_text = title.text.strip() if title else "No Title"
            
            # 기사 본문 찾기
            content = soup.find('div', {'id': 'content-blocks'})
            if not content:
                self.logger.error("Content area not found")
                return None
            
            content_parts = []
            processed_texts = set()  # 중복 텍스트 체크를 위한 set
            
            # 본문 내용 수집
            for element in content.find_all(['p', 'ul', 'ol'], recursive=True):
                # 부모가 style 속성을 가진 div인 경우만 처리
                parent = element.find_parent('div', style=True)
                if not parent or "padding" not in parent.get('style', ''):
                    continue
                    
                # 광고나 불필요한 섹션 제외
                if ("FROM OUR PARTNERS" in element.text or 
                    "generic-embed" in str(element.get('class', [])) or
                    element.find_parent(class_="generic-embed--root")):
                    continue
                
                if element.name in ['p']:
                    text = self.clean_text(element.text.strip())
                    if text and text not in processed_texts:
                        content_parts.append(text)
                        processed_texts.add(text)
                        
                elif element.name == 'ul':
                    items = element.find_all('li')
                    ul_items = []
                    for item in items:
                        text = self.clean_text(item.text.strip())
                        if text and text not in processed_texts:
                            ul_items.append(f"* {text}")
                            processed_texts.add(text)
                    if ul_items:
                        content_parts.append("\n".join(ul_items))
                        
                elif element.name == 'ol':
                    items = element.find_all('li')
                    ol_items = []
                    for idx, item in enumerate(items, 1):
                        text = self.clean_text(item.text.strip())
                        if text and text not in processed_texts:
                            ol_items.append(f"{idx}. {text}")
                            processed_texts.add(text)
                    if ol_items:
                        content_parts.append("\n".join(ol_items))
            
            if not content_parts:
                self.logger.error("No content parts found in the article")
                return None
                
            final_text = f"Title: {self.clean_text(title_text)}\n\n"
            final_text += "\n\n".join(content_parts)
            
            self.logger.info(f"Successfully extracted content, length: {len(final_text)}")
            return final_text
                
        except Exception as e:
            self.logger.error(f"Error getting article content: {str(e)}")
            self.logger.error(f"URL: {url}")
            return None
        
def get_article_content(self, url: str) -> str:
    """기사 내용 가져오기"""
    try:
        self.logger.info(f"Fetching article from URL: {url}")
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # beehiiv의 컨텐츠 영역 찾기
        content = soup.find('div', {'data-testid': 'post-body'})  # 수정된 선택자
        if not content:
            self.logger.error("Content area not found in the article")
            return None
        
        title = soup.find('h1')
        if not title:
            self.logger.error("Title not found in the article")
            title_text = "No Title"
        else:
            title_text = title.text.strip()
        
        content_parts = []
        for element in content.find_all(['p', 'h2', 'h3', 'ul', 'ol']):
            processed_text = self.process_element(element)
            if processed_text:
                content_parts.append(processed_text)
        
        if not content_parts:
            self.logger.error("No content parts found in the article")
            return None
            
        final_text = f"Title: {self.clean_text(title_text)}\n\n"
        final_text += "\n\n".join(content_parts)
        
        self.logger.info(f"Successfully extracted content with length: {len(final_text)}")
        return final_text
            
    except Exception as e:
        self.logger.error(f"Error getting article content: {str(e)}")
        return None

def save_article(self, content: str, date_str: str) -> bool:
    """기사 저장"""
    try:
        self.logger.info(f"Attempting to save article from date: {date_str}")
        
        # 날짜 파싱 및 파일명 생성
        date = datetime.strptime(date_str, "%B %d, %Y")
        filename = date.strftime("%y%m%d.txt")
        
        # 저장 경로 설정
        filepath = os.path.join(self.media_dir, filename)
        self.logger.info(f"Saving to filepath: {filepath}")
        
        # 디렉토리 존재 확인
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # 파일 저장
        with open(filepath, 'w', encoding='utf-8', errors='ignore') as f:
            f.write(content)
            
        self.logger.info(f"Successfully saved article to: {filepath}")
        return True
        
    except Exception as e:
        self.logger.error(f"Error saving article: {str(e)}")
        return False

class NewsletterMonitor:
    def __init__(self, base_url="https://www.theneuron.ai", media_name="neuron"):
        self.base_url = base_url
        self.media_name = media_name
        self.base_dir = "news_data"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.processed_urls_file = os.path.join(self.base_dir, self.media_name, "processed_urls.json")
        self.setup_directories()
        self.setup_logging()
        self.load_processed_urls()

    def setup_directories(self):
        """디렉토리 구조 설정"""
        self.media_dir = os.path.join(self.base_dir, self.media_name)
        os.makedirs(self.media_dir, exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "logs"), exist_ok=True)

    def setup_logging(self):
        """로깅 설정"""
        log_file = os.path.join(self.base_dir, "logs", f"{self.media_name}_monitor.log")
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def load_processed_urls(self):
        """처리된 URL 목록 로드"""
        try:
            if os.path.exists(self.processed_urls_file):
                with open(self.processed_urls_file, 'r') as f:
                    self.processed_urls = set(json.load(f))
            else:
                self.processed_urls = set()
        except Exception as e:
            self.logger.error(f"Error loading processed URLs: {e}")
            self.processed_urls = set()

    def save_processed_urls(self):
        """처리된 URL 목록 저장"""
        try:
            with open(self.processed_urls_file, 'w') as f:
                json.dump(list(self.processed_urls), f)
        except Exception as e:
            self.logger.error(f"Error saving processed URLs: {e}")

    def clean_text(self, text: str) -> str:
        """텍스트 정규화 및 인코딩 처리"""
        try:
            # HTML 엔티티 디코딩
            text = html.unescape(text)
            
            # 일반적인 인코딩 문제 해결
            replacements = {
                'â': "'",
                'â': '"',
                'â': '"',
                'â¦': '...',
                'â': '-',
                'â': "'",
                'â': '"',
                'â': '"',
                '\xa0': ' ',
            }
            
            for old, new in replacements.items():
                text = text.replace(old, new)
                
            return text
        except Exception as e:
            self.logger.error(f"Error cleaning text: {e}")
            return text

    def process_element(self, element):
        """HTML 요소를 텍스트로 처리"""
        if element.name in ['p', 'h2']:
            return self.clean_text(element.text.strip())
        elif element.name == 'ul':
            items = element.find_all('li')
            return '\n'.join(['* ' + self.clean_text(item.text.strip()) for item in items])
        elif element.name == 'ol':
            items = element.find_all('li')
            return '\n'.join([f"{idx+1}. {self.clean_text(item.text.strip())}" for idx, item in enumerate(items)])
        return None

    def get_latest_articles(self) -> List[Dict]:
        """최신 뉴스레터 목록 가져오기"""
        try:
            response = requests.get(f"{self.base_url}/newsletter", headers=self.headers)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            articles = []
            for article in soup.find_all('a', {'class': 'no-style-link'}):
                url = article.get('href')
                if not url or 'newsletter' not in url:
                    continue
                
                date_div = article.find('div', {'class': 'text-size-tiny'})
                if not date_div:
                    continue
                
                date = date_div.text.strip()
                title = article.find('h3')
                title = title.text if title else "No Title"
                
                articles.append({
                    'url': url,
                    'date': date,
                    'title': self.clean_text(title)
                })
            
            return articles
        except Exception as e:
            self.logger.error(f"Error fetching articles: {e}")
            return []

    def get_article_content(self, url: str) -> str:
        """기사 내용 가져오기"""
        try:
            response = requests.get(self.base_url + url, headers=self.headers)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            content = soup.find('div', {'id': 'richtext-content'})
            if not content:
                return None
            
            title = soup.find('h1', {'class': 'heading-style-h1'})
            title_text = title.text if title else "No Title"
            
            content_parts = []
            for element in content.children:
                if not hasattr(element, 'name'):
                    continue
                
                if element.name in ['p', 'h2', 'ul', 'ol']:
                    if "FROM OUR PARTNERS" not in element.text and "Share The Neuron" not in element.text:
                        processed_text = self.process_element(element)
                        if processed_text:
                            content_parts.append(processed_text)
            
            final_text = f"Title: {self.clean_text(title_text)}\n\n"
            final_text += "\n\n".join(content_parts)
            
            return final_text
            
        except Exception as e:
            self.logger.error(f"Error getting article content: {e}")
            return None

    def save_article(self, content: str, date_str: str) -> bool:
        """기사 저장"""
        try:
            date = datetime.strptime(date_str, "%B %d, %Y")
            filename = date.strftime("%y%m%d.txt")
            
            filepath = os.path.join(self.media_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(content)
                
            self.logger.info(f"Successfully saved: {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving article: {e}")
            return False

    def check_new_articles(self):
        """새로운 기사 확인 및 저장"""
        self.logger.info("Checking for new articles...")
        articles = self.get_latest_articles()
        
        for article in articles:
            if article['url'] not in self.processed_urls:
                self.logger.info(f"Found new article: {article['title']}")
                content = self.get_article_content(article['url'])
                
                if content:
                    if self.save_article(content, article['date']):
                        self.processed_urls.add(article['url'])
                        self.save_processed_urls()
                        self.logger.info(f"Successfully processed: {article['url']}")
                
                # 너무 빠른 요청 방지
                time.sleep(5)

import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
import logging
from typing import List, Dict
import html

class AiTimesMonitor:
    def __init__(self, base_url="https://www.aitimes.com"):
        self.base_url = base_url
        self.media_name = "aitimes"
        self.base_dir = "news_data"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.setup_directories()
        self.setup_logging()

    def setup_directories(self):
        """디렉토리 구조 설정"""
        self.media_dir = os.path.join(self.base_dir, self.media_name)
        os.makedirs(self.media_dir, exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "logs"), exist_ok=True)

    def setup_logging(self):
        """로깅 설정"""
        log_file = os.path.join(self.base_dir, "logs", f"{self.media_name}_monitor.log")
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def clean_text(self, text: str) -> str:
        """텍스트 정규화 및 인코딩 처리"""
        try:
            text = html.unescape(text)
            text = text.replace('\xa0', ' ').strip()
            return text
        except Exception as e:
            self.logger.error(f"Error cleaning text: {e}")
            return text

    def get_popular_articles(self) -> List[Dict]:
        """많이 본 기사 목록 가져오기"""
        try:
            url = f"{self.base_url}/news/articleList.html?view_type=sm"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            articles = []
            popular_section = soup.find('article', {'class': 'box-skin header-line'})
            
            if not popular_section:
                self.logger.error("Popular articles section not found")
                return []
            
            for item in popular_section.find_all('div', {'class': 'item'}):
                link = item.find('a')
                if not link:
                    continue
                    
                number = item.find('em', {'class': 'number'})
                title = item.find('span', {'class': 'auto-titles'})
                
                if not title:
                    continue
                    
                article_url = link.get('href')
                if not article_url.startswith('http'):
                    article_url = self.base_url + article_url
                
                articles.append({
                    'url': article_url,
                    'rank': number.text.strip() if number else "0",
                    'title': self.clean_text(title.text)
                })
            
            return articles
        except Exception as e:
            self.logger.error(f"Error fetching popular articles: {e}")
            return []

    def get_article_content(self, url: str) -> str:
        """기사 내용 가져오기"""
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            article = soup.find('article', {'id': 'article-view-content-div'})
            if not article:
                return None
            
            content_parts = []
            
            # 본문 내용 수집
            for p in article.find_all('p'):
                text = self.clean_text(p.text)
                if text and not text.startswith('<!--') and not text.endswith('-->'):
                    content_parts.append(text)
            
            if not content_parts:
                return None
                
            return '\n\n'.join(content_parts)
            
        except Exception as e:
            self.logger.error(f"Error getting article content: {e}")
            return None

    def save_articles(self) -> bool:
        """많이 본 기사들을 하나의 파일로 저장"""
        try:
            articles = self.get_popular_articles()
            if not articles:
                self.logger.error("No articles found")
                return False
            
            # 현재 날짜로 파일명 생성
            date = datetime.now().strftime("%y%m%d")
            filename = f"{date}.txt"
            filepath = os.path.join(self.media_dir, filename)
            
            contents = []
            
            for article in articles:
                self.logger.info(f"Processing article: {article['title']}")
                content = self.get_article_content(article['url'])
                
                if content:
                    article_text = f"[{article['rank']}. {article['title']}]\n\n{content}\n\n"
                    article_text += "=" * 80 + "\n\n"  # 구분선 추가
                    contents.append(article_text)
                    self.logger.info(f"Successfully processed article: {article['title']}")
                
            if contents:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(''.join(contents))
                self.logger.info(f"Successfully saved articles to: {filepath}")
                return True
            else:
                self.logger.error("No content to save")
                return False
                
        except Exception as e:
            self.logger.error(f"Error saving articles: {e}")
            return False

    def check_new_articles(self):
        """새로운 기사 확인 및 저장"""
        self.logger.info("Checking for new articles...")
        return self.save_articles()


import schedule
import time

def run_monitors():
    """여러 매체의 모니터링 실행"""
    # neuron 모니터
    neuron_monitor = NewsletterMonitor(
        base_url="https://www.theneuron.ai",
        media_name="neuron"
    )
    
    # aibreakfast 모니터
    aibreakfast_monitor = BeehiivNewsletterMonitor(
        base_url="https://aibreakfast.beehiiv.com",
        media_name="aibreakfast"
    )
    
    # aitimes 모니터
    aitimes_monitor = AiTimesMonitor(
        base_url="https://www.aitimes.com"
    )
    
    # 모니터 리스트
    monitors = [neuron_monitor, aibreakfast_monitor, aitimes_monitor]

    
    # 매일 아침 10시에 실행
    for monitor in monitors:
        schedule.every().day.at("09:00").do(monitor.check_new_articles)
    
    # 시작할 때 한 번 실행
    print("Starting initial check for all monitors...")
    for monitor in monitors:
        try:
            monitor.check_new_articles()
            print(f"Successfully checked {monitor.media_name}")
        except Exception as e:
            print(f"Error checking {monitor.media_name}: {str(e)}")
    
    print("\nNewsletter monitors are running. Press Ctrl+C to stop.")
    print("Scheduled to run daily at 09:00 AM")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 1분마다 스케줄 체크
    except KeyboardInterrupt:
        print("\nMonitors stopped by user")

if __name__ == "__main__":
    run_monitors()