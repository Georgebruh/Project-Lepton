# Task A11: Storm Facts (Quezon City)

Barangay lists and wettest days checked against every source on
2026-10-18 and corrected (review fix); the fourth storm, Kristine, was added the same day.
The values used by the code are in `config.STORMS`; check "A11 storm facts" in
`python -m src.checks` tests them.

## Rules

- **Flooded barangays.** A barangay is listed only if a source from the storm names it as
  flooded, affected, or with its own residents evacuated, rescued or made homeless.
  Not counted:
  - a road that shares a barangay's name. Many QC barangays are named after streets
    (E. Rodriguez, Don Manuel, N.S. Amoranto, Kamuning, Mangga), and MMDA lists name
    roads ("E-rod Araneta", "Biak na Bato corner Don Manuel"), not barangays;
  - a barangay that only hosts an evacuation center for other barangays' residents;
  - a report from another surge (e.g. 17 or 29 August 2026 for the 8-11 August storm);
  - a report whose page could not be opened, unless the wording was seen in search results
    (marked "page blocks automated reading" below: open the link to confirm).
  These lists are what C8 compares its flagged barangays with. They are not complete: a
  barangay missing here may have flooded without being named in a report found.
- **Wettest UTC days.** Three consecutive UTC days. C3 and C8 take the storm's wettest
  3-day IMERG total among the windows ending on these days, and A15 fetches the forecasts
  for them and the 2 days before. So they must hold the last day of IMERG's wettest 3-day
  window during the flood (catchment rain, `src/flood_exposure.py`). The A11 check tests it.
- **D** is the days from the day flooding began to the day it ended, both counted.
- PSGC codes match PSA's PSGC list (via psgc.gitlab.io, which mirrors it) and A5's 142.

---

## Storm 1: Typhoon Carina (July 2024) [`carina_2024`]

Typhoon Carina (Gaemi) enhanced the Southwest Monsoon (Habagat) in late July 2024, dumping
record 24-hour rainfall over Quezon City (345.0 mm at PAGASA Science Garden) and
triggering citywide river and street inundation.

