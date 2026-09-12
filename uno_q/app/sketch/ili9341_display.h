#pragma once

#include <Arduino.h>
#include <SPI.h>

class Ili9341Display {
 public:
  bool begin();
  void showState(uint8_t actualMask, bool actualValid, bool predictionValid,
                 uint8_t predictedMask);
  void showUnavailable(uint8_t actualMask, bool actualValid);
  void showRuntimeStatus(uint8_t actualMask, bool actualValid,
                         uint8_t statusCode);
  void runSelfTest();

 private:
  // Keep the original FRDM-MCXN947 IchiPing shield wiring so the shield can
  // be moved to the UNO Q without changing its traces or jumpers.
  static constexpr uint8_t kCsPin = A2;
  static constexpr uint8_t kResetPin = A3;
  static constexpr uint8_t kDcPin = A4;
  static constexpr uint8_t kBacklightPin = A5;
  static constexpr uint16_t kWidth = 320;
  static constexpr uint16_t kHeight = 240;

  // Flicker-free updates: the static frame is drawn once, and only digit
  // cells / the status bar whose content or colour changed are redrawn.
  struct Cell {
    char value;
    uint16_t color;
  };
  bool frameDrawn_ = false;
  Cell cells_[2][5] = {};              // [0] = inf row, [1] = act row
  const char* statusMessage_ = nullptr;  // nullptr = bar cleared (black)
  uint16_t statusForeground_ = 0;
  uint16_t statusBackground_ = 0;
  bool statusValid_ = false;

  void reset();
  void command(uint8_t value, const uint8_t* data = nullptr, size_t size = 0);
  void setWindow(uint16_t x, uint16_t y, uint16_t width, uint16_t height);
  void fillRect(uint16_t x, uint16_t y, uint16_t width, uint16_t height,
                uint16_t color);
  void fillScreen(uint16_t color);
  void drawChar(uint16_t x, uint16_t y, char value, uint16_t foreground,
                uint16_t background, uint8_t size);
  void drawString(uint16_t x, uint16_t y, const char* value,
                  uint16_t foreground, uint16_t background, uint8_t size);
  void invalidate();
  void ensureFrame();
  void drawDigits(uint8_t actualMask, bool actualValid, bool predictionValid,
                  uint8_t predictedMask);
  void drawCell(uint8_t row, uint8_t column, char value, uint16_t color);
  void drawStatus(const char* message, uint16_t foreground, uint16_t background);
};
