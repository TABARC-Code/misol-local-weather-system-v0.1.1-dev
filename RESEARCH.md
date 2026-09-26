Note: I used ai to rewrite this as loads of repos and notes and it was getting messy, im tired and its late or early dependng on view.

## Method

This project was designed after a public GitHub survey of repositories mentioning MISOL weather hardware plus a smaller set of EasyWeather/Ecowitt receivers. The research was basically used to identify protocols (im lazy and busy), deployment patterns and failure modes. No upstream source file was copied into MISOL Local.

The devices console's own manual was treated as the primary hardware description. Public repositories were secondary evidence for neighbouring MISOL models and the wider Fine Offset/Ecowitt ecosystem.

## MISOL repositories surveyed

### `andreypopov/misol-weather-station`

Python project with MQTT/etcd and Node-RED material. Its README says it was itself forked from a Bitbucket LoRa weather-station project. The GitHub repository has **no licence declared**.

Ok the iseful design observation: MISOL projects often become bridges rather than dashboards. That supports keeping acquisition, storage and output as separate layers here.

### `paveldn/misol-esphome`

ESPHome component for an RS485-output MISOL station. It documents 9600 baud, 8N1 serial, a roughly 16-second reporting interval and a broad sensor set: temperature, humidity, pressure on some models, wind, gust, rain, light and UV.

This is a different hardware path from my Wi-Fi console, so none of its parsing implementation belongs in this repo. The useful bits i got from it was the lesson to keep the internal observation model broad enough for the usual MISOL sensor family. You always learn

### `heesbeen/misol-esphome` and `selwynm99/misol-esphome`

Forks of `paveldn/misol-esphome`. They did not justify a separate implementation path for this project. I just nad a read and poked around the repo

### `greenioiot/MisolWeatherStation`

Arduino/ESP32 experiment reading a MISOL data frame and decoding wind, temperature, humidity, speed, gust, rainfall, UV, light and pressure. No separate licence was visible in the repository root during the survey.

Found useful observation: preserve raw input beside interpreted values. Several hobby projects hard-code byte positions or conversion factors, which works until the adjacent model is *nearly* the same.

### `greenioiot/WeatherStationMisol_SKT`

Related Arduino experiment with similar MISOL sensor fields. Again, it is an RS485/serial-style acquisition route rather than the custom-web upload route used here.

### `panlawan/ESP32-Misol_WeatherStation-RS485_Arduino`

Small Arduino RS485 reader with checksum handling and common MISOL weather fields. Its README is minimal. Useful mainly as corroboration that checksum validation and tolerant model handling matter on the serial side. i got ueful notes.

### `sidewinderz0ne/Weather-Station-Project`

ESP32 project with local AP mode, web UI, SD-card CSV logging, JSON output, configuration, watchdog and file management.

Useful ideas retained at the *behavioural* level: local-first operation, a human-readable JSON representation, persistent storage, and a simple diagnostic surface. The implementation here is completely different and runs on a normal Windows/Linux host rather than an ESP32.

### `jaja2302/Weather-Station-Project`

Closely related to the Sidewinder project and includes Raspberry Pi material. It did not add a distinct protocol requirement for my MISOL Local release. but worth a read, and tidy code

### `floatAsNeeded/LineaMeteoStazione-Personalised-Weather-Station`

MIT-licensed DIY weather station supporting several sensor families including MISOL. Hardware-heavy, with sender/receiver sketches and printable/electronic design material. Useful as evidence that 'MISOL' covers more than one practical integration route.

### `sydkahn/LineaMeteoStazione-Personalised-Weather-Station`
### `chrismayu/LineaMeteoStazione-Personalised-Weather-Station`

Forks/variants of the LineaMeteoStazione project. No separate feature were imported.

### `sclo/misol-weather-station`
### `esb82/misol-weather-station`
### `damico/misol-weather-station`
### `Odleral/misol-weather-station`
### `javieramartineml/misol-weather-station`
### `YurySokolov/misol-weather-station`
### `UB-EUSS/misol-weather-station`

These are forks or close derivatives of the `andreypopov/misol-weather-station` family. They were checked so the survey did not accidentally treat every search result as an independent design. One fork adds extra local material, but the family remains substantially the same upstream lineage.

## Adjacent receiver projects

### `sacarlson/easyweather-wifi-PWS-recorder`

GPL-3.0 local Python receiver/repeater for EasyWeather Wi-Fi stations. It stores data locally, can repeat it onward, and explicitly warns that its early implementation was not designed for exposed WAN use.

Behavioural lessons used here: local receiver first, SQLite is perfectly adequate for a pet weather logger, and LAN-only should be the default. **No GPL code was copied.**

### `the-rene/wetta-collector`

Small collector that expects the station to use a custom server with Ecowitt format and writes observations to MySQL. This reinforces the custom-server interception route but not the storage choice.

### `bachya/ecowitt2mqtt`

MIT-licensed, mature receiver for Fine Offset and white-labelled stations. It supports Ecowitt, Ambient Weather and Wunderground-style inputs, MQTT, unit conversion, calculated sensors, multiple gateways and Home Assistant discovery.

Useful architectural lessons: input format should be explicit, raw data should remain available, unknown gateways should not crash the service, and MQTT belongs behind a clean observation model rather than inside the HTTP parser.

MISOL Local deliberately starts much smaller. Calculated comfort indices, broad battery taxonomies and multi-gateway policy layers are not necessary for the first live capture.

### `bdavj/ecowittHttpBlaster`

MIT-licensed project intended to let an Ecowitt gateway publish to more than one custom server. It is a useful reminder that forwarding can become desirable later. Forwarding is left for a later milestone rather than being smuggled into v0.1.

## Design decisions from the survey

1. **Use the console's custom HTTP upload before attacking RF.** It is the least destructive, easiest-to-debug path for this unit.
2. **Core receiver has no web-framework dependency.** Python's standard library is enough for a LAN POST receiver and keeps Windows setup dull.
3. **SQLite, not a database server.** This is a side project. Requiring PostgreSQL to store a few readings every 16 seconds would be performance theatre.
4. **Raw + normalised storage.** New firmware fields survive even when the parser does not recognise them yet.
5. **Secrets are redacted.** `PASSKEY` is used only to derive a local station fingerprint and is not written to the database.
6. **MQTT is optional.** Home Assistant can be added without making MQTT a condition of receiving weather data.
7. **RF/rtl_433 is a later parallel input.** Once the HTTP path is proven, RF gives a useful independent observation path rather than an unnecessary first obstacle.

## Licence handling

- `sacarlson/easyweather-wifi-PWS-recorder`: GPL-3.0. Behaviour studied, code not reused.
- `bachya/ecowitt2mqtt`: MIT. Behaviour studied; this repository still uses its own implementation.
- `bdavj/ecowittHttpBlaster`: MIT. Behaviour studied; forwarding deferred.
- `floatAsNeeded/LineaMeteoStazione-Personalised-Weather-Station`: MIT. Hardware/ecosystem context only.
- several MISOL hobby repositories: no licence visible. Treated as read-only behavioural references.
