import sys
import pandas as pd
import geopandas as gpd
import plotly.express as px
from dash import Dash, html, dcc, Input, Output, State

# -----------------------------
# LOAD EXPORTED DATA
# -----------------------------
def load_exported_geodataframe(csv_path):
    df = pd.read_csv(csv_path)
    df["GEOID"] = df["GEOID"].astype(str)
    df["geometry"] = gpd.GeoSeries.from_wkt(df["geometry"])
    return gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")

unemployment_df = load_exported_geodataframe("unemployment_df.csv")
total_df = load_exported_geodataframe("total_df.csv")

# -----------------------------
# CLEAN DATA
# -----------------------------
for df in (unemployment_df, total_df):
    df["Value"] = (
        df["Value"]
        .astype(str)
        .str.replace("%", "", regex=False)
        .str.replace("±", "", regex=False)
        .str.replace("+/-", "", regex=False)
        .str.replace("+", "", regex=False)
        .str.replace("-", "", regex=False)
        .str.strip()
    )
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")

unemployment_df = unemployment_df.dropna(subset=["Value"]).copy()
total_df = total_df.dropna(subset=["Value"]).copy()

initial_section = unemployment_df["Section"].dropna().sort_values().iloc[0]
initial_label = (
    unemployment_df.loc[unemployment_df["Section"] == initial_section, "Label (Grouping)"]
    .dropna()
    .sort_values()
    .iloc[0]
)

# -----------------------------
# DASH APP
# -----------------------------
app = Dash(__name__)
server = app.server

app.layout = html.Div(
    [
        html.H2(
            "Community Development Dashboard",
            style={"textAlign": "center", "marginBottom": "24px", "color": "#17384f"}
        ),

        # -----------------------------
        # FILTER PANEL
        # -----------------------------
        html.Div(
            [
                # SECTION FILTER
                html.Div(
                    [
                        html.Div(
                            [
                                html.Label("Section", style={"fontWeight": "600"}),
                                html.Span(
                                    "ⓘ",
                                    id="section-help",
                                    style={
                                        "marginLeft": "6px",
                                        "cursor": "pointer",
                                        "display": "inline-block"
                                    }
                                ),
                                dcc.Tooltip(
                                    "Choose a Section to filter the dataset.",
                                    id="section-help-tooltip",
                                    targetable=True
                                )
                            ],
                            style={"display": "flex", "alignItems": "center"}
                        ),

                        dcc.Dropdown(
                            id="section-dropdown",
                            options=[
                                {"label": s, "value": s}
                                for s in sorted(unemployment_df["Section"].dropna().unique())
                            ],
                            value=initial_section,
                            clearable=False,
                        ),
                    ],
                    style={"flex": "1"}
                ),

                # LABEL FILTER
                html.Div(
                    [
                        html.Div(
                            [
                                html.Label("Label (Grouping)", style={"fontWeight": "600"}),
                                html.Span(
                                    "ⓘ",
                                    id="label-help",
                                    style={
                                        "marginLeft": "6px",
                                        "cursor": "pointer",
                                        "display": "inline-block"
                                    }
                                ),
                                dcc.Tooltip(
                                    "Choose a grouping to refine the Section filter.",
                                    id="label-help-tooltip",
                                    targetable=True
                                )
                            ],
                            style={"display": "flex", "alignItems": "center"}
                        ),

                        dcc.Dropdown(
                            id="label-dropdown",
                            options=[
                                {"label": lbl, "value": lbl}
                                for lbl in sorted(
                                    unemployment_df.loc[
                                        unemployment_df["Section"] == initial_section,
                                        "Label (Grouping)",
                                    ].dropna().unique()
                                )
                            ],
                            value=initial_label,
                            clearable=False,
                        ),
                    ],
                    style={"flex": "1"}
                ),
            ],
            style={"display": "flex", "gap": "16px", "marginBottom": "24px"}
        ),

        # -----------------------------
        # KPI CARDS
        # -----------------------------
        html.Div(
            id="kpi-cards",
            style={"display": "flex", "gap": "16px", "marginBottom": "24px"}
        ),

        # -----------------------------
        # MAP
        # -----------------------------
        html.Div(
            [
                html.Span(
                    "ⓘ",
                    id="map-help",
                    style={"cursor": "pointer", "float": "right", "display": "inline-block"}
                ),
                dcc.Tooltip(
                    "Click a census tract to view unemployment details.",
                    id="map-help-tooltip",
                    targetable=True
                )
            ],
            style={"marginBottom": "4px"}
        ),

        html.Div(
            dcc.Graph(id="map-graph"),
            style={"width": "100%", "marginBottom": "24px"}
        ),

        # -----------------------------
        # HISTOGRAM
        # -----------------------------
        html.Div(
            [
                html.Span(
                    "ⓘ",
                    id="hist-help",
                    style={"cursor": "pointer", "float": "right", "display": "inline-block"}
                ),
                dcc.Tooltip(
                    "Histogram shows number of tracts grouped by unemployment rate.",
                    id="hist-help-tooltip",
                    targetable=True
                )
            ],
            style={"marginBottom": "4px"}
        ),

        html.Div(
            dcc.Graph(id="chart-graph"),
            style={"width": "100%"}
        ),

        # -----------------------------
        # DOWNLOAD
        # -----------------------------
        html.Div(
            [
                html.Button(
                    "Download Data (CSV)",
                    id="download-button",
                    n_clicks=0,
                    style={"marginTop": "24px"}
                ),

                html.Span(
                    "ⓘ",
                    id="download-help",
                    style={"marginLeft": "8px", "cursor": "pointer", "display": "inline-block"}
                ),
                dcc.Tooltip(
                    "Download the filtered dataset as a CSV file.",
                    id="download-help-tooltip",
                    targetable=True
                )
            ]
        ),

        dcc.Download(id="download-data"),
    ],
    style={"padding": "24px"}
)

