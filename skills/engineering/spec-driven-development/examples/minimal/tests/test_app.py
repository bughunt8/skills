import unittest

from app import preview


class PreviewTests(unittest.TestCase):
    def test_accept(self):
        self.assertEqual(preview("hello", "local-1")[0], "accepted")

    def test_reject(self):
        self.assertEqual(preview("", "local-2")[0], "rejected")

    def test_safe_event(self):
        outcome, event = preview("hello", "local-3")
        self.assertEqual(set(event), {"event", "outcome", "correlation_id"})
        self.assertEqual(event["outcome"], outcome)

    def test_confidential_not_logged(self):
        marker = "confidential-message-9102"
        _, event = preview(marker, "local-4")
        self.assertNotIn(marker, str(event))


if __name__ == "__main__":
    unittest.main()
