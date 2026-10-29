#include <LiquidCrystal.h>

// LCD Pin-Belegung: RS, E, D4, D5, D6, D7
LiquidCrystal lcd(12, 11, 5, 4, 3, 2);

// 5 Taster Pins (6 bis 10) und zugehörige Befehle & Namen
const int buttonPins[] = {6, 7, 8, 9, 10};
const char* buttonCommands[] = {"CMD_MUTE", "CMD_SCREEN", "CMD_CAF", "CMD_CAS", "CMD_CAP"};
const char* buttonNames[] = {"Mute Toggle", "Screen Toggle", "Hotkey CAF", "Hotkey CAS", "Hotkey CAP"};
const int numButtons = 5;

int lastButtonStates[5] = {HIGH, HIGH, HIGH, HIGH, HIGH};

// Potentiometer für Lautstärke auf A0
const int potPin = A0;
int lastVolume = -1;

// true  = beim Start wird die Poti-Stellung sofort als Lautstärke an den PC gesendet
// false = die PC-Lautstärke bleibt unverändert, bis das Poti bewegt wird
const bool SEND_VOLUME_AT_START = false;

int readVolumePercent() {
  int potValue = analogRead(potPin);
  return constrain(map(potValue, 0, 1023, 0, 100), 0, 100);
}

void showVolume(int percent) {
  lcd.setCursor(0, 1);
  lcd.print("Vol: ");
  lcd.print(percent);
  lcd.print("%   ");
}

void setup() {
  Serial.begin(9600);

  // LCD starten (16 Spalten, 2 Zeilen)
  lcd.begin(16, 2);
  lcd.setCursor(0, 0);
  lcd.print("StreamDeck Ready"); // genau 16 Zeichen

  // Taster als Input mit Pullup konfigurieren
  for (int i = 0; i < numButtons; i++) {
    pinMode(buttonPins[i], INPUT_PULLUP);
  }

  if (!SEND_VOLUME_AT_START) {
    lastVolume = readVolumePercent();
    showVolume(lastVolume);
  }
}

void loop() {
  // 1. Taster abfragen
  for (int i = 0; i < numButtons; i++) {
    int currentState = digitalRead(buttonPins[i]);
    if (currentState == LOW && lastButtonStates[i] == HIGH) {
      Serial.println(buttonCommands[i]);

      // LCD Zeile 0 aktualisieren
      lcd.setCursor(0, 0);
      lcd.print("                ");
      lcd.setCursor(0, 0);
      lcd.print(buttonNames[i]);

      delay(200); // Entprellen
    }
    lastButtonStates[i] = currentState;
  }

  // 2. Potentiometer (Lautstärke) abfragen
  int volumePercent = readVolumePercent();

  // Nur senden, wenn sich die Lautstärke geändert hat
  if (abs(volumePercent - lastVolume) >= 2) {
    lastVolume = volumePercent;
    Serial.print("VOL:");
    Serial.println(volumePercent);
    showVolume(volumePercent);
  }

  delay(50);
}