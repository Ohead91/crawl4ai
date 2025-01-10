import asyncio
import json
from datetime import datetime
from pathlib import Path
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def save_to_markdown(article_data: dict):
    """개별 아티클을 마크다운으로 저장"""
    browser_config = BrowserConfig(
        headless=True,
        verbose=True
    )
    
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS
    )
    
    # 저장 경로 설정
    source = article_data['source']
    # ISO 형식의 날짜를 YYYYMMDD 형식으로 변환
    try:
        if 'T' in article_data['date']:
            date_obj = datetime.fromisoformat(article_data['date'].replace('Z', '+00:00'))
        else:
            date_obj = datetime.strptime(article_data['date'], "%B %d, %Y")
        date_str = date_obj.strftime('%Y%m%d')
    except Exception as e:
        print(f"Error parsing date {article_data['date']}: {e}")
        date_str = datetime.now().strftime('%Y%m%d')
    
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
            
            # 마크다운 파일에 내용 추가
            with markdown_file.open('a', encoding='utf-8') as f:
                f.write("\n---\n")  # 구분선
                # 메타데이터
                f.write("title: " + article_data.get('title', 'No Title') + "\n")
                f.write("url: " + article_data['url'] + "\n")
                f.write("date: " + article_data['date'] + "\n")
                f.write("source: " + article_data['source'] + "\n")
                if 'description' in article_data:
                    f.write("description: " + article_data['description'] + "\n")
                f.write("crawled_at: " + datetime.now().isoformat() + "\n")
                f.write("---\n\n")
                
                # 본문 내용
                f.write(result.markdown)
                f.write("\n\n")
            
            print(f"Saved markdown for: {article_data['title']}")
            return True
            
    except Exception as e:
        print(f"Error processing {article_data['url']}: {e}")
        return False

async def process_json_files():
    """newsletter_data 디렉토리의 JSON 파일들을 처리"""
    json_dir = Path("newsletter_data")
    if not json_dir.exists():
        print("newsletter_data directory not found")
        return
    
    # JSON 파일들을 찾아서 처리
    json_files = list(json_dir.glob("articles_*.json"))
    if not json_files:
        print("No JSON files found")
        return
    
    # 가장 최신 JSON 파일 사용
    latest_json = max(json_files, key=lambda x: x.stat().st_mtime)
    print(f"\nProcessing file: {latest_json}")
    
    with latest_json.open('r', encoding='utf-8') as f:
        articles = json.load(f)
    
    print(f"Found {len(articles)} articles to process")
    
    # 각 아티클 처리
    for article in articles:
        if 'url' not in article or 'source' not in article:
            print(f"Skipping invalid article: {article}")
            continue
            
        await save_to_markdown(article)

async def main():
    await process_json_files()

if __name__ == "__main__":
    asyncio.run(main())