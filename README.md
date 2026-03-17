# Chronos HFT Engine

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![C++](https://img.shields.io/badge/C%2B%2B-20-blue.svg)
![Build Status](https://github.com/GuangzuW/Chronos_High_Frequency_Trading_Engine/actions/workflows/ci.yml/badge.svg)

Chronos is an ultra-low-latency **Limit Order Book (LOB)** matching engine designed for high-frequency trading (HFT) environments. Built with **modern C++20**, it prioritizes deterministic execution, zero-allocation on the hot path, and seamless integration with AI-driven risk validation.

## 🚀 Key Features

-   **High-Performance Matching**: FIFO price-time priority engine with a matching latency baseline of **~286ns per order**.
-   **Zero-Allocation Hot Path**: Utilizes `std::pmr::monotonic_buffer_resource` and custom memory pools to eliminate runtime allocations during trading.
-   **AI Risk Engine**: Integrated **ONNX Runtime** for pre-trade risk scoring and real-time fraud detection.
-   **Horizontal Scaling**: **Symbol Sharding** architecture allows distributing order books across multiple cores/instances.
-   **Microservices Architecture**: Low-latency communication via **ZeroMQ** (ROUTER/DEALER for ingress, PUB/SUB for events).
-   **Deterministic Threading**: Built-in support for **CPU Pinning** and real-time thread isolation.
-   **Auditability**: Asynchronous background logging for non-blocking persistence of all trades and order updates.

## 🛠 Tech Stack

-   **Language**: C++20 (utilizing `std::span`, `std::pmr`, `StrongType` wrappers).
-   **Messaging**: ZeroMQ (libzmq).
-   **AI Inference**: ONNX Runtime.
-   **Build System**: CMake (with CppCheck static analysis).
-   **Testing**: Google Test (GTest).
-   **Containerization**: Docker (multi-stage builds).

## 📥 Setup & Installation

### Prerequisites

-   **Compiler**: GCC 13+ or Clang 16+ (C++20 support required).
-   **Build Tools**: CMake 3.20+ and Ninja/Make.
-   **Dependencies**: 
    -   `libzmq3-dev` (ZeroMQ)
    -   `onnxruntime` (Optional, for AI features)

#### On Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install -y cmake ninja-build libzmq3-dev
```

### Building the Project

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/GuangzuW/Chronos_High_Frequency_Trading_Engine.git
    cd Chronos_High_Frequency_Trading_Engine
    ```

2.  **Configure and Build (Release)**:
    ```bash
    cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
    cmake --build build
    ```

### Running the Engine

Start the matching engine service:
```bash
./build/chronos_engine
```
The gateway will listen on port `5555` for orders and publish events on port `5556`.

### Running Tests & Benchmarks

Execute the unit tests and performance benchmarks:
```bash
cd build
ctest --output-on-failure
```

## 🐳 Docker Deployment

Build the optimized production image:
```bash
docker build -t chronos-hft .
```

Run the container with CPU pinning permissions:
```bash
docker run --rm --cap-add=SYS_NICE --cpuset-cpus="1" chronos-hft
```

## 📈 Performance Baseline

Measured on `linux-x64`:
-   **Matching Core**: ~286 ns / match.
-   **Order Entry (End-to-End)**: < 1.5 μs (incl. Risk Checks).

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
