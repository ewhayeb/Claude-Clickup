import os
import json
import requests
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

CLICKUP_LISTS = {
    "sudheesh": "901816817140",
    "bader":    "901816817143",
    "yousef":   "901816817149",
    "me":       "901816817150",
    "general":  "901816817176"
}

CLICKUP_API_TOKEN = os.environ.get("CLICKUP_API_TOKEN", "")
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY", "")


def extract_tasks_from_meeting(meeting_text: str) -> list[dict]:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = (
        "Extract tasks from this meeting. Reply ONLY with a JSON array, no markdown.\n"
        "Each item: {title, description, assignee (sudheesh/bader/yousef/me/general), "
        "priority (urgent/high/normal/low), due_date (YYYY-MM-DD or null)}\n\n"
        "Meeting:\n" + meeting_text
    )

    response = model.generate_content(prompt)
    raw = response.text.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)


def create_clickup_task(task: dict) -> dict:
    assignee  = task.get("assignee", "general")
    list_id   = CLICKUP_LISTS.get(assignee, CLICKUP_LISTS["general"])
    priority_map = {"urgent": 1, "high": 2, "normal": 3, "low": 4}

    payload = {
        "name":        task["title"],
        "description": task.get("description", ""),
        "priority":    priority_map.get(task.get("priority", "normal"), 3),
    }

    if task.get("due_date"):
        try:
            from datetime import datetime
            dt = datetime.strptime(task["due_date"], "%Y-%m-%d")
            payload["due_date"]      = int(dt.timestamp() * 1000)
            payload["due_date_time"] = False
        except Exception:
            pass

    headers = {"Authorization": CLICKUP_API_TOKEN, "Content-Type": "application/json"}
    return requests.post(
        f"https://api.clickup.com/api/v2/list/{list_id}/task",
        headers=headers, json=payload
    ).json()


@app.route("/")
def index():
    return render_template("index.html", lists=CLICKUP_LISTS)


@app.route("/api/extract", methods=["POST"])
def api_extract():
    data = request.get_json()
    meeting_text = data.get("meeting_text", "").strip()
    if not meeting_text:
        return jsonify({"error": "Meeting text is required"}), 400
    if not GEMINI_API_KEY:
        return jsonify({"error": "GEMINI_API_KEY not configured"}), 500
    try:
        tasks = extract_tasks_from_meeting(meeting_text)
        return jsonify({"tasks": tasks})
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Failed to parse AI response: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/create-tasks", methods=["POST"])
def api_create_tasks():
    data  = request.get_json()
    tasks = data.get("tasks", [])
    if not tasks:
        return jsonify({"error": "No tasks provided"}), 400
    if not CLICKUP_API_TOKEN:
        return jsonify({"error": "CLICKUP_API_TOKEN not configured"}), 500

    results = []
    for task in tasks:
        try:
            result = create_clickup_task(task)
            results.append({
                "title":       task["title"],
                "assignee":    task.get("assignee", "general"),
                "status":      "success",
                "clickup_id":  result.get("id"),
                "clickup_url": result.get("url"),
            })
        except Exception as e:
            results.append({
                "title":    task["title"],
                "assignee": task.get("assignee", "general"),
                "status":   "error",
                "error":    str(e),
            })
    return jsonify({"results": results})


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
