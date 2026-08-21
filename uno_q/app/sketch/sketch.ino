#include <Arduino_RouterBridge.h>
#include <Wire.h>

#include "ili9341_display.h"

namespace {

constexpr uint8_t kStatePins[5] = {D3, D4, D5, D6, D7};
constexpr uint8_t kExecPin = D8;
constexpr uint8_t kRainPin = D9;
constexpr uint8_t kPca9685Address = 0x40;
constexpr uint32_t kDebounceMs = 30;
constexpr uint32_t kPredictionHoldMs = 5000;

Ili9341Display display;
bool displayInitialized = false;
uint8_t physicalState = 0;
uint8_t displayedState = 0;
uint8_t displayedConfidence = 0;
bool pca9685Present = false;
bool lastExecRaw = HIGH;
bool stableExec = HIGH;
uint32_t execChangedAt = 0;
uint32_t predictionHoldUntil = 0;

void renderState(uint8_t stateMask, uint8_t confidence) {
  if (displayInitialized) display.showState(stateMask, confidence);
}

void renderPing(uint8_t radius) {
  if (displayInitialized) display.showActivity(radius);
}

void runDisplaySelfTest() {
  if (displayInitialized) display.runSelfTest();
  renderState(displayedState, displayedConfidence);
}

uint8_t readPhysicalState() {
  uint8_t mask = 0;
  for (uint8_t i = 0; i < 5; ++i) {
    if (digitalRead(kStatePins[i]) == LOW) {
      mask |= (1U << i);
    }
  }
  return mask;
}

bool detectPca9685() {
  Wire.beginTransmission(kPca9685Address);
  return Wire.endTransmission() == 0;
}

void showPrediction(int stateMask, int confidence) {
  displayedState = static_cast<uint8_t>(stateMask) & 0x1F;
  displayedConfidence = static_cast<uint8_t>(constrain(confidence, 0, 100));
  predictionHoldUntil = millis() + kPredictionHoldMs;
  renderState(displayedState, displayedConfidence);
}

int getHardwareStatus() {
  // bit0=ILI9341 driver initialized, bit1=PCA9685 detected, bit2=rain active.
  int status = displayInitialized ? 0x01 : 0x00;
  if (pca9685Present) status |= 0x02;
  if (digitalRead(kRainPin) == LOW) status |= 0x04;
  return status;
}

int getPhysicalState() {
  return static_cast<int>(readPhysicalState());
}

void pollExecButton() {
  const bool raw = digitalRead(kExecPin);
  const uint32_t now = millis();
  if (raw != lastExecRaw) {
    lastExecRaw = raw;
    execChangedAt = now;
  }
  if ((now - execChangedAt) >= kDebounceMs && raw != stableExec) {
    stableExec = raw;
    if (stableExec == LOW) {
      physicalState = readPhysicalState();
      for (uint8_t frame = 0; frame < 8; ++frame) {
        renderPing(frame);
        delay(70);
      }
      Bridge.notify("on_infer_request", static_cast<int>(physicalState));
    }
  }
}

}  // namespace

void setup() {
  for (uint8_t pin : kStatePins) pinMode(pin, INPUT_PULLUP);
  pinMode(kExecPin, INPUT_PULLUP);
  pinMode(kRainPin, INPUT_PULLUP);

  Wire.begin();
  Wire.setClock(100000);
  pca9685Present = detectPca9685();

  displayInitialized = display.begin();

  Bridge.begin();
  Bridge.provide("show_prediction", showPrediction);
  Bridge.provide("run_display_self_test", runDisplaySelfTest);
  Bridge.provide("get_hardware_status", getHardwareStatus);
  Bridge.provide("get_physical_state", getPhysicalState);

  physicalState = readPhysicalState();
  displayedState = physicalState;
  renderState(displayedState, 0);
  Bridge.notify("on_runtime_status", "ready", getHardwareStatus());
}

void loop() {
  pollExecButton();
  physicalState = readPhysicalState();
  if (static_cast<int32_t>(millis() - predictionHoldUntil) >= 0 &&
      physicalState != displayedState) {
    displayedState = physicalState;
    displayedConfidence = 0;
    renderState(displayedState, displayedConfidence);
  }
  delay(5);
}
