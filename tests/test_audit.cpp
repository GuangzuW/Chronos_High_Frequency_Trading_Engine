#include <gtest/gtest.h>
#include <chronos/audit_logger.hpp>
#include <chronos/event_publisher.hpp>
#include <chronos/types.hpp>
#include <filesystem>
#include <thread>
#include <chrono>

namespace chronos {

class AuditLoggerTest : public ::testing::Test {
protected:
    void SetUp() override {
        pub_endpoint = "ipc:///tmp/chronos_test_audit_pub";
        log_file = "/tmp/chronos_audit.log";
        if (std::filesystem::exists(log_file)) {
            std::filesystem::remove(log_file);
        }
        
        publisher = std::make_unique<EventPublisher>(pub_endpoint);
        logger = std::make_unique<AuditLogger>(pub_endpoint, log_file);
    }

    void TearDown() override {
        logger->stop();
        if (std::filesystem::exists(log_file)) {
            std::filesystem::remove(log_file);
        }
    }

    std::string pub_endpoint;
    std::string log_file;
    std::unique_ptr<EventPublisher> publisher;
    std::unique_ptr<AuditLogger> logger;
};

TEST_F(AuditLoggerTest, PersistTradeEvent) {
    logger->start();
    
    // Give logger time to connect
    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    Trade trade;
    trade.price = Price(12345);
    trade.quantity = Quantity(500);
    trade.timestamp = 1678912345678ULL;
    
    publisher->publishTrade(trade);
    
    // Give logger time to receive and write
    std::this_thread::sleep_for(std::chrono::milliseconds(200));
    
    logger->stop();

    // Verify file content
    std::ifstream infile(log_file, std::ios::binary);
    ASSERT_TRUE(infile.is_open());

    // Read Topic Size
    size_t topic_size = 0;
    infile.read(reinterpret_cast<char*>(&topic_size), sizeof(topic_size));
    EXPECT_EQ(topic_size, 5); // "TRADE"

    // Read Topic
    char topic[6] = {0};
    infile.read(topic, 5);
    EXPECT_STREQ(topic, "TRADE");

    // Read Payload Size
    size_t payload_size = 0;
    infile.read(reinterpret_cast<char*>(&payload_size), sizeof(payload_size));
    EXPECT_EQ(payload_size, sizeof(Trade));

    // Read Trade
    Trade read_trade;
    infile.read(reinterpret_cast<char*>(&read_trade), sizeof(Trade));
    EXPECT_EQ(read_trade.price, trade.price);
    EXPECT_EQ(read_trade.quantity, trade.quantity);
}

} // namespace chronos
