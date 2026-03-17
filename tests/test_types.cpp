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

TEST(CoreTypesTest, StructInitialization) {
    Order order;
    order.id = 12345;
    order.price = 10050; // $100.50
    order.quantity = 100;
    order.side = OrderSide::Buy;
    order.status = OrderStatus::New;
    order.timestamp = 1678912345678ULL;
    
    EXPECT_EQ(order.id, 12345);
    EXPECT_EQ(order.price, 10050);
    EXPECT_EQ(order.quantity, 100);
    EXPECT_EQ(order.side, OrderSide::Buy);
    EXPECT_EQ(order.status, OrderStatus::New);
    EXPECT_EQ(order.timestamp, 1678912345678ULL);
}

TEST(CoreTypesTest, TradeInitialization) {
    Trade trade;
    trade.buy_order_id = 101;
    trade.sell_order_id = 102;
    trade.price = 10050;
    trade.quantity = 50;
    trade.timestamp = 1678912345680ULL;
    
    EXPECT_EQ(trade.buy_order_id, 101);
    EXPECT_EQ(trade.sell_order_id, 102);
    EXPECT_EQ(trade.price, 10050);
    EXPECT_EQ(trade.quantity, 50);
    EXPECT_EQ(trade.timestamp, 1678912345680ULL);
}

} // namespace chronos
