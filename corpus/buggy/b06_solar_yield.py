"""Estimating daily energy yield for a rooftop solar array."""

PANEL_AREA_M2 = 1.7
PANEL_EFFICIENCY = 0.21
INVERTER_EFFICIENCY = 0.96


def irradiance_kwh_per_m2(peak_sun_hours, cloud_cover_fraction):
    """Usable irradiance after cloud losses, in kWh per square metre."""
    clear_fraction = 1.0 - cloud_cover_fraction
    return peak_sun_hours * clear_fraction


def array_area_m2(panel_count):
    return panel_count * PANEL_AREA_M2


def dc_yield_kwh(panel_count, peak_sun_hours, cloud_cover_fraction):
    irradiance = irradiance_kwh_per_m2(peak_sun_hours, cloud_cover_fraction)
    area = array_area_m2(panel_count)
    return irradiance * area * PANEL_EFFICIENCY


def ac_yield_kwh(panel_count, peak_sun_hours, cloud_cover_fraction,
                 temperature_c):
    dc = dc_yield_kwh(panel_count, peak_sun_hours, cloud_cover_fraction)

    # Panels lose output above their 25 C rating.
    excess_degrees = temperature_c - 25.0
    if excess_degrees > 0:
        dc *= (1.0 - 0.004 * excess_degrees)

    return dc * INVERTER_EFFICIENCY
