"""Exercise HTTP CRUD and verify persistence through real Docker restarts.

Run from the project root: python scripts/verify_stack.py
Requires the stack to be running and uses only the Python standard library.
"""

import json
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

BASE_URL = "http://127.0.0.1:8000"


def compose(*args):
    result = subprocess.run(
        ["docker", "compose", *args], check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def request(method, path, payload=None, expected=200):
    body = json.dumps(payload).encode() if payload is not None else None
    req = Request(
        BASE_URL + path, data=body, method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        response = urlopen(req, timeout=5)
    except HTTPError as error:
        response = error
    with response:
        if response.status != expected:
            raise AssertionError(f"{method} {path}: expected {expected}, got {response.status}")
        data = response.read()
        return json.loads(data) if data else None


def wait_until_ready():
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            request("GET", "/tasks")
            return
        except (URLError, TimeoutError, OSError, AssertionError):
            time.sleep(1)
    raise RuntimeError("API did not become ready within 90 seconds")


def main():
    wait_until_ready()
    marker = f"persistence-{uuid4()}"
    created = []
    # Leave successful proof rows in Postgres so the result can be inspected.
    for suffix in ("one", "two"):
        task = request("POST", "/tasks", {"title": f"{marker}-{suffix}"}, 201)
        assert task["done"] is False
        created.append(task)

    first_id = created[0]["id"]
    updated = request("PUT", f"/tasks/{first_id}", {"done": True})
    assert updated == {**created[0], "done": True}
    created[0] = updated
    assert request("PUT", f"/tasks/{first_id}", {}) == updated
    request("POST", "/tasks", {"title": "   "}, 400)
    request("PUT", f"/tasks/{first_id}", {"title": "\t"}, 400)
    request("PUT", f"/tasks/{first_id}", {"done": "not-a-boolean"}, 422)
    for method in ("GET", "PUT", "DELETE"):
        request(method, "/tasks/-1", {} if method == "PUT" else None, 404)

    disposable = request("POST", "/tasks", {"title": f"{marker}-delete"}, 201)
    disposable_id = disposable["id"]
    request("DELETE", f"/tasks/{disposable_id}", expected=204)
    request("GET", f"/tasks/{disposable_id}", expected=404)

    def assert_persisted(stage):
        for task in created:
            assert request("GET", f"/tasks/{task['id']}") == task
        print(json.dumps({"stage": stage, "rows": created}), flush=True)

    assert_persisted("before restart")
    compose("restart", "app", "db")
    wait_until_ready()
    assert_persisted("after app + database restart")

    old_ids = {service: compose("ps", "-q", service) for service in ("app", "db")}
    # Recreate containers while retaining the named Postgres volume.
    compose("up", "-d", "--force-recreate", "--wait", "--wait-timeout", "120")
    wait_until_ready()
    new_ids = {service: compose("ps", "-q", service) for service in ("app", "db")}
    assert all(old_ids[service] != new_ids[service] for service in old_ids)
    assert_persisted("after app + database container recreation")
    print("PASS: HTTP CRUD and persistence; both container IDs changed.", flush=True)


if __name__ == "__main__":
    main()
