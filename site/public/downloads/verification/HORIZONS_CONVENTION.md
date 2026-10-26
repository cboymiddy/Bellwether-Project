# Exact Skyfield convention behind the astro_geo literals, and matching JPL Horizons settings

Software: Skyfield 1.55, ephemeris JPL DE421 (`data/raw/astronomy/de421.bsp`, sha256
`a20a7139da04cbc462454634918e9a9ca69127044e2cc9d4f9c16e238d2deedc`). Code: `src/literals/astro_family.py`.

## What the pool computes
1. **Instant.** `ts.utc(year, month, day)` with `ts = Loader(...).timescale()` (built-in leap-second and delta-T tables):
   **00:00:00 UTC** on the stated month/day of the election year. Skyfield delta-T there: -0.94 s (1900-11-06),
   24.49 s (1940-03-06), 69.38 s (2020). Dates used: days 1, 6, 11, 16, 21, 26 of January through October.
2. **Observer.** The Earth's centre (`eph['earth']`, NAIF 399), i.e. **geocentric**, no topocentric parallax.
3. **Targets.** Sun (10), Moon (301), and the barycentres of Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto
   (`'mercury barycenter'` ... `'pluto barycenter'`; NAIF 1-9 in Horizons).
4. **Position.** `earth.at(t).observe(body).apparent()`: light-time corrected (iterated), plus gravitational deflection
   by the Sun, Jupiter and Saturn (Skyfield's default deflectors) and stellar aberration from the observer's velocity.
   No refraction, no parallax.
5. **Frame.** `.ecliptic_latlon(epoch='date')` = `framelib.ecliptic_frame`, documented as the **true ecliptic and equinox of
   date**: ICRF vector rotated by `rot_x(-true_obliquity) x t.M`, where `t.M` is the precession-nutation matrix and
   nutation is **IAU 2000A** (`iau2000a_radians`), true obliquity = mean obliquity + d_eps.
6. **Longitude** = ecliptic longitude in degrees reduced to [0, 360).
7. **"sep" literals** use `separation(a, b) = |lon_a - lon_b| mod 360`, folded to [0, 180]: the **difference in ecliptic
   LONGITUDE**, not the full angular separation (latitudes are ignored). The statement text in the pool says "angular
   separation"; that wording is inaccurate. For ranks 2-10 of the T1 EC frontier, using the true 3-D separation instead changes
   no literal's truth in any of the 32 years (`years_truth_differs_if_true_sep` = 0 in `t1_margins_ranks2_10.csv`),
   but the values differ by up to a few degrees, so a Horizons check must compare ecliptic-longitude differences.
8. **Sector literals**: `lon in [p, p+30)`. **Threshold literals**: `sep >= c` (closed at c).

## Horizons settings that reproduce it (API: https://ssd.jpl.nasa.gov/api/horizons.api)
- `EPHEM_TYPE='OBSERVER'`, `CENTER='500@399'` (geocentric), `COMMAND` = `10` Sun, `301` Moon, `1`..`9` planet barycentres
  (Mercury barycentre .. Pluto barycentre; Horizons prints "Venus Barycenter (299)" for `2`).
- `TLIST='<JD>'`, `TLIST_TYPE='JD'`, `TIME_TYPE='UT'`, with JD = date.toordinal() + 1721424.5 for 00:00 on the date.
- `QUANTITIES='31'` (ObsEcLon, ObsEcLat), `ANG_FORMAT='DEG'`, `CSV_FORMAT='YES'`, `OBJ_DATA='NO'`.
- Horizons defines quantity 31 as "observer-centered IAU76/80 ecliptic-of-date longitude and latitude of the target centers'
  apparent position, with light-time, gravitational deflection of light, and stellar aberrations".
- Then compute the literal's quantity exactly as in point 6/7 from the two longitudes.

## Pilot comparison (6 body-dates, run once; raw responses in `horizons_pilot/`)
| body | date | Horizons lon | Skyfield lon | difference |
|---|---|---|---|---|
| Sun | 2020-09-06 | 163.8629547 | 163.862968 | -1.3e-5 deg |
| Moon | 2020-09-06 | 25.6959885 | 25.696002 | -1.3e-5 deg |
| Venus bary | 2020-02-01 | 351.9167104 | 351.916724 | -1.4e-5 deg |
| Pluto bary | 2020-02-01 | 293.4153102 | 293.415312 | -2e-6 deg |
| Uranus bary | 1940-03-06 | 48.6369923 | 48.636980 | +1.2e-5 deg |
| Venus bary | 1940-03-06 | 26.8983885 | 26.898660 | -2.7e-4 deg |

Differences are about 1e-5 degrees except Venus 1940 (2.7e-4 degrees, about 1 arcsecond; equivalent to about 20 s of Venus
motion). Horizons uses DE441, light bending by the Sun only, and treats pre-1962 times as UT1 (post-1962 as UTC); Skyfield
uses DE421, deflection by Sun/Jupiter/Saturn, and its own UTC-to-TT handling before 1972. I did not resolve the 1940 Venus
difference. It is far below every margin in `t1_margins_ranks2_10.csv` (smallest: 1.4986 degrees, equal to 31 hours of
Venus-Pluto motion; the Sun-Moon literal's 1.833 degrees is about 4 hours of clock error). Suggested match tolerance: 0.001 degrees.
This pilot is NOT the verification: `verification_sheet.csv` has `checked` blank and Horizons not yet queried for it.
