from app import create_app
import os

app = create_app()

if __name__ == "__main__":
    # Configuración para Render
    debug_mode = os.getenv("FLASK_DEBUG", "0") == "1"
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "10000"))
    
    # Ejecutar la aplicación con manejo de errores
    try:
        app.run(
            debug=debug_mode,
            host=host,
            port=port
        )
    except Exception as e:
        app.logger.error(f"Error al iniciar la aplicación: {e}")
        raise