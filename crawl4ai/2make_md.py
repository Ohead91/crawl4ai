import asyncio
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy  # 이 부분 추가


async def save_aitimes_articles(articles: list, date_str: str):
    browser_config = BrowserConfig(
        headless=True,
        verbose=True
    )
    
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS
    )
    
    save_dir = Path("newsletter_data") / "aitimes"
    save_dir.mkdir(parents=True, exist_ok=True)
    markdown_file = save_dir / f"{date_str}.md"
    
    with markdown_file.open('w', encoding='utf-8') as f:
        f.write("---\n")
        f.write(f"date: {date_str}\n")
        f.write(f"source: aitimes\n")
        f.write(f"crawled_at: {datetime.now().isoformat()}\n")
        f.write("---\n\n")
    
    sorted_articles = sorted(articles, key=lambda x: int(x.get('rank', '99')))
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        for article in sorted_articles:
            try:
                print(f"\nProcessing article: {article['url']}")
                result = await crawler.arun(
                    url=article['url'],
                    config=run_config
                )
                
                if result:
                    # print("\nDebug: Raw response received")
                    
                    # requests를 사용하여 직접 HTML 가져오기
                    import requests
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    response = requests.get(article['url'], headers=headers)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 본문 찾기
                    article_body = soup.find('article', {'id': 'article-view-content-div'})
                    # print(f"\nDebug: Found article body: {bool(article_body)}")
                    
                    if article_body:
                        content_parts = []
                        
                        # 이미지와 캡션 처리
                        first_image = article_body.find('figure', class_='photo-layout')
                        
                        with markdown_file.open('a', encoding='utf-8') as f:
                            f.write(f"## [{article['rank']}] {article['title']}\n\n")
                            f.write(f"URL: {article['url']}\n\n")
                            
                            # 이미지와 캡션 추가
                            if first_image:
                                # print("\nDebug: Found image")
                                img = first_image.find('img')
                                caption = first_image.find('figcaption')
                                if img and img.get('src'):
                                    f.write(f"![이미지]({img.get('src')})\n\n")
                                if caption:
                                    f.write(f"*{caption.get_text().strip()}*\n\n")
                            
                            # 본문 내용 수집
                            for p in article_body.find_all('p'):
                                text = p.get_text().strip()
                                # print(f"\nDebug: Found paragraph: {text[:50]}...")  # 첫 50자만 출력
                                if text and not text.startswith('<!--') and not text.endswith('-->'):
                                    if '기자' not in text and '@' not in text:
                                        content_parts.append(text)
                            
                            # 본문이 있는 경우에만 저장
                            if content_parts:
                                # print(f"\nDebug: Total paragraphs found: {len(content_parts)}")
                                f.write('\n\n'.join(content_parts))
                                f.write("\n\n")
                            # else:
                                # print("\nDebug: No content parts found!")
                            
                            f.write("---\n\n")
                # else:
                    # print(f"\nDebug: No result for {article['url']}")
                
            except Exception as e:
                print(f"Error processing {article['url']}: {e}")
                import traceback
                print(traceback.format_exc())
                continue

    # print("\nDebug: Processing completed")

async def save_to_markdown(article_data: dict):
    """개별 아티클을 마크다운으로 저장 (AI Times 제외)"""
    if article_data['source'] == 'aitimes':
        return True
        
    browser_config = BrowserConfig(
        headless=True,
        verbose=True
    )
    
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS
    )
    
    # 저장 경로 설정
    source = article_data['source']
    
    # 날짜를 YYMMDD 형식으로 변환
    try:
        if 'date' not in article_data:
            date_str = datetime.now().strftime('%y%m%d')
        elif 'T' in article_data['date']:
            date_obj = datetime.fromisoformat(article_data['date'].replace('Z', '+00:00'))
            date_str = date_obj.strftime('%y%m%d')
        else:
            date_obj = datetime.strptime(article_data['date'], "%B %d, %Y")
            date_str = date_obj.strftime('%y%m%d')
    except Exception as e:
        print(f"Error parsing date for {article_data.get('title', 'Unknown article')}: {e}")
        date_str = datetime.now().strftime('%y%m%d')
    
    save_dir = Path("newsletter_data") / source
    save_dir.mkdir(parents=True, exist_ok=True)
    
    markdown_file = save_dir / f"{date_str}.md"
    
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            print(f"\nFetching content from: {article_data['url']}")
            result = await crawler.arun(
                url=article_data['url'],
                config=run_config
            )
            
            with markdown_file.open('a', encoding='utf-8') as f:
                f.write("\n---\n")  # 구분선
                # 메타데이터
                f.write("title: " + article_data.get('title', 'No Title') + "\n")
                f.write("url: " + article_data['url'] + "\n")
                f.write("date: " + date_str + "\n")
                f.write("source: " + article_data['source'] + "\n")
                if 'description' in article_data:
                    f.write("description: " + article_data['description'] + "\n")
                f.write("crawled_at: " + datetime.now().isoformat() + "\n")
                f.write("---\n\n")
                
                # 본문 내용
                if result and result.markdown:
                    f.write(result.markdown)
                    f.write("\n\n")
            
            print(f"Saved markdown for: {article_data['title']}")
            return True
            
    except Exception as e:
        print(f"Error processing {article_data['url']}: {e}")
        return False

async def process_json_files():
    """newsletter_data 디렉토리의 가장 최신 JSON 파일만 처리"""
    json_dir = Path("newsletter_data")
    if not json_dir.exists():
        print("newsletter_data directory not found")
        return
    
    processed_file = json_dir / "processed_files.txt"
    processed_files = set()
    
    if processed_file.exists():
        with processed_file.open('r') as f:
            processed_files = set(f.read().splitlines())
    
    json_files = list(json_dir.glob("articles_*.json"))
    if not json_files:
        print("No JSON files found")
        return
    
    latest_json = max(json_files, key=lambda x: x.stat().st_mtime)
    
    if str(latest_json) in processed_files:
        print(f"\nFile already processed: {latest_json}")
        return
        
    print(f"\nProcessing file: {latest_json}")
    
    with latest_json.open('r', encoding='utf-8') as f:
        articles = json.load(f)
    
    print(f"Found {len(articles)} articles to process")
    
    # 소스별로 기사 분류
    articles_by_source = defaultdict(list)
    for article in articles:
        if 'url' not in article or 'source' not in article:
            print(f"Skipping invalid article: {article}")
            continue
        articles_by_source[article['source']].append(article)
    
    # AI Times 기사 처리
    aitimes_articles = articles_by_source.get('aitimes', [])
    if aitimes_articles:
        date_str = datetime.now().strftime('%y%m%d')
        await save_aitimes_articles(aitimes_articles, date_str)
    
    # 다른 소스의 기사들 처리
    for source, source_articles in articles_by_source.items():
        if source != 'aitimes':
            for article in source_articles:
                await save_to_markdown(article)
    
    # 처리 완료된 파일 기록
    with processed_file.open('a') as f:
        f.write(str(latest_json) + '\n')

async def main():
    await process_json_files()

if __name__ == "__main__":
    asyncio.run(main())