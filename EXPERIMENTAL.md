# Experimental status

MISOL Local is a pet project, not a safety system and not a calibrated weather service.

The current receiver is intended for LAN use while we learn the exact payload produced by one MISOL/Fine Offset-derived console. Protocol handling is intentionally tolerant: recognised values are normalised, unrecognised fields are retained in redacted raw form, and malformed values are rejected per-field rather than taking down the whole report.

Things not yet proven on the target hardware:

- the exact `stationtype` string;
- which rain counters this firmware emits;
- whether the console POSTs, GETs, or changes method between protocol modes;
- whether its path handling insists on a trailing slash;
- whether battery flags are present;
- whether the console retransmits after a failed upload;
- whether calibration is applied before upload.

None of those are reasons to make the first version cleverer. They are reasons to capture a real packet before pretending certainty.


## Quality and calibration

The quality-control and calibration features are experimental. Their output is advisory until enough real station history exists to judge the thresholds.

Raw observations are preserved. A QC rejection affects only derived processing when `reject_impossible = yes`. Calibration learns only from agreeing external references and does not alter `best_estimate` unless `apply_to_best_estimate = yes` is explicitly enabled.

External weather services are references, not ground truth. Model grids, satellite pixels and a sensor mounted on a house do not observe exactly the same air parcel. Apparent disagreement can be real local weather rather than sensor error.
