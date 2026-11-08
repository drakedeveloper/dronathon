# SKYFORGE prototype security boundary

This is a same-host research simulator, not an internet service or certified
aircraft. AirSim RPC has no authentication and is configured on loopback only.
Do not expose it through a router, public tunnel or a network-wide bind.

Implemented controls:

- Radio messages use a versioned schema, monotonic sequences, CRC32 and a
  256-bit shared-key HMAC-SHA256. Wire messages are at most999 bytes. CRC detects
  modeled accidental corruption; HMAC authenticates integrity. Neither encrypts.
- Replay protection, contiguous event ACKs, bounded4096-event ring and append
  journal. Receiver high-water marks persist before ACK; sender ACK checkpoints
  and pending authenticated events recover after radio-process restart.
- Complete corrupted journal records fail closed; only an incomplete final
  append can be trimmed. Mission/controller state recovery is a separate gap.
- Native control packets have a distinct key, finite vectors, bounded speed,
  energy, zones, mission phases and a short lifetime on the simulator clock.
  Sequence acceptance happens after payload validation.
- A post-verification state bit flip is detected by the reflex CRC seal, causing
  a hold. Stale odometry/lidar/commands cause holds. Agents do not directly write
  motors, and a route shield can overrule planning.
- Dashboard Host/Origin checks, CSRF token, bounded request bodies and safe goal
  envelope. It renders untrusted event text using textContent. Local diagnostic
  camera/state files are separate from the simulated radio channel.
- Secret key files, credentials, virtual disks and datasets are excluded from
  Git and Docker contexts. Source setup downloads preserve checksums/provenance.

Residual limits: local privileged processes are trusted; internal diagnostic
UDP statistics and the AirSim API are not protected against a hostile process
on the same laptop. This is not TLS, secure boot, hardware ECC, arbitrary memory
fault tolerance or radio-jamming certification. No person is classified hostile
from a real photo solely because they are human. All hostile simulation labels
are declared scenario roles and cause avoidance only.

Evidence is in tests/test_security.py, test_radio_integration.py,
test_native_mailbox.py and the recorded live campaign. A rejected packet alone
does not prove mission success; independently audit the final landing/deliveries.
