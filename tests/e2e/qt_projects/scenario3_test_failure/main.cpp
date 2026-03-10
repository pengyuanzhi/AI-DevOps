#include <QCoreApplication>
#include "calculator.h"

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);

    Calculator calc;
    // 正常使用
    double sum = calc.add(5, 3);

    return 0;
}
