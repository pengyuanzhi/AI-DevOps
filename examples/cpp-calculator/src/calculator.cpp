#include "calculator.h"
#include <cmath>
#include <stdexcept>

Calculator::Calculator() : lastResult(0.0) {}

Calculator::~Calculator() = default;

double Calculator::add(double a, double b) {
    lastResult = a + b;
    return lastResult;
}

double Calculator::subtract(double a, double b) {
    lastResult = a - b;
    return lastResult;
}

double Calculator::multiply(double a, double b) {
    lastResult = a * b;
    return lastResult;
}

double Calculator::divide(double a, double b) {
    if (b == 0.0) {
        throw std::invalid_argument("Division by zero is not allowed");
    }
    lastResult = a / b;
    return lastResult;
}

double Calculator::power(double base, double exponent) {
    lastResult = std::pow(base, exponent);
    return lastResult;
}

double Calculator::getLastResult() const {
    return lastResult;
}
