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
        # Header + Description
        html.Div(
            [
                html.H2(
                    "Community Development Dashboard",
                    style={
                        "textAlign": "center",
                        "marginBottom": "6px",
                        "color": "#1F3A5F",
                        "fontSize": "30px",
                        "fontWeight": "700"
                    }
                ),
                html.P(
                    "Interactive summary of unemployment patterns across Richmond census tracts.",
                    style={
                        "textAlign": "center",
                        "marginBottom": "20px",
                        "color": "#4A6FA5",
                        "fontSize": "16px"
                    }
                )
            ]
        ),

        # Filter Panel
        html.Div(
            [
                html.H3("Filters", style={"marginBottom": "12px", "color": "#1F3A5F"}),

                # Section Filter
                html.Div(
                    [
                        html.Div(
                            [
                                html.Label("Section", style={"fontWeight": "600", "color": "#1F3A5F"}),
                                html.Span("ⓘ", id="section-help", style={"marginLeft": "6px", "cursor": "pointer"}),
                                dcc.Tooltip("Choose a Section to filter the dataset.", id="section-help-tooltip", targetable=True)
                            ],
                            style={"display": "flex", "alignItems": "center", "marginBottom": "6px"}
                        ),
                        dcc.Dropdown(
                            id="section-dropdown",
                            options=[{"label": s, "value": s} for s in unemployment_df["Section"].unique()],
                            value=unemployment_df["Section"].unique()[0],
                            clearable=False,
                        ),
                    ],
                    style={"flex": "1"}
                ),

                # Label Filter
                html.Div(
                    [
                        html.Div(
                            [
                                html.Label("Label (Grouping)", style={"fontWeight": "600", "color": "#1F3A5F"}),
                                html.Span("ⓘ", id="label-help", style={"marginLeft": "6px", "cursor": "pointer"}),
                                dcc.Tooltip("Choose a grouping to refine the Section filter.", id="label-help-tooltip", targetable=True)
                            ],
                            style={"display": "flex", "alignItems": "center", "marginBottom": "6px"}
                        ),
                        dcc.Dropdown(id="label-dropdown", clearable=False),
                    ],
                    style={"flex": "1"}
                ),
            ],
            style={"background": "#F2F4F7", "padding": "16px", "borderRadius": "8px", "marginBottom": "20px"}
        ),

        # KPI Cards
        html.Div(id="kpi-cards", style={"display": "flex", "gap": "16px", "marginBottom": "20px"}),

        # Two-column layout
        html.Div(
            [
                # Map
                html.Div(
                    [
                        html.H3("Unemployment Map", style={"marginBottom": "8px", "color": "#1F3A5F"}),
                        html.Span("ⓘ", id="map-help", style={"cursor": "pointer", "float": "right"}),
                        dcc.Tooltip("Click a census tract to view unemployment details.", id="map-help-tooltip", targetable=True),
                        dcc.Graph(id="map-graph", style={"height": "400px"})
                    ],
                    style={"flex": "1", "paddingRight": "12px"}
                ),

                # Histogram
                html.Div(
                    [
                        html.H3("Unemployment Distribution", style={"marginBottom": "8px", "color": "#1F3A5F"}),
                        html.Span("ⓘ", id="hist-help", style={"cursor": "pointer", "float": "right"}),
                        dcc.Tooltip("Histogram shows number of tracts grouped by unemployment rate.", id="hist-help-tooltip", targetable=True),
                        dcc.Graph(id="chart-graph", style={"height": "400px"})
                    ],
                    style={"flex": "1", "paddingLeft": "12px"}
                ),
            ],
            style={"display": "flex", "gap": "16px", "marginBottom": "20px"}
        ),

        # Download
        html.Div(
            [
                html.Button(
                    "Download Data (CSV)",
                    id="download-button",
                    n_clicks=0,
                    style={
                        "marginTop": "12px",
                        "backgroundColor": "#1F3A5F",
                        "color": "white",
                        "padding": "10px 16px",
                        "borderRadius": "6px",
                        "border": "none",
                        "fontWeight": "600"
                    }
                ),
                html.Span("ⓘ", id="download-help", style={"marginLeft": "8px", "cursor": "pointer"}),
                dcc.Tooltip("Download the filtered dataset as a CSV file.", id="download-help-tooltip", targetable=True)
            ],
            style={"marginBottom": "20px"}
        ),

        dcc.Download(id="download-data"),
    ],
    style={"padding": "16px"}
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

    # KPI Cards
    kpi_cards = [
        html.Div(
            [
                html.Div("Total Population", style={"fontWeight": "600", "marginBottom": "4px", "color": "#2F3E46"}),
                html.Div(f"{total_sum:,.0f}", style={"fontSize": "28px", "fontWeight": "700", "color": "#FFFFFF"}),
            ],
            style={"padding": "16px", "backgroundColor": "#4A6FA5", "borderRadius": "12px", "flex": "1"},
        ),
        html.Div(
            [
                html.Div("Mean Unemployment Rate", style={"fontWeight": "600", "marginBottom": "4px", "color": "#2F3E46"}),
                html.Div(f"{unemployment_avg:,.2f}", style={"fontSize": "28px", "fontWeight": "700", "color": "#FFFFFF"}),
            ],
            style={"padding": "16px", "backgroundColor": "#2F3E46", "borderRadius": "12px", "flex": "1"},
        ),
    ]

    if tract_unemployment.empty:
        return px.scatter(title="No unemployment records"), px.bar(title="No data"), kpi_cards

    # Map
    map_fig = px.choropleth(
        tract_unemployment,
        geojson=tract_unemployment.__geo_interface__,
        locations="GEOID",
        featureidkey="properties.GEOID",
        color="unemployment_rate",
        color_continuous_scale="Blues",
        hover_data={"GEOID": True, "unemployment_rate": ":.2f"},
        labels={"unemployment_rate": "Unemployment Rate"},
        title="Unemployment Rate by Census Tract",
    )

    map_fig.update_geos(fitbounds="locations", visible=False)

    map_fig.update_layout(
        height=400,
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        title_font=dict(color="#2F3E46", size=18)
    )

    # Histogram
    chart_fig = px.histogram(
        tract_unemployment,
        x="unemployment_rate",
        nbins=12,
        color_discrete_sequence=["#4A6FA5"],
        labels={"unemployment_rate": "Unemployment Rate (%)"},
        title="Unemployment Rate Distribution",
    )

    chart_fig.add_vline(
        x=unemployment_avg,
        line_width=2,
        line_dash="dash",
        line_color="#C9A66B"
    )

    chart_fig.add_vline(
        x=tract_unemployment["unemployment_rate"].median(),
        line_width=2,
        line_color="#2F3E46"
    )

    chart_fig.update_layout(
        height=400,
        margin={"r": 12, "t": 40, "l": 6, "b": 12},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        title_font=dict(color="#2F3E46", size=18)
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
    if not n_clicks:
        return None

    filtered = unemployment_df.copy()
    if section_value:
        filtered = filtered[filtered["Section"] == section_value]
    if label_value:
        filtered = filtered[filtered["Label (Grouping)"] == label_value]

    return dcc.send_data_frame(
        filtered.to_csv,
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
