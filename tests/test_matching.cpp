#include <gtest/gtest.h>
#include <chronos/limit_order_book.hpp>
#include <chronos/memory_pool.hpp>

namespace chronos {

class MatchingTest : public ::testing::Test {
protected:
    void SetUp() override {
        pool = std::make_unique<MemoryPool>(1024 * 1024);
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

TEST_F(MatchingTest, ExactMatch) {
    lob->processOrder(createOrder(1, Price(100), Quantity(10), OrderSide::Buy), pool->get_resource());
    auto trades = lob->processOrder(createOrder(2, Price(100), Quantity(10), OrderSide::Sell), pool->get_resource());

    EXPECT_EQ(trades.size(), 1);
    EXPECT_EQ(trades[0].quantity, Quantity(10));
    EXPECT_EQ(trades[0].price, Price(100));
    EXPECT_EQ(trades[0].buy_order_id, OrderId(1));
    EXPECT_EQ(trades[0].sell_order_id, OrderId(2));

    EXPECT_EQ(lob->numOrders(), 0);
    EXPECT_EQ(lob->numBidLevels(), 0);
}

TEST_F(MatchingTest, PartialMatch) {
    lob->processOrder(createOrder(1, Price(100), Quantity(100), OrderSide::Buy), pool->get_resource());
    auto trades = lob->processOrder(createOrder(2, Price(100), Quantity(40), OrderSide::Sell), pool->get_resource());

    EXPECT_EQ(trades.size(), 1);
    EXPECT_EQ(trades[0].quantity, Quantity(40));
    
    EXPECT_EQ(lob->numOrders(), 1);
    EXPECT_EQ(lob->getBestBid()->totalQuantity(), Quantity(60));
}

TEST_F(MatchingTest, MultiLevelMatch) {
    lob->processOrder(createOrder(1, Price(100), Quantity(50), OrderSide::Sell), pool->get_resource());
    lob->processOrder(createOrder(2, Price(105), Quantity(50), OrderSide::Sell), pool->get_resource());

    // Buy 100 @ 110 should match both levels
    auto trades = lob->processOrder(createOrder(3, Price(110), Quantity(100), OrderSide::Buy), pool->get_resource());

    EXPECT_EQ(trades.size(), 2);
    EXPECT_EQ(trades[0].price, Price(100));
    EXPECT_EQ(trades[0].quantity, Quantity(50));
    EXPECT_EQ(trades[1].price, Price(105));
    EXPECT_EQ(trades[1].quantity, Quantity(50));

    EXPECT_EQ(lob->numOrders(), 0);
}

TEST_F(MatchingTest, FIFOPriority) {
    lob->processOrder(createOrder(1, Price(100), Quantity(50), OrderSide::Buy), pool->get_resource()); // T1
    lob->processOrder(createOrder(2, Price(100), Quantity(50), OrderSide::Buy), pool->get_resource()); // T2

    // Sell 50 @ 100 should match Order 1 (T1)
    auto trades = lob->processOrder(createOrder(3, Price(100), Quantity(50), OrderSide::Sell), pool->get_resource());

    EXPECT_EQ(trades.size(), 1);
    EXPECT_EQ(trades[0].buy_order_id, OrderId(1));
    
    EXPECT_EQ(lob->numOrders(), 1);
    EXPECT_EQ(lob->getBestBid()->front()->id, OrderId(2));
}

TEST_F(MatchingTest, NoMatch) {
    lob->processOrder(createOrder(1, Price(100), Quantity(10), OrderSide::Buy), pool->get_resource());
    auto trades = lob->processOrder(createOrder(2, Price(101), Quantity(10), OrderSide::Sell), pool->get_resource());

    EXPECT_EQ(trades.size(), 0);
    EXPECT_EQ(lob->numOrders(), 2);
}

} // namespace chronos
