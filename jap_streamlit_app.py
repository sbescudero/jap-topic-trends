import streamlit as st
import pandas as pd
import altair as alt
from pathlib import Path

# ============================
# FILES FOR DEPLOYED APP
# ============================
# These files should be in the same GitHub folder as this app.py file.
THEME_CSV = "subtheme_counts.csv"   # Existing file; displayed as "themes" in the app
TOPIC_CSV = "topic_counts.csv"
DOCUMENT_MATRIX_XLSX = "editorial_topic visualizations_To JAP SI Team.xlsx"

DOCUMENT_MATRIX_SHEET = "document matrix"
PY_COL = "PY"  # Publication year column in the document matrix

BASE_YEAR = 1980
WINDOW_SIZE = 5
# ============================


st.set_page_config(
    page_title="JAP Topic Trends",
    layout="wide"
)

st.title("Journal of Applied Psychology Topic Trends Over Time")

st.markdown(
    """
This interactive page shows trends for the topics and broader themes represented in the
special issue editorial.

**Raw counts** show the number of JAP articles in each 5-year window that were assigned
to each focal topic or theme.

**Share of JAP publications** shows those same counts as a percentage of all eligible
JAP articles published in the same 5-year window. This adjusts for changes in the total
number of JAP publications over time and helps show whether a topic or theme became more
or less prominent relative to the journal as a whole.
"""
)


def get_start_year(year_range):
    """Extract the first year from a range like '1980-1984'."""
    try:
        return int(str(year_range).split("-")[0])
    except Exception:
        return None


