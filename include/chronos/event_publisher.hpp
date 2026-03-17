#pragma once

#include <chronos/types.hpp>
#include <zmq.h>
#include <string>
#include <stdexcept>
#include <cstring>

namespace chronos {

/**
 * @brief High-performance trade and order event publisher.
 * 
 * Uses a ZMQ PUB socket to broadcast events asynchronously.
 */
class EventPublisher {
public:
    explicit EventPublisher(const std::string& endpoint) {
        context_ = zmq_ctx_new();
        if (!context_) {
            throw std::runtime_error("Failed to create ZMQ context");
        }

        socket_ = zmq_socket(context_, ZMQ_PUB);
        if (!socket_) {
            zmq_ctx_term(context_);
            throw std::runtime_error("Failed to create ZMQ PUB socket");
        }

        if (zmq_bind(socket_, endpoint.c_str()) != 0) {
            zmq_close(socket_);
            zmq_ctx_term(context_);
            throw std::runtime_error("Failed to bind ZMQ socket to: " + endpoint);
        }
    }

    ~EventPublisher() {
        if (socket_) {
            zmq_close(socket_);
        }
        if (context_) {
            zmq_ctx_term(context_);
        }
    }

    // Disable copy
    EventPublisher(const EventPublisher&) = delete;
    EventPublisher& operator=(const EventPublisher&) = delete;

    /**
     * @brief Publish a trade execution.
     * Protocol: [Topic: "TRADE"] [Binary: Trade struct]
     */
    void publishTrade(const Trade& trade) {
        publishEvent("TRADE", &trade, sizeof(Trade));
    }

    /**
     * @brief Publish an order status update.
     * Protocol: [Topic: "ORDER"] [Binary: Order struct]
     */
    void publishOrderUpdate(const Order& order) {
        publishEvent("ORDER", &order, sizeof(Order));
    }

private:
    void publishEvent(const char* topic, const void* data, size_t size) {
        // 1. Send Topic frame
        zmq_send(socket_, topic, strlen(topic), ZMQ_SNDMORE);
        
        // 2. Send Payload frame
        zmq_send(socket_, data, size, 0);
    }

    void* context_ = nullptr;
    void* socket_ = nullptr;
};

} // namespace chronos
