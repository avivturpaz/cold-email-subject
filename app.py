import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

from flask import Flask, jsonify, redirect, render_template, request
from werkzeug.exceptions import HTTPException


required = ["POLAR_PRODUCT_ID", "APP_SECRET_KEY"]
missing = [v for v in required if not os.environ.get(v)]
if missing:
    raise RuntimeError(f"Missing env vars: {missing}")


app = Flask(__name__)
app.secret_key = os.environ["APP_SECRET_KEY"]

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")
POLAR_PRODUCT_ID = os.environ["POLAR_PRODUCT_ID"].strip()

SPAM_TERMS = {
    "act now",
    "buy now",
    "cash",
    "cheap",
    "deal",
    "earn",
    "extra income",
    "free",
    "guarantee",
    "limited time",
    "make money",
    "money back",
    "offer",
    "prize",
    "risk free",
    "save big",
    "winner",
}

URGENCY_TERMS = {
    "act now",
    "before",
    "deadline",
    "ending",
    "final",
    "hurry",
    "last chance",
    "limited",
    "now",
    "soon",
    "today",
    "urgent",
    "this week",
}

PERSONALIZATION_TERMS = {
    "for you",
    "your",
    "you",
    "first name",
    "last name",
    "company",
    "team",
    "{{company}}",
    "{{first_name}}",
    "{company}",
    "{first_name}",
    "[first name]",
    "[company]",
}


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=1.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout = 1000")
    except sqlite3.Error as exc:
        app.logger.error("failed to configure sqlite busy timeout error=%s", exc)
    return conn


def init_db():
    try:
        with get_db() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS subject_tests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subjects_json TEXT NOT NULL,
                    results_json TEXT NOT NULL,
                    best_index INTEGER NOT NULL,
                    best_subject TEXT NOT NULL,
                    best_open_rate REAL NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
    except sqlite3.Error as exc:
        app.logger.error("database initialization failed error=%s", exc)


def json_error(message: str, status: int = 400):
    return jsonify({"ok": False, "error": message}), status


def log_request():
    app.logger.info(
        "request method=%s path=%s remote_addr=%s",
        request.method,
        request.path,
        request.headers.get("X-Forwarded-For", request.remote_addr),
    )


def is_api_request() -> bool:
    return request.path in {"/health", "/submit"}


@app.before_request
def before_request():
    log_request()


@app.errorhandler(HTTPException)
def handle_http_exception(exc: HTTPException):
    app.logger.error(
        "http error status=%s path=%s description=%s",
        exc.code,
        request.path,
        exc.description,
    )
    if is_api_request():
        return jsonify({"ok": False, "error": exc.description}), exc.code
    return exc.description, exc.code


@app.errorhandler(Exception)
def handle_exception(exc: Exception):
    app.logger.error("unexpected error path=%s error=%s", request.path, exc, exc_info=True)
    if is_api_request():
        return jsonify({"ok": False, "error": "An unexpected error occurred."}), 500
    return "An unexpected error occurred.", 500


