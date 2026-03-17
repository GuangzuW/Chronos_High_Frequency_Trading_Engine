#pragma once

#include <chronos/types.hpp>
#include <zmq.h>
#include <string>
#include <optional>
#include <vector>
#include <stdexcept>

namespace chronos {

/**
 * @brief ZeroMQ Gateway for high-performance order ingress.
 * 
 * Uses a ROUTER socket to handle multiple DEALER clients asynchronously.
 */
class ZmqGateway {
public:
    explicit ZmqGateway(const std::string& endpoint) {
        context_ = zmq_ctx_new();
        if (!context_) {
            throw std::runtime_error("Failed to create ZMQ context");
        }

        socket_ = zmq_socket(context_, ZMQ_ROUTER);
        if (!socket_) {
            zmq_ctx_term(context_);
            throw std::runtime_error("Failed to create ZMQ ROUTER socket");
        }

        if (zmq_bind(socket_, endpoint.c_str()) != 0) {
            zmq_close(socket_);
            zmq_ctx_term(context_);
            throw std::runtime_error("Failed to bind ZMQ socket to: " + endpoint);
        }
    }

    ~ZmqGateway() {
        if (socket_) {
            zmq_close(socket_);
        }
        if (context_) {
            zmq_ctx_term(context_);
        }
    }

    // Disable copy for safety
    ZmqGateway(const ZmqGateway&) = delete;
    ZmqGateway& operator=(const ZmqGateway&) = delete;

    /**
     * @brief Structure to hold the received message and its sender's identity.
     */
    struct ReceivedMessage {
        std::vector<uint8_t> identity;
        Order order;
    };

    /**
     * @brief Receive a binary order from a client in a non-blocking way.
     * @return Optional message containing the sender's identity and the parsed order.
     */
    std::optional<ReceivedMessage> receiveOrder() {
        // ZMQ ROUTER messages come in multipart: [Identity] ([Empty]) [Payload]
        
        // 1. Receive Identity
        zmq_msg_t identity_msg;
        zmq_msg_init(&identity_msg);
        int rc = zmq_msg_recv(&identity_msg, socket_, ZMQ_DONTWAIT);
        if (rc == -1) {
            zmq_msg_close(&identity_msg);
            return std::nullopt;
        }

        ReceivedMessage result;
        uint8_t* id_ptr = static_cast<uint8_t*>(zmq_msg_data(&identity_msg));
        result.identity.assign(id_ptr, id_ptr + zmq_msg_size(&identity_msg));
        bool more = zmq_msg_get(&identity_msg, ZMQ_MORE);
        zmq_msg_close(&identity_msg);

        if (!more) return std::nullopt;

        // 2. Receive next frame
        zmq_msg_t next_msg;
        zmq_msg_init(&next_msg);
        rc = zmq_msg_recv(&next_msg, socket_, 0);
        if (rc == -1) {
            zmq_msg_close(&next_msg);
            return std::nullopt;
        }

        // If it's an empty frame, it's the REQ/DEALER delimiter, skip it and get the payload
        if (zmq_msg_size(&next_msg) == 0 && zmq_msg_get(&next_msg, ZMQ_MORE)) {
            zmq_msg_close(&next_msg);
            zmq_msg_init(&next_msg);
            rc = zmq_msg_recv(&next_msg, socket_, 0);
            if (rc == -1) {
                zmq_msg_close(&next_msg);
                return std::nullopt;
            }
        }

        // Now next_msg should contain the Order
        if (zmq_msg_size(&next_msg) == sizeof(Order)) {
            std::memcpy(&result.order, zmq_msg_data(&next_msg), sizeof(Order));
            zmq_msg_close(&next_msg);
            return result;
        }

        zmq_msg_close(&next_msg);
        return std::nullopt;
    }

private:
    void* context_ = nullptr;
    void* socket_ = nullptr;
};

} // namespace chronos
