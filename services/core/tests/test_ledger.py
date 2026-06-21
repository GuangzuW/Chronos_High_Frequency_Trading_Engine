import unittest

from services.core.ledger import EXTERNAL, Ledger, LedgerError


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.ledger = Ledger()

    def test_fund_and_balance(self):
        self.ledger.fund("alice", 100_000, "fund-1")
        self.assertEqual(self.ledger.balance("alice"), 100_000)
        self.assertEqual(self.ledger.balance(EXTERNAL), -100_000)

    def test_total_balance_invariant_is_zero(self):
        self.ledger.fund("alice", 100_000, "f1")
        self.ledger.fund("bob", 50_000, "f2")
        self.ledger.transfer("alice", "bob", 25_000, "t1")
        self.assertEqual(self.ledger.total_balance(), 0)

    def test_unbalanced_post_raises(self):
        with self.assertRaises(LedgerError):
            self.ledger.post("bad", [("a", 100), ("b", -50)])

    def test_post_is_idempotent(self):
        legs = [("a", 100), ("b", -100)]
        self.assertTrue(self.ledger.post("t", legs))
        self.assertFalse(self.ledger.post("t", legs))  # no-op second time
        self.assertEqual(self.ledger.balance("a"), 100)

    def test_reserve_release_and_available(self):
        self.ledger.fund("alice", 100_000, "f1")
        self.ledger.reserve("h1", "alice", 30_000)
        self.assertEqual(self.ledger.available("alice"), 70_000)
        self.assertEqual(self.ledger.balance("alice"), 100_000)
        self.ledger.release("h1")
        self.assertEqual(self.ledger.available("alice"), 100_000)

    def test_reserve_insufficient_raises(self):
        self.ledger.fund("alice", 10_000, "f1")
        with self.assertRaises(LedgerError):
            self.ledger.reserve("h1", "alice", 20_000)

    def test_journal_records_postings(self):
        self.ledger.fund("alice", 100_000, "f1")
        self.assertEqual(len(self.ledger.journal()), 1)


if __name__ == "__main__":
    unittest.main()
