#pragma once

#include <chronos/price_level.hpp>
#include <chronos/memory_pool.hpp>
#include <map>
#include <unordered_map>
#include <functional>

namespace chronos {

/**
 * @brief Manages the Limit Order Book (LOB) for a single symbol.
 * 
 * Maintains sorted bids and asks and provides O(1) order lookup/cancellation.
 */
class LimitOrderBook {
public:
    explicit LimitOrderBook(std::pmr::memory_resource* resource)
        : bids_(resource), asks_(resource), order_lookup_(resource) {}

    /**
     * @brief Add a limit order to the book.
     * Note: This only adds to the book; matching logic is in Task 2.3.
     */
    void addOrder(Order* order) {
        if (order->side == OrderSide::Buy) {
            auto [it, inserted] = bids_.try_emplace(order->price, order->price, bids_.get_allocator().resource());
            auto list_it = it->second.addOrder(order);
            order_lookup_[order->id] = {order->price, list_it, OrderSide::Buy};
        } else {
            auto [it, inserted] = asks_.try_emplace(order->price, order->price, asks_.get_allocator().resource());
            auto list_it = it->second.addOrder(order);
            order_lookup_[order->id] = {order->price, list_it, OrderSide::Sell};
        }
    }

    /**
     * @brief Cancel an order in O(1).
     */
    bool cancelOrder(OrderId id) {
        auto it = order_lookup_.find(id);
        if (it == order_lookup_.end()) {
            return false;
        }

        const auto& entry = it->second;
        if (entry.side == OrderSide::Buy) {
            auto bid_it = bids_.find(entry.price);
            if (bid_it != bids_.end()) {
                bid_it->second.removeOrder(entry.list_iterator);
                if (bid_it->second.empty()) {
                    bids_.erase(bid_it);
                }
            }
        } else {
            auto ask_it = asks_.find(entry.price);
            if (ask_it != asks_.end()) {
                ask_it->second.removeOrder(entry.list_iterator);
                if (ask_it->second.empty()) {
                    asks_.erase(ask_it);
                }
            }
        }

        order_lookup_.erase(it);
        return true;
    }

    const PriceLevel* getBestBid() const {
        return bids_.empty() ? nullptr : &bids_.begin()->second;
    }

    const PriceLevel* getBestAsk() const {
        return asks_.empty() ? nullptr : &asks_.begin()->second;
    }

    std::size_t numBidLevels() const { return bids_.size(); }
    std::size_t numAskLevels() const { return asks_.size(); }
    std::size_t numOrders() const { return order_lookup_.size(); }

private:
    struct OrderEntry {
        Price price;
        PriceLevel::OrderListIterator list_iterator;
        OrderSide side;
    };

    // Bids: Sorted High -> Low
    std::pmr::map<Price, PriceLevel, std::greater<Price>> bids_;
    // Asks: Sorted Low -> High
    std::pmr::map<Price, PriceLevel, std::less<Price>> asks_;
    
    // Global lookup for O(1) cancellations
    std::pmr::unordered_map<OrderId, OrderEntry> order_lookup_;
};

} // namespace chronos
