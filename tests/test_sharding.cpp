#include <gtest/gtest.h>
#include <chronos/sharded_matching_engine.hpp>
#include <chronos/memory_pool.hpp>

namespace chronos {

class ShardingTest : public ::testing::Test {
protected:
    void SetUp() override {
        pool = std::make_unique<MemoryPool>(1024 * 1024);
        engine = std::make_unique<ShardedMatchingEngine>(pool->get_resource());
    }

    std::unique_ptr<MemoryPool> pool;
    std::unique_ptr<ShardedMatchingEngine> engine;

    Order* createOrder(uint64_t id, const char* symbol, Price price, Quantity qty, OrderSide side) {
        Order* order = pool->allocate<Order>();
        *order = Order{
            .id = OrderId(id),
            .price = price,
            .quantity = qty,
            .side = side,
            .status = OrderStatus::New,
            .timestamp = 0
        };
        std::memset(order->symbol.data(), 0, 8);
        std::strncpy(order->symbol.data(), symbol, 7);
        return order;
    }
};

TEST_F(ShardingTest, RouteToCorrectShard) {
    engine->addSymbol("AAPL");
    engine->addSymbol("GOOGL");

    // Sell AAPL @ 150
    engine->processOrder(createOrder(1, "AAPL", Price(150), Quantity(10), OrderSide::Sell), pool->get_resource());
    
    // Sell GOOGL @ 2800
    engine->processOrder(createOrder(2, "GOOGL", Price(2800), Quantity(10), OrderSide::Sell), pool->get_resource());

    // Buy AAPL @ 150 should match only AAPL
    auto trades = engine->processOrder(createOrder(3, "AAPL", Price(150), Quantity(10), OrderSide::Buy), pool->get_resource());
    
    EXPECT_EQ(trades.size(), 1);
    EXPECT_EQ(trades[0].price, Price(150));
    
    // Verify shards
    EXPECT_EQ(engine->getShard("AAPL")->numOrders(), 0);
    EXPECT_EQ(engine->getShard("GOOGL")->numOrders(), 1);
}

TEST_F(ShardingTest, UnknownSymbol) {
    // Should not crash, just return empty trades
    auto trades = engine->processOrder(createOrder(1, "UNKNOWN", Price(100), Quantity(10), OrderSide::Buy), pool->get_resource());
    EXPECT_TRUE(trades.empty());
}

} // namespace chronos
