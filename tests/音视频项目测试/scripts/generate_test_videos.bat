@echo off
echo ==========================================
echo   FFmpeg Test Video Generator
echo ==========================================
echo.

set OUTPUT_DIR=%~dp0..\materials

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [1/3] Generating timestamp delay test video...
ffmpeg -f lavfi -i color=size=1280x720:rate=30:color=black:duration=300 -vf "drawtext=fontfile='C\:/Windows/Fonts/consola.ttf':text='TIMESTAMP\: %%{pts}':fontcolor=white:fontsize=60:box=1:boxcolor=black@0.5:x=20:y=100,drawtext=fontfile='C\:/Windows/Fonts/consola.ttf':text='TIME\: %%{localtime}':fontcolor=white:fontsize=40:box=1:boxcolor=black@0.5:x=20:y=180,drawtext=fontfile='C\:/Windows/Fonts/consola.ttf':text='FRAME\: %%{n}':fontcolor=white:fontsize=40:box=1:boxcolor=black@0.5:x=20:y=240" -c:v libx264 -preset fast -crf 18 "%OUTPUT_DIR%\time_delay_test.mp4"

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to generate timestamp test video!
    echo Please verify FFmpeg is installed: run "ffmpeg -version" in cmd
    pause
    exit /b 1
)
echo   Done: time_delay_test.mp4

echo.
echo [2/3] Generating fluency test video (60fps)...
ffmpeg -f lavfi -i color=size=1280x720:rate=60:color=gray:duration=600 -vf "drawbox=x=0:y=350:w=1280:h=50:color=white@0.8:t=fill,drawtext=fontfile='C\:/Windows/Fonts/consola.ttf':text='FLUENCY TEST - 60FPS':fontcolor=black:fontsize=40:x=w*0.1:y=370,drawtext=fontfile='C\:/Windows/Fonts/consola.ttf':text='Frame Rate Test Video':fontcolor=black:fontsize=30:x=w*0.1:y=420,drawtext=fontfile='C\:/Windows/Fonts/consola.ttf':text='Time\: %%{pts}':fontcolor=red:fontsize=25:x=20:y=50" -c:v libx264 -preset fast -r 60 "%OUTPUT_DIR%\fluency_test_60fps.mp4"

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to generate fluency test video!
    pause
    exit /b 1
)
echo   Done: fluency_test_60fps.mp4

echo.
echo [3/3] Generating AV sync test video...
ffmpeg -f lavfi -i sine=frequency=1000:duration=300 -f lavfi -i color=size=1280x720:rate=30:color=darkblue:duration=300 -vf "drawtext=fontfile='C\:/Windows/Fonts/consola.ttf':text='AUDIO SYNC TEST':fontcolor=white:fontsize=70:box=1:boxcolor=black@0.5:x=20:y=100,drawtext=fontfile='C\:/Windows/Fonts/consola.ttf':text='VISUAL CUE - BEEP SOUND':fontcolor=yellow:fontsize=40:box=1:boxcolor=black@0.5:x=20:y=200,drawtext=fontfile='C\:/Windows/Fonts/consola.ttf':text='TIME\: %%{pts}':fontcolor=white:fontsize=30:x=20:y=280" -c:v libx264 -c:a aac -shortest "%OUTPUT_DIR%\av_sync_test.mp4"

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to generate AV sync test video!
    pause
    exit /b 1
)
echo   Done: av_sync_test.mp4

echo.
echo ==========================================
echo   ALL TEST VIDEOS GENERATED!
echo   Location: %OUTPUT_DIR%
echo ==========================================
echo.
echo Generated files:
dir "%OUTPUT_DIR%\*.mp4" /b 2>nul
echo.
pause
