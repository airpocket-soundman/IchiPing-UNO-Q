#include <Arduino_RouterBridge.h>
#include <Wire.h>

#include "ili9341_display.h"

namespace {

constexpr uint8_t kStatePins[5] = {D3, D4, D5, D6, D7};
constexpr uint8_t kExecPin = D8;
constexpr uint8_t kPca9685Address = 0x40;
constexpr uint8_t kPcaMode1Register = 0x00;
constexpr uint8_t kPcaMode2Register = 0x01;
constexpr uint8_t kPcaLed0OnLowRegister = 0x06;
constexpr uint8_t kPcaPrescaleRegister = 0xFE;
constexpr uint8_t kPcaServoPrescale50Hz = 121;
constexpr uint16_t kOriginalServoMinTick = 102;
constexpr uint16_t kOriginalServoMaxTick = 553;
constexpr uint32_t kDebounceMs = 30;

Ili9341Display display;
bool displayInitialized = false;
uint8_t physicalState = 0;
uint8_t servoState = 0;
bool servoStateKnown = false;
uint8_t displayedState = 0;
bool predictionValid = false;
bool pca9685Present = false;
bool servoControlsArmed = false;
bool servoAutomationEnabled = false;
bool servoFaultLatched = false;
bool inferenceBusy = false;
bool servoSyncPending = false;
bool lastExecRaw = HIGH;
bool stableExec = HIGH;
uint32_t execChangedAt = 0;

void renderState() {
  if (displayInitialized) {
    display.showState(servoState, servoStateKnown, predictionValid, displayedState);
  }
}

void runDisplaySelfTest() {
  if (displayInitialized) display.runSelfTest();
  renderState();
}

uint8_t readPhysicalState() {
  uint8_t mask = 0;
  for (uint8_t i = 0; i < 5; ++i) {
    // Original IchiPing toggle contract: grounded LOW=CLOSE(0), released
    // pull-up HIGH=OPEN(1). This bit polarity is also the training label.
    if (digitalRead(kStatePins[i]) == HIGH) {
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

bool disableAllPca9685Channels() {
  bool stopped = true;
  for (uint8_t channel = 0; channel < 16; ++channel) {
    stopped = disablePca9685Channel(channel) && stopped;
  }
  return stopped;
}

int latchServoFault(int error) {
  servoAutomationEnabled = false;
  servoControlsArmed = false;
  servoFaultLatched = true;
  servoStateKnown = false;
  predictionValid = false;
  (void)disableAllPca9685Channels();
  renderState();
  return error;
}

uint16_t servoPulseCount(uint16_t pulseUs) {
  return static_cast<uint16_t>((static_cast<uint32_t>(pulseUs) * 4096U + 10000U) / 20000U);
}

uint16_t originalServoAngleCount(uint16_t degrees) {
  const uint32_t span = kOriginalServoMaxTick - kOriginalServoMinTick;
  return static_cast<uint16_t>(kOriginalServoMinTick + ((span * degrees + 90U) / 180U));
}

int driveServoToAngle(int channel, int degrees) {
  if (channel < 0 || channel > 4 || degrees < 0 || degrees > 180) return -1;
  if (!servoControlsArmed) return -6;
  if (servoFaultLatched) return -7;
  if (!detectPca9685()) return latchServoFault(-2);
  if (!configurePca9685ForServos()) return latchServoFault(-3);
  if (!setPca9685Channel(static_cast<uint8_t>(channel),
                         originalServoAngleCount(static_cast<uint16_t>(degrees)))) {
    return latchServoFault(-4);
  }
  delay(500);
  if (!disablePca9685Channel(static_cast<uint8_t>(channel))) {
    return latchServoFault(-5);
  }
  return 0;
}

int moveServoToAngle(int channel, int degrees) {
  const int result = driveServoToAngle(channel, degrees);
  if (result != 0) return result;
  predictionValid = false;
  // An isolated endpoint command only preserves a complete state if the other
  // four channels were already known. Arbitrary test angles make it unknown.
  if (servoStateKnown && (degrees == 0 || degrees == 180)) {
    if (degrees == 0) {
      servoState |= (1U << channel);
    } else {
      servoState &= ~(1U << channel);
    }
  } else {
    servoStateKnown = false;
  }
  renderState();
  return 0;
}

int testServoChannel(int channel) {
  if (channel < 0 || channel > 4) return -1;
  if (!servoControlsArmed) return -6;
  if (servoFaultLatched) return -7;
  if (!detectPca9685()) return latchServoFault(-2);
  if (!configurePca9685ForServos()) return latchServoFault(-3);

  const uint16_t pulseUs[] = {1500, 1450, 1550, 1500};
  for (uint16_t pulse : pulseUs) {
    if (!setPca9685Channel(static_cast<uint8_t>(channel), servoPulseCount(pulse))) {
      return latchServoFault(-4);
    }
    delay(450);
  }
  if (!disablePca9685Channel(static_cast<uint8_t>(channel))) {
    return latchServoFault(-5);
  }
  servoStateKnown = false;
  predictionValid = false;
  renderState();
  return 0;
}

int showPrediction(int stateMask, int confidence, int capturedPhysicalState,
                   int requestId) {
  (void)confidence;  // Original display evaluates bits; it has no confidence bar.
  if (!servoStateKnown || (capturedPhysicalState & 0x1F) != servoState) {
    predictionValid = false;
    renderState();
    return -2;
  }
  displayedState = static_cast<uint8_t>(stateMask) & 0x1F;
  predictionValid = true;
  renderState();
  return requestId;
}

int setServoArmed(int enabled, int expectedStateMask) {
  if (!enabled) {
    servoAutomationEnabled = false;
    servoControlsArmed = false;
    if (!pca9685Present) return 0;
    return disableAllPca9685Channels() ? 0 : latchServoFault(-5);
  }
  if ((expectedStateMask & 0x1F) != readPhysicalState()) return -8;
  pca9685Present = detectPca9685();
  if (!pca9685Present) return -2;
  if (!disableAllPca9685Channels()) return latchServoFault(-5);
  servoFaultLatched = false;
  servoControlsArmed = true;
  return 0;
}

int setServoAutomation(int enabled) {
  if (!enabled) {
    servoAutomationEnabled = false;
    return !pca9685Present || disableAllPca9685Channels()
        ? 0 : latchServoFault(-5);
  }
  if (!servoControlsArmed) return -6;
  if (servoFaultLatched) return -7;
  if (!detectPca9685()) return latchServoFault(-2);

  // Original startup sequence establishes a known physical state without
  // driving all five SG90s simultaneously: BC -> AB -> c -> b -> a CLOSE.
  for (int channel = 4; channel >= 0; --channel) {
    const int result = driveServoToAngle(channel, 180);
    if (result != 0) return result;
  }
  servoState = 0;
  servoStateKnown = true;
  // Then synchronize only switches requesting OPEN, in a -> b -> c -> AB -> BC.
  const uint8_t requested = readPhysicalState();
  for (uint8_t channel = 0; channel < 5; ++channel) {
    if (requested & (1U << channel)) {
      const int result = driveServoToAngle(channel, 0);
      if (result != 0) return result;
      servoState |= (1U << channel);
    }
  }
  physicalState = requested;
  predictionValid = false;
  servoAutomationEnabled = true;
  renderState();
  return 0;
}

// Boot sequence helper: drive every servo CLOSE (BC -> a, one at a time) and
// mark the all-closed state as known, independent of the switch positions.
int closeAllServos() {
  if (!servoControlsArmed) return -6;
  if (servoFaultLatched) return -7;
  servoAutomationEnabled = false;
  for (int channel = 4; channel >= 0; --channel) {
    const int result = driveServoToAngle(channel, 180);
    if (result != 0) return result;
  }
  servoState = 0;
  servoStateKnown = true;
  predictionValid = false;
  renderState();
  return 0;
}

int setInferenceBusy(int busy) {
  inferenceBusy = busy != 0;
  return inferenceBusy ? 1 : 0;
}

void showInferenceUnavailable() {
  predictionValid = false;
  if (displayInitialized) display.showUnavailable(servoState, servoStateKnown);
}

void showRuntimeStatus(int statusCode) {
  predictionValid = false;
  if (displayInitialized) {
    display.showRuntimeStatus(servoState, servoStateKnown,
                              static_cast<uint8_t>(constrain(statusCode, 1, 9)));
  }
}

int getHardwareStatus() {
  // bit0=ILI9341 init sent, bit1=PCA9685 present, bit2=reserved,
  // bit4=servo controls armed, bit5=servo fault latched, bit6=inference busy,
  // bit7=all five servo endpoints are known from successful commands.
  pca9685Present = detectPca9685();
  int status = displayInitialized ? 0x01 : 0x00;
  if (pca9685Present) status |= 0x02;
  if (servoControlsArmed) status |= 0x10;
  if (servoFaultLatched) status |= 0x20;
  if (inferenceBusy) status |= 0x40;
  if (servoStateKnown) status |= 0x80;
  return status;
}

int getPhysicalState() {
  return static_cast<int>(readPhysicalState());
}

int getServoState() {
  return servoStateKnown ? static_cast<int>(servoState) : -1;
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
    if (stableExec == LOW && !inferenceBusy) {
      physicalState = readPhysicalState();
      if (!servoStateKnown) {
        showRuntimeStatus(9);
      } else {
        Bridge.notify("on_infer_request", static_cast<int>(servoState));
      }
    }
  }
}

}  // namespace

void setup() {
  for (uint8_t pin : kStatePins) pinMode(pin, INPUT_PULLUP);
  pinMode(kExecPin, INPUT_PULLUP);

  Wire.begin();
  Wire.setClock(100000);
  pca9685Present = detectPca9685();
  if (pca9685Present && !disableAllPca9685Channels()) {
    servoFaultLatched = true;
  }

  displayInitialized = display.begin();

  Bridge.begin();
  Bridge.provide("show_prediction", showPrediction);
  Bridge.provide("show_inference_unavailable", showInferenceUnavailable);
  Bridge.provide("show_runtime_status", showRuntimeStatus);
  Bridge.provide("run_display_self_test", runDisplaySelfTest);
  Bridge.provide("get_hardware_status", getHardwareStatus);
  Bridge.provide("get_physical_state", getPhysicalState);
  Bridge.provide("get_servo_state", getServoState);
  Bridge.provide("close_all_servos", closeAllServos);
  Bridge.provide("get_switch_states", getSwitchStates);
  Bridge.provide("test_servo_channel", testServoChannel);
  Bridge.provide("move_servo_deg", moveServoToAngle);
  Bridge.provide("set_servo_armed", setServoArmed);
  Bridge.provide("set_servo_automation", setServoAutomation);
  Bridge.provide("set_inference_busy", setInferenceBusy);

  physicalState = readPhysicalState();
  displayedState = physicalState;
  renderState();
  Bridge.notify("on_runtime_status", "ready", getHardwareStatus());
}

void loop() {
  pollExecButton();
  const uint8_t newPhysicalState = readPhysicalState();
  if (newPhysicalState != physicalState) {
    const uint8_t changed = newPhysicalState ^ physicalState;
    if (servoAutomationEnabled && inferenceBusy) {
      servoSyncPending = true;
    } else if (servoAutomationEnabled) {
      for (uint8_t channel = 0; channel < 5; ++channel) {
        if (changed & (1U << channel)) {
          const bool open = (newPhysicalState & (1U << channel)) != 0;
          if (driveServoToAngle(channel, open ? 0 : 180) != 0) {
            servoAutomationEnabled = false;
            break;
          }
          if (open) {
            servoState |= (1U << channel);
          } else {
            servoState &= ~(1U << channel);
          }
          predictionValid = false;
        }
      }
    }
    physicalState = newPhysicalState;
    renderState();
  }
  if (!inferenceBusy && servoAutomationEnabled && servoSyncPending) {
    servoSyncPending = false;
    const uint8_t requested = readPhysicalState();
    for (uint8_t channel = 0; channel < 5; ++channel) {
      const bool open = (requested & (1U << channel)) != 0;
      if (driveServoToAngle(channel, open ? 0 : 180) != 0) break;
      if (open) {
        servoState |= (1U << channel);
      } else {
        servoState &= ~(1U << channel);
      }
      predictionValid = false;
    }
    renderState();
  }
  delay(5);
}
