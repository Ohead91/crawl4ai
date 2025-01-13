@echo off
REM 파이썬 스크립트 순차 실행을 위한 배치 파일
REM daily_python_tasks.bat

REM Python 환경 경로 설정 (가상환경을 사용하는 경우 활성화)
REM call C:\Path\To\Your\venv\Scripts\activate.bat

REM 작업 디렉토리로 이동
cd /d %~dp0

REM 첫 번째 Python 파일 실행
python .\1crawler.py
if errorlevel 1 (
    echo 1crawler.py 실행 중 오류 발생
    exit /b 1
)

REM 두 번째 Python 파일 실행
python .\2make_md.py
if errorlevel 1 (
    echo 2make_md.py 실행 중 오류 발생
    exit /b 1
)

echo 모든 작업이 성공적으로 완료되었습니다.

REM 이메일-to-SMS 발송을 위한 PowerShell 스크립트
powershell -Command ^
    "$From = 'ohead91@gmail.com'; ^
    $To = '01073337310@kt.com'; ^
    $Subject = 'Crawling Report'; ^
    $Body = Get-Content -Path '%log_file%' | Out-String; ^
    $SMTPServer = 'smtp.gmail.com'; ^
    $SMTPPort = 587; ^
    $Username = 'ohead91@gmail.com'; ^
    $Password = 'blho xycl albz feeo'; ^
    $SMTPMessage = New-Object System.Net.Mail.MailMessage($From,$To,$Subject,$Body); ^
    $SMTPClient = New-Object Net.Mail.SmtpClient($SMTPServer, $SMTPPort); ^
    $SMTPClient.EnableSsl = $true; ^
    $SMTPClient.Credentials = New-Object System.Net.NetworkCredential($Username, $Password); ^
    try { ^
        $SMTPClient.Send($SMTPMessage); ^
        Write-Host 'SMS notification sent successfully'; ^
    } catch { ^
        Write-Host 'Failed to send SMS notification: ' $_.Exception.Message; ^
    }"

del %log_file%

if %error_occurred%==1 (
    exit /b 1
) else (
    exit /b 0
)