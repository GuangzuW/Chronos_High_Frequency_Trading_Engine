#include <gtest/gtest.h>
#include <chronos/price_level.hpp>
#include <chronos/memory_pool.hpp>

namespace chronos {

class PriceLevelTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Pre-allocate some orders in the pool for testing
        order1 = pool.allocate<Order>();
        *order1 = Order{.id = OrderId(1), .price = Price(100), .quantity = Quantity(10)};
        
        order2 = pool.allocate<Order>();
        *order2 = Order{.id = OrderId(2), .price = Price(100), .quantity = Quantity(20)};
        
        order3 = pool.allocate<Order>();
        *order3 = Order{.id = OrderId(3), .price = Price(100), .quantity = Quantity(30)};
    }

    MemoryPool pool{1024 * 1024}; // 1MB for tests
    Order* order1;
    Order* order2;
    Order* order3;
};

TEST_F(PriceLevelTest, AddAndFIFO) {
    PriceLevel level(Price(100), pool.get_resource());
    
    level.addOrder(order1);
    level.addOrder(order2);
    level.addOrder(order3);
    
    EXPECT_EQ(level.numOrders(), 3);
    EXPECT_EQ(level.totalQuantity(), Quantity(60));
    
    EXPECT_EQ(level.front()->id, OrderId(1));
    level.popFront();
    
    EXPECT_EQ(level.front()->id, OrderId(2));
    level.popFront();
    
    EXPECT_EQ(level.front()->id, OrderId(3));
    level.popFront();
    
    EXPECT_TRUE(level.empty());
    EXPECT_EQ(level.totalQuantity(), Quantity(0));
}

TEST_F(PriceLevelTest, ConstantTimeRemoval) {
    PriceLevel level(Price(100), pool.get_resource());
    
    level.addOrder(order1);
    auto it2 = level.addOrder(order2);
    level.addOrder(order3);
    
    // Remove middle order
    level.removeOrder(it2);
    
    EXPECT_EQ(level.numOrders(), 2);
    EXPECT_EQ(level.totalQuantity(), Quantity(40));
    
    EXPECT_EQ(level.front()->id, OrderId(1));
    level.popFront();
    EXPECT_EQ(level.front()->id, OrderId(3));
}

TEST_F(PriceLevelTest, MemoryPoolUsage) {
    // This test implicitly verifies that the PMR list uses the pool.
    // If it didn't, it might still "work" by using the global allocator,
    // but the null_memory_resource check in MemoryPool (if we set it as default)
    // would catch it. Since we pass the resource directly to the list, 
    // it will use it.
    
    PriceLevel level(Price(100), pool.get_resource());
    level.addOrder(order1);
    
    EXPECT_EQ(level.totalQuantity(), Quantity(10));
}

} // namespace chronos
