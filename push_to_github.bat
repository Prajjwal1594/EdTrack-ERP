@echo off
echo Initializing git repository and pushing to github.com/prajjwal1594/EdTrack-ERP...
git init
git branch -M main
git remote remove origin 2>nul
git remote add origin https://github.com/prajjwal1594/EdTrack-ERP.git
git add .
git commit -m "Initial commit: EdTrack ERP College & University Management System"
git push -u origin main
echo Done!
pause
