#include <gtest/gtest.h>
#include <chronos/limit_order_book.hpp>
#include <chronos/memory_pool.hpp>

namespace chronos {

class LOBTest : public ::testing::Test {
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

TEST_F(LOBTest, AddAndOrderSorting) {
    lob->addOrder(createOrder(1, Price(100), Quantity(10), OrderSide::Buy));
    lob->addOrder(createOrder(2, Price(110), Quantity(20), OrderSide::Buy));
    lob->addOrder(createOrder(3, Price(105), Quantity(15), OrderSide::Buy));

    // Bids should be sorted high -> low: 110, 105, 100
    EXPECT_EQ(lob->numBidLevels(), 3);
    EXPECT_EQ(lob->getBestBid()->price(), Price(110));

    lob->addOrder(createOrder(4, Price(120), Quantity(10), OrderSide::Sell));
    lob->addOrder(createOrder(5, Price(115), Quantity(20), OrderSide::Sell));

    // Asks should be sorted low -> high: 115, 120
    EXPECT_EQ(lob->numAskLevels(), 2);
    EXPECT_EQ(lob->getBestAsk()->price(), Price(115));
}

TEST_F(LOBTest, CancelOrder) {
    lob->addOrder(createOrder(1, Price(100), Quantity(10), OrderSide::Buy));
    lob->addOrder(createOrder(2, Price(100), Quantity(20), OrderSide::Buy));

    EXPECT_EQ(lob->numBidLevels(), 1);
    EXPECT_EQ(lob->numOrders(), 2);
    EXPECT_EQ(lob->getBestBid()->totalQuantity(), Quantity(30));

    // Cancel first order
    EXPECT_TRUE(lob->cancelOrder(OrderId(1)));
    EXPECT_EQ(lob->numOrders(), 1);
    EXPECT_EQ(lob->getBestBid()->totalQuantity(), Quantity(20));

    // Cancel second order, level should be cleaned up
    EXPECT_TRUE(lob->cancelOrder(OrderId(2)));
    EXPECT_EQ(lob->numOrders(), 0);
    EXPECT_EQ(lob->numBidLevels(), 0);
    EXPECT_EQ(lob->getBestBid(), nullptr);
}

TEST_F(LOBTest, CancelNonExistent) {
    EXPECT_FALSE(lob->cancelOrder(OrderId(999)));
}

} // namespace chronos
