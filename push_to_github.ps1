# Push project to GitHub
$gitCmd = if (Get-Command git -ErrorAction SilentlyContinue) { "git" } elseif (Test-Path "$env:LOCALAPPDATA\Programs\MinGit\cmd\git.exe") { "$env:LOCALAPPDATA\Programs\MinGit\cmd\git.exe" } else { throw "Git not found." }

Write-Host "Using Git: $gitCmd" -ForegroundColor Cyan
Write-Host "Initializing Git and setting remote to https://github.com/prajjwal1594/EdTrack-ERP.git..." -ForegroundColor Cyan

& $gitCmd init
& $gitCmd branch -M main
& $gitCmd remote remove origin 2>$null
& $gitCmd remote add origin https://github.com/prajjwal1594/EdTrack-ERP.git
& $gitCmd add .
& $gitCmd commit -m "Initial commit: EdTrack ERP College & University Management System"
& $gitCmd push -u origin main

Write-Host "Pushed successfully to GitHub!" -ForegroundColor Green
