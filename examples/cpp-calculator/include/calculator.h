#ifndef CALCULATOR_H
#define CALCULATOR_H

/**
 * @brief 简单的计算器类
 *
 * 提供基本的算术运算功能
 */
class Calculator {
public:
    Calculator();
    ~Calculator();

    /**
     * @brief 加法运算
     * @param a 第一个操作数
     * @param b 第二个操作数
     * @return 两数之和
     */
    double add(double a, double b);

    /**
     * @brief 减法运算
     * @param a 被减数
     * @param b 减数
     * @return 两数之差
     */
    double subtract(double a, double b);

    /**
     * @brief 乘法运算
     * @param a 第一个因数
     * @param b 第二个因数
     * @return 两数之积
     */
    double multiply(double a, double b);

    /**
     * @brief 除法运算
     * @param a 被除数
     * @param b 除数
     * @return 两数之商
     * @throws std::invalid_argument 如果除数为零
     */
    double divide(double a, double b);

    /**
     * @brief 幂运算
     * @param base 底数
     * @param exponent 指数
     * @return base 的 exponent 次幂
     */
    double power(double base, double exponent);

    /**
     * @brief 获取最后一次计算结果
     * @return 最后一次计算结果
     */
    double getLastResult() const;

private:
    double lastResult;
};

#endif // CALCULATOR_H
