#include <gtest/gtest.h>
#include <chronos/types.hpp>
#include <type_traits>

namespace chronos {

TEST(CoreTypesTest, OrderSizeAndAlignment) {
    EXPECT_EQ(sizeof(Order), 64);
    EXPECT_EQ(alignof(Order), 64);
}

TEST(CoreTypesTest, TradeSizeAndAlignment) {
    EXPECT_EQ(sizeof(Trade), 64);
    EXPECT_EQ(alignof(Trade), 64);
}

TEST(CoreTypesTest, StrongTypeSafety) {
    // Should NOT compile if we try to mix them implicitly
    // Price p = Quantity(100); // This should fail compilation if uncommented
    
    Price p1(100);
    Price p2(50);
    Price p3 = p1 + p2;
    
    EXPECT_EQ(p3.value(), 150);
    EXPECT_TRUE(p1 > p2);
}

TEST(CoreTypesTest, StructInitialization) {
    Order order;
    order.id = OrderId(12345);
    order.price = Price(10050); // $100.50
    order.quantity = Quantity(100);
    order.side = OrderSide::Buy;
    order.status = OrderStatus::New;
    order.timestamp = 1678912345678ULL;
    
    EXPECT_EQ(order.id.value(), 12345);
    EXPECT_EQ(order.price.value(), 10050);
    EXPECT_EQ(order.quantity.value(), 100);
    EXPECT_EQ(order.side, OrderSide::Buy);
    EXPECT_EQ(order.status, OrderStatus::New);
    EXPECT_EQ(order.timestamp, 1678912345678ULL);
}

TEST(CoreTypesTest, TradeInitialization) {
    Trade trade;
    trade.buy_order_id = OrderId(101);
    trade.sell_order_id = OrderId(102);
    trade.price = Price(10050);
    trade.quantity = Quantity(50);
    trade.timestamp = 1678912345680ULL;
    
    EXPECT_EQ(trade.buy_order_id.value(), 101);
    EXPECT_EQ(trade.sell_order_id.value(), 102);
    EXPECT_EQ(trade.price.value(), 10050);
    EXPECT_EQ(trade.quantity.value(), 50);
    EXPECT_EQ(trade.timestamp, 1678912345680ULL);
}

} // namespace chronos
