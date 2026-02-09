cmake_minimum_required(VERSION 3.20)
project(Chronos_HFT VERSION 0.1.0 LANGUAGES CXX)

# Modern C++ Standards
set(CMAKE_CXX_STANDARD 20)

# COVERAGE FLAGS(Debug Mode Only)
if(CMAKE_BUILD_TYPE MATCHES Debug)
    add_compile_options(--coverage -O0)
    add_link_options(--coverage)
endif()

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

# STATIC ANALYSIS (CppCheck) ---
# Check if cppcheck is installed
find_program(CPPCHECK_PATH cppcheck)

if(CPPCHECK_PATH)
    message(STATUS "CppCheck found: ${CPPCHECK_PATH}")
    # Enable static analysis for the next target
    set(CMAKE_CXX_CPPCHECK
            "${CPPCHECK_PATH}"
            "--enable=warning,performance,portability"
            "--suppress=missingIncludeSystem"
            "--inconclusive"
    )
else()
    message(WARNING "CppCheck not found! Static analysis disabled.")
endif()

# Main Executable
add_executable(chronos_engine src/main.cpp
        tests/test_main.cpp
        tests/test_main.h)
# MICROSERVICES LIB (ZeroMQ) ---
find_package(PkgConfig REQUIRED)
pkg_check_modules(ZMQ REQUIRED libzmq)

target_include_directories(chronos_engine PRIVATE ${ZMQ_INCLUDE_DIRS})
target_link_libraries(chronos_engine PRIVATE ${ZMQ_LIBRARIES})

#Testing Module
enable_testing()
add_subdirectory(tests)
