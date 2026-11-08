# Recorded prototype evidence

Local measurements, not competition acceptance or general safety certification.
The project-generated coastal scenario supplies explicit simulated distress
radio metadata. Camera confirmation is still required before delivery.

## Mission c5da6412: supplies and safe return

- Three virtual hover deliveries; no physical release is claimed.
- 171.06 simulation seconds and 112.49 m trace length.
- Returned to base with 5.481 Wh from a 15 Wh initial battery.
- Geometric checker: zero hazard-zone entries and static-collision segments.
- The checker sweeps a vehicle envelope against static boxes and hazard
  cylinders. Moving contacts, contact dynamics and rendered coverage are not
  certified.
- Image-receive-to-AI-command p95 remained about 215 ms under local load, above
  the 150 ms requirement. Complete capture-to-motor latency is not measured.

The summary JSON is stored next to this file. Local source traces and journals
remain under `artifacts/`, excluded from git. Earlier mission 6c012085 returned
with two deliveries and 2.934 Wh. Mission eb5d81bc delivered three supplies but
emergency landed short of base. These failures motivated conservative energy
budgeting and more directed search. This is not a controlled single-factor
ablation, and one successful run is not repeatability evidence.

A second run, `55b6ec39`, with the independent route shield enabled, completed
three virtual deliveries and returned with 5.803 Wh in 166.46 simulated seconds
over 111.82 m. Its geometric checks also found zero hazard entries/static
collisions. Receive-to-AI-command p95 was about 172 ms, still above the target.

`airsim-visible-flight.json` records a separate native AirSim physics demo:
climb to about 8 m, forward/sideways travel, return and ground-confirmed landing.
It used velocity commands; it did not run the rescue agents. `-Scenic` is an
explicit camera-teleport preview, a different mode from this physics demo.

## Vision and communications

Training/development validation uses 70/20 rendered images from two scene seeds,
not real-world photographs. Seed 33 was inspected and is not a blind test.
Input 384 reduced inference time but worsened casualty precision/recall at IoU
0.5. The active runtime keeps input 512. Mixed-resolution benchmarking keeps
secondary 512 and primary 384; it is not selected for deployment.

Real socket outage/replay/bitflip tests exist. A prior live outage preserved
autonomy and reconnection but contained no buffered events. A later live test
hit a dashboard snapshot race, which was fixed. Do not count that aborted test
as buffered replay proof. Receiver restart cursors now persist before ACK.
Onboard journal recovery after process death remains unfinished.

HMAC authenticates packets, CRC detects modeled corruption, and replay counters
reject duplicates. Encryption, ECC hardware and arbitrary hardware fault
tolerance are not claimed. Test results are summarized in `checks.json`.

Native AirSim: `native-visible-flight.json` records a bounded physical flight
and ground-confirmed landing. `native-failed-rescue-6049db46.json` is a failed
rescue audit: three virtual events, zero correct casualty deliveries, safe
return. Do not count event totals as rescue success. Native pipeline p95 was
about 182 ms and does not satisfy the competition deadline. Retraining and
negative-evidence/fresh-sighting fixes still require mission verification.
