"""Atmospheric correction factors for DC corona/PD analysis.

References:
- Peek, F.W., "Dielectric Phenomena in High Voltage Engineering" (1929) - relative
  air density factor delta and the empirical corona onset gradient formula.
- IEC 60060-1 - atmospheric correction for external insulation withstand tests
  (relative air density + humidity correction), adapted here to corona onset.

The humidity correction below is an approximation intended for interactive
exploration, not a certified test-lab correction. It is isolated in its own
function so it can be swapped for a more rigorous model (e.g. the full IEC
60060-1 iterative g/k procedure) without touching the rest of the physics.
"""
from __future__ import annotations

from dataclasses import dataclass

STANDARD_PRESSURE_KPA = 101.3
STANDARD_TEMPERATURE_C = 20.0
STANDARD_TEMPERATURE_K = STANDARD_TEMPERATURE_C + 273.15


@dataclass
class Environment:
    temperature_c: float = STANDARD_TEMPERATURE_C
    pressure_kpa: float = STANDARD_PRESSURE_KPA
    humidity_percent: float = 50.0  # relative humidity, 0-100

    def relative_air_density(self) -> float:
        """Peek's relative air density factor delta = (P/P0) * (T0/T)."""
        t_k = self.temperature_c + 273.15
        return (self.pressure_kpa / STANDARD_PRESSURE_KPA) * (
            STANDARD_TEMPERATURE_K / t_k
        )

    def absolute_humidity_g_m3(self) -> float:
        """Absolute humidity from relative humidity via saturation vapor pressure
        (Magnus/Tetens approximation), used for the humidity correction factor.
        """
        t = self.temperature_c
        # Saturation vapor pressure in hPa (Tetens formula).
        e_sat = 6.1078 * 10 ** ((7.5 * t) / (237.3 + t))
        e = e_sat * (self.humidity_percent / 100.0)
        t_k = t + 273.15
        # Absolute humidity (g/m^3) from ideal gas law for water vapor.
        return 216.7 * (e / t_k)

    def humidity_correction_factor(self) -> float:
        """Empirical multiplier on corona onset field due to humidity.

        Increasing absolute humidity slightly raises the DC corona onset
        gradient (water vapor is more electronegative / attaches electrons).
        Calibrated so that h = 11 g/m^3 (the IEC 60060-1 reference humidity)
        gives a factor of 1.0, with a modest +/-5% swing over the practical
        0-30 g/m^3 range. Replace with a validated model if precision matters.
        """
        h = self.absolute_humidity_g_m3()
        return 1.0 + 0.004 * (h - 11.0)

    def summary(self) -> dict:
        return {
            "temperature_c": self.temperature_c,
            "pressure_kpa": self.pressure_kpa,
            "humidity_percent": self.humidity_percent,
            "relative_air_density": round(self.relative_air_density(), 4),
            "absolute_humidity_g_m3": round(self.absolute_humidity_g_m3(), 2),
            "humidity_correction_factor": round(self.humidity_correction_factor(), 4),
        }


def peek_onset_gradient_kv_cm(radius_cm: float, env: Environment, relative_dielectric_strength: float = 1.0) -> float:
    """Peek's empirical DC corona onset gradient at a cylindrical/rod conductor
    surface, in kV/cm:

        g0 = 30 * delta * m * (1 + 0.301 / sqrt(delta * r))

    where r is the conductor radius in cm, delta the relative air density,
    and m a surface roughness/irregularity factor (1.0 for a smooth polished
    conductor, lower for stranded/rough surfaces). Humidity is applied as an
    additional multiplicative correction on top of Peek's base formula.

    `relative_dielectric_strength` scales the whole result for a non-air
    insulating gas (e.g. ~2.5-3x for SF6 relative to air at the same
    pressure) -- see physics/materials.py.
    """
    delta = env.relative_air_density()
    m = 1.0
    g0 = 30.0 * delta * m * (1.0 + 0.301 / (delta * radius_cm) ** 0.5)
    return g0 * env.humidity_correction_factor() * relative_dielectric_strength


def paschen_breakdown_voltage_v(gap_cm: float, env: Environment, relative_dielectric_strength: float = 1.0) -> float:
    """Paschen's law breakdown voltage (V) for a uniform-field gas gap, used
    for internal voids and surface-discharge gas paths:

        Vb = B * (p*d) / (ln(A * p*d) - ln(ln(1 + 1/gamma)))

    p*d in cm*mmHg, A and gamma are standard textbook constants for air.
    `relative_dielectric_strength` linearly rescales the result for a
    non-air gas fill (approximate -- Paschen's A/B/gamma constants are
    actually gas-specific, but this keeps the model to one tunable knob
    per gas; see physics/materials.py).
    """
    import math

    a_const = 112.0  # (cm * mmHg)^-1
    b_const = 2737.0  # V / (cm * mmHg)
    gamma = 0.01  # secondary electron emission coefficient for air

    pressure_mmhg = env.pressure_kpa * 7.50062
    pd = pressure_mmhg * gap_cm
    pd = max(pd, 1e-6)
    denom = math.log(a_const * pd) - math.log(math.log(1.0 + 1.0 / gamma))
    if denom <= 0:
        # Below the Paschen minimum region; fall back to the empirical
        # minimum sparking voltage for air (~327 V) to avoid a singularity.
        return 327.0 * relative_dielectric_strength
    return b_const * pd / denom * relative_dielectric_strength
