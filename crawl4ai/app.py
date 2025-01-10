from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os
from typing import List, Optional, Dict
from pydantic import BaseModel
from fastapi.responses import PlainTextResponse, Response
import typing

app = FastAPI(title="News API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 기본 데이터 디렉토리 설정
BASE_DIR = "newsletter_data"
MEDIA_OUTLETS = ["neuron", "deepview", "aibreakfast"]

class NewsResponse(BaseModel):
    media: str
    media_type: str
    date: str
    content: str
    headers: typing.Mapping[str, str]

class AvailableDates(BaseModel):
    dates: List[str]
    latest: Optional[str] = None

class AvailableNewsResponse(BaseModel):
    neuron: Optional[AvailableDates] = None
    deepview: Optional[AvailableDates] = None
    aibreakfast: Optional[AvailableDates] = None

def get_formatted_date(filename: str) -> str:
    """파일명의 날짜를 포맷팅된 문자열로 변환""" 
    try:
        date = datetime.strptime(filename.split('.')[0], "%y%m%d")
        return date.strftime("%Y-%m-%d")
    except:
        return filename.split('.')[0]

@app.get("/news/latest/{media}", response_model=NewsResponse)
async def get_latest_news(media: str):
    """특정 매체의 최신 뉴스 조회"""
    try:
        if media not in MEDIA_OUTLETS:
            raise HTTPException(status_code=404, detail=f"Media '{media}' not found")
        
        media_dir = os.path.join(BASE_DIR, media)
        if not os.path.exists(media_dir):
            raise HTTPException(status_code=404, detail=f"No directory found for {media}")
        
        # md 파일만 필터링하고 날짜순 정렬
        dates = [f.split('.')[0] for f in os.listdir(media_dir) 
                if f.endswith('.md') and len(f.split('.')[0]) == 6 and f[:-4].isdigit()]
        
        if not dates:
            raise HTTPException(status_code=404, detail=f"No news found for {media}")
        
        # 최신 날짜 선택
        latest_date = max(dates)
        
        # get_news 함수 재사용
        return await get_news(media, latest_date)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting latest news for {media}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/news/{media}/{date}")
async def get_news(media: str, date: str):
    """특정 매체의 특정 날짜 뉴스 조회"""
    if media not in MEDIA_OUTLETS:
        raise HTTPException(status_code=404, detail="Media not found")
    
    try:
        file_path = os.path.join(BASE_DIR, media, f"{date}.md")
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="News not found for this date")
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return NewsResponse(
            media=media,
            media_type="text/plain; charset=utf-8",
            date=get_formatted_date(date),
            content=content,
            headers={
                "Content-type": "text/plain; charset=utf-8",
                "X-Content-Type-Options": "nosniff"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/news/available", response_model=AvailableNewsResponse)
async def get_available_dates():
    """사용 가능한 뉴스 날짜 목록 조회"""
    response = AvailableNewsResponse()
    
    for media in MEDIA_OUTLETS:
        media_dir = os.path.join(BASE_DIR, media)
        if os.path.exists(media_dir):
            dates = [f.split('.')[0] for f in os.listdir(media_dir) 
                    if f.endswith('.md') and f[:-4].isdigit()]
            
            if dates:
                dates.sort(reverse=True)  # 최신 날짜순 정렬
                formatted_dates = [get_formatted_date(date) for date in dates]
                
                # Pydantic 모델의 동적 필드 설정
                setattr(response, media, AvailableDates(
                    dates=formatted_dates,
                    latest=formatted_dates[0] if formatted_dates else None
                ))
    
    return response


    
@app.get("/")
async def read_root():
    """API 루트 엔드포인트"""
    return {
        "message": "Welcome to News API",
        "available_endpoints": [
            "/news/{media}/{date}",
            "/news/available",
            "/news/latest/{media}"
        ],
        "supported_media": MEDIA_OUTLETS
    }

if __name__ == "__main__":
    import uvicorn
    
    # 필요한 디렉토리 생성
    for media in MEDIA_OUTLETS:
        os.makedirs(os.path.join(BASE_DIR, media), exist_ok=True)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)


#uvicorn app:app --host 0.0.0.0 --port 8000