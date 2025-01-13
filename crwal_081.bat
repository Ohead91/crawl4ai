@echo on
chcp 65001
setlocal EnableDelayedExpansion

REM 작업 디렉토리로 이동
cd /d %~dp0

REM 로그 파일 설정
set "log_dir=%~dp0logs"
set "LOGFILE=%log_dir%\crawling_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%.log"

REM 로그 디렉토리 생성
if not exist "%log_dir%" mkdir "%log_dir%"

REM 로그 시작
call :log "====================== 작업 시작 ======================"
call :log "시작 시간: %date% %time%"
call :log "작업 디렉토리: %cd%"

REM 첫 번째 Python 파일 실행
call :log ""
call :log "[1crawler.py 실행 시작...]"
python -u .\1crawler.py 2>&1 | findstr /v /c:"[DEBUG]" >> "%LOGFILE%"
if !errorlevel! equ 0 (
    call :log "[성공] 1crawler.py 실행 완료"
) else (
    call :log "[오류] 1crawler.py 실행 실패 (종료 코드: !errorlevel!)"
)

REM 두 번째 Python 파일 실행
call :log ""
call :log "[2make_md.py 실행 시작...]"
python -u .\2make_md.py 2>&1 | findstr /v /c:"[DEBUG]" >> "%LOGFILE%"
if !errorlevel! equ 0 (
    call :log "[성공] 2make_md.py 실행 완료"
) else (
    call :log "[오류] 2make_md.py 실행 실패 (종료 코드: !errorlevel!)"
)

REM 메일 발송
call :log ""
call :log "[메일 발송 시작]"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; ^
        $From = 'ohead91@gmail.com'; ^
        $To = 'ohead91@naver.com'; ^
        $Subject = 'Crawling Result - %date%'; ^
        $Body = Get-Content -Path '%LOGFILE%' -Raw -Encoding utf8; ^
        $SMTPServer = 'smtp.gmail.com'; ^
        $SMTPPort = 587; ^
        $Username = 'ohead91@gmail.com'; ^
        $Password = 'blhoxyclalbzfeeo'; ^
    try { ^
        $SMTPMessage = New-Object System.Net.Mail.MailMessage($From, $To, $Subject, $Body); ^
        $SMTPClient = New-Object Net.Mail.SmtpClient($SMTPServer, $SMTPPort); ^
        $SMTPClient.EnableSsl = $true; ^
        $SMTPClient.Credentials = New-Object System.Net.NetworkCredential($Username, $Password); ^
        $SMTPClient.Send($SMTPMessage); ^
        Write-Output '[성공] 메일 전송 완료' | Out-File -Append '%LOGFILE%' -Encoding utf8; ^
    } catch { ^
        Write-Output ('[실패] 메일 전송 오류: ' + $_.Exception.Message) | Out-File -Append '%LOGFILE%' -Encoding utf8; ^
    }"

REM 작업 완료
call :log ""
call :log "완료 시간: %date% %time%"
call :log "====================== 작업 완료 ======================"

echo 작업이 완료되었습니다. 로그 파일: %LOGFILE%
timeout /t 10
exit /b 0

:log
echo %~1 | cmd /d /c "type con > >"%LOGFILE%""
exit /b 0
