#pragma once

#include <cstdint>
#include <array>
#include <cstddef>
#include <chronos/strong_type.hpp>

namespace chronos {

enum class OrderSide : uint8_t {
    Buy = 0,
    Sell = 1
};

enum class OrderStatus : uint8_t {
    New = 0,
    Partial = 1,
    Filled = 2,
    Canceled = 3,
    Rejected = 4
};

/**
 * @brief Strong type definitions for core identifiers.
 */
using OrderId = StrongType<uint64_t, struct OrderIdTag>;
using Price = StrongType<int64_t, struct PriceTag>;
using Quantity = StrongType<int64_t, struct QuantityTag>;

/**
 * @brief Core Order structure, aligned to 64-byte cache line.
 */
struct alignas(64) Order {
    OrderId id;              // 8 bytes
    std::array<char, 8> symbol; // 8 bytes
    Price price;             // 8 bytes
    Quantity quantity;       // 8 bytes
    OrderSide side;          // 1 byte
    OrderStatus status;      // 1 byte
    uint64_t timestamp;      // 8 bytes (nanoseconds)
    
    // Explicit padding to make the struct 64 bytes.
    // offsets: id(0), symbol(8), price(16), quantity(24), side(32), status(33)
    // timestamp(needs 8-byte align) -> offset 40, size 8 -> ends at 48.
    // 64 - 48 = 16 bytes padding.
    std::byte padding[16];
};

/**
 * @brief Trade execution structure, aligned to 64-byte cache line.
 */
struct alignas(64) Trade {
    OrderId buy_order_id;    // 8 bytes
    OrderId sell_order_id;   // 8 bytes
    Price price;             // 8 bytes
    Quantity quantity;       // 8 bytes
    uint64_t timestamp;      // 8 bytes
    
    // Remaining: 64 - (8*5) = 64 - 40 = 24 bytes.
    std::byte padding[24];
};

} // namespace chronos
