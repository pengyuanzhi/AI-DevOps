#include <QtTest/QtTest>
#include "../calculator.h"

class CalculatorTest : public QObject
{
    Q_OBJECT

private slots:
    void testAddition();
    void testSubtraction();
    void testMultiplication();
    void testDivision();
    void testDivisionByZero();
};

void CalculatorTest::testAddition()
{
    Calculator calc;
    double result = calc.add(2, 3);

    // ❌ 错误：期望值不正确
    // 2 + 3 = 5，但测试期望是 6
    QCOMPARE(result, 6.0);  // 这会导致测试失败
}

void CalculatorTest::testSubtraction()
{
    Calculator calc;
    double result = calc.subtract(10, 4);

    // ❌ 错误：期望值不正确
    // 10 - 4 = 6，但测试期望是 7
    QCOMPARE(result, 7.0);  // 这会导致测试失败
}

void CalculatorTest::testMultiplication()
{
    Calculator calc;
    QCOMPARE(calc.multiply(6, 7), 42.0);  // ✅ 正确
}

void CalculatorTest::testDivision()
{
    Calculator calc;
    QCOMPARE(calc.divide(20, 4), 5.0);  // ✅ 正确
}

void CalculatorTest::testDivisionByZero()
{
    Calculator calc;
    QCOMPARE(calc.divide(10, 0), 0.0);  // ✅ 正确
}

QTEST_MAIN(CalculatorTest)
#include "tst_calculator.moc"
