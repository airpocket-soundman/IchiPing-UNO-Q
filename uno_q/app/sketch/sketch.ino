#include <Arduino_RouterBridge.h>
#include <Wire.h>

#include "ili9341_display.h"

namespace {

constexpr uint8_t kStatePins[5] = {D3, D4, D5, D6, D7};
constexpr uint8_t kExecPin = D8;
constexpr uint8_t kRainPin = D9;
constexpr uint8_t kPca9685Address = 0x40;
constexpr uint8_t kPcaMode1Register = 0x00;
constexpr uint8_t kPcaMode2Register = 0x01;
constexpr uint8_t kPcaLed0OnLowRegister = 0x06;
constexpr uint8_t kPcaPrescaleRegister = 0xFE;
constexpr uint8_t kPcaServoPrescale50Hz = 121;
constexpr uint16_t kOriginalServoMinTick = 102;
constexpr uint16_t kOriginalServoMaxTick = 553;
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

bool writePca9685Register(uint8_t address, uint8_t value) {
  Wire.beginTransmission(kPca9685Address);
  Wire.write(address);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

int readPca9685Register(uint8_t address) {
  Wire.beginTransmission(kPca9685Address);
  Wire.write(address);
  if (Wire.endTransmission(false) != 0) return -1;
  if (Wire.requestFrom(kPca9685Address, static_cast<uint8_t>(1)) != 1) return -1;
  return Wire.read();
}

bool configurePca9685ForServos() {
  const int mode1 = readPca9685Register(kPcaMode1Register);
  if (mode1 < 0) return false;

  const uint8_t oldMode = static_cast<uint8_t>(mode1);
  const uint8_t sleepMode = (oldMode & 0x7F) | 0x10;
  if (!writePca9685Register(kPcaMode1Register, sleepMode)) return false;
  if (!writePca9685Register(kPcaPrescaleRegister, kPcaServoPrescale50Hz)) return false;
  if (!writePca9685Register(kPcaMode2Register, 0x04)) return false;
  if (!writePca9685Register(kPcaMode1Register, oldMode & 0xEF)) return false;
  delay(5);
  return writePca9685Register(kPcaMode1Register, (oldMode & 0xEF) | 0xA0);
}

bool setPca9685Channel(uint8_t channel, uint16_t offCount) {
  const uint8_t base = kPcaLed0OnLowRegister + (4 * channel);
  return writePca9685Register(base, 0x00) &&
         writePca9685Register(base + 1, 0x00) &&
         writePca9685Register(base + 2, offCount & 0xFF) &&
         writePca9685Register(base + 3, (offCount >> 8) & 0x0F);
}

bool disablePca9685Channel(uint8_t channel) {
  const uint8_t base = kPcaLed0OnLowRegister + (4 * channel);
  return writePca9685Register(base + 3, 0x10);
}

uint16_t servoPulseCount(uint16_t pulseUs) {
  return static_cast<uint16_t>((static_cast<uint32_t>(pulseUs) * 4096U + 10000U) / 20000U);
}

uint16_t originalServoAngleCount(uint16_t degrees) {
  const uint32_t span = kOriginalServoMaxTick - kOriginalServoMinTick;
  return static_cast<uint16_t>(kOriginalServoMinTick + ((span * degrees + 90U) / 180U));
}

int moveServoToAngle(int channel, int degrees) {
  if (channel < 0 || channel > 15 || degrees < 0 || degrees > 180) return -1;
  if (!detectPca9685()) return -2;
  if (!configurePca9685ForServos()) return -3;
  if (!setPca9685Channel(static_cast<uint8_t>(channel),
                         originalServoAngleCount(static_cast<uint16_t>(degrees)))) return -4;
  delay(500);
  if (!disablePca9685Channel(static_cast<uint8_t>(channel))) return -5;
  return 0;
}

int testServoChannel(int channel) {
  if (channel < 0 || channel > 15) return -1;
  if (!detectPca9685()) return -2;
  if (!configurePca9685ForServos()) return -3;

  const uint16_t pulseUs[] = {1500, 1450, 1550, 1500};
  for (uint16_t pulse : pulseUs) {
    if (!setPca9685Channel(static_cast<uint8_t>(channel), servoPulseCount(pulse))) return -4;
    delay(450);
  }
  if (!disablePca9685Channel(static_cast<uint8_t>(channel))) return -5;
  return 0;
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

int getSwitchStates() {
  int states = static_cast<int>(readPhysicalState());
  if (digitalRead(kExecPin) == LOW) states |= (1 << 5);
  return states;
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
  Bridge.provide("get_switch_states", getSwitchStates);
  Bridge.provide("test_servo_channel", testServoChannel);
  Bridge.provide("move_servo_deg", moveServoToAngle);

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
