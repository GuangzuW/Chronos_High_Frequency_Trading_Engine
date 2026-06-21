"""Tests for the canonical Python wire codec (bridge.wire).

Mirrors the C++ golden test (tests/test_wire_codec.cpp) so both language sides are locked
to the exact same bytes defined in contracts/WIRE_FORMAT.md.

Run (no third-party deps required):
    PYTHONPATH=. python3 -m unittest bridge.tests.test_wire -v
"""

import struct
import unittest

from bridge import wire
from bridge.schemas import Order, OrderSide, OrderStatus, Trade


def golden_order() -> Order:
    # contracts/WIRE_FORMAT.md §Order fixture.
    return Order(
        id=1001,
        symbol="AAPL",
        price=15025,   # 150.25
        quantity=5000, # 5.000
        side=OrderSide.BUY,
        status=OrderStatus.NEW,
        timestamp=0,
    )


def golden_trade() -> Trade:
    # contracts/WIRE_FORMAT.md §Trade fixture.
    return Trade(buy_order_id=1001, sell_order_id=2002, price=15025, quantity=5000, timestamp=123)


class WireFormatTest(unittest.TestCase):
    def test_message_sizes_are_64(self):
        self.assertEqual(wire.MESSAGE_SIZE, 64)
        self.assertEqual(struct.calcsize(wire.ORDER_FORMAT), 64)
        self.assertEqual(struct.calcsize(wire.TRADE_FORMAT), 64)

    def test_order_golden_bytes(self):
        # Built byte-by-byte exactly like the C++ test's expected[] array.
        expected = bytearray(64)
        expected[0] = 0xE9
        expected[1] = 0x03  # id = 1001
        expected[8:12] = b"AAPL"  # symbol
        expected[16] = 0xB1
        expected[17] = 0x3A  # price = 15025
        expected[24] = 0x88
        expected[25] = 0x13  # quantity = 5000
        # side=0, status=0, timestamp=0 -> all remaining bytes zero
        self.assertEqual(wire.encode_order(golden_order()), bytes(expected))

    def test_trade_golden_bytes(self):
        expected = bytearray(64)
        expected[0] = 0xE9
        expected[1] = 0x03  # buy = 1001
        expected[8] = 0xD2
        expected[9] = 0x07  # sell = 2002
        expected[16] = 0xB1
        expected[17] = 0x3A  # price = 15025
        expected[24] = 0x88
        expected[25] = 0x13  # quantity = 5000
        expected[32] = 0x7B  # timestamp = 123
        self.assertEqual(wire.encode_trade(golden_trade()), bytes(expected))

    def test_backward_compatible_with_native_format(self):
        # The new explicit-LE format must produce identical bytes to the original
        # native-order format string that shipped in bridge/decoder.py, proving the
        # on-wire layout did not change.
        legacy_order = "Q8sqqBB6xQ16x"
        legacy_trade = "QQqqQ24x"
        o = golden_order()
        self.assertEqual(
            wire.encode_order(o),
            struct.pack(legacy_order, o.id, wire.make_symbol(o.symbol), o.price,
                        o.quantity, int(o.side), int(o.status), o.timestamp),
        )
        t = golden_trade()
        self.assertEqual(
            wire.encode_trade(t),
            struct.pack(legacy_trade, t.buy_order_id, t.sell_order_id, t.price,
                        t.quantity, t.timestamp),
        )


class RoundTripTest(unittest.TestCase):
    def test_order_round_trip(self):
        cases = [
            golden_order(),
            Order(id=42, symbol="BTC", price=-98765, quantity=1,
                  side=OrderSide.SELL, status=OrderStatus.PARTIAL, timestamp=1678912345678),
            Order(id=0, symbol="", price=0, quantity=0,
                  side=OrderSide.BUY, status=OrderStatus.REJECTED, timestamp=0),
            Order(id=2**64 - 1, symbol="ABCDEFGH", price=2**63 - 1, quantity=-(2**63),
                  side=OrderSide.SELL, status=OrderStatus.FILLED, timestamp=2**64 - 1),
        ]
        for o in cases:
            with self.subTest(order=o):
                self.assertEqual(wire.decode_order(wire.encode_order(o)), o)

    def test_trade_round_trip(self):
        cases = [
            golden_trade(),
            Trade(buy_order_id=1, sell_order_id=2, price=-500, quantity=999999, timestamp=0),
            Trade(buy_order_id=0, sell_order_id=0, price=0, quantity=0, timestamp=1678912345680),
        ]
        for t in cases:
            with self.subTest(trade=t):
                self.assertEqual(wire.decode_trade(wire.encode_trade(t)), t)


class SymbolTest(unittest.TestCase):
    def test_make_symbol_pads_to_8(self):
        self.assertEqual(wire.make_symbol("AAPL"), b"AAPL\x00\x00\x00\x00")

    def test_make_symbol_truncates_over_8(self):
        self.assertEqual(wire.make_symbol("TOOLONGSYMBOL"), b"TOOLONGS")

    def test_symbol_round_trip_via_order(self):
        o = Order(id=1, symbol="ABCDEFGH", price=1, quantity=1,
                  side=OrderSide.BUY, status=OrderStatus.NEW, timestamp=0)
        self.assertEqual(wire.decode_order(wire.encode_order(o)).symbol, "ABCDEFGH")


class ScalingTest(unittest.TestCase):
    def test_scale_round_trip(self):
        self.assertEqual(wire.scale_price(150.25), 15025)
        self.assertEqual(wire.scale_quantity(5.0), 5000)
        self.assertEqual(wire.unscale_price(15025), 150.25)
        self.assertEqual(wire.unscale_quantity(5000), 5.0)

    def test_scale_avoids_float_truncation_bug(self):
        # The old code used int(0.29 * 100) == 28 (0.29*100 == 28.999999999999996).
        # round() in scale_price fixes this to 29.
        self.assertEqual(int(0.29 * 100), 28)  # demonstrates the old bug
        self.assertEqual(wire.scale_price(0.29), 29)  # fixed
        self.assertEqual(wire.scale_quantity(0.001), 1)

    def test_scale_constants_match_contract(self):
        self.assertEqual(wire.PRICE_SCALE, 100)
        self.assertEqual(wire.QUANTITY_SCALE, 1000)


class ErrorHandlingTest(unittest.TestCase):
    def test_decode_order_rejects_wrong_size(self):
        with self.assertRaises(ValueError):
            wire.decode_order(b"\x00" * 63)

    def test_decode_trade_rejects_wrong_size(self):
        with self.assertRaises(ValueError):
            wire.decode_trade(b"\x00" * 65)


class BackwardCompatShimTest(unittest.TestCase):
    def test_decoder_module_still_exports_api(self):
        from bridge import decoder
        o = golden_order()
        # The shim must produce identical results to the canonical module.
        self.assertEqual(decoder.encode_order(o), wire.encode_order(o))
        self.assertEqual(decoder.decode_order(wire.encode_order(o)), wire.decode_order(wire.encode_order(o)))


if __name__ == "__main__":
    unittest.main()
