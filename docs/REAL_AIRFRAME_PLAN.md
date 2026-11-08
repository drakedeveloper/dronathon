# Real airframe design and calibration boundary

The chosen reference is an X500-class, repairable research/rescue quadrotor.
Its current executable model is the pinned PX4 X500 simulator aggregate plus
three 50 g supply kits and a 40 g mount. It is not a measured Holybro product.
The JSON records every mass, centre of gravity, inertia and source hash.

## Why this class

A documented research platform is easier to reproduce, repair and calibrate
than a speculative military-shaped airframe. Holybro's current X500 V2 ARF
listing is USD329 before controller, battery, computer, shipping and tax; its
frame-only variant is USD135. Its supplied motors are 2216 KV920 with 1045
propellers. Source: https://holybro.com/collections/multicopter-kit/products/x500-v2-kits
The ARF variant was marked unavailable when checked; these are listed prices,
not a confirmed purchasable local bill of materials.

Those 10-inch product propellers differ from the current simulator's declared
0.28 m propeller assumption. The current thrust coefficient is a published
simulator parameter, not a motor/propeller bench curve. A purchase recommendation
does not establish an exact physics match; do not relabel the model as calibrated.

## Current calculated configuration

| Quantity | Current reference |
|---|---:|
| All-up mass including three kits/mount | 2.2543 kg |
| Total maximum modeled thrust | 34.1943 N |
| Static thrust/weight | 1.5467 |
| Hover angular speed | about 804 rad/s, 7,678 RPM |
| Two-blade blade-passing frequency at hover | about 256 Hz |
| Battery design assumption | 4S, 5 Ah, nominal 74 Wh |
| Mission energy allowance | 15 Wh, separate from nominal battery capacity |

The simulation currently keeps its initial mass after virtual delivery. That is
conservative for modeled energy use but does not simulate a physical payload
mass change. Battery sag, measured propeller thrust/torque and real thermal
limits are not identified. Rotor rise/fall filtering also differs between
source and native implementation; see airframe-build.json after building.

## Realistic delivery tradeoff

A 50 g package released from 2.2 m has ideal gravitational energy mgh = 1.08 J
and vacuum impact speed sqrt(2gh) = 6.57 m/s. Drag changes these values, but a
virtual hover event is not proof of a safe real delivery. The final delivery
zone should be beside a person, camera-checked and clear of hazards.

A ground-placement winch is a useful later hardware experiment: reducing final
release height to 0.3 m reduces ideal energy to 0.147 J. Its extra motor, cable
and mount mass must be added to the profile, along with pendulum motion and
centre-of-gravity changes. No winch is claimed in the present implementation.

## Quiet propulsion and shape

Experimental toroidal propellers are an investigation, not a claim of silence
or a guaranteed efficiency improvement. Compare thrust at equal electrical
power and sound level at equal thrust, with the same microphone geometry and
background noise. A quieter result at lower thrust is not a fair comparison.
MIT Lincoln Laboratory's technology description is a starting point:
https://www.ll.mit.edu/partner-us/available-technologies/toroidal-propeller

Prioritize adequate rotor clearance, a low centre of gravity, replaceable arms,
unobstructed cameras and reliable cooling. Decorative ducts or unusual body
shapes add mass/drag and can obstruct the camera or change rotor inflow. They
must earn their place through measured mission benefit.

## Measurements needed for hardware agreement

Measure actual ready-to-fly mass and centre of gravity with payload states;
identify inertia or bound it from component geometry; record motor/propeller
thrust, torque, current and RPM across the operating range; identify motor
response, drag and battery voltage under load. Then check hover power, climb,
step response and return-energy prediction against observations. Preserve the
measured and assumed values separately in the profile and report the residuals.
