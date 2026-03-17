#include <gtest/gtest.h>
#include <chronos/risk_engine.hpp>
#include <chronos/types.hpp>

namespace chronos {

TEST(RiskEngineTest, StaticRuleQuantityLimit) {
    RiskConfig config;
    config.max_order_quantity = 100;
    RiskEngine engine("models/risk_model.onnx", config);
    
    Order risky_order;
    risky_order.price = Price(100);
    risky_order.quantity = Quantity(101); // Over limit
    
    EXPECT_EQ(engine.validateOrder(risky_order), 1.0f);
}

TEST(RiskEngineTest, StaticRuleValueLimit) {
    RiskConfig config;
    config.max_order_value = 1000;
    RiskEngine engine("models/risk_model.onnx", config);
    
    Order risky_order;
    risky_order.price = Price(101);
    risky_order.quantity = Quantity(10); // 101 * 10 = 1010 > 1000
    
    EXPECT_EQ(engine.validateOrder(risky_order), 1.0f);
}

TEST(RiskEngineTest, StaticRuleInvalidPrice) {
    RiskEngine engine("models/risk_model.onnx");
    
    Order bad_order;
    bad_order.price = Price(0);
    bad_order.quantity = Quantity(10);
    
    EXPECT_EQ(engine.validateOrder(bad_order), 1.0f);
}

TEST(RiskEngineTest, ValidOrderPasses) {
    RiskEngine engine("models/risk_model.onnx");
    
    Order good_order;
    good_order.price = Price(100);
    good_order.quantity = Quantity(10);
    
    EXPECT_LT(engine.validateOrder(good_order), 1.0f);
}

} // namespace chronos
