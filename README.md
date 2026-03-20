# Meeting → ClickUp Tasks 🤖

Paste any meeting notes and this app will:
1. Use Claude AI to extract tasks, responsibilities, priorities, and due dates
2. Let you review and edit every task before committing
3. Automatically create tasks in the correct ClickUp list based on assignee

---

## Project Structure

```
meeting-to-clickup/
├── app.py              # Flask backend
├── requirements.txt    # Python dependencies
├── render.yaml         # Render.com deploy config
└── templates/
    └── index.html      # Full UI (single file)
```

---

## ClickUp List Mapping

| Person   | ClickUp List ID  |
|----------|-----------------|
| sudheesh | 901816817140    |
| bader    | 901816817143    |
| yousef   | 901816817149    |
| me       | 901816817150    |
| general  | 901816817176    |

---

## Deploying to Render.com

### Step 1 — Push to GitHub
Create a new GitHub repo and push all files:
```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/YOUR_USERNAME/meeting-to-clickup.git
git push -u origin main
```

### Step 2 — Create a Web Service on Render
1. Go to https://render.com and sign in
2. Click **New → Web Service**
3. Connect your GitHub repo
4. Render will auto-detect `render.yaml` — confirm the settings:
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT`

### Step 3 — Add Environment Variables
In Render dashboard → your service → **Environment**:

| Key                  | Value                              |
|---------------------|------------------------------------|
| `ANTHROPIC_API_KEY`  | Your key from https://console.anthropic.com |
| `CLICKUP_API_TOKEN`  | Your ClickUp personal token (see below) |

### Step 4 — Get Your ClickUp API Token
1. Log in to ClickUp
2. Click your avatar → **Settings → Apps**
3. Under **API Token**, click **Generate** (or copy existing)
4. Paste it into Render as `CLICKUP_API_TOKEN`

### Step 5 — Deploy
Click **Manual Deploy → Deploy latest commit**

Your app will be live at: `https://meeting-to-clickup.onrender.com`

---

## How to Use

1. Open the app URL
2. Paste your meeting notes/transcript in the text area
3. Click **Extract Tasks with AI** — Claude analyzes the text
4. Review all extracted tasks:
   - Edit titles, descriptions, priorities
   - Change assignee if needed
   - Set due dates
   - Uncheck tasks you don't want to create
5. Click **Send to ClickUp** — tasks are created automatically
6. See a summary of what was created with direct links

---

## Running Locally

```bash
pip install -r requirements.txt

export ANTHROPIC_API_KEY="sk-ant-..."
export CLICKUP_API_TOKEN="pk_..."

python app.py
```

Then open: http://localhost:5000
