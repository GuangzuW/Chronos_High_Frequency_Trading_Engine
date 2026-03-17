#include <gtest/gtest.h>
#include <chronos/memory_pool.hpp>
#include <chronos/types.hpp>
#include <vector>

namespace chronos {

TEST(MemoryPoolTest, InitializationAndSize) {
    const std::size_t size = 1024;
    MemoryPool pool(size);
    EXPECT_EQ(pool.size(), size);
    EXPECT_NE(pool.get_resource(), nullptr);
}

TEST(MemoryPoolTest, AllocateType) {
    MemoryPool pool(1024);
    Order* order = pool.allocate<Order>();
    ASSERT_NE(order, nullptr);
    
    // Check alignment
    EXPECT_EQ(reinterpret_cast<std::uintptr_t>(order) % alignof(Order), 0);
    
    // Check we can write to it
    order->id = OrderId(55);
    EXPECT_EQ(order->id, OrderId(55));
}

TEST(MemoryPoolTest, UseWithPmrVector) {
    MemoryPool pool(1024);
    std::pmr::vector<Order> orders(pool.get_resource());
    
    orders.push_back(Order{.id = OrderId(1)});
    orders.push_back(Order{.id = OrderId(2)});
    
    EXPECT_EQ(orders.size(), 2);
    EXPECT_EQ(orders[0].id, OrderId(1));
    EXPECT_EQ(orders[1].id, OrderId(2));
}

TEST(MemoryPoolTest, ThrowsOnOverflow) {
    // Small pool that can only fit 1 Order (64 bytes)
    MemoryPool pool(64);
    
    // First allocation should succeed
    EXPECT_NO_THROW(pool.allocate<Order>());
    
    // Second allocation should throw bad_alloc because we used null_memory_resource
    EXPECT_THROW(pool.allocate<Order>(), std::bad_alloc);
}

} // namespace chronos
