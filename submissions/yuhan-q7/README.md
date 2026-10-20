# Yuhan Hu — Q7 / YH-02

**How much more do nonstop flights cost than connecting flights around the holidays?**

## Files

- [Tableau visualization](Q7_Nonstop_vs_Connecting.twbx): packaged workbook with its eight-row chart dataset.
- [Chart data](Q7_Tableau_chart.csv): one median fare and observed quote count per travel period and flight type.
- [Same-route data](Q7_route_comparison.csv): medians by directional airport route; select hasBothFlightTypes=True.
- [Website data](Q7_website_data.json): overall and route aggregates for the existing D3 chart.
- [Data-processing code](prepare_q7.py): standard-library Python script for regenerating the datasets.
- [Verification](validation.json): counts and independent checks.
- [Complete submission package](Q7_Yuhan_Submission.zip): workbook, data, code, and detailed methodology.

## Definitions

Departure windows in 2022, inclusive: Memorial Day May 26–31; July 4 June 30–July 5; Labor Day September 1–6; Non-holiday June 9–14 and August 11–16 pooled. Source: [Dillon Wong's Expedia Flight Prices](https://www.kaggle.com/datasets/dilwong/flightprices). The selected windows contain 13,066,299 observed quotes. Counts are observations, not unique flights or tickets sold.

In Tableau, use flightType on Rows, AVG(medianFare) on Columns, and holiday as a single-value filter. The fares are already medians.

Overall nonstop/connecting medians (USD): Memorial Day 258.60/408.61; July 4 255.60/417.69; Labor Day 208.61/317.60; Non-holiday 238.60/392.70. Negative nonstop-minus-connecting differences mean nonstop was cheaper in the pooled sample. Route mix and booking lead times vary; same-route results can reverse the overall pattern. The website's layover marker is schematic.

The Tableau worksheet was recovered from its October 20, 2026, 15:25 EDT automatic save. The shareable copy keeps the Q7 worksheet and its July 4 filter, removes an unrelated second worksheet, and packages only the data it uses. The original recovery file is unchanged. Later unsaved edits are not included. Native Tableau rendering could not be verified during packaging.
