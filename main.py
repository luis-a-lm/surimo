import os
import us
import base64
import streamlit as st
import pandas as pd
import plotly.express as px

# To run: python -m streamlit run main.py

st.set_page_config(layout="wide", page_title="SURIMO AI")

def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# logo_base64 = get_base64_image("my_logo.png")

last_updated_str = "1d ago"

# st.markdown(
#     f"""
#     <div style="background-color:#003478;padding:10px 20px;border-bottom:1px solid #ddd;display:flex;justify-content:space-between;align-items:center;">
#         <div style="display:flex;align-items:center;">
#             <img src="data:image/png;base64,{logo_base64}" alt="Logo" width="100" style="margin-right:15px;">
#             <h2 style="margin:0;">SURIMO AI - Automated Supplier Risk Monitor</h2>
#         </div>
#         <span style="font-size:0.9em;color:#FFFFFF;">Last updated: {last_updated_str}</span>
#     </div>
#     """,
#     unsafe_allow_html=True
# )

st.markdown(
    f"""
    <div style="background-color:#003478;padding:10px 20px;border-bottom:1px solid #ddd;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <h2 style="margin:0;color:white;">SURIMO AI - Automated Supplier Risk Monitor</h2>
            <span style="font-size:0.9em;color:#FFFFFF;">Last updated: {last_updated_str}</span>
        </div>
        <div style="text-align:center;margin-top:10px;">
            <span style="font-size:1.1em;color:white;">
                <strong>Data Sensitivity:</strong>
                <span style='color: #00FF00;'>Unrestricted: ✅</span> &nbsp;|&nbsp;
                <span style='color: #FF6347;'>CUI: ❌</span> &nbsp;|&nbsp;
                <span style='color: #FF6347;'>ECI: ❌</span> &nbsp;|&nbsp;
                <span style='color: #FF6347;'>LMPI: ❌</span>
            </span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


USE_TEST_FILE = False  # Set to False to enable file upload

if USE_TEST_FILE:
    uploaded_file = "output.csv"
    df = pd.read_csv(uploaded_file, dtype=str, quotechar='"', skipinitialspace=True)
else:
    uploaded_file = st.sidebar.file_uploader("Upload your CSV", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file, dtype=str, quotechar='"', skipinitialspace=True)
    else:
        st.warning("📤 Please upload a properly formatted CSV to begin.")
        st.stop()

if uploaded_file:

    # Clean all string values
    df = df.applymap(lambda x: x.strip('" ').strip() if isinstance(x, str) else x)

    # Rename columns safely
    column_map = {
        'Company Title': 'Company',
        'Risk Rating (0-5)': 'Risk Rating',
        'Risk Type (Event Tag)': 'Risk Type',
        'Justification': 'Justification',
        'Recommended Action': 'Recommended Action',
        'Source': 'Source',
        'Title': 'Article Title',
        'Article Link': 'Link',
        'Date': 'Date',
        'Summary': 'Summary',
        'Location (City, State)': 'Location'
    }

    existing_columns = df.columns
    safe_column_map = {k: v for k, v in column_map.items() if k in existing_columns}
    df.rename(columns=safe_column_map, inplace=True)

    # Convert Risk Rating to integer (fill NaN with 0)
    df['Risk Rating'] = pd.to_numeric(df['Risk Rating'], errors='coerce').fillna(0).astype(int)

    # Parse Date
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

    # Handle missing risk type
    if 'Risk Type' not in df.columns:
        df['Risk Type'] = 'Unspecified'
    else:
        df['Risk Type'] = df['Risk Type'].fillna('Unspecified')

    # Layout
    col1, col2, col3 = st.columns([0.7, 1, 0.7])

    # ---------------- Column 1 ----------------
    with col1:
        CSV_FILE = 'tracked_suppliers.csv'

        # --- Helper Functions ---
        def load_tracked_suppliers():
            if os.path.exists(CSV_FILE):
                df = pd.read_csv(CSV_FILE)
                return df['Supplier'].tolist()
            return []

        def save_tracked_suppliers(suppliers):
            df = pd.DataFrame(suppliers, columns=['Supplier'])
            df.to_csv(CSV_FILE, index=False)

        # --- App State Initialization ---
        if 'tracked_suppliers' not in st.session_state:
            st.session_state.tracked_suppliers = load_tracked_suppliers()
        
        # --- Display Currently Tracked Suppliers ---
        st.header("Currently Tracking")
        if st.session_state.tracked_suppliers:
            tracked_df = pd.DataFrame(st.session_state.tracked_suppliers, columns=["Supplier"])
            st.dataframe(tracked_df, height=220)
        else:
            st.info("No suppliers currently being tracked.")

        # --- Add Supplier UI ---
        st.header("Add/Remove Supplier")
        new_supplier = st.text_input("Enter supplier name")

        if st.button("Add Supplier"):
            if new_supplier and new_supplier not in st.session_state.tracked_suppliers:
                st.session_state.tracked_suppliers.append(new_supplier)
                save_tracked_suppliers(st.session_state.tracked_suppliers)
                st.success(f"Added '{new_supplier}' to tracking list.")
            elif new_supplier in st.session_state.tracked_suppliers:
                st.warning(f"'{new_supplier}' is already being tracked.")
            else:
                st.warning("Please enter a valid supplier name.")

        # --- Remove Supplier UI ---
        if st.session_state.tracked_suppliers:
            supplier_to_remove = st.selectbox("Select a supplier to remove", st.session_state.tracked_suppliers)

            if st.button("Remove Supplier"):
                st.session_state.tracked_suppliers.remove(supplier_to_remove)
                save_tracked_suppliers(st.session_state.tracked_suppliers)
                st.success(f"Removed '{supplier_to_remove}' from tracking list.")
        else:
            st.info("No suppliers currently being tracked to remove.")

        st.header("Vendor News Filter")
        search = st.text_input("Search Company")
        filtered = df[df['Company'].str.contains(search, case=False, na=False)]
        st.dataframe(filtered[['Company', 'Article Title', 'Risk Rating', 'Risk Type', 'Recommended Action']], height=170)

        st.header("Risk Score Distribution")
        # Count risk ratings and relabel them as "Level X"
        risk_data = df['Risk Rating'].value_counts().reset_index()
        risk_data.columns = ['Risk Rating', 'Count']
        risk_data = risk_data.sort_values(by='Risk Rating')
        risk_data['Level'] = risk_data['Risk Rating'].apply(lambda x: f"Level {x}")

        # Create the donut chart
        fig = px.pie(
            risk_data,
            names='Level',
            values='Count',
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.Blues_r
        )
        fig.update_traces(textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)

    # ---------------- Column 2 ----------------
    with col2:
        st.header("Risk Density Maps")

        # Extract US states from 'Location'
        def extract_state(location):
            if pd.isna(location):
                return None
            parts = location.split(',')
            for i, part in enumerate(parts):
                if 'United States' in part:
                    if i >= 1:
                        state_candidate = parts[i-1].strip()
                        if ',' in state_candidate:
                            state = state_candidate.split(',')[-1].strip()
                        else:
                            state = state_candidate
                        return state
            return None

        us_data = df.copy()
        us_data['State'] = us_data['Location'].apply(extract_state)

        def state_to_abbrev(state_name):
            try:
                return us.states.lookup(state_name).abbr
            except:
                return None

        us_data['State_Abbrev'] = us_data['State'].apply(state_to_abbrev)

        # Count risk by state
        risk_by_state = (
            us_data.dropna(subset=['State_Abbrev'])
                .groupby('State_Abbrev')
                .size()
                .reset_index(name='Risk Count')
        )

        # Create full list of all states to show zero-risk states as well
        all_states = pd.DataFrame([s.abbr for s in us.states.STATES], columns=['State_Abbrev'])
        risk_by_state = all_states.merge(risk_by_state, on='State_Abbrev', how='left').fillna(0)

        # Light mode settings
        light_bg_color = "#0e1117"  # dark blue background for sea
        light_sea_color = "#0e1117"  # also used for lakes and oceans
        light_green_for_zero = "#ffffff"

        # US color scale (blue hues)
        colorscale_us = [
            [0.0, '#e0f7fa'],   # light cyan
            [0.3, '#4dd0e1'],   # medium turquoise
            [0.6, '#0288d1'],   # strong blue
            [1.0, '#01579b']    # deep blue
]


        if not risk_by_state.empty:
            fig_us = px.choropleth(
                risk_by_state,
                locations='State_Abbrev',
                locationmode='USA-states',
                scope='usa',
                color='Risk Count',
                color_continuous_scale=colorscale_us,
                range_color=(0, risk_by_state['Risk Count'].max() or 1),
                title='Risk Density by U.S. State',
                labels={'Risk Count': 'Risk Count'}
            )
            fig_us.update_layout(
                height=285,
                margin={"r": 0, "t": 40, "l": 0, "b": 0},
                geo=dict(
                    bgcolor=light_bg_color,
                    lakecolor=light_sea_color,
                    showlakes=True,
                    showland=True,
                    landcolor="white",
                    showcountries=True,
                    countrycolor='black',
                    showsubunits=True,
                    subunitcolor='gray',
                    showframe=False,
                ),
                paper_bgcolor=light_bg_color,
                plot_bgcolor=light_bg_color,
                font=dict(color='black'),
            )
        else:
            fig_us = None

        # World Map: Aggregate risk by country
        def extract_country(location):
            if pd.isna(location):
                return None
            parts = location.split(',')
            return parts[-1].strip()

        world_data = df.copy()
        world_data['Country'] = world_data['Location'].apply(extract_country)

        risk_by_country = (
            world_data.dropna(subset=['Country'])
                    .groupby('Country')
                    .size()
                    .reset_index(name='Risk Count')
        )

        # World color scale: blue hues
        colorscale_world = [
            [0.0, '#e0f7fa'],   # light cyan
            [0.3, '#4dd0e1'],   # medium turquoise
            [0.6, '#0288d1'],   # strong blue
            [1.0, '#01579b']    # deep blue
        ]


        if not risk_by_country.empty:
            fig_world = px.choropleth(
                risk_by_country,
                locations='Country',
                locationmode='country names',
                color='Risk Count',
                color_continuous_scale=colorscale_world,
                title='Risk Density by Country',
            )
            fig_world.update_layout(
                height=285,
                margin={"r": 0, "t": 40, "l": 0, "b": 0},
                geo=dict(
                    bgcolor=light_bg_color,
                    lakecolor=light_sea_color,
                    showland=True,
                    landcolor="white",
                    showcountries=True,
                    countrycolor='black',
                    showframe=False,
                ),
                paper_bgcolor=light_bg_color,
                plot_bgcolor=light_bg_color,
                font=dict(color='black'),
            )
        else:
            fig_world = None

        # Map toggle
        view_option = st.radio("Select Map View:", options=['U.S. States (default)', 'World Map'])

        if view_option == 'U.S. States (default)':
            if fig_us:
                st.plotly_chart(fig_us, use_container_width=True)
            else:
                st.info("No valid U.S. state-level location data available.")
        else:
            if fig_world:
                st.plotly_chart(fig_world, use_container_width=True)
            else:
                st.info("No valid country-level location data available.")



        # Risk Timeline

        st.header("Risk Timeline")
        if df['Date'].notna().sum() > 0:
            timeline = df.groupby(df['Date'].dt.date).size().reset_index(name='Counts')
            fig = px.line(timeline, x='Date', y='Counts', markers=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No valid dates found to generate timeline.")

        # Risk Type Distribution Donut Chart

        st.header("Risk Type Distribution")
        pie_data = df['Risk Type'].value_counts().reset_index()
        pie_data.columns = ['Risk Type', 'Count']
        fig = px.pie(pie_data, names='Risk Type', values='Count', hole=0.4, color_discrete_sequence=px.colors.sequential.Blues)
        st.plotly_chart(fig, use_container_width=True)

    # ---------------- Column 3 ----------------
    with col3:
        st.header("Recent Articles")

        recent = df.sort_values(by='Date', ascending=False).head(20)

        # Build a scrollable HTML container for articles
        article_html = """
    <div style="max-height: 1050px; overflow-y: auto; padding-right: 10px;">
    """

        for _, row in recent.iterrows():
            company = row['Company']
            rating = row['Risk Rating']
            risk_type = row['Risk Type']
            title = row['Article Title']
            link = row['Link']
            summary = row['Summary']
            source = row['Source']
            date_str = row['Date'].strftime('%Y-%m-%d') if pd.notna(row['Date']) else 'Unknown'

            article_html += f"""
    <div style="margin-bottom:20px;">
        <strong>{company}</strong> | Risk: {rating} | Type: {risk_type}<br>
        <a href="{link}" target="_blank">{title}</a><br>
        <small>{source} - {date_str}</small><br>
        <p>{summary}</p>
        <hr>
    </div>
    """

        article_html += "</div>"

        # Render the scrollable HTML properly
        st.markdown(article_html, unsafe_allow_html=True)

        st.markdown("---")

        st.subheader("ℹ️ About This Dashboard")
        st.info("""
        The SURIMO AI Dashboard lets you monitor supplier risk by entering company names in the "Add Supplier to Track" section. It automatically checks for updates each day using data from the [GDELT Events 1.0](https://www.gdeltproject.org/) project.

        An LLM with retrieval-augmented generation (RAG) searches the GDELT database for matches, extracts relevant articles, and summarizes the results for each tracked company.
        """)
else:

    st.warning("📤 Please upload a properly formatted CSV to begin.")

