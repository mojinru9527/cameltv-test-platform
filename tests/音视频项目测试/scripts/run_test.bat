@echo off
REM  Enable delayed expansion: allows !variable! to be expanded at execution time
REM  instead of parse time. Needed for variables that change inside if/for blocks.
setlocal enabledelayedexpansion

echo ==========================================
echo   Live Stream Latency Test - Auto Script
echo ==========================================
echo.

REM ==================== CONFIG ====================
REM  Modify these if your environment differs.
REM  %~dp0 = the directory where THIS script lives (trailing backslash).
set SCRIPTS_DIR=%~dp0
REM  %~dp0..\results = the sibling "results" folder at project root.
set RESULTS_BASE=%~dp0..\results
REM  Change to "python3" or full path if "python" is not on your PATH.
set PYTHON_EXE=python
REM ================================================

REM === STEP 1: Determine the test scenario name ===
REM  Can be passed as the 1st argument (%1), or entered interactively.
set TEST_SCENARIO=%1
if "%TEST_SCENARIO%"=="" (
    set /p TEST_SCENARIO="Enter test scenario name (e.g. normal, weak_wifi, 4g): "
)

REM === STEP 2: Create a timestamped results folder ===
REM  Folder name format: test_YYYYMMDD_HHMMSS_scenarioName
REM  The TIMESTAMP string replaces spaces with zeros (e.g. " 9" -> "09").
set TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set TEST_DIR=%RESULTS_BASE%\test_%TIMESTAMP%_%TEST_SCENARIO%

echo [1/6] Creating test directory...
echo   %TEST_DIR%
REM  2>nul suppresses the error message if the folder already exists.
mkdir "%TEST_DIR%" 2>nul
REM  cd /d changes working drive AND directory (in case RESULTS_BASE is on another drive).
cd /d "%TEST_DIR%"

REM === STEP 3: Dump test environment info into a log file ===
REM  Captures network, Python, and FFmpeg versions for later reference.
echo [2/6] Recording environment info...
(
echo ===== Test Environment Info =====
echo Scenario: %TEST_SCENARIO%
echo Start Time: %date% %time%
echo Computer: %COMPUTERNAME%
echo User: %USERNAME%
echo.
echo --- Network Info ---
REM  findstr /i does case-insensitive filtering of "IPv4" lines.
ipconfig | findstr /i "IPv4"
echo.
echo --- Python Version ---
REM  2>&1 redirects stderr to stdout so version info is captured.
%PYTHON_EXE% --version 2>&1
echo.
echo --- FFmpeg Version ---
ffmpeg -version 2>&1 | findstr /i "version"
) > test_info.txt 2>&1
echo   Saved: test_info.txt

REM === STEP 4: Wait for the user to record the stream ===
REM  The user must manually: (1) start OBS streaming, (2) record via Bandicam,
REM  (3) save the recording, then (4) drag the .mp4 file into this console.
echo.
echo [3/6] Manual steps required:
echo   (1) Start OBS streaming (play timestamp test video)
echo   (2) Start Bandicam to record viewer screen
echo   (3) Stop Bandicam and save recording file
echo.
REM  User can type a path OR literally drag-and-drop the file onto this window.
set /p RECORDING_FILE="Drag and drop the recorded mp4 file here: "
REM  Strip surrounding double-quotes that Windows adds on drag-and-drop.
set RECORDING_FILE=%RECORDING_FILE:"=%

if not exist "%RECORDING_FILE%" (
    echo.
    echo ERROR: File "%RECORDING_FILE%" does not exist!
    pause
    exit /b 1
)

REM === STEP 5: Copy the recording into the test folder ===
REM  The original file stays untouched; we work on a copy named "recording.mp4".
echo.
echo [4/6] Copying recording file...
copy "%RECORDING_FILE%" "%TEST_DIR%\recording.mp4" >nul
echo   Copied: recording.mp4

REM === STEP 6: Run OCR on every frame to extract embedded timestamps ===
REM  opencv.py reads the video frame-by-frame, crops the timestamp area,
REM  and uses Tesseract OCR to recognize the numbers. Output is recording.log.
echo.
echo [5/6] Running video timestamp OCR recognition...
echo   This may take 1-3 minutes, please wait...
echo.
%PYTHON_EXE% "%SCRIPTS_DIR%opencv.py" "%TEST_DIR%\recording.mp4"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: opencv.py failed! Please check:
    echo   1. Python environment is working
    echo   2. OpenCV/Tesseract are installed
    echo   3. Recording file is not corrupted
    pause
    exit /b 1
)

REM === STEP 7: Analyze the OCR log and produce stats + charts ===
REM  analysis.py reads recording.log, computes delay statistics,
REM  and generates a 4-panel chart saved as recording_chart.png.
echo.
echo [6/6] Running delay analysis and generating charts...
%PYTHON_EXE% "%SCRIPTS_DIR%analysis.py" "%TEST_DIR%\recording.log"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: analysis.py failed!
    pause
    exit /b 1
)

REM === STEP 8: Print results and open the output folder ===
echo.
echo ==========================================
echo   TEST COMPLETE!
echo ==========================================
echo.
echo Result files:
echo   Log data:    %TEST_DIR%\recording.log
echo   Statistics:  %TEST_DIR%\recording_results.txt
echo   Chart:       %TEST_DIR%\recording_chart.png
echo   Recording:   %TEST_DIR%\recording.mp4
echo   Env info:    %TEST_DIR%\test_info.txt
echo.
echo Delay summary:
type "%TEST_DIR%\recording_results.txt" 2>nul
echo.

REM  Open the results folder in Windows Explorer for the user.
explorer "%TEST_DIR%"

pause
