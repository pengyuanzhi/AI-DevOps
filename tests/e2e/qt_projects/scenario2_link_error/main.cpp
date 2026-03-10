#include <QCoreApplication>
#include <QDebug>

// ❌ 错误：声明了函数但没有提供定义
extern int get_value();
extern double calculate_value(int x);

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);

    // 这会导致链接错误：undefined reference to `get_value()'
    int value = get_value();
    qDebug() << "Value:" << value;

    // 这也会导致链接错误：undefined reference to `calculate_value(int)'
    double result = calculate_value(value);
    qDebug() << "Result:" << result;

    return 0;
}

// ❌ 缺少 get_value() 和 calculate_value() 的实现
// 这会导致链接错误
