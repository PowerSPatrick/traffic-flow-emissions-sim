# Data plan

This project currently runs entirely on **synthetic** demand and does not
fetch or ship any real-world dataset. This document records the plan for
ingesting real UK data in later work, and the small synthetic demand
generator actually included here.

## Synthetic data (available now)

`generate_synthetic_demand.py` generates a plausible time-varying UK
urban traffic demand profile (a.m./p.m. peaks, an inter-peak trough) as a
CSV of hourly (or finer) vehicle counts. It's meant to feed more
realistic time-of-day demand curves into `traffic_sim` scenarios than the
flat-rate demand used in `experiments/`, not to represent any specific
real road.

Run:

```bash
python data/generate_synthetic_demand.py --out data/synthetic/demand_profile.csv
```

## Real UK datasets to ingest later

None of the following are fetched by this repository yet. This is a
plan, not a dependency.

### 1. DfT road traffic statistics
- **What**: Department for Transport annual/quarterly road traffic
  estimates (vehicle miles by road class/region), and the
  road-traffic-count API behind the interactive maps.
- **Where**: https://roadtraffic.dft.gov.uk/ and
  https://www.gov.uk/government/collections/road-traffic-statistics
- **Use here**: Calibrate realistic corridor demand levels (veh/hour) per
  UK road class (e.g. urban A-road vs motorway) instead of the
  illustrative flat rates in `experiments/scenarios/*.yaml`.

### 2. National Highways (Highways England) WebTRIS API
- **What**: Historical and near-real-time traffic count/speed data from
  strategic road network (motorway/trunk road) inductive-loop sites.
- **Where**: https://webtris.nationalhighways.co.uk/api/swagger/ui/index
  (site list, daily/monthly reports, quality metrics per site).
- **Use here**: Real speed-flow relationships to validate the IDM
  parameterisation (`traffic_sim.idm.IDMParams`) against observed
  motorway behaviour, and real ramp demand profiles for the ramp
  metering scenario.

### 3. TfL Unified API
- **What**: Transport for London's open API -- road corridor journey
  times, traffic disruption, and (via TfL's open data feeds) signal
  timing plans (SCOOT/UTC) for London junctions.
- **Where**: https://api.tfl.gov.uk/ (see the `Road` endpoints).
- **Use here**: Real signal cycle/offset data to replace the illustrative
  fixed-time and green-wave plans in `traffic_sim.signals`, and journey
  time data to validate simulated travel times for a London corridor.

### 4. DEFRA / NAEI emissions factors
- **What**: The UK National Atmospheric Emissions Inventory (NAEI,
  maintained for DEFRA) publishes official road transport emission
  factors (g/km by pollutant, vehicle type, Euro class, speed band),
  and DEFRA publishes the underlying EFT (Emission Factors Toolkit).
- **Where**: https://naei.beis.gov.uk/ and the DEFRA Emission Factors
  Toolkit (EFT) spreadsheet tool.
- **Use here**: **Directly replaces** the placeholder polynomial
  coefficients in `traffic_sim.emissions.EmissionFactors`, which are
  explicitly documented there as illustrative approximations, not real
  factors. This is the single highest-value real-data integration for
  the research goal, since it turns relative emissions comparisons into
  ones traceable to a recognised UK inventory methodology.

### Suggested ingestion order
1. NAEI/DEFRA emission factors (turns relative "% reduction" results into
   defensible absolute g/km figures).
2. WebTRIS site data for one or two real motorway corridors (grounds the
   ramp-metering scenario in an observed bottleneck).
3. TfL signal timing + journey time data for one real signalised corridor
   (grounds the green-wave scenario).
4. DfT statistics as a sanity-check / scaling reference across road
   classes.
