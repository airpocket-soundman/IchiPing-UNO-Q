#include "ili9341_display.h"

namespace {

constexpr uint32_t kSpiClockHz = 20000000;
constexpr uint16_t kBlack = 0x0000;
constexpr uint16_t kNavy = 0x0841;
constexpr uint16_t kBlue = 0x2D7F;
constexpr uint16_t kCyan = 0x07FF;
constexpr uint16_t kGreen = 0x07E0;
constexpr uint16_t kDarkGreen = 0x0180;
constexpr uint16_t kYellow = 0xFFE0;
constexpr uint16_t kRed = 0xF800;
constexpr uint16_t kWhite = 0xFFFF;

}  // namespace

bool Ili9341Display::begin() {
  pinMode(kCsPin, OUTPUT);
  pinMode(kResetPin, OUTPUT);
  pinMode(kDcPin, OUTPUT);
  pinMode(kBacklightPin, OUTPUT);
  digitalWrite(kCsPin, HIGH);
  digitalWrite(kDcPin, HIGH);
  digitalWrite(kBacklightPin, LOW);
  SPI.begin();
  reset();

  command(0x01);  // Software reset.
  delay(150);
  command(0x28);  // Display off.
  const uint8_t power1[] = {0x23};
  command(0xC0, power1, sizeof(power1));
  const uint8_t power2[] = {0x10};
  command(0xC1, power2, sizeof(power2));
  const uint8_t vcom1[] = {0x3E, 0x28};
  command(0xC5, vcom1, sizeof(vcom1));
  const uint8_t vcom2[] = {0x86};
  command(0xC7, vcom2, sizeof(vcom2));
  const uint8_t memoryAccess[] = {0x28};  // Landscape, BGR.
  command(0x36, memoryAccess, sizeof(memoryAccess));
  const uint8_t pixelFormat[] = {0x55};  // RGB565.
  command(0x3A, pixelFormat, sizeof(pixelFormat));
  const uint8_t frameRate[] = {0x00, 0x18};
  command(0xB1, frameRate, sizeof(frameRate));
  const uint8_t displayFunction[] = {0x08, 0x82, 0x27};
  command(0xB6, displayFunction, sizeof(displayFunction));
  command(0x11);  // Sleep out.
  delay(120);
  command(0x29);  // Display on.
  delay(20);
  digitalWrite(kBacklightPin, HIGH);
  fillScreen(kBlack);
  return true;
}

void Ili9341Display::reset() {
  digitalWrite(kResetPin, HIGH);
  delay(5);
  digitalWrite(kResetPin, LOW);
  delay(20);
  digitalWrite(kResetPin, HIGH);
  delay(150);
}

void Ili9341Display::command(uint8_t value, const uint8_t* data, size_t size) {
  SPI.beginTransaction(SPISettings(kSpiClockHz, MSBFIRST, SPI_MODE0));
  digitalWrite(kCsPin, LOW);
  digitalWrite(kDcPin, LOW);
  SPI.transfer(value);
  digitalWrite(kDcPin, HIGH);
  for (size_t i = 0; i < size; ++i) SPI.transfer(data[i]);
  digitalWrite(kCsPin, HIGH);
  SPI.endTransaction();
}

void Ili9341Display::setWindow(uint16_t x, uint16_t y, uint16_t width,
                               uint16_t height) {
  const uint16_t xEnd = x + width - 1;
  const uint16_t yEnd = y + height - 1;
  const uint8_t columns[] = {static_cast<uint8_t>(x >> 8),
                             static_cast<uint8_t>(x),
                             static_cast<uint8_t>(xEnd >> 8),
                             static_cast<uint8_t>(xEnd)};
  const uint8_t rows[] = {static_cast<uint8_t>(y >> 8),
                          static_cast<uint8_t>(y),
                          static_cast<uint8_t>(yEnd >> 8),
                          static_cast<uint8_t>(yEnd)};
  command(0x2A, columns, sizeof(columns));
  command(0x2B, rows, sizeof(rows));
  command(0x2C);
}

