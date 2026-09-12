#include "ili9341_display.h"

#include <cstring>

namespace {

constexpr uint32_t kSpiClockHz = 20000000;
constexpr uint16_t kBlack = 0x0000;
constexpr uint16_t kNavy = 0x000F;
constexpr uint16_t kBlue = 0x001F;
constexpr uint16_t kCyan = 0x07FF;
constexpr uint16_t kGreen = 0x07E0;
constexpr uint16_t kDarkGreen = 0x03E0;
constexpr uint16_t kDarkRed = 0x7800;
constexpr uint16_t kOrange = 0xFD20;
constexpr uint16_t kDarkOrange = 0x7A80;
constexpr uint16_t kGrey = 0x8410;
constexpr uint16_t kYellow = 0xFFE0;
constexpr uint16_t kRed = 0xF800;
constexpr uint16_t kWhite = 0xFFFF;

// Exact 5x7 ASCII font used by the original IchiPing ILI9341 driver.
constexpr uint8_t kFont5x7[] = {
    0x00,0x00,0x00,0x00,0x00, 0x00,0x00,0x5F,0x00,0x00,
    0x00,0x07,0x00,0x07,0x00, 0x14,0x7F,0x14,0x7F,0x14,
    0x24,0x2A,0x7F,0x2A,0x12, 0x23,0x13,0x08,0x64,0x62,
    0x36,0x49,0x55,0x22,0x50, 0x00,0x05,0x03,0x00,0x00,
    0x00,0x1C,0x22,0x41,0x00, 0x00,0x41,0x22,0x1C,0x00,
    0x14,0x08,0x3E,0x08,0x14, 0x08,0x08,0x3E,0x08,0x08,
    0x00,0x50,0x30,0x00,0x00, 0x08,0x08,0x08,0x08,0x08,
    0x00,0x60,0x60,0x00,0x00, 0x20,0x10,0x08,0x04,0x02,
    0x3E,0x51,0x49,0x45,0x3E, 0x00,0x42,0x7F,0x40,0x00,
    0x42,0x61,0x51,0x49,0x46, 0x21,0x41,0x45,0x4B,0x31,
    0x18,0x14,0x12,0x7F,0x10, 0x27,0x45,0x45,0x45,0x39,
    0x3C,0x4A,0x49,0x49,0x30, 0x01,0x71,0x09,0x05,0x03,
    0x36,0x49,0x49,0x49,0x36, 0x06,0x49,0x49,0x29,0x1E,
    0x00,0x36,0x36,0x00,0x00, 0x00,0x56,0x36,0x00,0x00,
    0x08,0x14,0x22,0x41,0x00, 0x14,0x14,0x14,0x14,0x14,
    0x00,0x41,0x22,0x14,0x08, 0x02,0x01,0x51,0x09,0x06,
    0x32,0x49,0x79,0x41,0x3E, 0x7E,0x11,0x11,0x11,0x7E,
    0x7F,0x49,0x49,0x49,0x36, 0x3E,0x41,0x41,0x41,0x22,
    0x7F,0x41,0x41,0x22,0x1C, 0x7F,0x49,0x49,0x49,0x41,
    0x7F,0x09,0x09,0x09,0x01, 0x3E,0x41,0x49,0x49,0x7A,
    0x7F,0x08,0x08,0x08,0x7F, 0x00,0x41,0x7F,0x41,0x00,
    0x20,0x40,0x41,0x3F,0x01, 0x7F,0x08,0x14,0x22,0x41,
    0x7F,0x40,0x40,0x40,0x40, 0x7F,0x02,0x0C,0x02,0x7F,
    0x7F,0x04,0x08,0x10,0x7F, 0x3E,0x41,0x41,0x41,0x3E,
    0x7F,0x09,0x09,0x09,0x06, 0x3E,0x41,0x51,0x21,0x5E,
    0x7F,0x09,0x19,0x29,0x46, 0x46,0x49,0x49,0x49,0x31,
    0x01,0x01,0x7F,0x01,0x01, 0x3F,0x40,0x40,0x40,0x3F,
    0x1F,0x20,0x40,0x20,0x1F, 0x3F,0x40,0x38,0x40,0x3F,
    0x63,0x14,0x08,0x14,0x63, 0x07,0x08,0x70,0x08,0x07,
    0x61,0x51,0x49,0x45,0x43, 0x00,0x7F,0x41,0x41,0x00,
    0x02,0x04,0x08,0x10,0x20, 0x00,0x41,0x41,0x7F,0x00,
    0x04,0x02,0x01,0x02,0x04, 0x40,0x40,0x40,0x40,0x40,
    0x00,0x01,0x02,0x04,0x00, 0x20,0x54,0x54,0x54,0x78,
    0x7F,0x48,0x44,0x44,0x38, 0x38,0x44,0x44,0x44,0x20,
    0x38,0x44,0x44,0x48,0x7F, 0x38,0x54,0x54,0x54,0x18,
    0x08,0x7E,0x09,0x01,0x02, 0x0C,0x52,0x52,0x52,0x3E,
    0x7F,0x08,0x04,0x04,0x78, 0x00,0x44,0x7D,0x40,0x00,
    0x20,0x40,0x44,0x3D,0x00, 0x7F,0x10,0x28,0x44,0x00,
    0x00,0x41,0x7F,0x40,0x00, 0x7C,0x04,0x18,0x04,0x78,
    0x7C,0x08,0x04,0x04,0x78, 0x38,0x44,0x44,0x44,0x38,
    0x7C,0x14,0x14,0x14,0x08, 0x08,0x14,0x14,0x18,0x7C,
    0x7C,0x08,0x04,0x04,0x08, 0x48,0x54,0x54,0x54,0x20,
    0x04,0x3F,0x44,0x40,0x20, 0x3C,0x40,0x40,0x20,0x7C,
    0x1C,0x20,0x40,0x20,0x1C, 0x3C,0x40,0x30,0x40,0x3C,
    0x44,0x28,0x10,0x28,0x44, 0x0C,0x50,0x50,0x50,0x3C,
    0x44,0x64,0x54,0x4C,0x44, 0x00,0x08,0x36,0x41,0x00,
    0x00,0x00,0x7F,0x00,0x00, 0x00,0x41,0x36,0x08,0x00,
    0x08,0x08,0x2A,0x1C,0x08};

uint8_t classOf14(uint8_t state) {
  const uint8_t a = state & 1U;
  const uint8_t b = (state >> 1) & 1U;
  const uint8_t c = (state >> 2) & 1U;
  const uint8_t ab = (state >> 3) & 1U;
  const uint8_t bc = (state >> 4) & 1U;
  if (!ab) return a;
  if (!bc) return 2U + a + 2U * b;
  return 6U + a + 2U * b + 4U * c;
}

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
  const uint8_t memoryAccess[] = {0xE8};  // Original landscape-flip + BGR.
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
  invalidate();
  ensureFrame();
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

void Ili9341Display::drawChar(uint16_t x, uint16_t y, char value,
                              uint16_t foreground, uint16_t background,
                              uint8_t size) {
  // One address window, background and glyph pixels streamed together: the
  // cell never shows an intermediate "background only" frame.
  if (value < 0x20 || value > 0x7E) value = '?';
  if (size == 0) return;
  const uint16_t width = 6U * size;
  const uint16_t height = 7U * size;
  if (x + width > kWidth || y + height > kHeight) return;
  const uint8_t* glyph = &kFont5x7[(value - 0x20) * 5];
  setWindow(x, y, width, height);

  uint8_t pixels[128];
  size_t used = 0;
  SPI.beginTransaction(SPISettings(kSpiClockHz, MSBFIRST, SPI_MODE0));
  digitalWrite(kCsPin, LOW);
  digitalWrite(kDcPin, HIGH);
  for (uint16_t py = 0; py < height; ++py) {
    const uint8_t row = py / size;
    for (uint16_t px = 0; px < width; ++px) {
      const uint8_t column = px / size;
      const bool on = column < 5 && (glyph[column] & (1U << row));
      const uint16_t color = on ? foreground : background;
      pixels[used++] = static_cast<uint8_t>(color >> 8);
      pixels[used++] = static_cast<uint8_t>(color);
      if (used == sizeof(pixels)) {
        // ZephyrSPI::transfer overwrites the buffer with RX data; it is
        // refilled from scratch for the next chunk.
        SPI.transfer(pixels, used);
        used = 0;
      }
    }
  }
  if (used) SPI.transfer(pixels, used);
  digitalWrite(kCsPin, HIGH);
  SPI.endTransaction();
}

void Ili9341Display::drawString(uint16_t x, uint16_t y, const char* value,
                                uint16_t foreground, uint16_t background,
                                uint8_t size) {
  while (*value != '\0') {
    drawChar(x, y, *value++, foreground, background, size);
    x += 6U * size;
  }
}

void Ili9341Display::invalidate() {
  frameDrawn_ = false;
  for (auto& row : cells_) {
    for (auto& cell : row) cell = {0, 0};
  }
  statusValid_ = false;
}

void Ili9341Display::ensureFrame() {
  // The static layout is painted once (boot / after the self-test), never on
  // every state update, so switch changes do not blank the whole screen.
  if (frameDrawn_) return;
  fillScreen(kBlack);
  fillRect(0, 0, 320, 28, kNavy);
  drawString(6, 7, "IchiPing infer", kWhite, kNavy, 2);
  drawString(6, 50, "inf", kWhite, kBlack, 2);
  drawString(6, 110, "act", kWhite, kBlack, 2);
  frameDrawn_ = true;
  statusMessage_ = nullptr;  // fillScreen left the bar black
  statusValid_ = true;
}

void Ili9341Display::drawCell(uint8_t row, uint8_t column, char value,
                              uint16_t color) {
  Cell& cached = cells_[row][column];
  if (cached.value == value && cached.color == color) return;
  constexpr uint16_t digitX = 85;
  constexpr uint16_t rowY[2] = {40, 100};
  drawChar(digitX + column * 30U, rowY[row], value, color, kBlack, 5);
  cached = {value, color};
}

void Ili9341Display::drawDigits(uint8_t actualMask, bool actualValid,
                                bool predictionValid, uint8_t predictedMask) {
  ensureFrame();
  constexpr uint8_t order[5] = {2, 4, 1, 3, 0};  // c, BC, b, AB, a.
  for (uint8_t column = 0; column < 5; ++column) {
    const uint8_t bit = order[column];
    const bool actual = (actualMask & (1U << bit)) != 0;
    const bool observable = actualValid && (bit == 0 || bit == 3 ||
        ((actualMask & (1U << 3)) && (bit == 1 || bit == 4)) ||
        ((actualMask & (1U << 3)) && (actualMask & (1U << 4)) && bit == 2));
    if (predictionValid) {
      const bool predicted = (predictedMask & (1U << bit)) != 0;
      const bool correct = predicted == actual;
      const uint16_t color = correct ? (observable ? kGreen : kDarkGreen)
                                     : (observable ? kRed : kDarkRed);
      drawCell(0, column, predicted ? '1' : '0', color);
    } else {
      drawCell(0, column, '-', kGrey);
    }
    drawCell(1, column, actualValid ? (actual ? '1' : '0') : '-',
             actualValid ? (observable ? kOrange : kDarkOrange) : kGrey);
  }
}

void Ili9341Display::drawStatus(const char* message, uint16_t foreground,
                                uint16_t background) {
  if (statusValid_ && statusMessage_ == message &&
      (message == nullptr ||
       (statusForeground_ == foreground && statusBackground_ == background))) {
    return;
  }
  constexpr uint16_t barX = 4, barY = 175, barWidth = 312, barHeight = 46;
  constexpr uint16_t textY = 191;
  constexpr uint8_t scale = 2;
  if (message == nullptr) {
    fillRect(barX, barY, barWidth, barHeight, kBlack);
  } else {
    // "Procedural sprite": the whole bar (background + scaled glyphs) is
    // generated pixel by pixel into ONE address window and streamed in one
    // SPI burst, so the old bar is replaced without any intermediate frame
    // and without a 28 KB off-screen buffer.
    const size_t length = strlen(message);
    const uint16_t textWidth = length * 6U * scale;
    const uint16_t textX = barX + (barWidth - textWidth) / 2U;
    setWindow(barX, barY, barWidth, barHeight);
    uint8_t pixels[128];
    size_t used = 0;
    SPI.beginTransaction(SPISettings(kSpiClockHz, MSBFIRST, SPI_MODE0));
    digitalWrite(kCsPin, LOW);
    digitalWrite(kDcPin, HIGH);
    for (uint16_t y = barY; y < barY + barHeight; ++y) {
      const int16_t glyphRow = (static_cast<int16_t>(y) - textY) / scale;
      const bool inTextRows = y >= textY && glyphRow < 7;
      for (uint16_t x = barX; x < barX + barWidth; ++x) {
        bool on = false;
        if (inTextRows && x >= textX && x < textX + textWidth) {
          const uint16_t offset = (x - textX) / scale;   // in font columns
          const uint16_t index = offset / 6U;
          const uint8_t column = offset % 6U;
          char value = message[index];
          if (value < 0x20 || value > 0x7E) value = '?';
          on = column < 5 && (kFont5x7[(value - 0x20) * 5 + column] & (1U << glyphRow));
        }
        const uint16_t color = on ? foreground : background;
        pixels[used++] = static_cast<uint8_t>(color >> 8);
        pixels[used++] = static_cast<uint8_t>(color);
        if (used == sizeof(pixels)) {
          SPI.transfer(pixels, used);  // RX overwrites the chunk; refilled next
          used = 0;
        }
      }
    }
    if (used) SPI.transfer(pixels, used);
    digitalWrite(kCsPin, HIGH);
    SPI.endTransaction();
  }
  statusMessage_ = message;
  statusForeground_ = foreground;
  statusBackground_ = background;
  statusValid_ = true;
}

void Ili9341Display::showState(uint8_t actualMask, bool actualValid,
                               bool predictionValid, uint8_t predictedMask) {
  drawDigits(actualMask, actualValid, predictionValid, predictedMask);
  if (!predictionValid) {
    drawStatus(nullptr, kWhite, kBlack);
    return;
  }
  if (predictedMask == actualMask) {
    drawStatus("Complete Success", kWhite, kBlue);
  } else if (classOf14(predictedMask) == classOf14(actualMask)) {
    drawStatus("Conditional Success", kWhite, kGreen);
  } else {
    drawStatus("Failure", kWhite, kRed);
  }
}

void Ili9341Display::showUnavailable(uint8_t actualMask, bool actualValid) {
  showRuntimeStatus(actualMask, actualValid, 1);
}

void Ili9341Display::showRuntimeStatus(uint8_t actualMask, bool actualValid,
                                      uint8_t statusCode) {
  // Digits first, then the runtime message directly (no cleared bar between).
  drawDigits(actualMask, actualValid, false, 0);
  const char* message = "Runtime error";
  uint16_t background = kRed;
  uint16_t foreground = kWhite;
  switch (statusCode) {
    case 1: message = "Audio not ready"; background = kYellow; foreground = kBlack; break;
    case 2: message = "Close all first"; background = kYellow; foreground = kBlack; break;
    case 3: message = "Calibrating..."; background = kCyan; foreground = kBlack; break;
    case 4: message = "Listening..."; background = kCyan; foreground = kBlack; break;
    case 5: message = "Capture error"; break;
    case 6: message = "Model error"; break;
    case 7: message = "Baseline ready"; background = kGreen; foreground = kBlack; break;
    case 8: message = "State changed"; background = kYellow; foreground = kBlack; break;
    case 9: message = "Servo not synced"; background = kYellow; foreground = kBlack; break;
  }
  drawStatus(message, foreground, background);
}

void Ili9341Display::runSelfTest() {
  const uint16_t colors[] = {kRed, kGreen, kBlue, kWhite, kBlack};
  for (uint16_t color : colors) {
    fillScreen(color);
    delay(180);
  }
  invalidate();  // the next showState repaints the frame and every cell
}
