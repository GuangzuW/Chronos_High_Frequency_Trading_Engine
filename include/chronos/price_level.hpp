#pragma once

#include <chronos/types.hpp>
#include <list>
#include <memory_resource>

namespace chronos {

/**
 * @brief Represents a single price level in the Limit Order Book (LOB).
 * 
 * Manages a list of orders at a specific price point, maintaining FIFO priority.
 */
class PriceLevel {
public:
    using OrderListIterator = std::pmr::list<Order*>::iterator;

    explicit PriceLevel(Price price, std::pmr::memory_resource* resource)
        : price_(price), orders_(resource), total_quantity_(0) {}

    /**
     * @brief Adds an order to the end of the price level (FIFO).
     * @return Iterator to the newly added order for O(1) removal.
     */
    OrderListIterator addOrder(Order* order) {
        total_quantity_ += static_cast<int64_t>(order->quantity);
        orders_.push_back(order);
        return std::prev(orders_.end());
    }

    /**
     * @brief Removes an order by its iterator (O(1)).
     */
    void removeOrder(OrderListIterator it) {
        if (it != orders_.end()) {
            total_quantity_ -= static_cast<int64_t>((*it)->quantity);
            orders_.erase(it);
        }
    }

    /**
     * @brief Get the oldest order at this price (FIFO front).
     */
    Order* front() {
        return orders_.empty() ? nullptr : orders_.front();
    }

    /**
     * @brief Remove the oldest order (O(1)).
     */
    void popFront() {
        if (!orders_.empty()) {
            total_quantity_ -= static_cast<int64_t>(orders_.front()->quantity);
            orders_.pop_front();
        }
    }

    [[nodiscard]] bool empty() const noexcept {
        return orders_.empty();
    }

    [[nodiscard]] Price price() const noexcept {
        return price_;
    }

    [[nodiscard]] Quantity totalQuantity() const noexcept {
        return Quantity(total_quantity_);
    }

    [[nodiscard]] std::size_t numOrders() const noexcept {
        return orders_.size();
    }

private:
    Price price_;
    std::pmr::list<Order*> orders_;
    int64_t total_quantity_; // Track total quantity for book depth calculations
};

} // namespace chronos
