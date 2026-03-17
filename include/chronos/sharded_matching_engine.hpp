#pragma once

#include <chronos/limit_order_book.hpp>
#include <chronos/memory_pool.hpp>
#include <unordered_map>
#include <string>
#include <memory>

namespace chronos {

/**
 * @brief Manages multiple Limit Order Books sharded by symbol.
 */
class ShardedMatchingEngine {
public:
    explicit ShardedMatchingEngine(std::pmr::memory_resource* resource, EventPublisher* publisher = nullptr)
        : resource_(resource), publisher_(publisher), shards_(resource) {}

    /**
     * @brief Initialize a shard for a symbol.
     */
    void addSymbol(const std::string& symbol) {
        if (shards_.find(symbol) == shards_.end()) {
            shards_.emplace(symbol, std::make_unique<LimitOrderBook>(resource_, publisher_));
        }
    }

    /**
     * @brief Route an order to the correct symbol shard.
     */
    std::pmr::vector<Trade> processOrder(Order* order, std::pmr::memory_resource* trade_resource) {
        std::string symbol(order->symbol.data());
        auto null_pos = symbol.find('\0');
        if (null_pos != std::string::npos) {
            symbol.resize(null_pos);
        }

        auto it = shards_.find(symbol);
        if (it != shards_.end()) [[likely]] {
            return it->second->processOrder(order, trade_resource);
        }

        // Symbol not found, return empty trades (or could auto-create shard)
        return std::pmr::vector<Trade>(trade_resource);
    }

    LimitOrderBook* getShard(const std::string& symbol) {
        auto it = shards_.find(symbol);
        return (it != shards_.end()) ? it->second.get() : nullptr;
    }

    std::size_t numShards() const { return shards_.size(); }

private:
    std::pmr::memory_resource* resource_;
    EventPublisher* publisher_;
    std::pmr::unordered_map<std::string, std::unique_ptr<LimitOrderBook>> shards_;
};

} // namespace chronos
