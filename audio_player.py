import adafruit_dht
import board
import subprocess
import time
from datetime import datetime, timedelta
import os

# === CONFIGURATION ===
# Automatically detect current script directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Full path to loop.wav inside ~/dacpro_player
AUDIO_FILE = os.path.join(SCRIPT_DIR, "loop.wav")
LOG_FILE = os.path.join(SCRIPT_DIR, "audio_player.log")

# Initialize the sensor once at the top
dht_device = adafruit_dht.DHT22(board.D4)
MAX_TEMP_C = 85.0
COOLDOWN_DURATION_MIN = 15
CHECK_INTERVAL_SEC = 30

# === STATE ===
cooling_until = None
player = None

# === LOGGING FUNCTION ===
def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"[{timestamp}] {msg}")

def play_audio():
    return subprocess.Popen(["mpv", "--loop", AUDIO_FILE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def stop_audio():
    global player
    if player and player.poll() is None:
        player.terminate()
        player.wait()
        log("🔇 Playback stopped.")

def get_sensor_data():
    try:
        temperature = dht_device.temperature
        humidity = dht_device.humidity
        return humidity, temperature
    except RuntimeError as error:
        log(f"⚠️ Sensor read error: {error}")
        return None, None

# === MAIN LOOP ===
try:
    log("📼 Audio playback controller starting...")

    log("⏳ Waiting 5 minutes before starting...")
    time.sleep(300)  # Sleep for 5 minutes

    while True:
        humidity, temperature = get_sensor_data()

        if humidity is not None and temperature is not None:
            log(f"🌡️ Temp: {temperature:.1f}°C  💧 Humidity: {humidity:.1f}%")
        else:
            log("⚠️ Sensor read failed")

        # Handle cooldown state
        if cooling_until and datetime.now() < cooling_until:
            stop_audio()
            log(f"❄️ Cooling down until {cooling_until.strftime('%H:%M:%S')}")
            time.sleep(CHECK_INTERVAL_SEC)
            continue
        else:
            cooling_until = None

        # Start playback if not already running
        if not player or player.poll() is not None:
            player = play_audio()
            log("▶️ Audio playback started.")

        # Handle high temperature
        if temperature and temperature > MAX_TEMP_C:
            stop_audio()
            cooling_until = datetime.now() + timedelta(minutes=COOLDOWN_DURATION_MIN)
            log(f"🔥 Temp exceeded {MAX_TEMP_C}°C — cooling for {COOLDOWN_DURATION_MIN} min.")

        time.sleep(CHECK_INTERVAL_SEC)

except KeyboardInterrupt:
    log("🔌 Interrupted. Shutting down...")
    stop_audio()
