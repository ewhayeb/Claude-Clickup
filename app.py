import os
import json
import requests
from flask import Flask, request, jsonify, render_template
from anthropic import Anthropic

app = Flask(__name__)

# ClickUp List IDs per assignee
CLICKUP_LISTS = {
    "sudheesh": "901816817140",
    "bader": "901816817143",
    "yousef": "901816817149",
    "me": "901816817150",
    "general": "901816817176"
}

CLICKUP_API_TOKEN = os.environ.get("CLICKUP_API_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)


def extract_tasks_from_meeting(meeting_text: str) -> list[dict]:
    """Use Claude to extract tasks from meeting notes."""
    
    system_prompt = """You are an expert at analyzing meeting notes and extracting actionable tasks.

You must respond ONLY with a valid JSON array, no markdown, no explanation, just raw JSON.

Each task object must have:
- "title": short task title (string)
- "description": detailed description of what needs to be done (string)
- "assignee": one of ["sudheesh", "bader", "yousef", "me", "general"] — pick based on who is responsible. If unclear or shared, use "general"
- "priority": one of ["urgent", "high", "normal", "low"] (string)
- "due_date": estimated due date as "YYYY-MM-DD" if mentioned, otherwise null

Known team members:
- sudheesh: Sudheesh
- bader: Bader  
- yousef: Yousef
- me: the meeting organizer / "me" / "I"
- general: shared, unassigned, or company-wide tasks

Example output:
[
  {
    "title": "Prepare Q1 report",
    "description": "Compile sales data and prepare the Q1 financial report for the board meeting",
    "assignee": "bader",
    "priority": "high",
    "due_date": "2026-03-25"
  }
]"""

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"Extract all tasks and responsibilities from this meeting:\n\n{meeting_text}"
            }
        ]
    )

    raw = response.content[0].text.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    
    tasks = json.loads(raw)
    return tasks


def create_clickup_task(task: dict) -> dict:
    """Create a task in ClickUp under the appropriate list."""
    assignee = task.get("assignee", "general")
    list_id = CLICKUP_LISTS.get(assignee, CLICKUP_LISTS["general"])
    
    priority_map = {"urgent": 1, "high": 2, "normal": 3, "low": 4}
    priority_num = priority_map.get(task.get("priority", "normal"), 3)

    payload = {
        "name": task["title"],
        "description": task.get("description", ""),
        "priority": priority_num,
    }

    if task.get("due_date"):
        try:
            from datetime import datetime
            dt = datetime.strptime(task["due_date"], "%Y-%m-%d")
            payload["due_date"] = int(dt.timestamp() * 1000)
            payload["due_date_time"] = False
        except Exception:
            pass

    headers = {
        "Authorization": CLICKUP_API_TOKEN,
        "Content-Type": "application/json"
    }

    response = requests.post(
        f"https://api.clickup.com/api/v2/list/{list_id}/task",
        headers=headers,
        json=payload
    )

    return response.json()


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", lists=CLICKUP_LISTS)


@app.route("/api/extract", methods=["POST"])
def api_extract():
    """Extract tasks from meeting text using Claude."""
    data = request.get_json()
    meeting_text = data.get("meeting_text", "").strip()
    
    if not meeting_text:
        return jsonify({"error": "Meeting text is required"}), 400
    
    if not ANTHROPIC_API_KEY:
        return jsonify({"error": "ANTHROPIC_API_KEY not configured"}), 500

    try:
        tasks = extract_tasks_from_meeting(meeting_text)
        return jsonify({"tasks": tasks})
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Failed to parse AI response: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/create-tasks", methods=["POST"])
def api_create_tasks():
    """Create approved tasks in ClickUp."""
    data = request.get_json()
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
                "title": task["title"],
                "assignee": task.get("assignee", "general"),
                "status": "success",
                "clickup_id": result.get("id"),
                "clickup_url": result.get("url"),
            })
        except Exception as e:
            results.append({
                "title": task["title"],
                "assignee": task.get("assignee", "general"),
                "status": "error",
                "error": str(e),
            })

    return jsonify({"results": results})


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
