import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import os

# Initialize session state
if 'alerts_df' not in st.session_state:
    st.session_state.alerts_df = None
if 'selected_alert' not in st.session_state:
    st.session_state.selected_alert = None
if 'timestamp_filter' not in st.session_state:
    st.session_state.timestamp_filter = 'all'

def parse_timestamp(text):
    try:
        # Try to extract timestamp from the alert text
        data = json.loads(text)
        if 'data' in data and 'event' in data['data'] and 'data_timestamp' in data['data']['event']:
            return datetime.fromtimestamp(data['data']['event']['data_timestamp'])
    except:
        pass
    return None

def filter_alerts_by_timestamp(alerts_df, filter_option):
    if filter_option == 'all':
        return alerts_df
    
    now = datetime.now()
    if filter_option == 'today':
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter_option == 'yesterday':
        start_time = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter_option == 'last_week':
        start_time = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        return alerts_df
    
    # Apply timestamp filter
    filtered_alerts = []
    for _, alert in alerts_df.iterrows():
        timestamp = datetime.strptime(alert.get('data_timestamp'), "%Y-%m-%d %H:%M:%S.%f%z").replace(tzinfo=None)
        if timestamp:
            if filter_option == 'yesterday':
                if start_time <= timestamp < end_time:
                    filtered_alerts.append(alert)
            else:
                if timestamp >= start_time:
                    filtered_alerts.append(alert)
    
    return pd.DataFrame(filtered_alerts)

def group_alerts(alerts_df):
    grouped = {}
    ungrouped = []
    
    # Filter out alerts from custom_bot source
    alerts_df = alerts_df[alerts_df['source'] != 'Doctor Droid'].copy()
    
    for _, alert in alerts_df.iterrows():
        # If no service, try to group by infrastructure
        infra_components = str(alert.get('infra_components', '')).split(', ') if pd.notna(alert.get('infra_components')) else ['']
        if infra_components and infra_components[0]:  # If infra components exist and not empty
            for component in infra_components:
                if component not in grouped:
                    grouped[component] = []
                grouped[component].append(alert)
            continue
            
        # First try to group by service
        services = str(alert.get('services', '')).split(', ') if pd.notna(alert.get('services')) else ['']
        if services and services[0]:  # If services exist and not empty
            for service in services:
                if service not in grouped:
                    grouped[service] = []
                grouped[service].append(alert)
            continue
        else:
            ungrouped.append(alert)
    
    return grouped, ungrouped

def display_alert_details(alert):
    st.sidebar.title("Alert Details")
    st.sidebar.markdown(f"**Title:** {alert['title']}")
    st.sidebar.markdown(f"**Source:** {alert['source']}")
    st.sidebar.markdown(f"**Tags:** {str(alert['tags'])}")
    
    # Display timestamp
    timestamp = parse_timestamp(alert['text'])
    if timestamp:
        st.sidebar.markdown(f"**Timestamp:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Display full text in a code block
    st.sidebar.markdown("**Full Alert Text:**")
    st.sidebar.code(alert['text'], language='json')

def format_timestamp(timestamp):
    if timestamp:
        return timestamp.strftime('%Y-%m-%d %H:%M:%S')
    return 'N/A'

def main():
    st.title("Alert Analysis Dashboard")
    
    # Sidebar for file selection and filters
    st.sidebar.header("Configuration")
    
    # Get list of Excel files in the current directory
    excel_files = [f for f in os.listdir('.') if f.endswith('_updated.xlsx')]
    
    if not excel_files:
        st.error("No Excel files found. Please run the AlertParser first to generate the Excel file.")
        return
    
    selected_file = st.sidebar.selectbox(
        "Select Excel File",
        excel_files,
        format_func=lambda x: x.replace('_updated.xlsx', '')
    )
    
    # Add timestamp filter
    timestamp_filter = st.sidebar.selectbox(
        "Filter by Time",
        ['all', 'today', 'yesterday', 'last_week'],
        format_func=lambda x: x.replace('_', ' ').title()
    )
    
    # Load data if not already loaded or if file changed
    if st.session_state.alerts_df is None or st.session_state.current_file != selected_file:
        with st.spinner("Loading alerts..."):
            st.session_state.alerts_df = pd.read_excel(selected_file)
            st.session_state.current_file = selected_file
    
    # Main content area
    if st.session_state.alerts_df is not None:
        # Apply timestamp filter
        filtered_df = filter_alerts_by_timestamp(st.session_state.alerts_df, timestamp_filter)
        
        # Group alerts
        grouped, ungrouped = group_alerts(filtered_df)
        
        # Display ungrouped alerts first
        if ungrouped:
            with st.expander("Ungrouped Alerts", expanded=True):
                for alert in ungrouped:
                    col1, col2, col3 = st.columns([0.6, 0.2, 0.2])
                    with col1:
                        if st.button(f"{alert['title']}", key=f"ungrouped_{alert['id']}"):
                            st.session_state.selected_alert = alert
                    with col2:
                        st.text(alert['source'])
                    with col3:
                        timestamp = alert['data_timestamp']
                        st.text(timestamp)
        
        # Display grouped alerts
        for group_name, alerts in grouped.items():
            with st.expander(f"{group_name} ({len(alerts)} alerts)", expanded=True):
                # Sort alerts by timestamp if available
                sorted_alerts = sorted(
                    alerts,
                    key=lambda x: parse_timestamp(x['text']) or datetime.min,
                    reverse=True
                )
                
                for alert in sorted_alerts:
                    col1, col2, col3 = st.columns([0.6, 0.2, 0.2])
                    with col1:
                        if st.button(f"{alert['title']}", key=f"{group_name}_{alert['id']}"):
                            st.session_state.selected_alert = alert
                    with col2:
                        st.text(alert['source'])
                    with col3:
                        timestamp = alert['data_timestamp']
                        st.text(timestamp)
        
        # Display selected alert details in sidebar
        if st.session_state.selected_alert is not None:
            display_alert_details(st.session_state.selected_alert)

if __name__ == "__main__":
    main() 