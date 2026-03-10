#include <QCoreApplication>
#include <QDebug>
#include "calculator.h"

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);

    Calculator calc;
    qDebug() << "2 + 3 =" << calc.add(2, 3);
    qDebug() << "10 - 4 =" << calc.subtract(10, 4);
    qDebug() << "6 * 7 =" << calc.multiply(6, 7);
    qDebug() << "20 / 4 =" << calc.divide(20, 4);

    return 0;
}
