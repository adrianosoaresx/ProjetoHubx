import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
manage_path = BASE_DIR / "manage.py"
asgi_path = "Hubx.asgi:application"


def is_venv_active():
    return (BASE_DIR / ".venv" / "Scripts" / "activate").exists()


def runserver():
    print("🚀 Iniciando com Django runserver...")
    env = os.environ.copy()
    # Desativa WebSockets no template quando usando runserver (sem ASGI server)
    env.setdefault("WEBSOCKETS_ENABLED", "0")
    subprocess.run([sys.executable, str(manage_path), "runserver"], env=env)


def uvicorn_server():
    print("🌐 Iniciando com uvicorn (WebSocket ready)...")
    env = os.environ.copy()
    env.setdefault("WEBSOCKETS_ENABLED", "1")
    subprocess.run(
        [sys.executable, "-m", "uvicorn", asgi_path, "--reload", "--port", "8000"],
        env=env,
    )


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
