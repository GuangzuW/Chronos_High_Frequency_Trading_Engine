#pragma once

#include <chrono>
#include <string>
#include <iostream>

namespace chronos {

/**
 * @brief Simple RAII nanosecond latency logger.
 */
class LatencyLogger {
public:
    explicit LatencyLogger(const std::string& name)
        : name_(name), start_(std::chrono::high_resolution_clock::now()) {}

    ~LatencyLogger() {
        auto end = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start_).count();
        std::cout << "[Latency] " << name_ << ": " << duration << " ns\n";
    }

private:
    std::string name_;
    std::chrono::time_point<std::chrono::high_resolution_clock> start_;
};

} // namespace chronos
