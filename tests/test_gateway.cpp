#include <gtest/gtest.h>
#include <chronos/zmq_gateway.hpp>
#include <chronos/types.hpp>
#include <thread>
#include <chrono>

namespace chronos {

class ZmqGatewayTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Use an IPC endpoint for faster and more reliable local testing
        endpoint = "ipc:///tmp/chronos_test_gateway";
        gateway = std::make_unique<ZmqGateway>(endpoint);
    }

    void TearDown() override {
        gateway.reset();
    }

    std::string endpoint;
    std::unique_ptr<ZmqGateway> gateway;
};

TEST_F(ZmqGatewayTest, ReceiveBinaryOrder) {
    // 1. Setup a mock DEALER client to send an order
    void* context = zmq_ctx_new();
    void* client = zmq_socket(context, ZMQ_DEALER);
    
    // Set identity for the client
    const char* identity = "test_client";
    zmq_setsockopt(client, ZMQ_IDENTITY, identity, strlen(identity));
    
    ASSERT_EQ(zmq_connect(client, endpoint.c_str()), 0);

    // 2. Prepare a binary Order
    Order original_order;
    std::memset(&original_order, 0, sizeof(Order));
    original_order.id = OrderId(999);
    original_order.price = Price(54321);
    original_order.quantity = Quantity(100);
    original_order.side = OrderSide::Buy;
    original_order.status = OrderStatus::New;
    std::strncpy(original_order.symbol.data(), "AAPL", 4);

    // 3. Send the order (DEALER automatically adds identity frame)
    // Send payload (DEALER -> ROUTER adds Identity and Empty frame)
    zmq_msg_t msg;
    zmq_msg_init_size(&msg, sizeof(Order));
    std::memcpy(zmq_msg_data(&msg), &original_order, sizeof(Order));
    ASSERT_EQ(zmq_msg_send(&msg, client, 0), sizeof(Order));

    // 4. Gateway receives and parses
    std::optional<ZmqGateway::ReceivedMessage> received;
    int attempts = 10;
    while (attempts-- > 0) {
        received = gateway->receiveOrder();
        if (received) break;
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }

    ASSERT_TRUE(received.has_value());
    EXPECT_EQ(received->order.id, original_order.id);
    EXPECT_EQ(received->order.price, original_order.price);
    EXPECT_EQ(received->order.quantity, original_order.quantity);
    EXPECT_STREQ(received->order.symbol.data(), "AAPL");
    EXPECT_EQ(received->identity.size(), strlen(identity));
    EXPECT_EQ(std::memcmp(received->identity.data(), identity, strlen(identity)), 0);

    // Cleanup
    zmq_close(client);
    zmq_ctx_term(context);
}

} // namespace chronos
