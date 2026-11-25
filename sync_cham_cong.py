"""Sync the last seven days of ZKTeco attendance logs to the HRM worker."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from zk import ZK


# Device and API settings
DEVICE_IP = "192.168.1.201"
DEVICE_PORT = 4370
COMM_KEY = 0
API_URL = "https://quan-ly-nhan-suu.phuoc-nhtvietcasa.workers.dev/api/sync/cham"
API_KEY = "PASTE_CONNECTION_CODE_HERE"

# Optional mapping when device user IDs differ from employee codes.
USER_ID_TO_MA = {}

API_BATCH_SIZE = 500
STATUS_TO_TYPE = {0: "vao", 1: "ra", 2: "ra", 3: "vao", 4: "vao", 5: "ra"}
VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def collect_logs():
    cutoff = datetime.now(VN_TZ) - timedelta(days=7)
    zk = ZK(DEVICE_IP, port=DEVICE_PORT, timeout=10, password=COMM_KEY, force_udp=False)
    connection = None
    try:
        connection = zk.connect()
        grouped = {}
        punch_states = set()
        for record in connection.get_attendance():
            if record.timestamp is None or record.user_id is None:
                continue
            timestamp = record.timestamp
            timestamp = timestamp.replace(tzinfo=VN_TZ) if timestamp.tzinfo is None else timestamp.astimezone(VN_TZ)
            if timestamp < cutoff:
                continue

            user_id = str(record.user_id).strip()
            ma = str(USER_ID_TO_MA.get(user_id, user_id)).strip().upper()
            try:
                punch = int(record.punch or 0)
            except (TypeError, ValueError):
                continue
            if not ma:
                continue

            punch_states.add(punch)
            event = {
                "ma": ma,
                "t": int(timestamp.timestamp() * 1000),
                "tb": f"ZKTeco {DEVICE_IP}",
                "ghi": f"status={record.status}, punch={record.punch}",
                "loai": STATUS_TO_TYPE.get(punch),
            }
            grouped.setdefault((ma, timestamp.date().isoformat()), []).append(event)

        logs = []
        single_state = len(punch_states) <= 1
        for punches in grouped.values():
            if single_state:
                first = min(punches, key=lambda x: x["t"])
                last = max(punches, key=lambda x: x["t"])
                logs.append({**first, "loai": "vao"})
                if last["t"] - first["t"] >= 60 * 60 * 1000:
                    logs.append({**last, "loai": "ra"})
                continue

            checkins = [x for x in punches if x["loai"] == "vao"]
            checkouts = [x for x in punches if x["loai"] == "ra"]
            if checkins:
                logs.append(min(checkins, key=lambda x: x["t"]))
            if checkouts:
                logs.append(max(checkouts, key=lambda x: x["t"]))
        logs.sort(key=lambda x: (x["ma"], x["t"]))
        return logs
    finally:
        if connection is not None:
            connection.disconnect()


def upload_logs(logs):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    total = 0
    with requests.Session() as session:
        for start in range(0, len(logs), API_BATCH_SIZE):
            response = session.post(
                API_URL,
                json={"list": logs[start : start + API_BATCH_SIZE]},
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
            if not result.get("ok") or not isinstance(result.get("n"), int):
                raise RuntimeError(f"Import rejected: {result}")
            total += result["n"]
    return total


def main():
    if not API_KEY or API_KEY == "PASTE_CONNECTION_CODE_HERE":
        raise RuntimeError("Set API_KEY to the connection code from the HRM settings.")

    logs = collect_logs()
    if not logs:
        print("No attendance logs from the last 7 days.")
        return

    uploaded = upload_logs(logs)
    print(f"Imported {uploaded} of {len(logs)} attendance logs.")


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as exc:
        print(f"API request failed: {exc}")
        raise SystemExit(1) from exc
    except Exception as exc:
        print(f"Sync failed: {exc}")
        raise SystemExit(1) from exc
