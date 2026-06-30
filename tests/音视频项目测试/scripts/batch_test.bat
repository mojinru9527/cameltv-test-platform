@echo off
setlocal

echo ==========================================
echo   Batch Live Stream Test Script
echo ==========================================
echo.
echo This script will guide you through 3 scenarios:
echo   Scenario 1: Ideal Network (WiFi 5GHz)
echo   Scenario 2: Home Network (WiFi 2.4GHz)
echo   Scenario 3: Mobile Network (4G/5G)
echo.
echo For each scenario you need to:
echo   - Switch to the target network
echo   - Stream via OBS + Record with Bandicam
echo   - Drag the recording file for auto analysis
echo.
echo Prerequisites:
echo   [ ] OBS configured with stream URL
echo   [ ] Bandicam ready
echo   [ ] Test app logged in on phone
echo   [ ] Test video ready at materials\
echo.

pause

REM ===== Scenario 1: Ideal Network =====
echo.
echo ==========================================
echo   Scenario 1/3: Ideal Network
echo ==========================================
echo.
echo Setup:
echo   - Network: 5GHz WiFi, same room as router
echo   - Signal strength: 80%% or above
echo   - Time: off-peak hours
echo.
echo Start recording, then press any key when done...
pause >nul
call "%~dp0run_test.bat" ideal_network

REM ===== Scenario 2: Home Network =====
echo.
echo ==========================================
echo   Scenario 2/3: Home Network
echo ==========================================
echo.
echo Setup:
echo   - Network: 2.4GHz WiFi, one wall between
echo   - Time: peak hours (7-9pm)
echo.
echo Switch network, record, then press any key when done...
pause >nul
call "%~dp0run_test.bat" home_network

REM ===== Scenario 3: Mobile Network =====
echo.
echo ==========================================
echo   Scenario 3/3: Mobile Network
echo ==========================================
echo.
echo Setup:
echo   - Network: 4G/5G mobile data
echo   - Turn OFF WiFi
echo   - Location: indoor near window
echo.
echo Switch network, record, then press any key when done...
pause >nul
call "%~dp0run_test.bat" mobile_network

REM ===== Collect Results =====
echo.
echo ==========================================
echo   ALL SCENARIOS COMPLETE!
echo ==========================================
echo.
echo Generating summary report...
python "%~dp0collect_results.py" "%~dp0..\results"
echo.
echo Results folder: %~dp0..\results\
echo.
echo Recent test directories:
dir "%~dp0..\results" /b /ad /o-d 2>nul
echo.
pause
