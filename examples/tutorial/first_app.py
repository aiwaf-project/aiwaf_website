"""Local learning app. Its small limits are for the tutorial, not production."""

from flask import Flask
from aiwaf.flask import AIWAF, aiwaf_exempt

app = Flask(__name__)
app.config.update(
    AIWAF_USE_CSV=True,
    AIWAF_DATA_DIR="aiwaf_data",
    AIWAF_RATE_WINDOW=60,
    AIWAF_RATE_MAX=3,
    AIWAF_RATE_FLOOD=100,
    AIWAF_PATH_RULES=[
        {"PREFIX": "/api/message", "RATE_LIMIT": {"WINDOW": 60, "MAX": 3, "FLOOD": 100}},
    ],
    AIWAF_LOG_DIR="aiwaf_logs",
    AIWAF_LOG_FORMAT="json",
)


@app.get("/api/message")
def message():
    return {"message": "Hello from a protected route"}


@app.get("/health")
@aiwaf_exempt
def health():
    return {"ok": True}


AIWAF(app, middlewares=["rate_limit", "logging"])
