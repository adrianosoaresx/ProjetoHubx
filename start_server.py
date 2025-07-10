import subprocess
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
manage_path = BASE_DIR / "manage.py"
asgi_path = "Hubx.asgi:application"

def is_venv_active():
    return (BASE_DIR / ".venv" / "Scripts" / "activate").exists()

def runserver():
    print("🚀 Iniciando com Django runserver...")
    subprocess.run([sys.executable, str(manage_path), "runserver"])

def uvicorn_server():
    print("🌐 Iniciando com uvicorn (WebSocket ready)...")
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        asgi_path,
        "--reload",
        "--port", "8000"
    ])

def main():
    if not is_venv_active():
        print("❗ Ambiente virtual não detectado ou não ativado. Ative com:\n")
        print("    .\\.venv\\Scripts\\activate (Windows)")
        print("    source .venv/bin/activate   (Linux/Mac)")
        return

    print("✅ Ambiente detectado.")
    mode = input("Modo [1] runserver | [2] uvicorn: ").strip()

    if mode == "2":
        uvicorn_server()
    else:
        runserver()

if __name__ == "__main__":
    main()
