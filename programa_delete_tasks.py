import requests
from bs4 import BeautifulSoup
import re

PROJECT_ID = "338807"   # change this

# === Credentials at the top for easy copy/paste ===
EMAIL = "Mariana.rdminteriors@gmail.com"
PASSWORD = "HeRedeems777&"

# === Constants ===
BASE_URL = "https://app.programa.design"
LOGIN_URL = f"{BASE_URL}/login/"
TASKS_URL = f"{BASE_URL}/projects/{PROJECT_ID}/tasks"

# === Common headers (mimic browser) ===
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


def login():
    """Login to Programa and keep session."""
    r = session.get(LOGIN_URL, headers=COMMON_HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")
    token = soup.find("input", {"name": "authenticity_token"})["value"]

    payload = {
        "authenticity_token": token,
        "user[email]": EMAIL,
        "user[password]": PASSWORD,
    }

    headers = COMMON_HEADERS.copy()
    headers.update({"Content-Type": "application/x-www-form-urlencoded"})

    res = session.post(LOGIN_URL, headers=headers, data=payload)
    print("Login POST status:", res.status_code)
    return res.status_code == 200


def get_csrf_token():
    """Grab CSRF token from project tasks page."""
    r = session.get(TASKS_URL, headers=COMMON_HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")
    meta = soup.find("meta", {"name": "csrf-token"})
    return meta["content"] if meta else None


def get_all_task_ids():
    """Scrape task IDs from the tasks page."""
    r = session.get(TASKS_URL, headers=COMMON_HEADERS)
    task_ids = re.findall(r'/tasks/(\d+)/edit', r.text)
    print(f"Found {len(task_ids)} tasks in project {PROJECT_ID}")
    return list(set(task_ids))  # deduplicate


def delete_task(task_id, csrf_token):
    """Delete a single task by ID."""
    delete_url = f"{BASE_URL}/tasks/{task_id}"

    headers = COMMON_HEADERS.copy()
    headers.update({
        "X-CSRF-Token": csrf_token,
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    })

    payload = {
        "_method": "delete",
        "authenticity_token": csrf_token,
    }

    res = session.post(delete_url, headers=headers, data=payload)
    print(f"Delete task {task_id} status:", res.status_code)


if __name__ == "__main__":
    if login():
        csrf_token = get_csrf_token()
        if not csrf_token:
            print("❌ Could not retrieve CSRF token")
        else:
            task_ids = get_all_task_ids()
            for tid in task_ids:
                delete_task(tid, csrf_token)
