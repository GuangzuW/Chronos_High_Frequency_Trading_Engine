add_executable(unit_tests test_main.cpp)
target_link_libraries(unit_tests GTest::gtest_main)
add_test(NAME CoreLogicTest COMMAND unit_tests)