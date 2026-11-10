"""Measured fuel consumption, built from odometer and fuel-% samples.

The API gives only the fuel level in % and the odometer. We watch both on every
poll. Each interval gives a segment: km driven and % of tank used. Intervals
with a refuel are skipped. The consumption is the total over the last
``WINDOW_KM`` km, so one noisy reading does not matter.

Segments store the % of tank used, not litres. A change of the tank size option
then applies to the old data too.
"""

from __future__ import annotations

WINDOW_KM = 500.0  # keep about this much driving in the window
MIN_KM = 50.0  # no result before this distance (the gauge steps are coarse)
REFUEL_JUMP_PCT = 2.0  # a rise bigger than this is a refuel
MAX_STEP_KM = 300.0  # a bigger jump between two polls is not trusted


class ConsumptionTracker:
    def __init__(self, segments=None, last=None) -> None:
        # Each segment is [km_driven, percent_of_tank_used].
        self.segments: list[list[float]] = [list(s) for s in (segments or [])]
        self.last: tuple[float, float] | None = tuple(last) if last else None

    @property
    def window_km(self) -> float:
        return round(sum(s[0] for s in self.segments), 1)

    def add_sample(self, km, fuel_pct) -> bool:
        """Add one reading. Returns True if the stored state changed."""
        if km is None or fuel_pct is None:
            return False

        if self.last is None:
            self.last = (km, fuel_pct)
            return True

        last_km, last_fuel = self.last
        d_km = km - last_km
        used = last_fuel - fuel_pct  # positive = fuel went down

        # Odometer went back or jumped: start again from this reading.
        if d_km < 0 or d_km > MAX_STEP_KM:
            self.last = (km, fuel_pct)
            return True

        # Car did not move. The gauge can move by itself (fuel slosh), so ignore it.
        if d_km == 0:
            return False

        if used < -REFUEL_JUMP_PCT:
            # Refuel in this interval. Skip it and use the new level as the base.
            self.last = (km, fuel_pct)
            return True

        if used < 0:
            # Small rise: gauge noise. Count the km, keep the old fuel level as base.
            self.segments.append([d_km, 0.0])
            self.last = (km, last_fuel)
        else:
            self.segments.append([d_km, used])
            self.last = (km, fuel_pct)

        self._trim()
        return True

    def _trim(self) -> None:
        while len(self.segments) > 1 and (
            sum(s[0] for s in self.segments) - self.segments[0][0] >= WINDOW_KM
        ):
            self.segments.pop(0)

    def consumption(self, tank_liters: float) -> float | None:
        """Measured consumption in L/100 km, or None if there is not enough data."""
        km = sum(s[0] for s in self.segments)
        pct = sum(s[1] for s in self.segments)
        if km < MIN_KM or pct <= 0:
            return None
        return round(pct / 100 * tank_liters / km * 100, 1)

    def to_dict(self) -> dict:
        return {"segments": self.segments, "last": list(self.last) if self.last else None}

    @classmethod
    def from_dict(cls, data: dict | None) -> "ConsumptionTracker":
        data = data or {}
        return cls(data.get("segments"), data.get("last"))
