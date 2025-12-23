cmake_minimum_required(VERSION 3.20)
project(Chronos_HFT VERSION 0.1.0 LANGUAGES CXX)

# Modern C++ Standards
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Compile Warnings
if(MSVC)
    add_compile_options(/W4 /WX)
else()
    add_compile_options(-Wall -Wextra -Wpedantic -Werror)
endif()

# Dependencies
include(FetchContent)

# Google test for Unit Testing
FetchContent_Declare(
    googletest
    URL https://github.com/google/googletest/archive/refs/tags/v1.14.0.zip
)
FetchContent_MakeAvailable(googletest)

# Main Executable
add_executable(chronos_engine src/main.cpp
        tests/test_main.cpp
        tests/test_main.h)

#Testing Module
enable_testing()
add_subdirectory(tests)