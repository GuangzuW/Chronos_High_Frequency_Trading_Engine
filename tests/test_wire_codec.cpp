#include <gtest/gtest.h>

#include <chronos/client/wire.hpp> // libs/client-core: the portable wire codec under test
#include <chronos/types.hpp>       // engine structs, to prove binary compatibility

#include <array>
#include <cstdint>
#include <cstring>

namespace wire = chronos::client::wire;

// Guard: the engine structs must stay 64 bytes for the wire contract to hold.
static_assert(sizeof(chronos::Order) == 64, "chronos::Order must be 64 bytes");
static_assert(sizeof(chronos::Trade) == 64, "chronos::Trade must be 64 bytes");
static_assert(wire::kMessageSize == sizeof(chronos::Order),
              "wire message size must match engine Order");

namespace {

// Canonical fixture from contracts/WIRE_FORMAT.md §Order.
wire::Order goldenOrder() {
    wire::Order o;
    o.id = 1001;
    o.symbol = wire::makeSymbol("AAPL");
    o.price = 15025;    // 150.25
    o.quantity = 5000;  // 5.000
    o.side = wire::Side::Buy;
    o.status = wire::Status::New;
    o.timestamp_ns = 0;
    return o;
}

// Canonical fixture from contracts/WIRE_FORMAT.md §Trade.
wire::Trade goldenTrade() {
    wire::Trade t;
    t.buy_order_id = 1001;
    t.sell_order_id = 2002;
    t.price = 15025;
    t.quantity = 5000;
    t.timestamp_ns = 123;
    return t;
}

void expectBytesEqual(const wire::Buffer& actual, const wire::Buffer& expected) {
    for (std::size_t i = 0; i < wire::kMessageSize; ++i) {
        EXPECT_EQ(actual[i], expected[i]) << "byte mismatch at offset " << i;
    }
}

} // namespace

// ---- Golden bytes: locks the codec to the exact on-wire layout ----------------------------

TEST(WireCodecTest, OrderGoldenBytes) {
    // Expected 64 bytes for the §Order fixture (verified against bridge/decoder.py's
    // struct.pack(ORDER_FORMAT, ...) output). All unspecified bytes are zero.
    wire::Buffer expected{};
    expected[0] = 0xE9; expected[1] = 0x03;                 // id = 1001
    expected[8] = 'A'; expected[9] = 'A';
    expected[10] = 'P'; expected[11] = 'L';                 // "AAPL"
    expected[16] = 0xB1; expected[17] = 0x3A;               // price = 15025
    expected[24] = 0x88; expected[25] = 0x13;               // quantity = 5000
    // offset 32 side=0, 33 status=0, 40 timestamp=0 -> all zero, already set.

    expectBytesEqual(wire::encodeOrder(goldenOrder()), expected);
}

TEST(WireCodecTest, TradeGoldenBytes) {
    // Expected 64 bytes for the §Trade fixture (verified against TRADE_FORMAT).
    wire::Buffer expected{};
    expected[0] = 0xE9; expected[1] = 0x03;                 // buy_order_id = 1001
    expected[8] = 0xD2; expected[9] = 0x07;                 // sell_order_id = 2002
    expected[16] = 0xB1; expected[17] = 0x3A;               // price = 15025
    expected[24] = 0x88; expected[25] = 0x13;               // quantity = 5000
    expected[32] = 0x7B;                                    // timestamp = 123

    expectBytesEqual(wire::encodeTrade(goldenTrade()), expected);
}

// ---- Round-trip: decode(encode(x)) == x ---------------------------------------------------

TEST(WireCodecTest, OrderRoundTrip) {
    for (const wire::Order& o : {
             goldenOrder(),
             wire::Order{42, wire::makeSymbol("BTC"), -98765, 1, wire::Side::Sell,
                         wire::Status::Partial, 1678912345678ULL},
             wire::Order{0, wire::makeSymbol(""), 0, 0, wire::Side::Buy, wire::Status::Rejected, 0},
         }) {
        EXPECT_EQ(wire::decodeOrder(wire::encodeOrder(o)), o);
    }
}

TEST(WireCodecTest, TradeRoundTrip) {
    for (const wire::Trade& t : {
             goldenTrade(),
             wire::Trade{1, 2, -500, 999999, 0},
             wire::Trade{0, 0, 0, 0, 1678912345680ULL},
         }) {
        EXPECT_EQ(wire::decodeTrade(wire::encodeTrade(t)), t);
    }
}

// ---- Binary compatibility with the engine structs ----------------------------------------

TEST(WireCodecTest, OrderMatchesEngineLayout) {
    const wire::Buffer buf = wire::encodeOrder(goldenOrder());

    chronos::Order engine{};
    std::memcpy(&engine, buf.data(), wire::kMessageSize);

    EXPECT_EQ(engine.id.value(), 1001u);
    EXPECT_EQ(std::string(engine.symbol.data(), 4), "AAPL");
    EXPECT_EQ(engine.price.value(), 15025);
    EXPECT_EQ(engine.quantity.value(), 5000);
    EXPECT_EQ(static_cast<std::uint8_t>(engine.side),
              static_cast<std::uint8_t>(wire::Side::Buy));
    EXPECT_EQ(static_cast<std::uint8_t>(engine.status),
              static_cast<std::uint8_t>(wire::Status::New));
    EXPECT_EQ(engine.timestamp, 0u);
}

TEST(WireCodecTest, TradeMatchesEngineLayout) {
    const wire::Buffer buf = wire::encodeTrade(goldenTrade());

    chronos::Trade engine{};
    std::memcpy(&engine, buf.data(), wire::kMessageSize);

    EXPECT_EQ(engine.buy_order_id.value(), 1001u);
    EXPECT_EQ(engine.sell_order_id.value(), 2002u);
    EXPECT_EQ(engine.price.value(), 15025);
    EXPECT_EQ(engine.quantity.value(), 5000);
    EXPECT_EQ(engine.timestamp, 123u);
}

// ---- Fixed-point scaling helpers ----------------------------------------------------------

TEST(WireCodecTest, FixedPointScaling) {
    EXPECT_EQ(wire::scalePrice(150.25), 15025);
    EXPECT_EQ(wire::scaleQuantity(5.0), 5000);
    EXPECT_DOUBLE_EQ(wire::unscalePrice(15025), 150.25);
    EXPECT_DOUBLE_EQ(wire::unscaleQuantity(5000), 5.0);
}