# -----------------------------
# CALLBACKS
# -----------------------------
@app.callback(
    Output("label-dropdown", "options"),
    Output("label-dropdown", "value"),
    Input("section-dropdown", "value"),
)
def sync_label_options(section_value):
    filtered = unemployment_df
    if section_value:
        filtered = filtered[filtered["Section"] == section_value]

    labels = sorted(filtered["Label (Grouping)"].dropna().unique())
    return [{"label": lbl, "value": lbl} for lbl in labels], (labels[0] if labels else None)


@app.callback(
    Output("map-graph", "figure"),
    Output("chart-graph", "figure"),
    Output("kpi-cards", "children"),
    Input("section-dropdown", "value"),
    Input("label-dropdown", "value"),
)
def update_dashboard(section_value, label_value):
    map_data = unemployment_df
    if section_value:
        map_data = map_data[map_data["Section"] == section_value]
    if label_value:
        map_data = map_data[map_data["Label (Grouping)"] == label_value]

    tract_unemployment = (
        map_data.groupby(["GEOID", "geometry"], as_index=False)["Value"]
        .mean()
        .rename(columns={"Value": "unemployment_rate"})
    )
    tract_unemployment = gpd.GeoDataFrame(
        tract_unemployment, geometry="geometry", crs=unemployment_df.crs
    )

    total_data = total_df
    if section_value:
        total_data = total_data[total_data["Section"] == section_value]
    if label_value:
        total_data = total_data[total_data["Label (Grouping)"] == label_value]

    total_sum = total_data["Value"].sum() if not total_data.empty else 0.0
    unemployment_avg = map_data["Value"].mean() if not map_data.empty else 0.0

    kpi_cards = [
        html.Div(
            [
                html.Div("Total Population", style={"fontWeight": "600", "marginBottom": "4px", "color": "#e6f0f7"}),
                html.Div(f"{total_sum:,.0f}", style={"fontSize": "28px", "fontWeight": "700", "color": "#f8fbff"}),
            ],
            style={"padding": "16px", "backgroundColor": "#17384f", "borderRadius": "12px", "flex": "1"},
        ),
        html.Div(
            [
                html.Div("Mean Unemployment Rate", style={"fontWeight": "600", "marginBottom": "4px", "color": "#16324a"}),
                html.Div(f"{unemployment_avg:,.2f}", style={"fontSize": "28px", "fontWeight": "700", "color": "#10273a"}),
            ],
            style={"padding": "16px", "backgroundColor": "#8ba7ba", "borderRadius": "12px", "flex": "1"},
        ),
    ]

    if tract_unemployment.empty:
        return px.scatter(title="No unemployment records"), px.bar(title="No data"), kpi_cards

    map_fig = px.choropleth(
        tract_unemployment,
        geojson=tract_unemployment.__geo_interface__,
        locations="GEOID",
        featureidkey="properties.GEOID",
        color="unemployment_rate",
        color_continuous_scale="Cividis",
        hover_data={"GEOID": True, "unemployment_rate": ":.2f"},
        labels={"unemployment_rate": "Unemployment Rate"},
        title="Unemployment Rate by Richmond Census Tract",
    )

    map_fig.update_geos(
        fitbounds="locations",
        visible=False,
        projection_scale=1,
        center=None
    )

    map_fig.update_layout(
        height=600,
        dragmode="pan",
        margin={"r": 0, "t": 48, "l": 0, "b": 0},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
    )

    chart_fig = px.histogram(
        tract_unemployment,
        x="unemployment_rate",
        nbins=12,
        color_discrete_sequence=["#17384f"],
        labels={"unemployment_rate": "Unemployment Rate (%)"},
        title="Distribution of Unemployment Rates Across Tracts",
    )

    chart_fig.add_vline(
        x=unemployment_avg,
        line_width=2,
        line_dash="dash",
        line_color="#6d8ea5"
    )

    chart_fig.add_vline(
        x=tract_unemployment["unemployment_rate"].median(),
        line_width=2,
        line_color="#17384f"
    )

    chart_fig.update_layout(
        height=420,
        margin={"r": 12, "t": 48, "l": 6, "b": 24},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
    )

    return map_fig, chart_fig, kpi_cards

# -----------------------------
# DOWNLOAD CALLBACK
# -----------------------------
@app.callback(
    Output("download-data", "data"),
    Input("download-button", "n_clicks"),
    State("section-dropdown", "value"),
    State("label-dropdown", "value"),
    prevent_initial_call=True
)
def download_filtered_data(n_clicks, section_value, label_value):
    filtered = unemployment_df.copy()

    if section_value:
        filtered = filtered[filtered["Section"] == section_value]
    if label_value:
        filtered = filtered[filtered["Label (Grouping)"] == label_value]

    export_df = filtered.drop(columns="geometry", errors="ignore")

    return dcc.send_data_frame(
        export_df.to_csv,
        "filtered_unemployment_data.csv",
        index=False
    )

# -----------------------------
# RUN APP
# -----------------------------
if "ipykernel" in sys.modules:
    app.run(jupyter_mode="inline", debug=True)
elif __name__ == "__main__":
    app.run(debug=True)
