import streamlit as st
import pandas as pd
import plotly.express as px


st.set_page_config(layout="wide")
st.title("Provisional Natality Data Dashboard")
st.subheader("Birth Analysis by State and Gender")


@st.cache_data
def load_data():
    try:
        df = pd.read_csv("Provisional_Natality_2025_CDC.csv")
    except FileNotFoundError:
        st.error("Dataset file not found in repository.")
        return None
    except Exception as exc:
        st.error(f"Unable to load the dataset: {exc}")
        return None

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )

    required_fields = [
        "state_of_residence",
        "month",
        "month_code",
        "year_code",
        "sex_of_infant",
        "births",
    ]

    normalized_lookup = {
        column.replace("_", "").lower(): column for column in df.columns
    }

    matched_columns = {}
    missing_fields = []

    for field in required_fields:
        normalized_field = field.replace("_", "").lower()
        if field in df.columns:
            matched_columns[field] = field
        elif normalized_field in normalized_lookup:
            matched_columns[field] = normalized_lookup[normalized_field]
        else:
            missing_fields.append(field)

    if missing_fields:
        st.error(
            "Missing required logical fields: " + ", ".join(missing_fields)
        )
        st.write(df.columns)
        return None

    rename_map = {
        actual_name: logical_name
        for logical_name, actual_name in matched_columns.items()
        if actual_name != logical_name
    }
    if rename_map:
        df = df.rename(columns=rename_map)

    df["births"] = pd.to_numeric(df["births"], errors="coerce")
    df = df.dropna(subset=["births"]).copy()

    return df


def apply_multiselect_filter(data, column, selected_values):
    if "All" in selected_values or not selected_values:
        return data
    return data[data[column].isin(selected_values)]


df = load_data()
if df is None:
    st.stop()

month_order = (
    df[["month", "month_code"]]
    .dropna(subset=["month"])
    .drop_duplicates()
    .sort_values(["month_code", "month"], na_position="last")["month"]
    .astype(str)
    .tolist()
)
gender_options = sorted(df["sex_of_infant"].dropna().astype(str).unique().tolist())
state_options = sorted(
    df["state_of_residence"].dropna().astype(str).unique().tolist()
)

selected_months = st.sidebar.multiselect(
    "Select Month",
    options=["All"] + month_order,
    default=["All"],
)
selected_genders = st.sidebar.multiselect(
    "Select Gender",
    options=["All"] + gender_options,
    default=["All"],
)
selected_states = st.sidebar.multiselect(
    "Select State",
    options=["All"] + state_options,
    default=["All"],
)

filtered_df = df.copy()
filtered_df = apply_multiselect_filter(filtered_df, "month", selected_months)
filtered_df = apply_multiselect_filter(
    filtered_df, "sex_of_infant", selected_genders
)
filtered_df = apply_multiselect_filter(
    filtered_df, "state_of_residence", selected_states
)

if filtered_df.empty:
    st.warning("No data matches the selected filters.")
else:
    chart_data = (
        filtered_df.groupby(
            ["state_of_residence", "sex_of_infant"], as_index=False,
            dropna=False,
        )["births"]
        .sum()
        .sort_values(["state_of_residence", "sex_of_infant"])
    )

    figure = px.bar(
        chart_data,
        x="state_of_residence",
        y="births",
        color="sex_of_infant",
        title="Total Births by State and Gender",
        labels={
            "state_of_residence": "State of Residence",
            "births": "Total Births",
            "sex_of_infant": "Gender",
        },
        template="plotly_white",
        barmode="group",
    )
    figure.update_layout(
        legend_title_text="Gender",
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis={"categoryorder": "array", "categoryarray": sorted(chart_data["state_of_residence"].astype(str).unique())},
    )

    st.plotly_chart(figure, use_container_width=True)

    display_df = filtered_df.sort_values(
        ["state_of_residence", "month_code", "sex_of_infant"],
        na_position="last",
    ).reset_index(drop=True)
    st.dataframe(display_df, use_container_width=True, hide_index=True)