void Ili9341Display::fillRect(uint16_t x, uint16_t y, uint16_t width,
                              uint16_t height, uint16_t color) {
  if (x >= kWidth || y >= kHeight || width == 0 || height == 0) return;
  width = width < (kWidth - x) ? width : (kWidth - x);
  height = height < (kHeight - y) ? height : (kHeight - y);
  setWindow(x, y, width, height);

  uint8_t pixels[128];
  uint32_t remaining = static_cast<uint32_t>(width) * height;
  SPI.beginTransaction(SPISettings(kSpiClockHz, MSBFIRST, SPI_MODE0));
  digitalWrite(kCsPin, LOW);
  digitalWrite(kDcPin, HIGH);
  while (remaining > 0) {
    // ZephyrSPI::transfer is full-duplex and overwrites this buffer with RX,
    // so regenerate the solid-color chunk before every transfer.
    for (size_t i = 0; i < sizeof(pixels); i += 2) {
      pixels[i] = static_cast<uint8_t>(color >> 8);
      pixels[i + 1] = static_cast<uint8_t>(color);
    }
    const size_t count =
        remaining < (sizeof(pixels) / 2) ? remaining : (sizeof(pixels) / 2);
    SPI.transfer(pixels, count * 2);
    remaining -= count;
  }
  digitalWrite(kCsPin, HIGH);
  SPI.endTransaction();
}

void Ili9341Display::fillScreen(uint16_t color) {
  fillRect(0, 0, kWidth, kHeight, color);
}

void Ili9341Display::showState(uint8_t stateMask, uint8_t confidence) {
  fillScreen(kNavy);
  constexpr uint16_t tileWidth = 50;
  constexpr uint16_t tileGap = 9;
  constexpr uint16_t tileTop = 44;
  constexpr uint16_t tileHeight = 150;
  for (uint8_t item = 0; item < 5; ++item) {
    const uint16_t x = 10 + item * (tileWidth + tileGap);
    const bool isOpen = (stateMask & (1U << item)) != 0;
    fillRect(x, tileTop, tileWidth, tileHeight,
             isOpen ? kGreen : kDarkGreen);
    fillRect(x + 5, tileTop + 5, tileWidth - 10, tileHeight - 10,
             isOpen ? kGreen : kBlack);
  }

  // Confidence meter on the right edge and a thin status strip at the bottom.
  const uint16_t meterHeight =
      static_cast<uint16_t>(constrain(confidence, 0, 100) * 190U / 100U);
  fillRect(305, 24, 10, 190, kBlack);
  if (meterHeight > 0) {
    fillRect(305, 214 - meterHeight, 10, meterHeight,
             confidence >= 70 ? kCyan : kYellow);
  }
  fillRect(10, 220, 285, 8, confidence >= 70 ? kBlue : kYellow);
}

void Ili9341Display::showActivity(uint8_t frame) {
  fillScreen(kNavy);
  const uint16_t requestedInset = static_cast<uint16_t>(frame) * 12U;
  const uint16_t inset = requestedInset < 96U ? requestedInset : 96U;
  const uint16_t width = kWidth - inset * 2U;
  const uint16_t height = kHeight - inset * 2U;
  if (width > 4 && height > 4) {
    fillRect(inset, inset, width, 4, kCyan);
    fillRect(inset, kHeight - inset - 4, width, 4, kCyan);
    fillRect(inset, inset, 4, height, kCyan);
    fillRect(kWidth - inset - 4, inset, 4, height, kCyan);
  }
}

void Ili9341Display::runSelfTest() {
  const uint16_t colors[] = {kRed, kGreen, kBlue, kWhite, kBlack};
  for (uint16_t color : colors) {
    fillScreen(color);
    delay(180);
  }
}
