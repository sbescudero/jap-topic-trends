
import streamlit as st
import pandas as pd
import altair as alt

# ============================
# USER SETTINGS – EDIT THIS
# ============================
SUBTHEME_CSV = "subtheme_counts.csv"
TOPIC_CSV = "topic_counts.csv"
# ============================

st.set_page_config(
    page_title="JAP Topic Trends",
    layout="wide"
)

st.title("Journal of Applied Psychology Topic Trends Over Time")

st.markdown(
    """
This graph shows how topics and broader subthemes represented in JAP have trended over time.
Use the controls on the left to switch between **subtheme** and **topic** views,
and to filter by subtheme.
"""
)

def get_start_year(r):
    try:
        return int(str(r).split("-")[0])
    except Exception:
        return None

@st.cache_data
def load_data():
    sub_df = pd.read_csv(SUBTHEME_CSV)
    topic_df = pd.read_csv(TOPIC_CSV)

    # Basic checks
    for col in ["Subtheme", "YearRange5", "Count"]:
        if col not in sub_df.columns:
            raise ValueError(f"subtheme_counts.csv missing column: {col}")
    for col in ["Subtheme", "Topic", "YearRange5", "Count"]:
        if col not in topic_df.columns:
            raise ValueError(f"topic_counts.csv missing column: {col}")

    # Order for year ranges (based on start year)
    year_order = sorted(sub_df["YearRange5"].unique(), key=get_start_year)

    return sub_df, topic_df, year_order

subtheme_counts, topic_counts, year_range_order = load_data()

# Sidebar controls
st.sidebar.header("Controls")

view_level = st.sidebar.radio(
    "View level",
    ["Subthemes", "Topics"],
    index=0
)

subthemes = sorted(subtheme_counts["Subtheme"].dropna().unique())
subtheme_options = ["All subthemes"] + subthemes
selected_subtheme = st.sidebar.selectbox(
    "Subtheme filter",
    subtheme_options,
    index=0
)

if view_level == "Topics":
    # Available topics depend on subtheme filter
    if selected_subtheme == "All subthemes":
        topic_pool = topic_counts["Topic"].dropna().unique()
    else:
        topic_pool = topic_counts.loc[
            topic_counts["Subtheme"] == selected_subtheme, "Topic"
        ].dropna().unique()

    topic_pool = sorted(topic_pool)
    default_topics = topic_pool[:10] if len(topic_pool) > 10 else topic_pool

    selected_topics = st.sidebar.multiselect(
        "Topics to display",
        topic_pool,
        default=default_topics
    )

# Main content
if view_level == "Subthemes":
    st.subheader("Subtheme-level trends (article counts per 5-year range)")

    if selected_subtheme == "All subthemes":
        data = subtheme_counts.copy()
        subtitle = "All subthemes"
    else:
        data = subtheme_counts[subtheme_counts["Subtheme"] == selected_subtheme]
        subtitle = f"Subtheme: {selected_subtheme}"

    st.markdown(f"**View:** {subtitle}")

    if data.empty:
        st.warning("No data available for this selection.")
    else:
        chart = (
            alt.Chart(data)
            .mark_line(point=True)
            .encode(
                x=alt.X(
                    "YearRange5:N",
                    sort=year_range_order,
                    title="5-year range"
                ),
                y=alt.Y("Count:Q", title="Number of articles"),
                color=alt.Color("Subtheme:N", title="Subtheme"),
                tooltip=["Subtheme", "YearRange5", "Count"]
            )
            .properties(height=450)
            .interactive()
        )
        st.altair_chart(chart, use_container_width=True)

else:  # view_level == "Topics"
    st.subheader("Topic-level trends (article counts per 5-year range)")

    if selected_subtheme == "All subthemes":
        data = topic_counts.copy()
        subtitle = "All subthemes"
    else:
        data = topic_counts[topic_counts["Subtheme"] == selected_subtheme]
        subtitle = f"Subtheme: {selected_subtheme}"

    st.markdown(f"**View:** {subtitle}")

    if "selected_topics" in locals() and selected_topics:
        data = data[data["Topic"].isin(selected_topics)]

    if data.empty:
        st.warning("No data available for this selection.")
    else:
        chart = (
            alt.Chart(data)
            .mark_line(point=True)
            .encode(
                x=alt.X(
                    "YearRange5:N",
                    sort=year_range_order,
                    title="5-year range"
                ),
                y=alt.Y("Count:Q", title="Number of articles"),
                color=alt.Color("Topic:N", title="Topic"),
                tooltip=["Subtheme", "Topic", "YearRange5", "Count"]
            )
            .properties(height=450)
            .interactive()
        )
        st.altair_chart(chart, use_container_width=True)
