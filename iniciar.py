"""
PASTORAL INGENIERÍA COMERCIAL UC
Script de inicio con túnel público (ngrok)
Permite que CUALQUIER persona entre desde su celular o computadora,
estén donde estén.

USO:
  python iniciar.py

Si ya tenés cuenta en ngrok y tu authtoken:
  python iniciar.py --token TU_TOKEN_AQUI
"""

import sys
import os
import threading
import time

# ── Verificar que Flask exista ──
try:
    from app import app, init_excel
except ImportError as e:
    print(f"Error: {e}")
    print("Asegurate de estar en la carpeta pastoral-fondos")
    sys.exit(1)

# ── Intentar levantar túnel ngrok ──
def iniciar_ngrok():
    try:
        from pyngrok import ngrok, conf

        # Si pasaron un token por argumento
        if "--token" in sys.argv:
            idx = sys.argv.index("--token")
            token = sys.argv[idx + 1]
            conf.get_default().auth_token = token

        tunnel = ngrok.connect(5000, "http")
        url = tunnel.public_url
        # Asegurarse de usar https
        if url.startswith("http://"):
            url = url.replace("http://", "https://", 1)

        print("\n" + "🌐 " + "="*55)
        print("  ENLACE PÚBLICO (funciona desde cualquier lugar):")
        print(f"  ➜  {url}")
        print("="*58)
        print("  Compartí ese link con todos los participantes.")
        print("  (El link cambia cada vez que reiniciás el programa)")
        print("="*58 + "\n")

        return url
    except Exception as e:
        print(f"\n[!] No se pudo crear el túnel ngrok: {e}")
        print("[!] Podés acceder igual por la red WiFi local.")
        return None


def main():
    import socket

    # Inicializar datos
    init_excel()

    # IP local
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "tu-ip-local"

    print("\n" + "="*60)
    print("  PASTORAL INGENIERÍA COMERCIAL UC")
    print("  Sistema de Metas de Recaudación")
    print("="*60)
    print(f"  Red local (misma WiFi): http://{local_ip}:5000")
    print(f"  Esta PC:                http://localhost:5000")
    print("  Admin: admin / admin123")
    print("="*60)
    print("\nIniciando túnel para acceso desde internet...")

    # Iniciar ngrok en hilo separado (para que no bloquee)
    ngrok_thread = threading.Thread(target=iniciar_ngrok, daemon=True)
    ngrok_thread.start()
    ngrok_thread.join(timeout=15)  # esperar hasta 15s que ngrok arranque

    print("\nServidor corriendo. Presioná CTRL+C para detener.\n")

    # Iniciar Flask
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
