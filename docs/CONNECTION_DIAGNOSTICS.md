# MirvDesk 1.6.1 connection diagnostics

On a non-local peer with a configured relay and no force-relay policy,
the client starts a relay attempt after 2.5 seconds (1.2 seconds after
a remembered direct failure), without cancelling the direct attempt.
When relay is ready, P2P has another 200 ms to complete. Relay failure
does not interrupt P2P.

This is a hedge, not a hard time limit. Other connection timeouts remain.

Linux logs: ~/.local/share/logs/MirvDesk/
Relevant lines: rendezvous server, punch attempt with, peer address,
ms used to ... punch hole, used to establish, hedged relay failed.

Test P2P and relay-only paths on different NATs, including mobile.
Check no duplicate remote sessions or approval dialogs are created.

On Android discovery now precedes initial NAT probes. Android release
CI checks every bundled native library for the required build URL.


## Rendezvous and transport timing (1.7 development)

The client now emits structured log messages:

- stage=rendezvous_attempt_no_reply: each missed hbbs rendezvous reply with duration. The three retries have 3-, 6-, and 9-second response windows, up to 18 seconds in total.
- stage=rendezvous_done: hbbs registration/punch negotiation completed.
- The existing "used to establish TCP/UDP/WebRTC/Relay connection" log marks transport established.
- stage=secure_ready: peer security handshake completed.

Compare the timestamps for one affected connection. Slow rendezvous may indicate hbbs, filtering or peer registration; slow transport suggests NAT, P2P or relay; slow secure_ready suggests the cryptographic handshake or retry. These are diagnostics only, not proof of a particular bottleneck.
