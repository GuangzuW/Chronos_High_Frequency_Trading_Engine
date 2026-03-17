#pragma once

#include <compare>
#include <utility>

namespace chronos {

/**
 * @brief StrongType wrapper to prevent accidental type mixing.
 * 
 * @tparam T The underlying type (e.g., int64_t).
 * @tparam Tag A unique tag type to distinguish different strong types.
 */
template <typename T, typename Tag>
class StrongType {
public:
    using UnderlyingType = T;

    constexpr explicit StrongType(T val) : value_(std::move(val)) {}
    constexpr StrongType() = default;

    constexpr T& value() noexcept { return value_; }
    constexpr const T& value() const noexcept { return value_; }

    // Explicit conversion for when we NEED the underlying type
    constexpr explicit operator T() const noexcept { return value_; }

    // Comparison operators (C++20 spaceship)
    auto operator<=>(const StrongType&) const = default;

    // Arithmetic operators (optional, enabled for Price/Quantity)
    constexpr StrongType& operator+=(const StrongType& other) {
        value_ += other.value_;
        return *this;
    }

    constexpr StrongType& operator-=(const StrongType& other) {
        value_ -= other.value_;
        return *this;
    }

    friend constexpr StrongType operator+(StrongType lhs, const StrongType& rhs) {
        lhs += rhs;
        return lhs;
    }

    friend constexpr StrongType operator-(StrongType lhs, const StrongType& rhs) {
        lhs -= rhs;
        return lhs;
    }

private:
    T value_{};
};

} // namespace chronos
