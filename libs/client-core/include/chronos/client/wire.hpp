#pragma once

// chronos-client-core :: wire codec
//
// The single, portable implementation of the Chronos 64-byte on-wire format defined in
// contracts/WIRE_FORMAT.md. This replaces the hand-synced Python struct format strings in
// bridge/decoder.py and the fixed-point scaling duplicated across the bridge and dashboard.
//
// Design notes:
//  * Explicit little-endian byte packing — does NOT rely on host endianness or struct
//    padding/alignment, so the exact same bytes are produced on every client platform
//    (Android arm64, iOS/macOS arm64+x86_64, Windows x86_64) and the Linux engine.
//  * Header-only and dependency-free (no engine headers, no ZMQ) so it can be bound to
//    React Native via JSI on all four platforms.
//  * Layout is locked by a golden-bytes test (tests/test_wire_codec.cpp). Reordering any
//    field changes the emitted bytes and fails the test — the contract is enforced, not
//    merely documented.

#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <string>
#include <string_view>

namespace chronos::client::wire {

inline constexpr std::size_t kMessageSize = 64;
inline constexpr std::size_t kSymbolSize = 8;

// Fixed-point scaling — the single definition of the convention (see WIRE_FORMAT.md / types.proto).
inline constexpr std::int64_t kPriceScale = 100;     // 2 decimal places
inline constexpr std::int64_t kQuantityScale = 1000; // 3 decimal places

using Buffer = std::array<std::uint8_t, kMessageSize>;

// Native engine wire values (uint8_t), per WIRE_FORMAT.md.
enum class Side : std::uint8_t { Buy = 0, Sell = 1 };
enum class Status : std::uint8_t { New = 0, Partial = 1, Filled = 2, Canceled = 3, Rejected = 4 };

struct Order {
    std::uint64_t id{};
    std::array<char, kSymbolSize> symbol{}; // ASCII, NUL-padded
    std::int64_t price{};                   // fixed-point, scaled by kPriceScale
    std::int64_t quantity{};                // fixed-point, scaled by kQuantityScale
    Side side{Side::Buy};
    Status status{Status::New};
    std::uint64_t timestamp_ns{};

    friend bool operator==(const Order&, const Order&) = default;
};

struct Trade {
    std::uint64_t buy_order_id{};
    std::uint64_t sell_order_id{};
    std::int64_t price{};
    std::int64_t quantity{};
    std::uint64_t timestamp_ns{};

    friend bool operator==(const Trade&, const Trade&) = default;
};

namespace detail {

inline void putU64(Buffer& b, std::size_t off, std::uint64_t v) {
    for (std::size_t i = 0; i < 8; ++i) {
        b[off + i] = static_cast<std::uint8_t>((v >> (8 * i)) & 0xFFu);
    }
}

inline std::uint64_t getU64(const Buffer& b, std::size_t off) {
    std::uint64_t v = 0;
    for (std::size_t i = 0; i < 8; ++i) {
        v |= static_cast<std::uint64_t>(b[off + i]) << (8 * i);
    }
    return v;
}

inline void putI64(Buffer& b, std::size_t off, std::int64_t v) {
    putU64(b, off, static_cast<std::uint64_t>(v));
}

inline std::int64_t getI64(const Buffer& b, std::size_t off) {
    return static_cast<std::int64_t>(getU64(b, off));
}

} // namespace detail

// ---- Symbol helpers ----------------------------------------------------------------------

// Build an 8-byte NUL-padded symbol field; truncates input longer than 8 chars.
inline std::array<char, kSymbolSize> makeSymbol(std::string_view s) {
    std::array<char, kSymbolSize> out{};
    const std::size_t n = s.size() < kSymbolSize ? s.size() : kSymbolSize;
    std::memcpy(out.data(), s.data(), n);
    return out;
}

inline std::string symbolToString(const std::array<char, kSymbolSize>& sym) {
    const char* p = sym.data();
    std::size_t n = 0;
    while (n < kSymbolSize && p[n] != '\0') ++n;
    return std::string(p, n);
}

// ---- Fixed-point helpers -----------------------------------------------------------------

inline std::int64_t scalePrice(double price) {
    return static_cast<std::int64_t>(std::llround(price * static_cast<double>(kPriceScale)));
}
inline double unscalePrice(std::int64_t scaled) {
    return static_cast<double>(scaled) / static_cast<double>(kPriceScale);
}
inline std::int64_t scaleQuantity(double qty) {
    return static_cast<std::int64_t>(std::llround(qty * static_cast<double>(kQuantityScale)));
}
inline double unscaleQuantity(std::int64_t scaled) {
    return static_cast<double>(scaled) / static_cast<double>(kQuantityScale);
}

// ---- Order codec  (WIRE_FORMAT.md §Order) -------------------------------------------------

inline Buffer encodeOrder(const Order& o) {
    Buffer b{}; // zero-initialized: all padding bytes are zero
    detail::putU64(b, 0, o.id);
    std::memcpy(b.data() + 8, o.symbol.data(), kSymbolSize);
    detail::putI64(b, 16, o.price);
    detail::putI64(b, 24, o.quantity);
    b[32] = static_cast<std::uint8_t>(o.side);
    b[33] = static_cast<std::uint8_t>(o.status);
    // bytes 34..39 padding remain zero
    detail::putU64(b, 40, o.timestamp_ns);
    // bytes 48..63 padding remain zero
    return b;
}

inline Order decodeOrder(const Buffer& b) {
    Order o{};
    o.id = detail::getU64(b, 0);
    std::memcpy(o.symbol.data(), b.data() + 8, kSymbolSize);
    o.price = detail::getI64(b, 16);
    o.quantity = detail::getI64(b, 24);
    o.side = static_cast<Side>(b[32]);
    o.status = static_cast<Status>(b[33]);
    o.timestamp_ns = detail::getU64(b, 40);
    return o;
}

// ---- Trade codec  (WIRE_FORMAT.md §Trade) -------------------------------------------------

inline Buffer encodeTrade(const Trade& t) {
    Buffer b{};
    detail::putU64(b, 0, t.buy_order_id);
    detail::putU64(b, 8, t.sell_order_id);
    detail::putI64(b, 16, t.price);
    detail::putI64(b, 24, t.quantity);
    detail::putU64(b, 32, t.timestamp_ns);
    // bytes 40..63 padding remain zero
    return b;
}

inline Trade decodeTrade(const Buffer& b) {
    Trade t{};
    t.buy_order_id = detail::getU64(b, 0);
    t.sell_order_id = detail::getU64(b, 8);
    t.price = detail::getI64(b, 16);
    t.quantity = detail::getI64(b, 24);
    t.timestamp_ns = detail::getU64(b, 32);
    return t;
}

} // namespace chronos::client::wire
