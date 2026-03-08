# C++ Calculator 示例项目

这是一个用于演示 AI-CICD 系统的简单 C++ 计算器项目。

## 项目结构

```
cpp-calculator/
├── CMakeLists.txt       # CMake 配置
├── include/             # 头文件
│   └── calculator.h     # 计算器类声明
├── src/                 # 源文件
│   └── calculator.cpp   # 计算器类实现
├── tests/               # 测试文件
│   └── test_calculator.cpp  # 单元测试（由 AI-CICD 生成）
└── README.md            # 本文件
```

## 功能

Calculator 类提供以下功能：

- `add(a, b)` - 加法
- `subtract(a, b)` - 减法
- `multiply(a, b)` - 乘法
- `divide(a, b)` - 除法（除零时抛出异常）
- `power(base, exponent)` - 幂运算
- `getLastResult()` - 获取最后一次计算结果

## 构建和测试

### 使用 CMake 构建

```bash
mkdir build
cd build
cmake ..
make
```

### 运行测试

```bash
cd build
ctest --output-on-failure
```

或直接运行测试可执行文件：

```bash
./test_calculator
```

## AI-CICD 集成

这个项目可以用于测试 AI-CICD 的以下功能：

1. **C++ 代码解析** - 分析类、方法、参数
2. **测试生成** - 自动生成 Google Test 测试用例
3. **代码审查** - 使用 clang-tidy/cppcheck 进行静态分析
4. **CMake 集成** - 自动更新 CMakeLists.txt

## 技术栈

- **C++ 标准**: C++17
- **构建系统**: CMake 3.16+
- **测试框架**: Google Test (gtest)
- **CI/CD**: GitLab CI

## 示例测试用例（预期输出）

AI-CICD 应该能够生成类似以下的测试代码：

```cpp
TEST_F(CalculatorTest, AddTwoPositiveNumbers_ReturnsCorrectSum) {
    Calculator calc;
    EXPECT_DOUBLE_EQ(calc.add(2.0, 3.0), 5.0);
}

TEST_F(CalculatorTest, DivideByZero_ThrowsInvalidArgument) {
    Calculator calc;
    EXPECT_THROW(calc.divide(10.0, 0.0), std::invalid_argument);
}

TEST_F(CalculatorTest, PowerWithZeroExponent_ReturnsOne) {
    Calculator calc;
    EXPECT_DOUBLE_EQ(calc.power(5.0, 0.0), 1.0);
}
```

## 贡献

这是一个示例项目，用于展示 AI-CICD 的功能。欢迎提交问题和建议。
