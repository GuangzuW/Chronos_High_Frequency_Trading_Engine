#pragma once

#include <memory_resource>
#include <vector>
#include <cstddef>

namespace chronos {

/**
 * @brief Memory pool manager using std::pmr::monotonic_buffer_resource.
 * 
 * Provides fast, pre-allocated memory for core structures and containers 
 * to ensure zero allocations on the hot path.
 */
class MemoryPool {
public:
    /**
     * @brief Initialize the memory pool with a fixed pre-allocated size.
     * @param initial_size_bytes Total bytes to pre-allocate (default 100MB).
     */
    explicit MemoryPool(std::size_t initial_size_bytes = 100 * 1024 * 1024)
        : buffer_(initial_size_bytes),
          pool_resource_(buffer_.data(), buffer_.size(), std::pmr::null_memory_resource()) {
        // null_memory_resource() ensures it will throw std::bad_alloc if it exceeds initial size,
        // rather than using the default (global) resource, which is what we want for HFT 
        // to detect sizing issues early and avoid unexpected mallocs.
    }

    /**
     * @brief Get the underlying PMR memory resource.
     * Use this with PMR-compatible containers like std::pmr::vector<Order>.
     */
    std::pmr::memory_resource* get_resource() {
        return &pool_resource_;
    }

    /**
     * @brief Allocate memory for a specific type.
     * @tparam T The type to allocate.
     * @return T* Pointer to the allocated memory.
     */
    template <typename T>
    T* allocate() {
        void* ptr = pool_resource_.allocate(sizeof(T), alignof(T));
        return static_cast<T*>(ptr);
    }

    /**
     * @brief Return the total size of the buffer.
     */
    std::size_t size() const {
        return buffer_.size();
    }

private:
    std::vector<std::byte> buffer_; // Pre-allocated block
    std::pmr::monotonic_buffer_resource pool_resource_;
};

} // namespace chronos
