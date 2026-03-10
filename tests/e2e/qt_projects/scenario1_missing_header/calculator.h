#ifndef CALCULATOR_H
#define CALCULATOR_H

#include <QObject>

class Calculator : public QObject
{
    Q_OBJECT

public:
    explicit Calculator(QObject *parent = nullptr);

    double add(double a, double b);
    double subtract(double a, double b);
    double multiply(double a, double b);
    double divide(double a, double b);

signals:
    void calculationStarted(const QString &operation);
    void calculationFinished(const QString &operation, double result);
};

#endif // CALCULATOR_H
