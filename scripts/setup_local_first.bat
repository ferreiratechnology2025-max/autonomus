@echo off
echo === Setup Local-First Jarvis v3 ===
echo.

:: 1. Venv
if not exist "venv\" (
    echo [1/5] Criando venv...
    python -m venv venv
) else (
    echo [1/5] Venv ja existe
)

call venv\Scripts\activate.bat

:: 2. Dependencias
echo [2/5] Instalando dependencias...
pip install -r requirements.txt -q
pip install textual chromadb ollama python-dotenv -q

:: 3. Config
echo [3/5] Verificando .env...
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env
        echo      .env criado de .env.example — edite sua OPENROUTER_API_KEY
    ) else (
        echo      .env nao encontrado — criando template
        (
            echo OPENROUTER_API_KEY=
            echo PRIVACY_MODE=false
            echo OLLAMA_BASE_URL=http://localhost:11434
            echo OLLAMA_MODEL=qwen2.5:3b
            echo OLLAMA_TIMEOUT=30.0
            echo LLM_REQUEST_TIMEOUT_SECONDS=10.0
        ) > .env
    )
)

:: 4. Diretorios
echo [4/5] Criando diretorios de dados...
if not exist "data\" mkdir data
if not exist "data\logs" mkdir data\logs
if not exist "data\cache" mkdir data\cache

:: 5. Ollama
echo [5/5] Verificando Ollama...
where ollama >nul 2>&1
if %errorlevel% equ 0 (
    echo      Ollama encontrado. Verificando modelos...
    ollama list
) else (
    echo      Ollama nao encontrado no PATH
    echo      Instale em https://ollama.com e puxe os modelos:
    echo        ollama pull qwen2.5:3b
    echo        ollama pull qwen2.5-coder:3b
)

echo.
echo === Setup concluido! ===
echo.
echo Para iniciar:
echo   python -m src.main
echo.
echo Para testar o diagnostico:
echo   python scripts\diagnose_local_first.py
echo.
pause
