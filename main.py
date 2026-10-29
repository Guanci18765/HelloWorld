import json
import os
import time
import subprocess
import serial
import comtypes
from pynput.keyboard import Controller as KeyboardController, Key
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL

CONFIG_FILE = "hotkeys.json"

default_config = {
    "COM_PORT": "COM3",
    "BAUD_RATE": 9600,
    "hotkeys": {
        "CMD_CAF": ["ctrl", "alt", "f"],
        "CMD_CAS": ["ctrl", "alt", "s"],
        "CMD_CAP": ["ctrl", "alt", "p"]
    }
}

# Sondertasten, die in hotkeys.json als Text stehen dürfen
KEY_MAP = {
    "ctrl": Key.ctrl_l,
    "alt": Key.alt_l,
    "shift": Key.shift,
    "win": Key.cmd,
    "enter": Key.enter,
    "esc": Key.esc,
    "tab": Key.tab,
}

if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w") as f:
        json.dump(default_config, f, indent=4)

with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

keyboard = KeyboardController()


# ---------- Audio ----------
def init_audio():
    """Holt den Lautstärke-Regler. Funktioniert mit alten und neuen pycaw-Versionen."""
    try:
        speakers = AudioUtilities.GetSpeakers()
        # Neuere pycaw-Versionen liefern direkt ein Objekt mit EndpointVolume
        if hasattr(speakers, "EndpointVolume"):
            return speakers.EndpointVolume
        # Ältere Versionen
        interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return interface.QueryInterface(IAudioEndpointVolume)
    except Exception as e:
        print(f"Audio-Fehler: {e}")
        return None


comtypes.CoInitialize()
volume = init_audio()


# ---------- Aktionen ----------
screen_state = True


def toggle_primary_monitor():
    global screen_state
    screen_state = not screen_state
    if screen_state:
        # Beide Bildschirme (Erweitert)
        subprocess.run(["DisplaySwitch.exe", "/extend"], shell=True)
    else:
        # Nur Bildschirm 2 (Zweiter Bildschirm)
        subprocess.run(["DisplaySwitch.exe", "/external"], shell=True)


def execute_hotkey(action):
    keys = config["hotkeys"].get(action)
    if not keys:
        return
    pressed_keys = []
    try:
        for k in keys:
            pk = KEY_MAP.get(k, k)
            keyboard.press(pk)
            pressed_keys.append(pk)
        time.sleep(0.05)
    finally:
        for pk in reversed(pressed_keys):
            keyboard.release(pk)


def handle_line(line):
    if line.startswith("VOL:") and volume:
        try:
            val = int(line.split(":")[1])
            val = max(0, min(100, val))
            volume.SetMasterVolumeLevelScalar(val / 100.0, None)
        except Exception as e:
            print(f"Lautstärke-Fehler: {e}")
    elif line == "CMD_MUTE" and volume:
        try:
            muted = volume.GetMute()
            volume.SetMute(0 if muted else 1, None)
        except Exception as e:
            print(f"Mute-Fehler: {e}")
    elif line == "CMD_SCREEN":
        toggle_primary_monitor()
    elif line in config["hotkeys"]:
        execute_hotkey(line)


# ---------- Serielle Verbindung ----------
def connect():
    """Verbindet sich mit dem Arduino und versucht es bei Fehlern immer wieder."""
    while True:
        try:
            print(f"Verbinde mit Arduino auf {config['COM_PORT']}...")
            ser = serial.Serial(config["COM_PORT"], config["BAUD_RATE"], timeout=1)
            # Der Uno startet beim Öffnen des Ports neu und braucht ca. 2 Sekunden
            time.sleep(2)
            ser.reset_input_buffer()
            print("Stream Deck Bridge läuft!")
            return ser
        except serial.SerialException as e:
            print(f"Verbindung fehlgeschlagen: {e} - neuer Versuch in 3 Sekunden")
            time.sleep(3)


def main():
    ser = connect()
    try:
        while True:
            try:
                if ser.in_waiting > 0:
                    line = ser.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        handle_line(line)
                else:
                    time.sleep(0.01)  # verhindert 100 % CPU-Last
            except (serial.SerialException, OSError):
                print("Verbindung verloren - verbinde neu...")
                try:
                    ser.close()
                except Exception:
                    pass
                ser = connect()
    except KeyboardInterrupt:
        print("Beendet.")
    finally:
        try:
            ser.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()