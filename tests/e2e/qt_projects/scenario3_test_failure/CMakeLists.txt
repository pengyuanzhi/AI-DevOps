cmake_minimum_required(VERSION 3.16)
project(Scenario3_TestFailure VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(CMAKE_AUTOMOC ON)

find_package(Qt6 REQUIRED COMPONENTS Core Widgets Test)

# 主程序
add_executable(qt_test_app
    calculator.cpp
    main.cpp
)

target_link_libraries(qt_test_app PRIVATE
    Qt6::Core
    Qt6::Widgets
)

# 测试
enable_testing()
add_subdirectory(tests)
