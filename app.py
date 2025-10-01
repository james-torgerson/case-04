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

    original_email = payload.get('email', '') 

    # hashing PII
    if 'email' in payload and payload['email']:
        hashed_email = hash_string(payload['email'])
        payload['email_hash'] = hashed_email
        del payload['email']
    
    if 'age' in payload and payload['age'] is not None:
        try:
            # Convert age to a string before hashing
            age_str = str(payload['age']) 
            
            hashed_age = hash_string(age_str)
            payload['age_hash'] = hashed_age # New field name for the hash
            del payload['age'] # Remove the original integer value
        except Exception:
            # Optionally log an error if age couldn't be processed, 
            # but allow Pydantic to handle remaining validation errors.
            pass

    # Creating submission_id
    if not payload.get('submission_id'):
        
        time_format = datetime.now(timezone.utc).strftime("%Y%m%d%H")
        
        if original_email:
            unique_string = original_email + time_format
            computed_id = hash_string(unique_string)
            payload['submission_id'] = computed_id
        else:
            # Handle case where no email was provided (e.g., generate based on IP/time)
            payload['submission_id'] = hash_string(time_format + "NO_EMAIL")

    try:
        submission = SurveySubmission(**payload)
    except ValidationError as ve:
        return jsonify({"error": "validation_error", "detail": ve.errors()}), 422

    record = StoredSurveyRecord(
        **submission.dict(),
        received_at=datetime.now(timezone.utc),
        ip=request.headers.get("X-Forwarded-For", request.remote_addr or "")
    )
    append_json_line(record.dict())
    return jsonify({"status": "ok"}), 201

if __name__ == "__main__":
    app.run(port=5000, debug=True)
