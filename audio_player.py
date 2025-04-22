import Adafruit_DHT
import subprocess
import time
from datetime import datetime, timedelta

# === CONFIGURATION ===
AUDIO_FILE = "/home/pi/audio/loop.wav"
DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 4  # GPIO4
MAX_TEMP_C = 65.0
COOLDOWN_DURATION_MIN = 15
CHECK_INTERVAL_SEC = 10

# Active hours: 7:00–17:00
ACTIVE_HOURS = {"start": 7, "end": 17}

# === STATE ===
cooling_until = None
player = None

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
        print("🔇 Playback stopped.")

def get_temperature():
    humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
    return temperature

# === MAIN LOOP ===
try:
    print("📼 Audio playback controller starting...")

    while True:
        now = datetime.now()
        active = is_within_active_hours()

        if not active:
            # During daytime: stop playback if running
            stop_audio()
            print(f"[{now.strftime('%H:%M:%S')}] ⏸️ Paused for daytime hours (07:00–17:00)")
            time.sleep(CHECK_INTERVAL_SEC)
            continue

        # If in cooldown window
        if cooling_until and datetime.now() < cooling_until:
            print(f"[{now.strftime('%H:%M:%S')}] ❄️ Cooling until {cooling_until.strftime('%H:%M:%S')}")
            stop_audio()
            time.sleep(CHECK_INTERVAL_SEC)
            continue
        else:
            cooling_until = None

        # Start playback if not already running
        if not player or player.poll() is not None:
            print(f"[{now.strftime('%H:%M:%S')}] ▶️ Starting playback")
            player = play_audio()

        # Check temp
        temperature = get_temperature()
        if temperature:
            print(f"[{now.strftime('%H:%M:%S')}] 🌡️ Temp: {temperature:.1f}°C")
            if temperature > MAX_TEMP_C:
                print(f"[{now.strftime('%H:%M:%S')}] 🔥 Temp too high. Cooling down for {COOLDOWN_DURATION_MIN} min.")
                stop_audio()
                cooling_until = datetime.now() + timedelta(minutes=COOLDOWN_DURATION_MIN)

        time.sleep(CHECK_INTERVAL_SEC)

except KeyboardInterrupt:
    print("🔌 Interrupted. Shutting down...")
    stop_audio()
