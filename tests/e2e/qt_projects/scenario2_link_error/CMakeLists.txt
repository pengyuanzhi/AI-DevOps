cmake_minimum_required(VERSION 3.16)
project(Scenario2_LinkError VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(CMAKE_AUTOMOC ON)

find_package(Qt6 REQUIRED COMPONENTS Core)

add_executable(qt_app
    main.cpp
)

target_link_libraries(qt_app PRIVATE
    Qt6::Core
)

# ❌ 错误：没有链接包含 get_value() 定义的库或源文件
