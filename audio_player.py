import Adafruit_DHT
import subprocess
import time
from datetime import datetime, timedelta

# === CONFIGURATION ===
AUDIO_FILE = "/home/pi/audio/loop.wav"
LOG_FILE = "/home/pi/audio_player.log"

DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 4  # GPIO4
MAX_TEMP_C = 85
COOLDOWN_DURATION_MIN = 15
CHECK_INTERVAL_SEC = 10

# Active hours: 7:00–17:00
ACTIVE_HOURS = {"start": 7, "end": 17}

# === STATE ===
cooling_until = None
player = None

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

def is_within_active_hours():
    now = datetime.now()
    hour = now.hour
    return hour >= ACTIVE_HOURS["start"] or hour < ACTIVE_HOURS["end"]

def play_audio():
    return subprocess.Popen(["mpv", "--loop", AUDIO_FILE])

def stop_audio():
    global player
    if player and player.poll() is None:
        player.terminate()
        player.wait()
        log("🔇 Playback stopped.")

def get_temperature():
    humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
    return temperature

# === MAIN LOOP ===
try:
    log("📼 Audio playback controller started.")

    while True:
        now = datetime.now()
        active = is_within_active_hours()

        if not active:
            stop_audio()
            log("⏸️ Paused for daytime hours (07:00–17:00).")
            time.sleep(CHECK_INTERVAL_SEC)
            continue

        # Cooldown check
        if cooling_until and datetime.now() < cooling_until:
            log(f"❄️ Cooling until {cooling_until.strftime('%H:%M:%S')}")
            stop_audio()
            time.sleep(CHECK_INTERVAL_SEC)
            continue
        else:
            cooling_until = None

        # Start playback if needed
        if not player or player.poll() is not None:
            log("▶️ Starting audio playback.")
            player = play_audio()

        # Temperature check
        temperature = get_temperature()
        if temperature:
            log(f"🌡️ Temp: {temperature:.1f}°C")
            if temperature > MAX_TEMP_C:
                log(f"🔥 Temp too high ({temperature:.1f}°C). Stopping playback for {COOLDOWN_DURATION_MIN} min.")
                stop_audio()
                cooling_until = datetime.now() + timedelta(minutes=COOLDOWN_DURATION_MIN)

        time.sleep(CHECK_INTERVAL_SEC)

except KeyboardInterrupt:
    log("🔌 Script interrupted by user. Exiting...")
    stop_audio()
except Exception as e:
    log(f"💥 Unexpected error: {e}")
    stop_audio()
