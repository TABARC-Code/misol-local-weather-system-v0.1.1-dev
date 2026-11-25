# Weather quality, fusion and calibration

MISOL Local treats raw observations, external references and derived estimates as different things. That sounds obvious until software starts averaging them together and quietly loses track of which instrument actually measured what.

## Raw observation

The normalised MISOL reading is preserved as the local observation. Quality-control flags do not rewrite it. Calibration does not rewrite it. External providers do not rewrite it.

That record is the evidence trail.

## Quality control

The current QC pass checks broad physical plausibility for temperature, humidity, pressure, wind, rain, solar radiation and UV. It also checks selected rates of change against the previous station observation and tests that reported gust speed is not implausibly below sustained wind speed.

The result is metadata with a descriptor of `pass`, `questioned` or `rejected`, plus per-field flags.

These are intentionally broad checks. They catch nonsense. They do not claim that a reading inside the allowed range is meteorologically correct.

If `reject_impossible = yes`, only fields that fail a physical range check are removed from the derived fusion input. Raw history remains untouched.

## External references

OpenWeather is treated as a regional blended current-weather reference. Open-Meteo current conditions are treated as model-based reference data. Open-Meteo satellite radiation is treated as a satellite observation for solar comparison.

Each provider is isolated. Failure, timeout or bad JSON from one provider is recorded in provider health and does not stop local data ingestion.

Provider age is checked before fusion. Stale external data should not win an argument with a fresh local observation.

## Fusion modes

`compare_only` records comparison metadata and leaves the best estimate local.

`fill_gaps` keeps every available local value and fills only missing fields from a fresh external provider.

`guarded` can replace a field in the derived best-estimate stream only when at least two external sources agree within half the configured tolerance and both disagree with the local value beyond the full tolerance.

One outside API is never enough to overrule an existing local value.

## Historical calibration

Calibration samples are created only when at least two external sources agree closely enough to form a reference. The learner records local value, reference value, bias and provider provenance.

Profiles use median bias rather than a simple mean so a handful of odd comparisons have less influence. Stability is measured with median absolute deviation. A profile must also reach the configured minimum sample count before it can be considered stable.

Automatic application is off by default.

When enabled, a stable correction applies only to the derived best-estimate field when that field is still locally sourced. The local observation remains unchanged and the applied correction is stored as metadata.

## Things this deliberately does not claim

Two weather APIs are not automatically two independent measurements. They may consume common observations or related forecast models.

A satellite pixel is not the same physical location as a garden light sensor.

A model's 10 metre wind field is not equivalent to an anemometer mounted below roof height.

Long-term disagreement can indicate sensor bias, installation effects, shading, local microclimate or provider bias. The software records the evidence. It does not pretend to know which explanation is correct without enough history.

## Useful API endpoints

`/api/crosscheck` shows external readings, errors and provider health.

`/api/calibration` shows sample counts and learned profiles.

`/api/latest` shows the latest local, quality, external and derived data.

`/health` reports receiver state and external-provider health.

This entire layer remains experimental until it has been exercised against long-running real hardware.