def make_year_range5(year):
    """Convert an exact publication year into a 5-year window anchored at BASE_YEAR."""
    year = int(year)
    start = BASE_YEAR + ((year - BASE_YEAR) // WINDOW_SIZE) * WINDOW_SIZE
    end = start + WINDOW_SIZE - 1
    return f"{start}-{end}"


@st.cache_data
def load_data():
    # ----------------------------
    # Load existing focal count files
    # ----------------------------
    theme_path = Path(THEME_CSV)
    topic_path = Path(TOPIC_CSV)
    workbook_path = Path(DOCUMENT_MATRIX_XLSX)

    if not theme_path.exists():
        raise FileNotFoundError(f"Could not find theme count file: {THEME_CSV}")

    if not topic_path.exists():
        raise FileNotFoundError(f"Could not find topic count file: {TOPIC_CSV}")

    if not workbook_path.exists():
        raise FileNotFoundError(f"Could not find document matrix workbook: {DOCUMENT_MATRIX_XLSX}")

    theme_df = pd.read_csv(theme_path)
    topic_df = pd.read_csv(topic_path)

    # Basic checks
    for col in ["Subtheme", "YearRange5", "Count"]:
        if col not in theme_df.columns:
            raise ValueError(f"{THEME_CSV} missing column: {col}")

    for col in ["Subtheme", "Topic", "YearRange5", "Count"]:
        if col not in topic_df.columns:
            raise ValueError(f"{TOPIC_CSV} missing column: {col}")

    # Rename Subtheme -> Theme for user-facing app language
    theme_df = theme_df.rename(columns={"Subtheme": "Theme"})
    topic_df = topic_df.rename(columns={"Subtheme": "Theme"})

    # Make counts numeric
    theme_df["Count"] = pd.to_numeric(theme_df["Count"], errors="coerce").fillna(0)
    topic_df["Count"] = pd.to_numeric(topic_df["Count"], errors="coerce").fillna(0)

    # Get the year windows already used in the focal CSV files
    year_range_order = sorted(
        set(theme_df["YearRange5"].dropna().unique()).union(
            set(topic_df["YearRange5"].dropna().unique())
        ),
        key=get_start_year
    )

    # ----------------------------
    # Load full document matrix for denominator
    # ----------------------------
    doc_matrix = pd.read_excel(
        workbook_path,
        sheet_name=DOCUMENT_MATRIX_SHEET
    )

    if PY_COL not in doc_matrix.columns:
        raise ValueError(
            f"Document matrix missing column '{PY_COL}'. "
            f"Available columns include: {list(doc_matrix.columns)[:20]}"
        )

    # Clean publication year
    doc_matrix[PY_COL] = pd.to_numeric(doc_matrix[PY_COL], errors="coerce")
    doc_matrix = doc_matrix.dropna(subset=[PY_COL]).copy()
    doc_matrix[PY_COL] = doc_matrix[PY_COL].astype(int)

    # Convert exact year to same 5-year windows used in topic/theme CSVs
    doc_matrix["YearRange5"] = doc_matrix[PY_COL].apply(make_year_range5)

    # Keep only windows shown in the visualization
    doc_matrix = doc_matrix[doc_matrix["YearRange5"].isin(year_range_order)].copy()

    # Total eligible JAP publications per 5-year window
    jap_totals = (
        doc_matrix.groupby("YearRange5")
        .size()
        .reset_index(name="Total_JAP_Publications")
    )

    # ----------------------------
    # Add share-of-JAP columns
    # ----------------------------
    def add_share_of_jap(df):
        out = df.merge(jap_totals, on="YearRange5", how="left")
        out["Share_of_JAP"] = out["Count"] / out["Total_JAP_Publications"]
        out["Percent_of_JAP"] = out["Share_of_JAP"] * 100
        return out

    theme_df = add_share_of_jap(theme_df)
    topic_df = add_share_of_jap(topic_df)

    return theme_df, topic_df, year_range_order


theme_counts, topic_counts, year_range_order = load_data()


# ============================
# SIDEBAR CONTROLS
# ============================

st.sidebar.header("Controls")

view_level = st.sidebar.radio(
    "View level",
    ["Themes", "Topics"],
    index=0
)

themes = sorted(theme_counts["Theme"].dropna().unique())
theme_options = ["All themes"] + themes

selected_theme = st.sidebar.selectbox(
    "Theme filter",
    theme_options,
    index=0
)

if view_level == "Topics":
    if selected_theme == "All themes":
        topic_pool = topic_counts["Topic"].dropna().unique()
    else:
        topic_pool = topic_counts.loc[
            topic_counts["Theme"] == selected_theme, "Topic"
        ].dropna().unique()

    topic_pool = sorted(topic_pool)
    default_topics = topic_pool[:10] if len(topic_pool) > 10 else topic_pool

    selected_topics = st.sidebar.multiselect(
        "Topics to display",
        topic_pool,
        default=default_topics
    )


# ============================
# CHART HELPERS
# ============================

def make_line_chart(data, label_col, y_col, y_title, tooltip_cols):
    """
    Creates a line chart with a bottom legend and no label truncation.
    """
    legend = alt.Legend(
        orient="bottom",
        direction="vertical",
        columns=2,
        labelLimit=0,
        titleLimit=0,
        symbolLimit=0
    )

    return (
        alt.Chart(data)
        .mark_line(point=True)
        .encode(
            x=alt.X(
                "YearRange5:N",
                sort=year_range_order,
                title="5-year range"
            ),
            y=alt.Y(f"{y_col}:Q", title=y_title),
            color=alt.Color(
                f"{label_col}:N",
                title=label_col,
                legend=legend
            ),
            tooltip=tooltip_cols
        )
        .properties(height=450)
        .interactive()
    )


def show_trend_view(data, label_col, subtitle):
    st.markdown(f"**View:** {subtitle}")

    if data.empty:
        st.warning("No data available for this selection.")
        return

    tab_raw, tab_share = st.tabs(["Raw counts", "Share of JAP publications"])

    with tab_raw:
        st.markdown(
            """
**Raw counts** show the number of articles in each 5-year window assigned to each
focal topic or theme. These values are useful for understanding absolute publication
volume over time.
"""
        )

        raw_chart = make_line_chart(
            data=data,
            label_col=label_col,
            y_col="Count",
            y_title="Number of articles",
            tooltip_cols=[label_col, "YearRange5", "Count"]
        )

        st.altair_chart(raw_chart, use_container_width=True)

    with tab_share:
        st.markdown(
            """
**Share of JAP publications** divides each focal topic/theme count by the total number
of eligible JAP articles published in the same 5-year window. This helps distinguish
growth in a topic/theme from growth in JAP's overall publication volume.
"""
        )

        share_chart = make_line_chart(
            data=data,
            label_col=label_col,
            y_col="Percent_of_JAP",
            y_title="Percent of all eligible JAP articles",
            tooltip_cols=[
                label_col,
                "YearRange5",
                "Count",
                "Total_JAP_Publications",
                alt.Tooltip("Percent_of_JAP:Q", format=".2f", title="Percent of JAP")
            ]
        )

        st.altair_chart(share_chart, use_container_width=True)


# ============================
# MAIN CONTENT
# ============================

if view_level == "Themes":
    st.subheader("Theme-level trends by 5-year range")

    if selected_theme == "All themes":
        data = theme_counts.copy()
        subtitle = "All themes"
    else:
        data = theme_counts[theme_counts["Theme"] == selected_theme].copy()
        subtitle = f"Theme: {selected_theme}"

    show_trend_view(
        data=data,
        label_col="Theme",
        subtitle=subtitle
    )

else:
    st.subheader("Topic-level trends by 5-year range")

    if selected_theme == "All themes":
        data = topic_counts.copy()
        subtitle = "All themes"
    else:
        data = topic_counts[topic_counts["Theme"] == selected_theme].copy()
        subtitle = f"Theme: {selected_theme}"

    if "selected_topics" in locals() and selected_topics:
        data = data[data["Topic"].isin(selected_topics)].copy()

    show_trend_view(
        data=data,
        label_col="Topic",
        subtitle=subtitle
    )