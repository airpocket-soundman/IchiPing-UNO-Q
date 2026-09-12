import unittest

from request_mailbox import RequestMailbox


class RequestMailboxTests(unittest.TestCase):
    def test_empty_and_masking(self):
        mailbox = RequestMailbox()
        self.assertIsNone(mailbox.take())
        self.assertTrue(mailbox.submit(0xFF))
        self.assertEqual(mailbox.take(), 0x1F)
        self.assertIsNone(mailbox.take())

    def test_newest_request_coalesces(self):
        mailbox = RequestMailbox()
        self.assertTrue(mailbox.submit(1))
        self.assertFalse(mailbox.submit(2))
        self.assertEqual(mailbox.take(), 2)


if __name__ == "__main__":
    unittest.main()
