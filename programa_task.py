import requests
from bs4 import BeautifulSoup
import csv
from collections import defaultdict
import re
from datetime import datetime

PROJECT_ID = "338807"                     # <-- set your project

# ======================
#  Credentials / Config
# ======================
EMAIL = "Mariana.rdminteriors@gmail.com"
PASSWORD = "HeRedeems777&"

CSV_PATH = r"C:\Users\kennethn\workspace\Harber Project Management.csv"
BASE_URL   = "https://app.programa.design"
LOGIN_URL  = f"{BASE_URL}/login/"
TASKS_URL  = f"{BASE_URL}/projects/{PROJECT_ID}/tasks"
CREATE_TASK_URL = f"{TASKS_URL}?status=to_do"


# ======================
#  Headers (keep them)
# ======================
COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Connection": "keep-alive",
    "Origin": BASE_URL,
    "Referer": LOGIN_URL,
}

session = requests.Session()

# ----------------------
# Helpers
# ----------------------
def clean_text(s: str) -> str:
    """Normalize whitespace for reliable comparisons."""
    return re.sub(r"\s+", " ", s or "").strip()

def format_due_date(raw_date: str) -> str:
    """
    Convert MM/DD/YYYY -> 'DD Mon, YYYY' (e.g., '01 Aug, 2025')
    Returns '' if parsing fails.
    """
    raw_date = (raw_date or "").strip()
    if not raw_date:
        return ""
    try:
        dt = datetime.strptime(raw_date, "%m/%d/%Y")
        return dt.strftime("%d %b, %Y")
    except Exception:
        return ""

def load_tasks_from_csv(csv_path):
    """
    Reads CSV rows of: phase,task,subtask[,target_date]
    Returns: dict keyed by (phase, task) -> list of (subtask, target_date_or_empty)
    """
    grouped = defaultdict(list)
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or len(row) < 3:
                continue
            # Skip header-ish rows
            hdr = ",".join([c.lower() for c in row[:3]])
            if "phase" in hdr and "task" in hdr and "subtask" in hdr:
                # optional: also allow 4th header to be "target date"
                continue

            phase = (row[0] if len(row) > 0 else "").strip()
            task = (row[1] if len(row) > 1 else "").strip()
            subtask = (row[2] if len(row) > 2 else "").strip()
            target_date = (row[3] if len(row) > 3 else "").strip()

            if not task:
                continue  # must have a task title

            if subtask:
                grouped[(phase, task)].append((subtask, target_date))
            else:
                grouped.setdefault((phase, task), [])
    return grouped

def login():
    # 1) GET login for authenticity_token
    r = session.get(LOGIN_URL, headers=COMMON_HEADERS)
    print("GET login status:", r.status_code)
    soup = BeautifulSoup(r.text, "html.parser")
    token_tag = soup.find("input", {"name": "authenticity_token"})
    if not token_tag:
        raise RuntimeError("authenticity_token not found on login page")
    token = token_tag["value"]

    # 2) POST login
    payload = {
        "authenticity_token": token,
        "user[email]": EMAIL,
        "user[password]": PASSWORD,
    }
    headers = COMMON_HEADERS.copy()
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    res = session.post(LOGIN_URL, headers=headers, data=payload, allow_redirects=True)
    print("Login POST status:", res.status_code)
    return res.status_code == 200

