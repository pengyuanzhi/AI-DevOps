add_executable(tst_calculator
    tst_calculator.cpp
    ../calculator.cpp
)

target_link_libraries(tst_calculator PRIVATE
    Qt6::Core
    Qt6::Widgets
    Qt6::Test
)

add_test(NAME CalculatorTest COMMAND tst_calculator)
