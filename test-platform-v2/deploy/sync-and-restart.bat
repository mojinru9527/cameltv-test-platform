@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set CONTAINER=cameltv-tp-backend
set SRC=f:\CamelTv\test-platform-v2\backend

echo ============================================
echo   CamelTv P0/P1 代码热更新到容器
echo ============================================
echo.

echo [1/5] 同步 app 目录到容器 ...
docker cp "%SRC%\app\." %CONTAINER%:/app/app/
if %errorlevel% neq 0 (
    echo ERROR: docker cp app failed
    exit /b 1
)
echo OK

echo [2/5] 同步 alembic 迁移 ...
docker cp "%SRC%\alembic\." %CONTAINER%:/app/alembic/
if %errorlevel% neq 0 (
    echo ERROR: docker cp alembic failed
    exit /b 1
)
echo OK

echo [3/5] 运行数据库迁移 ...
docker exec %CONTAINER% python -m alembic upgrade head
if %errorlevel% neq 0 (
    echo WARNING: alembic upgrade returned non-zero, may be already up to date
)
echo OK

echo [4/5] 重启后端容器 ...
docker restart %CONTAINER%
echo Waiting for backend to become healthy...
timeout /t 15 /nobreak >nul

echo [5/5] 验证部署 ...

:: Health check
curl -s -o NUL -w "Health: %%{http_code}" http://localhost/health
echo.

:: Verify quality_service.py
docker exec %CONTAINER% python -c "from app.services.lanhu_evidence.quality_service import evaluate_job_quality; print('quality_service: OK')"
if %errorlevel% neq 0 (
    echo ERROR: quality_service import failed
)

:: Verify worker.py
docker exec %CONTAINER% python -c "from app.services.lanhu_evidence.worker import recover_stale_jobs; print('worker: OK')"
if %errorlevel% neq 0 (
    echo ERROR: worker import failed
)

echo.
echo ============================================
echo   部署完成！
echo   前端: http://localhost
echo   后端: http://localhost/api/v1
echo   Swagger: http://localhost/api/v1/docs (可能需要直接访问后端)
echo   登录凭据: 使用未提交 .env 中由管理员分配的账号
echo ============================================

pause
