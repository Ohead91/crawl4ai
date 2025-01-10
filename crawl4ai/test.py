import asyncio
from datetime import datetime, timedelta
import json
from typing import List, Dict, Set
from pathlib import Path
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

class NewsletterCrawler:
    def __init__(self, history_file: str = "crawl_history.json"):
        self.history_file = Path(history_file)
        self.crawled_urls = self._load_history()
        
        self.sites = {
            "neuron": {
                "url": "https://www.theneuron.ai/newsletter",
                "schema": {
                    "name": "Neuron Articles",
                    "baseSelector": "a[href*='/newsletter/']",
                    "fields": [
                        {
                            "name": "title",
                            "selector": "h3.heading-style-h4",
                            "type": "text"
                        },
                        {
                            "name": "url",
                            "type": "attribute",
                            "attribute": "href"
                        },
                        {
                            "name": "date",
                            "selector": "div[fs-cmssort-type='date']",
                            "type": "text"
                        },
                        {
                            "name": "description",
                            "selector": "div[fs-cmsfilter-field='desc']",
                            "type": "text",
                            "optional": True
                        }
                    ]
                }
            },
            "aibreakfast": {
                "url": "https://aibreakfast.beehiiv.com",
                "schema": {
                    "name": "AI Breakfast Articles",
                    "baseSelector": ".space-y-3",
                    "fields": [
                        {
                            "name": "title",
                            "selector": "h2.line-clamp-2",
                            "type": "text"
                        },
                        {
                            "name": "url",
                            "selector": "a[href*='/p/']",
                            "type": "attribute",
                            "attribute": "href"
                        },
                        {
                            "name": "date",
                            "selector": "time",
                            "type": "attribute",
                            "attribute": "datetime"
                        }
                    ]
                }
            },
            "deepview": {
                "url": "https://www.thedeepview.co",
                "schema": {
                    "name": "Deep View Articles",
                    "baseSelector": ".space-y-2",
                    "fields": [
                        {
                            "name": "title",
                            "selector": "h2.line-clamp-2",
                            "type": "text"
                        },
                        {
                            "name": "url",
                            "selector": "a[href*='/p/']",
                            "type": "attribute",
                            "attribute": "href"
                        },
                        {
                            "name": "date",
                            "selector": "time",
                            "type": "attribute",
                            "attribute": "datetime"
                        }
                    ]
                }
            }
        }

    def _load_history(self) -> Set[str]:
        """이전에 크롤링한 URL 목록 로드"""
        if self.history_file.exists():
            with self.history_file.open('r', encoding='utf-8') as f:
                try:
                    history = json.load(f)
                    return set(history.get('urls', []))
                except json.JSONDecodeError:
                    return set()
        return set()

    def _save_history(self, new_urls: List[str]):
        """크롤링한 URL 목록 저장"""
        self.crawled_urls.update(new_urls)
        with self.history_file.open('w', encoding='utf-8') as f:
            json.dump({'urls': list(self.crawled_urls)}, f, indent=2)

    def normalize_url(self, url: str, base_url: str) -> str:
        """URL을 절대 경로로 변환"""
        if url.startswith('http'):
            return url
            
        # neuron의 경우 특별 처리
        if 'theneuron.ai' in base_url:
            # newsletter가 중복되는 것을 방지
            if url.startswith('/newsletter/'):
                return f"https://www.theneuron.ai{url}"
            else:
                return f"https://www.theneuron.ai/newsletter/{url.lstrip('/')}"
            
        # 일반적인 상대 경로 처리
        return f"{base_url.rstrip('/')}/{url.lstrip('/')}"

    def parse_date(self, date_str: str) -> datetime:
        """날짜 문자열을 datetime 객체로 변환"""
        try:
            now = datetime.now().replace(tzinfo=None)
            
            # ISO 형식 (datetime 속성)
            if 'T' in date_str:
                # timezone 정보 제거
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return dt.replace(tzinfo=None)
            
            # "January 9, 2025" 형식
            return datetime.strptime(date_str.strip(), "%B %d, %Y")
            
        except Exception as e:
            print(f"Date parsing error for {date_str}: {e}")
            return now

    async def save_article_markdown(self, article_url: str, source: str):
        """개별 아티클을 마크다운으로 저장"""
        browser_config = BrowserConfig(
            headless=True,
            verbose=True
        )
        
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            try:
                result = await crawler.arun(
                    url=article_url,
                    config=run_config
                )
                
                # 날짜를 파일명 형식으로 변환
                article_date = self.parse_date(result.metadata.get('published_time', datetime.now().isoformat()))
                date_str = article_date.strftime('%Y%m%d')
                
                # 저장 경로 설정
                save_dir = Path("newsletter_data") / source
                save_dir.mkdir(parents=True, exist_ok=True)
                
                # 마크다운 파일 저장
                file_path = save_dir / f"{date_str}.md"
                with file_path.open('a', encoding='utf-8') as f:
                    f.write("---\n")
                    f.write(f"url: {article_url}\n")
                    f.write(f"source: {source}\n")
                    f.write(f"crawled_at: {datetime.now().isoformat()}\n")
                    f.write("---\n\n")
                    f.write(result.markdown)
                    f.write("\n\n---\n\n")  # 구분선 추가
                
                print(f"Saved markdown for {article_url} to {file_path}")
                return True
                
            except Exception as e:
                print(f"Error saving markdown for {article_url}: {e}")
                return False

    async def crawl_site(self, site_key: str, since_date: datetime):
        site_info = self.sites[site_key]
        browser_config = BrowserConfig(
            headless=True,
            verbose=True
        )
        
        run_config = CrawlerRunConfig(
            extraction_strategy=JsonCssExtractionStrategy(site_info["schema"]),
            cache_mode=CacheMode.BYPASS
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            try:
                print(f"\nFetching {site_info['url']}...")
                result = await crawler.arun(
                    url=site_info["url"],
                    config=run_config
                )
                
                articles = json.loads(result.extracted_content) if isinstance(result.extracted_content, str) else result.extracted_content
                if not isinstance(articles, list):
                    articles = [articles]
                
                filtered_articles = []
                new_urls = []
                
                print(f"Found {len(articles)} articles, filtering...")
                
                for article in articles:
                    try:
                        if not article.get('url') or not article.get('date'):
                            continue
                            
                        # URL 정규화
                        article['url'] = self.normalize_url(article['url'], site_info['url'])
                        
                        # 이미 수집한 URL 제외
                        if article['url'] in self.crawled_urls:
                            print(f"Skipping already crawled: {article['url']}")
                            continue
                        
                        # 날짜 확인
                        article_date = self.parse_date(article['date'])
                        if article_date < since_date:
                            print(f"Skipping old article: {article_date}")
                            continue
                            
                        article['crawled_at'] = datetime.now().isoformat()
                        article['source'] = site_key
                        filtered_articles.append(article)
                        new_urls.append(article['url'])
                        
                        # 마크다운 저장
                        await self.save_article_markdown(article['url'], site_key)
                        
                        print(f"Added article: {article.get('title', 'No title')} ({article_date})")
                        
                    except Exception as e:
                        print(f"Error processing article in {site_key}: {e}")
                        continue
                
                # 새로 수집한 URL 저장
                if new_urls:
                    self._save_history(new_urls)
                
                return filtered_articles
                
            except Exception as e:
                print(f"Error crawling {site_key}: {e}")
                return []

async def main():
    # 7일 이내의 아티클만 수집
    since_date = datetime.now().replace(tzinfo=None) - timedelta(days=7)
    print(f"Collecting articles since: {since_date}")
    
    crawler = NewsletterCrawler()
    all_articles = []
    
    for site_key in crawler.sites.keys():
        print(f"\nProcessing {site_key}...")
        articles = await crawler.crawl_site(site_key, since_date)
        all_articles.extend(articles)
        
        print(f"\nFound {len(articles)} new articles from {site_key}")
        for article in articles:
            print(f"\nTitle: {article.get('title', 'No title')}")
            print(f"URL: {article.get('url', 'No URL')}")
            print(f"Date: {article.get('date', 'No date')}")
            if article.get('description'):
                print(f"Description: {article['description']}")
    
    if all_articles:
        # 결과를 JSON 파일로 저장
        output_dir = Path("newsletter_data")
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / f"articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with output_file.open('w', encoding='utf-8') as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=2)
        
        print(f"\nSaved {len(all_articles)} articles to {output_file}")
    else:
        print("\nNo new articles found.")

if __name__ == "__main__":
    asyncio.run(main())