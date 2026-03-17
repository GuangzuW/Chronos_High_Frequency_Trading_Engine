#include <chronos/memory_pool.hpp>
#include <chronos/zmq_gateway.hpp>
#include <chronos/risk_engine.hpp>
#include <chronos/limit_order_book.hpp>
#include <chronos/event_publisher.hpp>
#include <chronos/audit_logger.hpp>
#include <chronos/thread_utils.hpp>
#include <iostream>
#include <csignal>
#include <atomic>

using namespace chronos;

std::atomic<bool> running{true};

void signalHandler(int signum) {
    std::cout << "\nInterrupt signal (" << signum << ") received. Shutting down...\n";
    running = false;
}

int main() {
    std::signal(SIGINT, signalHandler);
    std::signal(SIGTERM, signalHandler);

    std::cout << "[Chronos] Engine Starting...\n";

    try {
        // 1. Foundation: Memory Management
        auto pool = std::make_unique<MemoryPool>(100 * 1024 * 1024); // 100MB
        
        // 2. Gateway & Infrastructure
        ZmqGateway gateway("tcp://*:5555");
        EventPublisher publisher("tcp://*:5556");
        AuditLogger logger("tcp://127.0.0.1:5556", "trading_audit.log");
        
        // 3. AI Risk Engine
        RiskEngine risk_engine("models/risk_model.onnx");
        
        // 4. Matching Engine (Order Book)
        LimitOrderBook lob(pool->get_resource(), &publisher);

        // Start Audit Logger
        logger.start();

        std::cout << "[Chronos] Gateway listening on port 5555\n";
        std::cout << "[Chronos] Publisher on port 5556\n";
        std::cout << "[Chronos] Engine Ready.\n";

        // 5. Main Hot Path Loop
        // Pin main thread to Core 1 for matching performance
        if (pinThreadToCore(1)) {
            std::cout << "[Chronos] Thread pinned to Core 1\n";
        }
        setMaxPriority();

        while (running) {
            // A. Receive Order (Non-blocking)
            auto msg = gateway.receiveOrder();
            if (!msg) {
                // In production, we might use a spin-wait or a small sleep 
                // to avoid 100% CPU usage if that's desired, or busy-wait for ultra-low latency.
                continue;
            }

            Order& order = msg->order;

            // B. Pre-trade Risk Validation (AI + Static)
            float risk_score = risk_engine.validateOrder(order);
            if (risk_score > 0.8f) {
                std::cout << "[Risk] Order " << order.id.value() << " REJECTED (Score: " << risk_score << ")\n";
                order.status = OrderStatus::Rejected;
                publisher.publishOrderUpdate(order);
                continue;
            }

            // C. Matching
            auto trades = lob.processOrder(&order, pool->get_resource());
            
            if (!trades.empty()) {
                std::cout << "[Match] Executed " << trades.size() << " trades for Order " << order.id.value() << "\n";
            }
        }

        logger.stop();
        std::cout << "[Chronos] Shutdown complete.\n";

    } catch (const std::exception& e) {
        std::cerr << "[Error] Fatal: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
