# Push project to GitHub
Write-Host "Initializing Git and setting remote to https://github.com/prajjwal1594/EdTrack-ERP.git..." -ForegroundColor Cyan

git init
git branch -M main
git remote remove origin 2>$null
git remote add origin https://github.com/prajjwal1594/EdTrack-ERP.git
git add .
git commit -m "Initial commit: EdTrack ERP College & University Management System"
git push -u origin main

Write-Host "Pushed successfully to GitHub!" -ForegroundColor Green
