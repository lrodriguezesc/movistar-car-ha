from movistar_car.consumption import MIN_KM, WINDOW_KM, ConsumptionTracker


def drive(t, steps):
    """steps = list of (km, fuel_pct)."""
    for km, fuel in steps:
        t.add_sample(km, fuel)


def test_no_result_before_min_km():
    t = ConsumptionTracker()
    drive(t, [(1000, 80), (1010, 79)])
    assert t.consumption(45) is None


def test_basic_consumption():
    t = ConsumptionTracker()
    # 100 km, 10 % of a 50 L tank = 5 L -> 5 L/100 km
    drive(t, [(1000, 80), (1050, 75), (1100, 70)])
    assert t.window_km == 100
    assert t.consumption(50) == 5.0


def test_tank_size_applies_to_old_data():
    t = ConsumptionTracker()
    drive(t, [(1000, 80), (1100, 70)])
    assert t.consumption(50) == 5.0
    assert t.consumption(40) == 4.0


def test_refuel_interval_is_skipped():
    t = ConsumptionTracker()
    drive(t, [(1000, 20), (1060, 14), (1070, 95), (1130, 89)])
    # 60 km at 6 % and 60 km at 6 %. The 10 km refuel interval is not counted.
    assert t.window_km == 120
    assert t.consumption(50) == 5.0  # 12 % of 50 L = 6 L over 120 km


def test_parked_gauge_movement_is_ignored():
    t = ConsumptionTracker()
    drive(t, [(1000, 80), (1000, 78), (1000, 80), (1100, 70)])
    assert t.window_km == 100
    assert t.consumption(50) == 5.0


def test_small_rise_is_noise_and_does_not_add_fuel():
    t = ConsumptionTracker()
    # fuel goes 80 -> 81 (noise) -> 70: total used is 10 %, measured from 80
    drive(t, [(1000, 80), (1050, 81), (1100, 70)])
    assert t.consumption(50) == 5.0


def test_odometer_reset_or_big_jump_restarts_baseline():
    t = ConsumptionTracker()
    drive(t, [(1000, 80), (900, 79), (1300, 70)])
    assert t.segments == []
    assert t.last == (1300, 70)


def test_window_is_trimmed():
    t = ConsumptionTracker()
    km, fuel = 0.0, 100.0
    t.add_sample(km, fuel)
    for _ in range(40):
        km += 50
        fuel -= 2
        t.add_sample(km, fuel)
        if fuel < 20:
            fuel = 100.0
            t.add_sample(km, fuel)
    assert WINDOW_KM <= t.window_km < WINDOW_KM + 50


def test_missing_values_are_ignored():
    t = ConsumptionTracker()
    assert t.add_sample(None, 80) is False
    assert t.add_sample(1000, None) is False
    assert t.last is None


def test_save_and_restore_round_trip():
    t = ConsumptionTracker()
    drive(t, [(1000, 80), (1100, 70)])
    t2 = ConsumptionTracker.from_dict(t.to_dict())
    assert t2.consumption(50) == t.consumption(50)
    assert t2.last == t.last
    assert ConsumptionTracker.from_dict(None).segments == []


def test_min_km_constant_is_used():
    t = ConsumptionTracker()
    drive(t, [(1000, 80), (1000 + MIN_KM - 1, 70)])
    assert t.consumption(50) is None