def normalize_subject(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def parse_subjects(payload: dict[str, Any]) -> list[str]:
    raw_subjects = payload.get("subjects")
    if isinstance(raw_subjects, list):
        subjects = [normalize_subject(str(item)) for item in raw_subjects]
    else:
        subjects = [
            normalize_subject(payload.get(f"subject_{idx}", ""))
            for idx in range(1, 6)
        ]
    if len(subjects) != 5:
        raise ValueError("Enter exactly 5 subject line variants.")
    if any(not subject for subject in subjects):
        raise ValueError("All 5 subject lines are required.")
    return subjects


def score_length(subject: str) -> int:
    length = len(subject)
    score = 100 - min(abs(length - 42) * 2, 80)
    return max(0, int(round(score)))


def score_personalization(subject: str) -> int:
    text = subject.lower()
    score = 0
    if re.search(r"\{\{\s*first_name\s*\}\}|\{first_name\}|\[first name\]", text):
        score += 70
    if re.search(r"\{\{\s*company\s*\}\}|\{company\}|\[company\]", text):
        score += 55
    if re.search(r"\byour\b|\byou\b|\bteam\b|\bfor you\b", text):
        score += 30
    if re.search(r"\bfirst name\b|\blast name\b", text):
        score += 20
    return min(100, score)


def score_urgency(subject: str) -> int:
    text = subject.lower()
    score = 0
    for term in URGENCY_TERMS:
        if term in text:
            score += 18
    if "!" in subject:
        score += 8
    if re.search(r"\b\d{1,2}\s?(am|pm|days?|hours?|minutes?)\b", text):
        score += 12
    return min(100, score)


def score_spam_risk(subject: str) -> int:
    text = subject.lower()
    penalty = 0
    if len(subject) < 18:
        penalty += 14
    if len(subject) > 80:
        penalty += 16
    if sum(1 for char in subject if char.isupper()) >= max(4, len(subject) // 3):
        penalty += 18
    if subject.count("!") >= 2:
        penalty += 14
    if subject.count("?") >= 2:
        penalty += 8
    if re.search(r"\b\d{3,}\b", subject):
        penalty += 10
    for term in SPAM_TERMS:
        if term in text:
            penalty += 15
    if re.search(r"[$%]", subject):
        penalty += 8
    return min(100, penalty)


def predicted_open_rate(length_score: int, personalization_score: int, urgency_score: int, spam_risk: int) -> float:
    open_rate = 12.0
    open_rate += length_score * 0.16
    open_rate += personalization_score * 0.14
    open_rate += urgency_score * 0.11
    open_rate -= spam_risk * 0.17
    return round(max(3.0, min(68.0, open_rate)), 1)


def notes_for_subject(subject: str, length_score: int, personalization_score: int, urgency_score: int, spam_risk: int) -> list[str]:
    notes: list[str] = []
    if len(subject) < 25:
        notes.append("Very short subject lines can read as vague.")
    elif len(subject) > 60:
        notes.append("Long subject lines risk getting cut off.")
    if personalization_score >= 50:
        notes.append("Strong personalization signal.")
    if urgency_score >= 36:
        notes.append("Clear urgency cue detected.")
    if spam_risk >= 30:
        notes.append("Spam risk is elevated by wording or punctuation.")
    if length_score >= 85:
        notes.append("Length is in the strong range for inbox visibility.")
    return notes or ["Balanced phrasing with no obvious spam flags."]


def analyze_subjects(subjects: list[str]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for index, subject in enumerate(subjects, start=1):
        length_score = score_length(subject)
        personalization_score = score_personalization(subject)
        urgency_score = score_urgency(subject)
        spam_risk = score_spam_risk(subject)
        open_rate = predicted_open_rate(length_score, personalization_score, urgency_score, spam_risk)
        results.append(
            {
                "index": index,
                "subject": subject,
                "character_count": len(subject),
                "length_score": length_score,
                "personalization_score": personalization_score,
                "urgency_score": urgency_score,
                "spam_risk": spam_risk,
                "predicted_open_rate": open_rate,
                "notes": notes_for_subject(
                    subject,
                    length_score,
                    personalization_score,
                    urgency_score,
                    spam_risk,
                ),
            }
        )

    best = max(results, key=lambda item: item["predicted_open_rate"])
    average_open_rate = round(sum(item["predicted_open_rate"] for item in results) / len(results), 1)
    return {
        "results": results,
        "best_index": best["index"],
        "best_subject": best["subject"],
        "best_open_rate": best["predicted_open_rate"],
        "average_open_rate": average_open_rate,
    }


def save_test(subjects: list[str], analysis: dict[str, Any]) -> int:
    try:
        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO subject_tests (
                    subjects_json,
                    results_json,
                    best_index,
                    best_subject,
                    best_open_rate,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    json.dumps(subjects),
                    json.dumps(analysis["results"]),
                    analysis["best_index"],
                    analysis["best_subject"],
                    analysis["best_open_rate"],
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            return int(cursor.lastrowid)
    except sqlite3.Error as exc:
        app.logger.error("failed to save subject test error=%s", exc)
        return -1


def fetch_recent_tests(limit: int = 8) -> list[dict[str, Any]]:
    try:
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT id, best_subject, best_open_rate, best_index, created_at
                FROM subject_tests
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as exc:
        app.logger.error("failed to fetch recent tests error=%s", exc)
        return []


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/")
def index():
    return render_template(
        "index.html",
        recent_tests=fetch_recent_tests(),
        plausible_domain=os.environ.get("PLAUSIBLE_DOMAIN", ""),
    )


@app.route("/submit", methods=["POST"])
def submit():
    payload = request.get_json(silent=True) or request.form.to_dict(flat=True)
    if not isinstance(payload, dict):
        return json_error("Invalid payload.", 400)

    try:
        subjects = parse_subjects(payload)
    except ValueError as exc:
        return json_error(str(exc), 400)

    try:
        analysis = analyze_subjects(subjects)
        submission_id = save_test(subjects, analysis)
        app.logger.info(
            "saved subject test id=%s best_index=%s best_open_rate=%s",
            submission_id,
            analysis["best_index"],
            analysis["best_open_rate"],
        )
        return jsonify(
            {
                "ok": True,
                "submission_id": submission_id,
                "analysis": analysis,
            }
        )
    except Exception as exc:
        app.logger.error("submit failed error=%s", exc, exc_info=True)
        return json_error("Unable to score subject lines right now.", 500)


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(silent=True) or {}
        if data.get("type") == "order.created":
            order = data.get("data", {})
            polar_order_id = order.get("id", "")
            product_id = (order.get("product") or {}).get("id", "")
            amount = (order.get("amount") or 0) / 100.0
            currency = (order.get("currency") or "usd").upper()
            customer_email = (order.get("customer") or {}).get("email", "")
            try:
                import sqlite3 as _sqlite3
                _db = os.path.join(os.path.dirname(__file__), "..", "..", "data", "venture.db")
                _conn = _sqlite3.connect(_db)
                _conn.execute(
                    "INSERT OR IGNORE INTO revenue (product, polar_product_id, amount, currency, customer_email, polar_order_id) VALUES (?, ?, ?, ?, ?, ?)",
                    ("cold-email-subject", product_id, amount, currency, customer_email, polar_order_id),
                )
                _conn.commit()
                _conn.close()
            except Exception as exc:
                app.logger.error("webhook db error: %s", exc)
    except Exception as exc:
        app.logger.error("webhook error: %s", exc)
    return jsonify({"ok": True}), 200


@app.route("/pay")
def pay():
    checkout_url = f"https://buy.polar.sh/{POLAR_PRODUCT_ID}"
    if POLAR_PRODUCT_ID.startswith("http://") or POLAR_PRODUCT_ID.startswith("https://"):
        checkout_url = POLAR_PRODUCT_ID
    app.logger.info("redirecting to polar checkout url=%s", checkout_url)
    return redirect(checkout_url, code=302)


init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
