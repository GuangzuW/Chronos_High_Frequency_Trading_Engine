# Implementation Plan: Task 3.2 - ONNX Runtime Integration

Integrate ONNX Runtime into the Chronos HFT Engine to enable real-time, pre-trade risk validation using machine learning models.

## Objective
Implement a `RiskEngine` that uses an ONNX model to score incoming orders for potential risk (e.g., fraud, market manipulation). The engine will run inference on a pre-trained model and return a risk score.

## Key Files & Context
- `include/chronos/risk_engine.hpp`: New header for the `RiskEngine` class.
- `src/risk/risk_engine.cpp`: Implementation of the risk scoring logic.
- `CMakeLists.txt`: Add ONNX Runtime dependency.
- `models/risk_model.onnx`: Placeholder for the risk model.

## Implementation Steps

### 1. Update `CMakeLists.txt`
Add ONNX Runtime to the project. Since it's a large dependency, I'll attempt to find it via `find_package` or provide instructions on how to install it. If I use `FetchContent`, it might take a long time to build.

Alternative: Assume the user will provide the ONNX Runtime library path or install it via a package manager. I'll add a section to `CMakeLists.txt` that looks for `onnxruntime`.

### 2. Create `include/chronos/risk_engine.hpp`
Define the `RiskEngine` class:
- Member variables:
    - `Ort::Env env_`: ONNX Runtime environment.
    - `Ort::Session session_`: Inference session.
    - `std::vector<const char*> input_names_`, `output_names_`: Model input/output names.
- Methods:
    - `explicit RiskEngine(const std::string& model_path)`: Constructor to load the model.
    - `float validateOrder(const Order& order)`: Map `Order` fields to model inputs, run inference, and return the score.

### 3. Implement `src/risk/risk_engine.cpp`
- Load the ONNX model from the specified path.
- Implement the `Order` to `Tensor` mapping: Convert fields like `price`, `quantity`, and `side` into floating-point features for the model.
- Execute the session and extract the output score.

### 4. Create `tests/test_risk_engine.cpp`
- Test 1: Load a mock ONNX model (or use a tiny one) and verify that the `RiskEngine` can initialize.
- Test 2: Verify that `validateOrder` returns a score within the expected range.
- Mocking: If ONNX Runtime is not available during testing, I'll use a mock/stub for the risk engine.

## Verification & Testing
1.  Run `cmake --build build`.
2.  Run `cd build && ctest --output-on-failure`.
3.  Ensure that `RiskEngineTest` passes.
