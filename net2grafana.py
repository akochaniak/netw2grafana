import subprocess
import requests
import time

PUSHGATEWAY_URL = "http://your-pushgateway:9091"
JOB_NAME = "networker_backup"
timestamp = int(time.time())

def run_mminfo():
    # Pobiera dane z mminfo
    try:
        output = subprocess.check_output([
            "mminfo", "-avot",
            "-r", "client,totalsize,ssflags",
            "-t", "24 hours ago"
        ], universal_newlines=True)
        return output.strip().splitlines()
    except subprocess.CalledProcessError as e:
        print("Error running mminfo:", e)
        return []

def parse_and_push(lines):
    for line in lines:
        parts = line.split()
        if len(parts) < 3:
            continue

        client = parts[0]
        size_str = parts[1]
        flags = parts[2]

        # Parsowanie wielkości (np. GB → bajty)
        try:
            if size_str.endswith("KB"):
                size = float(size_str[:-2]) * 1024
            elif size_str.endswith("MB"):
                size = float(size_str[:-2]) * 1024**2
            elif size_str.endswith("GB"):
                size = float(size_str[:-2]) * 1024**3
            elif size_str.endswith("TB"):
                size = float(size_str[:-2]) * 1024**4
            else:
                size = float(size_str)  # jeśli w bajtach
        except ValueError:
            size = 0

        status = 1 if "a" in flags else 0

        # Generuj metryki
        metrics = f"""
# TYPE networker_backup_status gauge
networker_backup_status{{client="{client}"}} {status}

# TYPE networker_backup_size_bytes gauge
networker_backup_size_bytes{{client="{client}"}} {size}
"""

        url = f"{PUSHGATEWAY_URL}/metrics/job/{JOB_NAME}/instance/{client}"
        response = requests.post(url, data=metrics.encode("utf-8"))

        if response.status_code != 202:
            print(f"Failed to push metrics for {client}: {response.status_code}")
        else:
            print(f"Pushed metrics for {client}")

def main():
    lines = run_mminfo()
    if lines:
        parse_and_push(lines)

if __name__ == "__main__":
    main()
