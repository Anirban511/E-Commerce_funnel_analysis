# Power BI Dashboard — Build Guide (GA Merchandise Store)

The pipeline pre-aggregates everything the dashboard needs into the six CSVs in
this folder. You only build visuals.

## 1. Load the data
`Home → Get Data → Text/CSV`, import all six:

| File | Use |
|------|-----|
| `funnel_stage.csv` | headline funnel visual |
| `funnel_by_device.csv` | device comparison |
| `channel_performance.csv` | channelGrouping KPIs |
| `device_channel_matrix.csv` | worst-pocket heatmap |
| `daily_trend.csv` | conversion / revenue over time |
| `category_revenue.csv` | revenue by product category |

## 2. Core DAX measures
```DAX
Overall Conversion = DIVIDE(SUM(channel_performance[orders]), SUM(channel_performance[sessions]))
Total Revenue      = SUM(channel_performance[revenue])
Total Orders       = SUM(channel_performance[orders])
AOV                = DIVIDE([Total Revenue], [Total Orders])
```

## 3. Page layout
1. KPI cards: Total Sessions, Overall Conversion %, Total Revenue, AOV.
2. Funnel visual from `funnel_stage` (stage on axis, ordered by `stage_order`).
3. Clustered bar — conversion by device from `funnel_by_device` (mobile in red).
4. Bar — conversion by channel from `channel_performance`, sorted descending.
5. Matrix/heatmap from `device_channel_matrix` (device rows × channel cols,
   `conversion_rate` with a colour scale — mobile × Display/Social is darkest).
6. Line — conversion over time from `daily_trend`, with device/channel/date slicers.

## 4. Storytelling
- Title the page with the finding, not "Dashboard":
  *"Mobile converts 5× worse than desktop"*.
- Note the GA-typical low absolute conversion (~1.3%) so cards aren't misread.
- Highlight mobile in a single accent colour; grey the rest.
