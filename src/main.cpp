#include <iostream>
#include <vector>
#include <span>

int main() {
    std::vercor<int> market_data = {100, 101, 102, 99, 98};
    //Usage of c++20 std:span(Zero-copy view)
    std::span<int> data_view = market_data;

    std::cout << "[Chronos] Engine Online, Processing" << data_view.size() << " ticks."<<std::endl;
    return 0;
}