from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from pydantic import ValidationError
from models import SurveySubmission, StoredSurveyRecord
from storage import append_json_line
import hashlib

app = Flask(__name__)
# Allow cross-origin requests so the static HTML can POST from localhost or file://
CORS(app, resources={r"/v1/*": {"origins": "*"}})

def hash_string(data: str) -> str:
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

@app.route("/ping", methods=["GET"])
def ping():
    """Simple health check endpoint."""
    return jsonify({
        "status": "ok",
        "message": "API is alive",
        "utc_time": datetime.now(timezone.utc).isoformat()
    })

@app.post("/v1/survey")
def submit_survey():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "invalid_json", "detail": "Body must be application/json"}), 400
        
    try:
        submission = SurveySubmission(**payload)
    except ValidationError as ve:
        return jsonify({"error": "validation_error", "detail": ve.errors()}), 422

    # hash PII
    email_normalized = submission.email.strip().lower()
    email_hash = hash_string(email_normalized)
    age_hash = hash_string(str(submission.age))

    # create submission ID
    hour_stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H")
    submission_id = submission.submission_id or hash_string(email_normalized + hour_stamp)

    record = StoredSurveyRecord(
        name=submission.name,
        email=email_hash,
        age=age_hash,
        consent=submission.consent,
        rating=submission.rating,
        comments=submission.comments,
        user_agent=submission.user_agent,
        submission_id=submission_id,
        received_at=datetime.now(timezone.utc),
        ip=request.headers.get("X-Forwarded-For", request.remote_addr or "")
    )
    append_json_line(record.dict())
    return jsonify({"status": "ok"}), 201

if __name__ == "__main__":
    app.run(port=5000, debug=True)
