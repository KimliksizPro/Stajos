import logging
import os
from app import create_app
from app.ai.factory import start_ai_recovery

logger = logging.getLogger(__name__)

app = create_app()

try:
    start_ai_recovery(app)
except Exception:
    logger.warning("AI recovery failed at startup", exc_info=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=app.config.get("DEBUG", False))
