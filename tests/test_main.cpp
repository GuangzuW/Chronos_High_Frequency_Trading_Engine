#include <gtest/gtest.h>
#include <vector>
#include <span>

// Basic test to verify that C++20 span and vector are working as expected
TEST(CoreLogicTest, SpanBasicTest) {
    std::vector<int> market_data = {100, 101, 102};
    std::span<int> data_view = market_data;
    
    EXPECT_EQ(data_view.size(), 3);
    EXPECT_EQ(data_view[0], 100);
    EXPECT_EQ(data_view[2], 102);
}
