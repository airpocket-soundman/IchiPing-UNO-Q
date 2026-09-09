# UNO Q test-only SSH key

This directory records the public key for the dedicated IchiPing UNO Q test
board. The private key is local-only and ignored by Git. Never authorize this
test key on production or personal devices.

Test-board credentials:

- Host: `unoQ4G.local`
- User: `airpocket`
- Password: managed locally; not published in the repository.

The vendor-provided `arduino` account remains in place because Arduino App Lab
and board services may depend on it.

Connect after the public key has been installed on the board:

```powershell
ssh -i uno_q/test_ssh/unoq_test_ed25519 airpocket@unoQ4G.local
```

Expected public-key fingerprint:

```text
SHA256:ESdIoV47BI7TyWj7nfFmxUl9QEtcJZEdxN0sScs/Vxk
```

Anyone holding the private key and able to reach the board can log in.
Remove it from `/home/airpocket/.ssh/authorized_keys` when the test
board is retired or repurposed.
