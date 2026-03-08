cmake_minimum_required(VERSION 3.16)
project(Calculator VERSION 1.0 LANGUAGES CXX)

# C++ 标准
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 启用测试
enable_testing()

# 包含目录
include_directories(${CMAKE_SOURCE_DIR}/include)

# 计算器库
add_library(calculator
    src/calculator.cpp
)

target_include_directories(calculator
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

# Google Test
find_package(GTest REQUIRED)
include_directories(${GTEST_INCLUDE_DIRS})

# 示例可执行文件（可选）
add_executable(calculator_app
    examples/main.cpp
)

target_link_libraries(calculator_app
    PRIVATE
        calculator
)

# 测试
add_executable(test_calculator
    tests/test_calculator.cpp
)

target_link_libraries(test_calculator
    PRIVATE
        calculator
        gtest
        gmock
        gtest_main
)

discover_tests(test_calculator)
