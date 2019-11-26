#!/usr/bin/python3
import unittest
import tempfile
import mailbox
import email
import sys
import os

sys.path.insert(0, "../")
import maildedup

def sample_mail(subject="Sample subject"):
    msg = mailbox.MaildirMessage()
    msg.set_unixfrom('author Sat Jan 01 15:35:34 2019')
    msg['From'] = "from@localhost"
    msg['To'] = "to@localhost"
    msg['Subject'] = subject
    msg['Date'] = email.utils.formatdate()
    msg.set_payload("Sample body")
    return msg

class MaildirTests(unittest.TestCase):
    def test_add(self):
        with tempfile.TemporaryDirectory() as tempdir:
            mbox = maildedup.Maildir(os.path.join(tempdir, "maildir"))

            # Verify that _lookup() for a non-existent entry causes
            # _last_read to change.
            mbox._last_read = 0
            mbox._toc_mtimes = dict.fromkeys(mbox._toc_mtimes, 0)
            with self.assertRaises(KeyError):
                mbox._lookup("nonexistent")
            self.assertNotEqual(mbox._last_read, 0)

            # Adding a message should add it immediately to the cache.
            # Verify that there are no more lookups involved, no matter
            # where the message is created.
            mbox._last_read = 0
            mbox._toc_mtimes = dict.fromkeys(mbox._toc_mtimes, 0)
            msg = sample_mail()
            key = mbox.add(msg)
            self.assertEqual(mbox._toc[key], os.path.join("new", key))
            msg = mbox.get_message(key)
            self.assertNotEqual(msg, None)
            self.assertEqual(mbox._last_read, 0)

            msg.set_subdir("cur")
            key = mbox.add(msg)
            self.assertEqual(mbox._toc[key], os.path.join("cur", key))
            msg = mbox.get_message(key)
            self.assertNotEqual(msg, None)
            self.assertEqual(mbox._last_read, 0)

            msg.set_info("hello")
            key = mbox.add(msg)
            self.assertEqual(mbox._toc[key], os.path.join("cur", key + ":hello"))
            msg = mbox.get_message(key)
            self.assertNotEqual(msg, None)
            self.assertEqual(mbox._last_read, 0)

    def test_remove(self):
        with tempfile.TemporaryDirectory() as tempdir:
            mbox = maildedup.Maildir(os.path.join(tempdir, "maildir"))

            # Verify that _lookup() for a non-existent entry causes
            # _last_read to change.
            mbox._last_read = 0
            mbox._toc_mtimes = dict.fromkeys(mbox._toc_mtimes, 0)
            with self.assertRaises(KeyError):
                mbox._lookup("nonexistent")
            self.assertNotEqual(mbox._last_read, 0)

            # Add a message for testing purposes.
            msg = sample_mail()
            key = mbox.add(msg)
            msg = mbox.get_message(key)
            self.assertNotEqual(msg, None)
            self.assertEqual(mbox._toc[key], os.path.join("new", key))

            # Deleting a message should delete it from the cache immediately.
            mbox._last_read = 0
            mbox._toc_mtimes = dict.fromkeys(mbox._toc_mtimes, 0)
            mbox.remove(key)
            self.assertNotIn(key, mbox._toc)
            with self.assertRaises(KeyError):
                mbox.get_message(key)
            self.assertNotEqual(mbox._last_read, 0)

    def test___setitem__(self):
        with tempfile.TemporaryDirectory() as tempdir:
            mbox = maildedup.Maildir(os.path.join(tempdir, "maildir"))

            # Verify that _lookup() for a non-existent entry causes
            # _last_read to change.
            mbox._last_read = 0
            mbox._toc_mtimes = dict.fromkeys(mbox._toc_mtimes, 0)
            with self.assertRaises(KeyError):
                mbox._lookup("nonexistent")
            self.assertNotEqual(mbox._last_read, 0)

            # Add a message for testing purposes.
            msg = sample_mail()
            key = mbox.add(msg)
            msg = mbox.get_message(key)
            self.assertNotEqual(msg, None)
            self.assertEqual(mbox._toc[key], os.path.join("new", key))
            self.assertEqual(len(mbox._toc), 1)

            # Verify that replacing a message does not involve any directory
            # lookups.
            mbox._last_read = 0
            mbox._toc_mtimes = dict.fromkeys(mbox._toc_mtimes, 0)
            msg = sample_mail("New subject")
            mbox[key] = msg
            self.assertEqual(mbox._toc[key], os.path.join("new", key))
            self.assertEqual(len(mbox._toc), 1)
            msg = mbox.get_message(key)
            self.assertNotEqual(msg, None)
            self.assertEqual(msg['subject'], "New subject")
            self.assertEqual(mbox._last_read, 0)

            # Verify that there are no duplicate messages anywhere.
            mbox._last_read = 0
            mbox._toc_mtimes = dict.fromkeys(mbox._toc_mtimes, 0)
            mbox._refresh()
            self.assertNotEqual(mbox._last_read, 0)
            self.assertEqual(len(mbox._toc), 1)

if __name__ == '__main__':
    unittest.main()
