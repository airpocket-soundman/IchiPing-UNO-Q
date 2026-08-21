#pragma once

#include <Arduino.h>
#include <SPI.h>

class Ili9341Display {
 public:
  bool begin();
  void showState(uint8_t stateMask, uint8_t confidence);
  void showActivity(uint8_t frame);
  void runSelfTest();

 private:
  static constexpr uint8_t kCsPin = D10;
  static constexpr uint8_t kResetPin = A0;
  static constexpr uint8_t kDcPin = A1;
  static constexpr uint8_t kBacklightPin = A2;
  static constexpr uint16_t kWidth = 320;
  static constexpr uint16_t kHeight = 240;

  void reset();
  void command(uint8_t value, const uint8_t* data = nullptr, size_t size = 0);
  void setWindow(uint16_t x, uint16_t y, uint16_t width, uint16_t height);
  void fillRect(uint16_t x, uint16_t y, uint16_t width, uint16_t height,
                uint16_t color);
  void fillScreen(uint16_t color);
};