Day flooding began: 2024-07-23
- [QC LGU: Localized Rainfall Advisory #4 & Evacuation Updates (July 24, 2024)](https://quezoncity.gov.ph/quezon-city-localized-rainfall-advisory-july-24-2024/)
- [Inquirer Live Updates: MMDA reports initial Metro Manila road floods on July 23, 2024](https://www.inquirer.net/409587/live-updates-typhoon-carina/)

Days flooded: D = 3, 2024-07-23 to 2024-07-25 (D ± 1: 2 and 4 days)
- [QC LGU: CarinaPH Status of Roads in Quezon City – 12:00 NN (July 24, 2024)](https://quezoncity.gov.ph/carina-ph-status-of-roads-in-quezon-city-1200-nn/)
- [QC LGU: CarinaPH Evacuation Update – 10:00 PM (July 24–25, 2024)](https://quezoncity.gov.ph/carinaph-evacuation-update-1000-pm/)
- [Inquirer: LIST: Flooded roads in Metro Manila on Thursday, July 25, 2024](https://newsinfo.inquirer.net/1965503/fwd-list-of-flooded-areas)

Wettest UTC days: 2024-07-23 to 2024-07-25. IMERG's wettest 3-day window is 22-24 July
(120.0 mm over the catchments), which ends inside them.

Scale: "80 out of 142 barangays flooded" and over 25,000 residents evacuated
([Inquirer live updates, July 24, 2024](https://www.inquirer.net/409587/live-updates-typhoon-carina/)).
The 80 could not be checked against a list.

Flooded barangays (12):
- Apolonio Samson (`1381300003`), Bagong Silangan (`1381300010`), Del Monte (`1381300029`),
  Doña Imelda (`1381300031`), Masambong (`1381300064`), Roxas (`1381300090`),
  Tatalon (`1381300121`): Mayor Belmonte named them as the barangays that "suffered the
  most during the onslaught of habagat and typhoon Carina"
  ([Daily Tribune, October 3, 2024](https://tribune.net.ph/2024/10/03/qc-barangays-back-flood-mitigation-programs)).
  Also: Bagong Silangan's evacuation center and river inspection
  ([QC LGU, July 25, 2024](https://quezoncity.gov.ph/mayor-belmonte-leads-distribution-of-essentials-to-affected-qcitizens-by-typhoon-carina-in-evacuation-centers/));
  Masambong residents hit by Carina and habagat
  ([QC LGU, July 26, 2024](https://quezoncity.gov.ph/mayor-joy-belmonte-visits-brgy-masambong-residents-affected-by-typhoon-carina/)).
- Damayang Lagi (`1381300028`): rescue operations amid severe flooding in Brgy. Damayang Lagi
  ([GMA News, July 24, 2024](https://www.gmanetwork.com/news/topstories/nation/914528/carina-habagat-wallop-livelihoods-roads-houses/story/)).
- Nagkaisang Nayon (`1381300068`), San Bartolome (`1381300097`): residents who lost their
  homes to Carina
  ([QC LGU, July 27, 2024](https://quezoncity.gov.ph/mayor-joy-belmonte-visits-barangay-nagkaisang-nayon-and-san-bartolome-residents-affected-by-typhoon-carina/)).
- Santo Domingo (Matalahib) (`1381300065`): "NS Amoranto Brgy Sto. Domingo, above waist-high
  flood"; the same list has "Champaca corner Vargas Street, Brgy. Roxas"
  ([Inquirer, July 25, 2024](https://newsinfo.inquirer.net/1965503/fwd-list-of-flooded-areas); page blocks automated reading).
  Confirmed 2026-10-18 on a page that opens: "Flood also reached waist level in Barangay
  Sto. Domingo also in Quezon City"
  ([GMA News, July 23, 2024, 2:38 PM](https://www.gmanetwork.com/news/topstories/nation/914392/carina-metro-manila-flood/story/)).
- Talayan (`1381300118`): QCDRRMO search and rescue in Barangay Talayan
  ([Manila Bulletin, July 24, 2024](https://mb.com.ph/2024/7/24/qc-lgu-evacuates-residents-in-flooded-areas); page blocks automated reading).
  Confirmed 2026-10-18 on the city's own post: QCDRRMO "search and rescue operation ... sa
  Brgy. Talayan upang matulungan ang mga residenteng na-trap sa baha", flooding "dulot ng
  bagyong Carina at Southwest Moonsoon"
  ([QC LGU, July 24, 2024](https://quezoncity.gov.ph/qcdrrmo-rescue-operations-in-brgy-talayan)).

Not counted (14 in the first version of this file):
- Balingasa, Kalusugan, Kamuning, Mariana, Paltok, Phil-Am, South Triangle: the
  [DZRH list of July 24, 2024](https://www.dzrh.com.ph/post/typhoon-carina-flooded-areas-on-wednesday-july-24)
  names roads only (G. Araneta–Ma. Clara, E-rod Araneta, Balintawak, EDSA–Quezon Ave, ...).
- Don Manuel, E. Rodriguez, N.S. Amoranto (Gintong Silahis): GMA names Don Manuel Agregado
  Street, E. Rodriguez and N.S. Amoranto Avenue as roads; only Damayang Lagi as a barangay.
- Fairview: the [QC roads update of 2:35 PM](https://quezoncity.gov.ph/carinaph-status-of-roads-in-quezon-city-235-pm/) names no road or barangay.
- Mariblo: the [QC post on District 1 evacuations](https://quezoncity.gov.ph/evacuation-operations-for-stranded-district-1-residents/) names no barangay.
- Quirino 2-A: hosted an evacuation center
  ([QC LGU](https://quezoncity.gov.ph/quezon-city-government-provides-relief-packs-and-hygiene-kits-to-evacuees-in-barangay-quirino-2-a/)); not reported flooded.
- Novaliches Proper: no barangay-level report found (only a flooded Quirino Highway photo).

---

## Storm 2: July 2025 floods [`floods_2025`]

Successive tropical cyclones (STS Crising/Wipha, Dante, and Emong) enhanced the Southwest
Monsoon from July 19 to 24, 2025, placing Quezon City under a State of Calamity
(63 barangays affected, [QC LGU, July 22, 2025](https://quezoncity.gov.ph/qc-declares-state-of-calamity/))
and triggering the early-August 2025 QCESD leptospirosis outbreak.

Day flooding began: 2025-07-19
- [QC LGU: Status of Roads in Quezon City – 09:00 A.M. (July 19, 2025)](https://quezoncity.gov.ph/status-of-roads-in-quezon-city-0900-a-m/)
- [QC LGU: Evacuation Update – 03:00 P.M. (July 19, 2025)](https://quezoncity.gov.ph/evacuation-update-0300-p-m/)

Days flooded: D = 6, 2025-07-19 to 2025-07-24 (D ± 1: 5 and 7 days)
- [QC LGU: Evacuation Update – 11:00 P.M. (July 21, 2025)](https://quezoncity.gov.ph/evacuation-update-1100-p-m/)
- [QC LGU: Evacuation Update – 05:00 P.M. (July 22, 2025)](https://quezoncity.gov.ph/evacuation-update-0500-p-m-4/)
- [QC LGU: QC Sounds Alarm on Rising Leptospirosis Cases (August 3, 2025)](https://quezoncity.gov.ph/qc-sounds-alarm-on-rising-leptospirosis-cases-residents-advised-to-act-fast-on-symptoms/)
- [Philstar: Quezon City under state of calamity due to habagat (July 22, 2025)](https://www.philstar.com/nation/2025/07/22/2459925/quezon-city-under-state-calamity-due-habagat-manila-declare-next)

Wettest UTC days: 2025-07-17 to 2025-07-19 (changed 2026-10-18 from 21-23 July). IMERG's
wettest 3-day window during the flood is 17-19 July, 191.0 mm over the catchments (daily
71.1, 54.5, 65.4 mm), ending on the day flooding began; 21-23 July hold 124.0 mm. With
21-23 July, C8 could not reach the 17-19 window and would have used 170.2 mm (19-21 July).

Scale: 10,576 families (35,847 individuals) evacuated at the July 23, 2025 peak
([QC LGU Habagat Report](https://quezoncity.gov.ph/qc-flood-mitigation-efforts-show-gains-as-habagat-evacuees-drop-80/)).
A separate 1-day thunderstorm flash flood swamped 36 QC barangays on 2025-08-30
([Daily Tribune](https://tribune.net.ph/2025/08/31/qc-reels-from-ondoy-like-floods-as-36-barangays-swamped)); not part of this storm.

Flooded barangays (14), all from QC's road updates, which list each flooded road under its
barangay ("Brgy. X: road, depth"):
- Santo Domingo (Matalahib) (`1381300065`), North Fairview (`1381300142`):
  [QC LGU, Status of Roads 9:00 AM, July 19, 2025](https://quezoncity.gov.ph/status-of-roads-in-quezon-city-0900-a-m/).
- Apolonio Samson (`1381300003`), Damayan (`1381300027`), Damayang Lagi (`1381300028`),
  Del Monte (`1381300029`), Doña Imelda (`1381300031`), Katipunan (`1381300049`),
  Mariana (`1381300060`), Milagrosa (`1381300067`), Payatas (`1381300138`),
  Roxas (`1381300090`), Santo Domingo (Matalahib), Sienna (`1381300112`; "Brgy. Siena"),
  Tatalon (`1381300121`):
  [QC LGU, Status of Roads 11:20 PM, July 21, 2025](https://quezoncity.gov.ph/status-of-roads-in-quezon-city-1120-p-m/).

Not counted (11 in the first version of this file):
- Bagong Silangan, Fairview, Gulod, Santa Cruz, Santa Lucia: the cited QC evacuation
  updates (July 21 and 22) give city totals only and name no barangay.
- Commonwealth, Loyola Heights, Mangga, Pasong Tamo, Tandang Sora: cited to a Manila
  Bulletin Facebook post that cannot be opened. "Mangga St." is also a street in
  Brgy. Katipunan.
- N.S. Amoranto (Gintong Silahis): a street here ("Araneta cor. NS Amoranto" is listed under
  Brgy. Sto. Domingo).

---

## Storm 3: August 2026 habagat floods [`habagat_2026`]

Intensified Southwest Monsoon surges in August 2026 (peaking August 8–11, with secondary
surges on August 17 and August 29–30 when La Mesa Dam reached spilling level) caused up to
head-deep flooding and forced evacuations across low-lying Quezon City barangays. This
storm is the 8-11 August surge only.

Day flooding began: 2026-08-08
- [DZRH / QC LGU: LIST: Flooded areas in Quezon City on Saturday afternoon, Aug. 8, 2026](https://www.dzrh.com.ph/post/list-flooded-areas-in-quezon-city-on-saturday-afternoon-aug-8)
- [QC LGU: Evacuation Update – 06:00 A.M. (August 9, 2026)](https://quezoncity.gov.ph/evacuation-update-0600-a-m/)
- [QC LGU: Status of Roads in Quezon City – 10:50 A.M. (August 9, 2026)](https://quezoncity.gov.ph/status-of-roads-in-quezon-city-1050-a-m/)

Days flooded: D = 4, 2026-08-08 to 2026-08-11 (D ± 1: 3 and 5 days; 10 days if counting
the full 2026-08-02 to 2026-08-11 habagat window)
- [QC LGU: Evacuation Update – 05:32 A.M. (August 10, 2026)](https://quezoncity.gov.ph/evacuation-update-0532-a-m/)
- [QC LGU: Evacuation Update – 11:00 P.M. (August 10, 2026)](https://quezoncity.gov.ph/evacuation-update-1100-p-m-2/)
- [QC LGU: QC flood mitigation efforts show gains as Habagat evacuees drop 80% (August 11, 2026)](https://quezoncity.gov.ph/qc-flood-mitigation-efforts-show-gains-as-habagat-evacuees-drop-80/)

Wettest UTC days: 2026-08-08 to 2026-08-10. IMERG's wettest 3-day window is 7-9 August
(140.9 mm over the catchments), which ends inside them. The late-August surge is wetter in
IMERG (28-30 August, 158.7 mm; 91.8 mm on 29 August alone) but is a separate event.

Scale: 2,146 families (8,220 individuals) evacuated during the August 2–11, 2026 surge
([QC LGU](https://quezoncity.gov.ph/qc-flood-mitigation-efforts-show-gains-as-habagat-evacuees-drop-80/)).

Flooded barangays (17):
- Apolonio Samson (`1381300003`), Damayan (`1381300027`), Damayang Lagi (`1381300028`),
  Del Monte (`1381300029`), Doña Imelda (`1381300031`), Lourdes (`1381300054`),
  Roxas (`1381300090`), Santo Domingo (Matalahib) (`1381300065`), Sienna (`1381300112`),
  Tatalon (`1381300121`), Vasra (`1381300129`): each a heading in the
  [DZRH list of August 8, 2026](https://www.dzrh.com.ph/post/list-flooded-areas-in-quezon-city-on-saturday-afternoon-aug-8),
  with its flooded streets under it.
- Bagong Silangan (`1381300010`), Bagumbayan (`1381300011`), Gulod (`1381300043`),
  Santa Cruz (`1381300104`), Santa Lucia (`1381300105`), and Doña Imelda and Roxas again:
  the seven barangays where 351 families were evacuated, "other affected barangays"
  ([Philstar, August 10, 2026](https://www.philstar.com/nation/2026/08/10/2548167/thousands-evacuated-monsoons-flood-metro)).
- Tandang Sora (`1381300120`): A. Rodriguez Ave. cor. D. Muñoz, Brgy. Tandang Sora, waist
  deep ([QC LGU, Status of Roads 10:50 AM, August 9, 2026](https://quezoncity.gov.ph/status-of-roads-in-quezon-city-1050-a-m/)).

Not counted (21 in the first version of this file):
- From the later surges only:
  [Manila Bulletin, August 17](https://mb.com.ph/2026/08/17/waist-deep-floods-hit-parts-of-qc-as-habagat-persists)
  (Bahay Toro, Kamuning, Marilag, Masagana, N.S. Amoranto, Paang Bundok, Pinyahan,
  Project 6, San Roque, Socorro) and
  [ABS-CBN, August 29](https://www.abs-cbn.com/news/nation/2026/8/29/flooding-hits-quezon-city-and-bulacan-due-to-heavy-rains-2149)
  (Culiat, Katipunan, Mariana, Obrero, Pasong Tamo, Ramon Magsaysay, North Fairview).
- Don Manuel and Talipapa: in the DZRH list they are places under Brgy. Del Monte
  ("Biak na Bato corner Don Manuel", "Talipapa riverside alleys"), not barangays.
- E. Rodriguez ([ABS-CBN, August 10](https://www.abs-cbn.com/news/weather-traffic/2026/8/10/habagat-rains-flood-parts-of-metro-manila-number-coding-suspended-0726),
  page blocks automated reading) and Talayan ([PNA photo 84301](https://www.pna.gov.ph/photos/84301),
  page not found): could not be checked.

---

## Storm 4: Severe Tropical Storm Kristine (October 2024) [`kristine_2024`]

Added 2026-10-18; not in the proposal. Carina, the proposal's main storm, falls near R0 on
IMERG's catchment rain (see `Notes.md`), so its doses come out near zero. Kristine (Trami)
is the wettest storm in IMERG's catchment rain since Open-Meteo's forecast archive began
(February 2024), so it is one storm where both C8 (observed rain) and C9 (forecasts) show
the chain working. QC declared a state of calamity on October 25, 2024: all 142
barangays affected, 40 hit hardest, the storm's onslaught starting October 22
([Journal News Online, October 26, 2024](https://journalnews.com.ph/qc-under-state-of-calamity-due-to-sts-kristine/)).

Day flooding began: 2024-10-24. Days flooded: D = 1, 2024-10-24 (D ± 1: 2 days).
The reports found show QC flooding on October 24 only: roads still flooded at 6:00 AM
([QC LGU, Status of Roads 6:00 AM, October 24, 2024](https://quezoncity.gov.ph/status-of-roads-in-quezon-city-0600-a-m/))
and floods in parts of Metro Manila "yesterday"
([Philstar, October 25, 2024](https://www.philstar.com/nation/2024/10/25/2395091/kristine-floods-metro-manila-classes-still-suspended)).
Ask QC DRRMO (A1) for the real span if there is time; D = 2 is the ± 1 test.
Checked 2026-10-18 for flooding on October 22-23: none found. The earliest QC reports are
the 6:00 AM roads update and the city's evacuation update for Doña Imelda, October 24,
3:00 PM ([QC LGU](https://quezoncity.gov.ph/evacuation-update-barangay-dona-imelda/)); the
Inquirer's QC evacuation report blocks automated reading. D = 1 stands.

Wettest UTC days: 2024-10-22 to 2024-10-24, IMERG's wettest 3-day window (195.1 mm over the
catchments; daily 81.5, 44.5, 69.1 mm).

Scale: 8,880 people (2,500+ families) in 38 evacuation centers in 26 barangays
([Philstar, October 26, 2024](https://www.philstar.com/nation/2024/10/26/2395352/quezon-city-declares-state-calamity)).

Flooded barangays (8):
- Tatalon (`1381300121`), Bagong Silangan (`1381300010`), Batasan Hills (`1381300139`):
  among the worst affected, per the city council (Journal News Online, above).
- Commonwealth (`1381300022`; knee deep), Sienna (`1381300112`; "Brgy. Siena", not
  passable), Santo Domingo (Matalahib) (`1381300065`; not passable), and Tatalon again
  (gutter deep): QC roads update of 6:00 AM, October 24 (above).
- Masambong (`1381300064`), Payatas (`1381300138`), and Bagong Silangan again: police sent
  to "flood-hit areas" (Philstar, October 25, above). La Loma and Galas, named there too,
  are districts, not PSGC barangays.

Not counted: the 18 barangays Philstar (October 25) lists only as places with evacuation
centers (Project 6, Bahay Toro, Sta. Cruz, Del Monte, Damayan, Manresa, Balingasa,
Commonwealth, Roxas, Damayang Lagi, Kristong Hari, Doña Imelda, UP Campus, Old Capitol
Site, Balong Bato, Apolonio Samson, Tatalon, Bagong Silangan), unless named above.
