import requests

API_BASE = "http://localhost:3000/api/tiktok"


def fetch_pending_task():
    res = requests.get(f"{API_BASE}/task/pending", timeout=10)
    res.raise_for_status()
    data = res.json()

    # Không có task
    if not data:
        return None

    # Nếu là list → lấy task đầu tiên
    if isinstance(data, list):
        return data[0] if data else None

    # Nếu có wrapper { data: {...} }
    if isinstance(data, dict) and "data" in data:
        return data["data"]

    # Nếu là object task
    return data

def update_task_status(task_id, status, result=None):
    payload = {"status": status}
    if result is not None:
        payload["result"] = result

    requests.patch(
        f"{API_BASE}/task/{task_id}",
        json=payload,
        timeout=10
    )