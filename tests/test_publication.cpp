#include <gtest/gtest.h>
#include <chronos/limit_order_book.hpp>
#include <chronos/event_publisher.hpp>
#include <chronos/memory_pool.hpp>
#include <thread>
#include <chrono>

namespace chronos {

class PublicationTest : public ::testing::Test {
protected:
    void SetUp() override {
        pool = std::make_unique<MemoryPool>(1024 * 1024);
        pub_endpoint = "ipc:///tmp/chronos_test_pub";
        publisher = std::make_unique<EventPublisher>(pub_endpoint);
        lob = std::make_unique<LimitOrderBook>(pool->get_resource(), publisher.get());
    }

    std::string pub_endpoint;
    std::unique_ptr<MemoryPool> pool;
    std::unique_ptr<EventPublisher> publisher;
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

TEST_F(PublicationTest, PublishTradeOnMatch) {
    // 1. Setup a SUB client to listen for trades
    void* context = zmq_ctx_new();
    void* sub = zmq_socket(context, ZMQ_SUB);
    ASSERT_EQ(zmq_connect(sub, pub_endpoint.c_str()), 0);
    ASSERT_EQ(zmq_setsockopt(sub, ZMQ_SUBSCRIBE, "TRADE", 5), 0);

    // Give ZMQ time to connect
    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    // 2. Trigger a match
    lob->processOrder(createOrder(1, Price(100), Quantity(10), OrderSide::Sell), pool->get_resource());
    lob->processOrder(createOrder(2, Price(100), Quantity(10), OrderSide::Buy), pool->get_resource());

    // 3. Verify SUB receives the trade
    zmq_msg_t topic_msg;
    zmq_msg_init(&topic_msg);
    int rc = zmq_msg_recv(&topic_msg, sub, ZMQ_DONTWAIT);
    if (rc == -1) {
        // Retry once after a short sleep
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        rc = zmq_msg_recv(&topic_msg, sub, ZMQ_DONTWAIT);
    }
    
    ASSERT_NE(rc, -1);
    zmq_msg_close(&topic_msg);

    // Receive Payload
    Trade received_trade;
    rc = zmq_recv(sub, &received_trade, sizeof(Trade), 0);
    ASSERT_EQ(rc, sizeof(Trade));
    EXPECT_EQ(received_trade.price, Price(100));
    EXPECT_EQ(received_trade.quantity, Quantity(10));

    zmq_close(sub);
    zmq_ctx_term(context);
}

} // namespace chronos
