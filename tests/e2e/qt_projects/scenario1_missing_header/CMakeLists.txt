cmake_minimum_required(VERSION 3.16)
project(Scenario1_Calculator VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

# 查找Qt6
find_package(Qt6 REQUIRED COMPONENTS Core Widgets Test)

# 源文件
set(SOURCES
    main.cpp
    calculator.cpp
)

set(HEADERS
    calculator.h
)

# 创建可执行文件
add_executable(calculator ${SOURCES} ${HEADERS})

# 链接Qt库
target_link_libraries(calculator PRIVATE
    Qt6::Core
    Qt6::Widgets
)

# 启用测试
enable_testing()
add_subdirectory(tests)
