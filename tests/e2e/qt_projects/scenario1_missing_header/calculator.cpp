#include "calculator.h"
#include "math_utils.h"  // ❌ 错误：这个文件不存在
#include <QDebug>

Calculator::Calculator(QObject *parent)
    : QObject(parent)
{
}

double Calculator::add(double a, double b)
{
    emit calculationStarted("add");
    double result = MathUtils::add(a, b);  // ❌ 错误：MathUtils未定义
    emit calculationFinished("add", result);
    return result;
}

double Calculator::subtract(double a, double b)
{
    emit calculationStarted("subtract");
    double result = a - b;
    emit calculationFinished("subtract", result);
    return result;
}

double Calculator::multiply(double a, double b)
{
    emit calculationStarted("multiply");
    double result = a * b;
    emit calculationFinished("multiply", result);
    return result;
}

double Calculator::divide(double a, double b)
{
    emit calculationStarted("divide");
    if (b == 0.0) {
        qWarning() << "Division by zero!";
        return 0.0;
    }
    double result = a / b;
    emit calculationFinished("divide", result);
    return result;
}
