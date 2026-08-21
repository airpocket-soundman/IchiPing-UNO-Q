#include <Arduino_LED_Matrix.h>
#include <Arduino_RouterBridge.h>
#include <Wire.h>

namespace {

constexpr uint8_t kStatePins[5] = {D3, D4, D5, D6, D7};
constexpr uint8_t kExecPin = D8;
constexpr uint8_t kRainPin = D9;
constexpr uint8_t kPca9685Address = 0x40;
constexpr uint32_t kDebounceMs = 30;
constexpr uint32_t kPredictionHoldMs = 5000;

Arduino_LED_Matrix matrix;
uint8_t pixels[8 * 13] = {};
uint8_t physicalState = 0;
uint8_t displayedState = 0;
uint8_t displayedConfidence = 0;
bool pca9685Present = false;
bool lastExecRaw = HIGH;
bool stableExec = HIGH;
uint32_t execChangedAt = 0;
uint32_t predictionHoldUntil = 0;

void clearPixels() {
  memset(pixels, 0, sizeof(pixels));
}

void setPixel(uint8_t row, uint8_t col, uint8_t brightness) {
  if (row < 8 && col < 13) {
    pixels[row * 13 + col] = constrain(brightness, 0, 7);
  }
}

void drawHouseFrame() {
  for (uint8_t col = 1; col <= 10; ++col) {
    setPixel(1, col, 2);
    setPixel(7, col, 2);
  }
  for (uint8_t row = 2; row <= 6; ++row) {
    setPixel(row, 0, 2);
    setPixel(row, 11, 2);
  }
  setPixel(0, 5, 2);
  setPixel(0, 6, 2);
}

void renderState(uint8_t stateMask, uint8_t confidence) {
  clearPixels();
  drawHouseFrame();

  // Five vertical cells represent window a/b/c and door AB/BC from left to right.
  for (uint8_t item = 0; item < 5; ++item) {
    const uint8_t col = 1 + item * 2;
    const uint8_t level = (stateMask & (1U << item)) ? 7 : 1;
    for (uint8_t row = 3; row <= 5; ++row) {
      setPixel(row, col, level);
      setPixel(row, col + 1, level);
    }
  }

  // Rightmost column is a bottom-up confidence meter (0..100%).
  const uint8_t bars = static_cast<uint8_t>((constrain(confidence, 0, 100) * 8U + 99U) / 100U);
  for (uint8_t i = 0; i < bars; ++i) {
    setPixel(7 - i, 12, 7);
  }
  matrix.draw(pixels);
}

void renderPing(uint8_t radius) {
  clearPixels();
  const int centerRow = 4;
  const int centerCol = 6;
  for (int row = 0; row < 8; ++row) {
    for (int col = 0; col < 13; ++col) {
      const int distance = abs(row - centerRow) + abs(col - centerCol);
      if (distance == radius || (radius == 0 && distance == 0)) {
        setPixel(row, col, 7);
      }
    }
  }
  matrix.draw(pixels);
}

void runMatrixSelfTest() {
  for (uint8_t radius = 0; radius < 10; ++radius) {
    renderPing(radius);
    delay(70);
  }
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
  // bit0=matrix initialized, bit1=PCA9685 detected, bit2=rain input active.
  int status = 0x01;
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
      runMatrixSelfTest();
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

  matrix.begin();
  matrix.setGrayscaleBits(3);
  matrix.clear();

  Bridge.begin();
  Bridge.provide("show_prediction", showPrediction);
  Bridge.provide("run_matrix_self_test", runMatrixSelfTest);
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
