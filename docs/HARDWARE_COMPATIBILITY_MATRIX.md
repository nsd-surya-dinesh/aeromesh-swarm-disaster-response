# HARDWARE COMPATIBILITY MATRIX — AeroMesh-Swarm Stage 2
Created: 2026-10-11 | Budget: ~₹66,687 + GST (from spreadsheet, thermal/UWB pricing TBD)
Status: PARTIAL — budget verified; thermal and UWB models unspecified; no physical tests run.

| Component | Budget Qty | Function | Known Spec | Unknown / Unverified | Driver / Protocol | Risk | Test Needed | Status |
|---|---|---|---|---|---|---|---|---|
| Pixhawk 2.4.8 + GPS | 2 | Flight controller | Board rev; MAVLink; ArduPilot compatible | Firmware version; GPS module (u-blox?) | MAVLink / ArduPilot | MED | Firmware check; SAT lock test | PARTIAL |
| Raspberry Pi Zero 2 W | 2 | Companion computer | 4-core ARM; WiFi; 512MB RAM | OS version; Python env; USB/serial adapter | Linux / pymavlink | MED | CPU/RAM load test; UART bridge | PARTIAL |
| A2212 1000KV motor | 8 | Propulsion | 1000KV; 2S-3S; ~10-15A | Exact thrust curve; prop match | ESC PWM | LOW (budget listed) | Throttle response; thermal | PASS (listed) |
| 30A ESC | 8 | Motor drive | 30A; BEC 2-3A | BEC voltage; firmware | PWM / DSHOT | LOW | Current draw; BEC load | PASS (listed) |
| 1045 propellers | 4 + spares | Lift | 10in; 4.5in pitch | Balance; material | Mechanical | LOW | Balance check; vibration | PASS (listed) |
| F450 frame | 2 | Airframe | 450mm; plastic/carbon | Weight; arm strength | Mechanical | LOW | Structural load | PASS (listed) |
| 4S 4200mAh LiPo | 2 | Main battery | 4S; 4200mAh; ~60C? | Exact C-rating; voltage sag | Battery management | MED | Voltage under load; RC failsafe | PARTIAL |
| Battery charger | 1 | Charging | 4S Li-po compatible | Charge rate; balance | Charge protocol | LOW | Charge cycle; balance check | PASS (listed) |
| RC TX/RX | 1 set | Manual override | 2.4GHz; PPM/IBUS? | Channel count; range | RC protocol | MED | Range; failsafe; channel mapping | PARTIAL |
| 915 MHz telemetry kit | 2 | GCS link | 915 MHz; SiK? | Exact module model; baud; protocol | MAVLink / SiK | MED | Link test; range; interference | PARTIAL |
| Thermal sensing module | 1 | Thermal survey | **MODEL UNKNOWN** | Interface (I2C/I2C? USB?); resolution; FOV | Unknown | HIGH — BLOCKED | Datasheet identification | BLOCKED |
| UWB module | 1 | Ranging / positioning | **MODEL UNKNOWN** | Protocol (DW1000/UWB-1?); anchors needed; range | Unknown | HIGH — BLOCKED | Datasheet; placement check | BLOCKED |
| Wiring / connectors / power reg | — | Integration | — | Pinouts; voltage levels; ground | Electrical | MED | Continuity; ground loop; voltage | BLOCKED (needs design) |

NOTES:
- Thermal and UWB have NO identifiable model, datasheet, or interface specification.
- System must remain functional in simulation when these optional sensors are unavailable.
- No physical UAV tests have been performed (NOT RUN for all hardware items).
- No motor tests performed (safety rule: never arm physical motors).
- Recommend: purchase thermal and UWB with datasheets before any hardware integration claims.
