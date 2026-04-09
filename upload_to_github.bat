@echo off
echo ====================================================
echo    DermaCare AI - GitHub Upload Script
echo ====================================================

:: 1. Add all changes
echo [+] Adding files to Git...
git add .

:: 2. Commit changes
echo [+] Committing changes...
git commit -m "SonarCloud Zero-Issue Remediation: Fixed security hotspots, reliability bugs, and duplication"

:: 3. Setup remote (ignores error if already exists)
echo [+] Setting up remote...
git remote add origin https://github.com/vensipokiya/AI-Based-Skin-Disease-Detection-System.git 2>nul
git remote set-url origin https://github.com/vensipokiya/AI-Based-Skin-Disease-Detection-System.git

:: 4. Push to main branch
echo [+] Pushing to main branch...
git push -u origin main

if %errorlevel% neq 0 (
    echo [!] Push failed on 'main'. Trying 'master'...
    git push -u origin master
)

echo ====================================================
echo    Upload Complete!
echo ====================================================
pause
