# start_kafka.py
import subprocess
import os
import time
import socket

# 🔹 Update this path to where Kafka is extracted
KAFKA_PATH = "kafka_2.13-4.1.0"
META_FILE = "/tmp/kraft-combined-logs/meta.properties"
CONFIG_FILE = "config/server.properties"

def is_kafka_running(host="localhost", port=9092):
    """Check if Kafka broker is accepting connections."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def start_kafka():
    """Start Kafka (KRaft mode) and verify readiness."""
    if is_kafka_running():
        print("✅ Kafka is already running on localhost:9092")
        return True

    print("⚙️ Kafka not running — initializing KRaft cluster...")

    try:
        # Step 1: Check if storage is already formatted
        if not os.path.exists(META_FILE):
            print("🗄️ No existing metadata found — formatting storage...")

            # Generate a unique Cluster ID
            cluster_id = subprocess.check_output(
                ["bash", "-c", "bin/kafka-storage.sh random-uuid"],
                cwd=KAFKA_PATH
            ).decode().strip()

            # Format storage for KRaft mode
            format_cmd = f"bin/kafka-storage.sh format --standalone -t {cluster_id} -c {CONFIG_FILE}"
            subprocess.run(["bash", "-c", format_cmd], cwd=KAFKA_PATH, check=True)
            print(f"✅ Storage formatted with Cluster ID: {cluster_id}")
        else:
            print("ℹ️ Existing Kafka metadata found — skipping format.")

        # Step 2: Start Kafka Broker
        print("🚀 Starting Kafka Server (KRaft mode)...")
        subprocess.Popen(
            ["bash", "-c", f"bin/kafka-server-start.sh {CONFIG_FILE}"],
            cwd=KAFKA_PATH,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Step 3: Wait for Kafka to be ready
        print("⏳ Waiting for Kafka to become ready...")
        for _ in range(60):  # Wait up to 60 seconds
            if is_kafka_running():
                print("✅ Kafka started successfully in KRaft mode!")
                return True
            time.sleep(1)

        print("❌ Kafka did not become ready in time.")
        return False

    except subprocess.CalledProcessError as e:
        print(f"❌ Kafka initialization error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    start_kafka()
