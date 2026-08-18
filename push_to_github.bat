@echo off
setlocal

:: Check if git is in PATH, otherwise use MinGit path
where git >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "GIT_CMD=git"
) else if exist "%LOCALAPPDATA%\Programs\MinGit\cmd\git.exe" (
    set "GIT_CMD=%LOCALAPPDATA%\Programs\MinGit\cmd\git.exe"
) else (
    echo [ERROR] Git is not installed or not found.
    pause
    exit /b 1
)

echo Using Git: %GIT_CMD%
echo Initializing git repository and pushing to github.com/prajjwal1594/EdTrack-ERP...
"%GIT_CMD%" init
"%GIT_CMD%" branch -M main
"%GIT_CMD%" remote remove origin 2>nul
"%GIT_CMD%" remote add origin https://github.com/prajjwal1594/EdTrack-ERP.git
"%GIT_CMD%" add .
"%GIT_CMD%" commit -m "Initial commit: EdTrack ERP College & University Management System"
"%GIT_CMD%" push -u origin main
echo Done!
pause
