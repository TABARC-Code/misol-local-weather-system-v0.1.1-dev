# Future notes

This is a working dump, not a promise list. I would rather leave half-formed ideas visible here than turn every passing thought into a milestone and spend the next year serving a roadmap I wrote while the coffee was still warm.

## Real station evidence first

The next useful dataset is not another API. It is several weeks of real MISOL traffic with firmware version, packet interval, missed reports, rain-counter behaviour and the occasional genuinely ugly weather day.

I want fixture files made from redacted real packets. Those should become regression tests. Consumer weather firmware has a talent for being almost consistent, which is generally worse than being obviously broken.

Rain deserves particular attention. Cumulative counters, hourly totals and provider-specific rolling windows can look interchangeable until midnight, a reboot or a heavy shower proves otherwise.

## Calibration needs seasons, not enthusiasm

The current learner can identify a stable median bias when independent references agree. That is a useful start, but a bias that appears stable over three mild November days is not necessarily stable in direct summer sun or freezing fog.

I may add profiles by condition, such as day versus night, wet versus dry and broad temperature range. I do not want to create a little machine-learning circus merely to correct a thermometer. Simple evidence should remain understandable.

Sensor ageing is more interesting. A slow change in median bias over months could become a drift warning. That should be reported as a trend with dates and evidence, not as an automatic correction quietly chasing the sensor downhill.

## Better independence scoring

OpenWeather and Open-Meteo are useful references, but they are not guaranteed to be statistically independent. Both can ingest overlapping observation networks or similar model families.

A later provider registry could label source type: local instrument, nearby ground observation, numerical model, radar, satellite or blended service. Consensus could then require diversity of source type rather than merely two different provider names.

For the UK, a direct Met Office observation feed would be worth investigating if access terms and practical limits make sense. A nearby SYNOP or METAR station could also provide a strong pressure and temperature sanity check, although distance and elevation must be accounted for.

## RF reception remains tempting

An rtl_433 adapter still makes sense as an optional second local path. It could read JSON from an existing rtl_433 process and feed observations into the same internal data model without linking GPL code into this project.

That would let the system compare the console's HTTP upload with the outdoor transmitter itself. It also provides continuity if the console Wi-Fi fails.

I am not folding an SDR decoder into the core application. That turns a weather logger into a radio project and doubles the number of things that can be broken before breakfast.

## Home Assistant

MQTT works, but proper Home Assistant discovery would remove repetitive manual entity configuration. It should expose stable entity IDs, device metadata, availability and unit classes.

I would publish local observation, best estimate and selected quality state as separate entities or attributes rather than replacing one with another. A dashboard should make it obvious when a displayed value came from the roof sensor and when it came from gap filling.

## Provider health

The external manager now records last attempt, last success, latency and consecutive failures. That can grow into a small reliability history.

There is no need for an absurd decimal confidence score. A source can be fresh, stale, failing, frequently divergent or healthy. Those labels are explainable.

Rate-limit handling also needs attention. External providers should back off after repeated failures rather than politely hammering a dead endpoint every ten minutes forever.

## Database housekeeping

SQLite remains the right default for this scale. One station reporting every sixteen seconds is not a cluster-computing problem.

I may add retention rules for raw payloads while keeping normalised observations longer. Vacuum and backup commands would help people who want the station running for years.

Schema migrations need tests every time the database changes. Weather data becomes valuable precisely because it accumulates, so a clever migration that eats three years of rain history is not clever.

## Installation

Windows still deserves the easiest path because that is where a complete beginner is most likely to encounter Python packaging, firewall prompts and local IP addresses all at once.

A signed standalone executable could eventually remove Python installation entirely. I would only do that once the protocol and data model settle down, otherwise every small code change becomes a packaging exercise.

Linux service files are straightforward and probably worth adding sooner. Docker is optional later. This project does not need six containers to receive an HTTP form post.

## Security

The HTTP listener is intended for a trusted LAN or isolated IoT VLAN. I do not intend to pretend that a tiny built-in HTTP server is a public internet service because it has a couple of security headers.

An IP allow-list could be useful. So could a simple per-client rate limit and clearer warnings when binding outside localhost.

Raw packet logging needs to stay redacted. API credentials belong in configuration or environment variables, never diagnostics. If a future forwarding feature sends data to third parties, credentials must not leak into SQLite or normal logs.

## Compatibility

I want a real compatibility matrix: branding, model, firmware, radio frequency if known, accepted upload protocol, working fields and quirks.

The useful contribution from another user is not a vague message saying their station works. It is a redacted packet, console model, firmware version and the exact custom-server settings that produced it.

## Things I am not planning

No hosted MISOL Local cloud.

No public multi-user dashboard.

No account system.

No attempt to replace the manufacturer's console firmware.

No claim that every Fine Offset-derived station is compatible because the plastic shell looks familiar.

If this pet project grows far enough that it genuinely needs those things, I would rather split them into separate software than turn the receiver into a monolith.

## What success looks like

The useful end state is boring. The station reports reliably, local history survives internet outages, questionable readings are visible, external references provide context rather than authority, and long-term drift can be spotted before it quietly ruins a year of data.

If I can also point an SDR at it later and compare the radio packet with the console upload, fine. Everyone needs one unnecessary rabbit hole.
