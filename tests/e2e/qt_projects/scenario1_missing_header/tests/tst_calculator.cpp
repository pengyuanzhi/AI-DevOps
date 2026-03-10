#include <QtTest/QtTest>
#include "../calculator.h"

class TestCalculator : public QObject
{
    Q_OBJECT

private slots:
    void testAddition();
    void testSubtraction();
    void testMultiplication();
    void testDivision();
    void testDivisionByZero();
};

void TestCalculator::testAddition()
{
    Calculator calc;
    QCOMPARE(calc.add(2, 3), 5.0);
}

void TestCalculator::testSubtraction()
{
    Calculator calc;
    QCOMPARE(calc.subtract(10, 4), 6.0);
}

void TestCalculator::testMultiplication()
{
    Calculator calc;
    QCOMPARE(calc.multiply(6, 7), 42.0);
}

void TestCalculator::testDivision()
{
    Calculator calc;
    QCOMPARE(calc.divide(20, 4), 5.0);
}

void TestCalculator::testDivisionByZero()
{
    Calculator calc;
    QCOMPARE(calc.divide(10, 0), 0.0);
}

QTEST_MAIN(TestCalculator)
#include "tst_calculator.moc"
