from backend.app import app
import os
from waitress import serve

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    
    if debug:
        print(f"🧠 RL Memory System [DEBUG MODE] starting at http://localhost:{port}")
        app.run(debug=True, port=port)
    else:
        print(f"🧠 RL Memory System [PRODUCTION MODE] starting at http://0.0.0.0:{port}")
        serve(app, host="0.0.0.0", port=port)