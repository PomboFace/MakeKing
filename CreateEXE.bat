@echo off
echo ============================
echo   Building MakeKing (Safe)
echo ============================

REM Clean previous builds
rmdir /s /q build
rmdir /s /q dist
del MakeKing.spec

REM Build with PyInstaller (safer settings)
pyinstaller ^
--noconsole ^
--name MakeKing ^
--icon=sprites\icon.ico ^
--add-data "sprites;sprites" ^
--version-file version.txt ^
--noupx ^
MakeKing.py

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo Build FAILED.
    pause
    exit /b
)

REM Copy README files into build folder
echo Copying README files...
for %%F in (README_*.txt) do (
    if exist "%%F" (
        copy "%%F" "dist\MakeKing\"
    )
)

REM Copy presets folder into build folder
echo Copying presets folder...
xcopy "presets" "dist\MakeKing\presets" /E /I /Y >nul


REM make py_version folder
echo Creating py_version folder...
mkdir "dist\py_version"

REM Copy main into py_version folder
echo Copying MakeKing.py...
if exist "MakeKing.py" (
    copy "MakeKing.py" "dist\py_version\"
)

REM Copy game_common library into py_version folder
echo Copying game_common.py...
if exist "game_common.py" (
    copy "game_common.py" "dist\py_version\"
)

REM Copy sprites folder into py_version folder (only copy png files)
echo Copying sprite PNG files...
mkdir "dist\py_version\sprites"

for /R "sprites" %%F in (*.png) do (
    copy "%%F" "dist\py_version\sprites\"
)

REM Copy presets folder into py_version folder
echo Copying presets folder...
xcopy "presets" "dist\py_version\presets" /E /I /Y >nul

REM Copy README files into py_version folder
echo Copying README files...
for %%F in (README_*.txt) do (
    if exist "%%F" (
        copy "%%F" "dist\py_version\"
    )
)


REM Zip build
echo Creating ZIP archive...
powershell -Command ^
"Compress-Archive -Path 'dist\MakeKing' -DestinationPath 'dist\MakeKing.zip' -Force"
if %ERRORLEVEL% NEQ 0 (
    echo ZIP creation FAILED.
) else (
    echo ZIP created successfully: dist\MakeKing.zip
)

echo.
echo Build SUCCESS!
echo Your game is in the "dist\MakeKing\" folder.
pause