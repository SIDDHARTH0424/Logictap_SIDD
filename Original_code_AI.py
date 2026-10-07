import sqlite3
from flask import Flask, request, jsonify

DB = "calls.db"
app = Flask(__name__)


def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


with db() as c:
    c.execute(
        "CREATE TABLE IF NOT EXISTS calls ("
        "call_id TEXT PRIMARY KEY, status TEXT, duration_secs INTEGER)"
    )


@app.post("/call-ended")
def call_ended():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="body must be a JSON object"), 400

    call_id = data.get("call_id")
    if not isinstance(call_id, str) or not call_id.strip():
        return jsonify(error="call_id is required and must be a non-empty string"), 400

    status = data.get("status")
    dur = data.get("duration_secs")
    if status is not None and not isinstance(status, str):
        return jsonify(error="status must be a string"), 400
    if dur is not None and (isinstance(dur, bool) or not isinstance(dur, int)):
        return jsonify(error="duration_secs must be an integer"), 400

    con = db()
    try:
        with con:  # commits atomically
            # PRIMARY KEY makes dedup atomic; first write wins
            cur = con.execute(
                "INSERT OR IGNORE INTO calls VALUES (?, ?, ?)",
                (call_id.strip(), status, dur),
            )
        created = cur.rowcount == 1
    finally:
        con.close()

    if created:
        return jsonify(result="created", call_id=call_id.strip()), 201
    return jsonify(result="duplicate_ignored", call_id=call_id.strip()), 200


@app.get("/calls/<call_id>")
def get_call(call_id):
    con = db()
    try:
        row = con.execute("SELECT * FROM calls WHERE call_id = ?", (call_id,)).fetchone()
    finally:
        con.close()
    if row is None:
        return jsonify(error="call not found"), 404
    return jsonify(dict(row)), 200


if __name__ == "__main__":
    app.run(port=5000)