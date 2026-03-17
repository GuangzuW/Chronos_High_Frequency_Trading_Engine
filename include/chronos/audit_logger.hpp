#pragma once

#include <zmq.h>
#include <string>
#include <thread>
#include <atomic>
#include <fstream>
#include <vector>
#include <iostream>

namespace chronos {

/**
 * @brief Asynchronous audit logger that persists ZMQ events to disk.
 */
class AuditLogger {
public:
    explicit AuditLogger(const std::string& pub_endpoint, const std::string& filename)
        : pub_endpoint_(pub_endpoint), filename_(filename), running_(false) {}

    ~AuditLogger() {
        stop();
    }

    void start() {
        if (running_) return;
        running_ = true;
        logger_thread_ = std::thread(&AuditLogger::run, this);
    }

    void stop() {
        if (!running_) return;
        running_ = false;
        if (logger_thread_.joinable()) {
            logger_thread_.join();
        }
    }

private:
    void run() {
        void* context = zmq_ctx_new();
        void* sub = zmq_socket(context, ZMQ_SUB);
        
        if (zmq_connect(sub, pub_endpoint_.c_str()) != 0) {
            zmq_close(sub);
            zmq_ctx_term(context);
            return;
        }
        
        // Subscribe to all topics
        zmq_setsockopt(sub, ZMQ_SUBSCRIBE, "", 0);
        
        // Set a timeout for recv so we can check the running_ flag
        int timeout = 100; // ms
        zmq_setsockopt(sub, ZMQ_RCVTIMEO, &timeout, sizeof(timeout));

        std::ofstream outfile(filename_, std::ios::binary | std::ios::app);
        
        while (running_) {
            zmq_msg_t topic_msg;
            zmq_msg_init(&topic_msg);
            int rc = zmq_msg_recv(&topic_msg, sub, 0);
            
            if (rc == -1) {
                zmq_msg_close(&topic_msg);
                continue;
            }

            // Write topic length and topic
            size_t topic_size = zmq_msg_size(&topic_msg);
            outfile.write(reinterpret_cast<const char*>(&topic_size), sizeof(topic_size));
            outfile.write(static_cast<const char*>(zmq_msg_data(&topic_msg)), topic_size);
            
            bool more = zmq_msg_get(&topic_msg, ZMQ_MORE);
            zmq_msg_close(&topic_msg);

            if (more) {
                zmq_msg_t payload_msg;
                zmq_msg_init(&payload_msg);
                rc = zmq_msg_recv(&payload_msg, sub, 0);
                
                if (rc != -1) {
                    size_t payload_size = zmq_msg_size(&payload_msg);
                    outfile.write(reinterpret_cast<const char*>(&payload_size), sizeof(payload_size));
                    outfile.write(static_cast<const char*>(zmq_msg_data(&payload_msg)), payload_size);
                }
                zmq_msg_close(&payload_msg);
            }
            
            outfile.flush();
        }

        outfile.close();
        zmq_close(sub);
        zmq_ctx_term(context);
    }

    std::string pub_endpoint_;
    std::string filename_;
    std::thread logger_thread_;
    std::atomic<bool> running_;
};

} // namespace chronos