def get_tasks_csrf():
    r = session.get(TASKS_URL, headers=COMMON_HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")
    meta = soup.find("meta", {"name": "csrf-token"})
    return meta["content"] if meta else None

def create_task():
    """
    Creates an empty 'to_do' task in the project and returns (task_id, csrf_from_tasks_page)
    """
    csrf_token = get_tasks_csrf()
    if not csrf_token:
        print("❌ Could not retrieve CSRF token from tasks page")
        return None, None

    headers = COMMON_HEADERS.copy()
    headers.update({
        "X-CSRF-Token": csrf_token,
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "Referer": TASKS_URL,
    })

    res = session.post(CREATE_TASK_URL, headers=headers, data={"authenticity_token": csrf_token})
    print("Create task POST status:", res.status_code)

    # Find the new task ID
    m = re.search(r'/tasks/(\d+)', res.text) or re.search(r'id="task-edit-(\d+)"', res.text)
    if not m:
        print("❌ Task ID not found.")
        print("Response snippet:\n", res.text[:500])
        return None, csrf_token

    task_id = m.group(1)
    print(f"✅ Task created with ID: {task_id}")
    return task_id, csrf_token

def fetch_edit_page_tokens_and_phase_map(task_id):
    """
    Loads /tasks/<id>/edit and returns (authenticity_token, phase_map{name->id})
    Handles both <select> and modern div-based dropdown.
    """
    edit_url = f"{BASE_URL}/tasks/{task_id}/edit"
    headers = COMMON_HEADERS.copy()
    headers.update({
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": TASKS_URL,
    })
    r = session.get(edit_url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")

    # authenticity_token
    token_input = soup.find("input", {"name": "authenticity_token"})
    token = token_input["value"] if token_input else None
    if not token:
        meta = soup.find("meta", {"name": "csrf-token"})
        token = meta["content"] if meta else None

    # Phase map: try both <select> and <div.option-wrapper>
    phase_map = {}

    select = soup.find("select", {"name": "projects_task[phase_id]"})
    if select:
        for opt in select.find_all("option"):
            val = (opt.get("value") or "").strip()
            txt = clean_text(opt.text)
            if val and txt and txt.lower() != "select phase":
                phase_map[txt] = val

    for div in soup.find_all("div", class_="option-wrapper"):
        val = div.get("data-select-dropdown-selected-value-param")
        txt = clean_text(div.get("data-filterable-value"))
        if val and txt:
            phase_map[txt] = val

    # Debug: show what we found
    print(f"Phase map for task {task_id}: {phase_map}")
    return token, phase_map

def update_task_via_edit(task_id, title, description, phase_name, subtasks, maybe_due_date_raw):
    """
    Sends a POST with _method=patch to /tasks/<id> with title, phase, subtasks, and due date.
    """
    edit_token, phase_map = fetch_edit_page_tokens_and_phase_map(task_id)
    if not edit_token:
        print(f"❌ No authenticity_token from edit page for task {task_id}")
        return False

    # resolve phase_id
    phase_id = None
    if phase_name:
        for k, v in phase_map.items():
            if clean_text(k).lower() == clean_text(phase_name).lower():
                phase_id = v
                break

    # Format due date if provided
    formatted_due = format_due_date(maybe_due_date_raw)
    if maybe_due_date_raw and not formatted_due:
        print(f"⚠️  Could not parse due date '{maybe_due_date_raw}' for task {task_id}")

    # Build payload
    payload = {
        "_method": "patch",
        "authenticity_token": edit_token,
        "projects_task[title]": title or "",
        "projects_task[description]": description or "",
        "projects_task[status]": "to_do",
        "label": "",
        "tag-search": "",
    }
    if phase_id:
        payload["projects_task[phase_id]"] = phase_id
    else:
        # Fallback: use the name (this worked earlier to create phases)
        if phase_name:
            payload["projects_task[phase_id]"] = phase_name

    if formatted_due:
        payload["projects_task[due_date]"] = formatted_due

    # Subtasks
    for i, (sub_title, _target_date) in enumerate(subtasks):
        if not sub_title:
            continue
        payload[f"projects_task[subtasks_attributes][{i}][completed]"] = "0"
        payload[f"projects_task[subtasks_attributes][{i}][title]"] = sub_title
        payload[f"projects_task[subtasks_attributes][{i}][_destroy]"] = "false"
        payload[f"projects_task[subtasks_attributes][{i}][position]"] = str(i)

    update_url = f"{BASE_URL}/tasks/{task_id}"
    headers = COMMON_HEADERS.copy()
    headers.update({
        "X-CSRF-Token": edit_token,
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "turbo-frame": f"task-edit-{task_id}",
        "Referer": f"{BASE_URL}/tasks/{task_id}/edit",
    })

    # Debug: show what we're about to send for due date/phase
    dbg_phase = payload.get("projects_task[phase_id]", "(none)")
    dbg_due = payload.get("projects_task[due_date]", "(none)")
    print(f"→ Patching task {task_id}: title='{title}', phase='{dbg_phase}', due='{dbg_due}'")

    res = session.post(update_url, headers=headers, data=payload)
    print("Update (PATCH) task status:", res.status_code)
    if res.status_code in (200, 204):
        return True
    print("Response preview:\n", res.text[:500])
    return False

# ----------------------
# Main
# ----------------------
if __name__ == "__main__":
    tasks_grouped = load_tasks_from_csv(CSV_PATH)

    if not login():
        raise SystemExit("Login failed.")

    for (phase_name, task_title), sub_items in tasks_grouped.items():
        # choose a task-level due date: first non-empty among that task's rows
        task_due_raw = ""
        for _, dt in sub_items:
            if dt and dt.strip():
                task_due_raw = dt.strip()
                break

        task_id, _csrf = create_task()
        if not task_id:
            continue

        ok = update_task_via_edit(
            task_id=task_id,
            title=task_title,
            description="",
            phase_name=phase_name,
            subtasks=sub_items,
            maybe_due_date_raw=task_due_raw,
        )
        if ok:
            print(f"✅ Updated task {task_id} → '{task_title}' ({phase_name}) with {len(sub_items)} subtasks")
        else:
            print(f"❌ Failed to update task {task_id} ('{task_title}')")
