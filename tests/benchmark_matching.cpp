#include <gtest/gtest.h>
#include <chronos/limit_order_book.hpp>
#include <chronos/memory_pool.hpp>
#include <chronos/latency_utils.hpp>
#include <vector>

namespace chronos {

class MatchingBenchmark : public ::testing::Test {
protected:
    void SetUp() override {
        // Use a larger pool for benchmarks
        pool = std::make_unique<MemoryPool>(256 * 1024 * 1024);
        lob = std::make_unique<LimitOrderBook>(pool->get_resource());
    }

    std::unique_ptr<MemoryPool> pool;
    std::unique_ptr<LimitOrderBook> lob;

    Order* createOrder(uint64_t id, Price price, Quantity qty, OrderSide side) {
        Order* order = pool->allocate<Order>();
        *order = Order{
            .id = OrderId(id),
            .price = price,
            .quantity = qty,
            .side = side,
            .status = OrderStatus::New,
            .timestamp = 0
        };
        return order;
    }
};

TEST_F(MatchingBenchmark, BenchmarkThroughput) {
    const int num_levels = 100;
    const int orders_per_level = 100;
    const int total_incoming = 10000;

    std::cout << "[Benchmark] Filling book with " << num_levels * orders_per_level << " orders...\n";
    for (int i = 0; i < num_levels; ++i) {
        for (int j = 0; j < orders_per_level; ++j) {
            lob->processOrder(createOrder(i * 1000 + j, Price(1000 + i), Quantity(10), OrderSide::Sell), pool->get_resource());
        }
    }

    std::cout << "[Benchmark] Matching " << total_incoming << " orders...\n";
    {
        LatencyLogger logger("Matching 10k Orders");
        for (int i = 0; i < total_incoming; ++i) {
            // Each of these matches 10 orders (1 level)
            lob->processOrder(createOrder(1000000 + i, Price(1000 + (i % num_levels)), Quantity(100), OrderSide::Buy), pool->get_resource());
        }
    }
}

} // namespace chronos
