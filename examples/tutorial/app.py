"""Local learning app. Its small limits are for the tutorial, not production."""

from flask import Flask
from aiwaf.flask import AIWAF, aiwaf_exempt, aiwaf_exempt_from

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


# Added in the tutorial's route-policy chapter.
@app.get("/api/preview")
@aiwaf_exempt_from("rate_limit")
def preview():
    return {"message": "Preview has no rate limit"}


# Pin the preview budget too; its decorator selectively bypasses that check.
app.config["AIWAF_PATH_RULES"].append(
    {"PREFIX": "/api/preview", "RATE_LIMIT": {"WINDOW": 60, "MAX": 3, "FLOOD": 100}}
)


AIWAF(app, middlewares=["rate_limit", "logging"])
