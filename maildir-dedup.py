#!/usr/bin/python3
import email.utils
import argparse
import mailbox
import hashlib
import copy
import io
from collections import defaultdict

def maildir_dedup(mbox, dryrun=False):
    # Enumerate all messages in the Maildir and group messages by
    # the X-GMAIL-MSGID header field.
    key_by_msgid = defaultdict(list)
    for key, msg in mbox.iteritems():
        msgid = msg['X-GMAIL-MSGID']
        if msgid is None:
            continue

        key_by_msgid[msgid].append(key)

    # For any msgid present two or more times, compute hash of the
    # message body to verify that they are indeed the same.
    for msgid, keys in key_by_msgid.items():
        if len(keys) < 2:
            continue

        msg_by_digest = defaultdict(list)
        for key in keys:
            msg = mbox.get_message(key)

            # Remove mailbox / label attributes before computing the hash.
            tmp_msg = copy.deepcopy(msg)
            del tmp_msg['X-getmail-retrieved-from-mailbox']
            del tmp_msg['X-GMAIL-LABELS']

            # Get a binary representation of the message. This is the same
            # method that is also internally used by Pythons Maildir implementation.
            buf = io.BytesIO()
            mbox._dump_message(tmp_msg, buf)
            buf.seek(0)
            buf = buf.read()
            assert len(buf) > 0

            # Record the hash of the message.
            h = hashlib.sha512()
            h.update(buf)
            msg_by_digest[h.digest()].append((key, msg))

        # If the hash for two messages matches we consider them identical.
        # Merge both messages by combining their header fields.
        for _, msgs in msg_by_digest.items():
            if len(msgs) < 2:
                continue

            # Sort by timestamp. The oldest message is kept, all others are
            # deleted (after merging any relevant header fields).
            msgs = sorted(msgs, key=lambda key_msg: key_msg[1].get_date())

            # Grab the oldest message, update the timestamp to the newest one.
            new_key, new_msg = msgs.pop(0)
            new_msg.set_date(msgs[-1][1].get_date())
            changed = False

            # Now collect all the header fields.
            for _, msg in msgs:
                for key, val in msg.items():
                    if key not in ('X-getmail-retrieved-from-mailbox', 'X-GMAIL-LABELS'):
                        continue
                    if (key, val) in new_msg.items():
                        continue
                    new_msg[key] = val
                    changed = True

            if changed:
                print ("Updating message %s" % (new_key,))
            for key, msg in msgs:
                print ("Deleting duplicate message %s" % (key,))

            if dryrun:
                continue

            # Update the initial message, delete all the other ones.
            # To avoid unnecessary write accesses, only update the file if
            # anything changed.
            if changed:
                mbox[new_key] = new_msg
            for key, _ in msgs:
                mbox.remove(key)
            mbox.flush()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Deduplicate mails in Maildir")
    parser.add_argument('--dryrun', action='store_true', help="Do not perform any changes")
    parser.add_argument('path', nargs='+', help="Location of the Maildir")
    args = parser.parse_args()

    for path in args.path:
        mbox = mailbox.Maildir(path, create=False)
        maildir_dedup(mbox, dryrun=args.dryrun)
