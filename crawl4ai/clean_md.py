import re

# 파일 불러오기
def load_markdown(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

# 불필요한 섹션 제거 함수
def clean_markdown(content):
    # 1. 광고 및 반복 메시지 제거
    content = re.sub(r'(?i)(oops! Something went wrong|limited time offer|subscribe|free chatgpt training|by subscribing you will|advertise with us)', '', content)
    
    # 2. 이미지 태그 제거
    content = re.sub(r'!\[.*?\]\(.*?\)', '', content)
    
    # 3. 링크 버튼 제거
    content = re.sub(r'\[.*?\]\(https?://.*?\)', '', content)
    
    # 4. 소셜 미디어 링크 제거
    content = re.sub(r'https?://(www\.)?(facebook|twitter|linkedin|reddit|imdb|youtube)\.com/[\w\-/]+', '', content)
    
    # 5. 빈 줄 및 공백 정리
    content = re.sub(r'\n\s*\n', '\n', content)
    content = content.strip()
    
    return content

# 결과 저장 함수
def save_cleaned_content(file_path, content):
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)

# 실행
input_file_1 = '/Users/ohead/Documents/crawl4ai/newsletter_data/deepview/20250109.md'
input_file_2 = '/Users/ohead/Documents/crawl4ai/newsletter_data/aibreakfast/20250109.md'
output_file_1 = '/Users/ohead/Documents/crawl4ai/newsletter_data/deepview/clean_20250109.md'
output_file_2 = '/Users/ohead/Documents/crawl4ai/newsletter_data/aibreakfast/clean_20250109.md'

# 파일 정리 및 저장
for input_file, output_file in [(input_file_1, output_file_1), (input_file_2, output_file_2)]:
    markdown_content = load_markdown(input_file)
    cleaned_content = clean_markdown(markdown_content)
    save_cleaned_content(output_file, cleaned_content)

print("파일 정리가 완료되었습니다.")