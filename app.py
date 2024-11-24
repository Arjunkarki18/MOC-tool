import os
import glob
import requests
import base64
import json
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import streamlit as st

# Constants
USERNAME = "dew"  # Replace with your O*NET username
PASSWORD = "5998nhd"  # Replace with your O*NET password
OUTPUT_DIR = "./occupation_data"

# Utility functions
def clean_output_directory(directory_path):
    """Remove all JSON files from the specified directory."""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
    json_files = glob.glob(os.path.join(directory_path, "*.json"))
    for file in json_files:
        os.remove(file)

def fetch_soc_data(keyword):
    """Fetch and process SOC data for a given keyword."""
    soc_url = f"https://services.onetcenter.org/ws/veterans/military?keyword={keyword}"
    response = requests.get(soc_url, auth=(USERNAME, PASSWORD))

    if response.status_code != 200:
        st.error(f"Failed to fetch military SOC codes. Error: {response.text}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    soc_codes = [code.text.strip() for code in soup.find_all("code")]

    if not soc_codes:
        st.warning("No SOC codes found for the given keyword.")
        return []

    soc_data = []
    for soc_code in soc_codes:
        soc_url = f"https://services.onetcenter.org/ws/online/occupations/{soc_code}/"
        response = requests.get(soc_url, auth=(USERNAME, PASSWORD))
        if response.status_code != 200:
            #st.error(f"Failed to fetch data for SOC code {soc_code}. Error: {response.text}")
            continue

        try:
            root = ET.fromstring(response.content)
        except ET.ParseError:
            st.error(f"Failed to parse XML for SOC code {soc_code}.")
            continue

        # Build output data
        output_data = {
            "code": root.findtext("code", ""),
            "title": root.findtext("title", ""),
            "description": root.findtext("description", "").strip(),
            "also_called": [title.text.strip() for title in root.findall("sample_of_reported_job_titles/title")],
            "tasks": [],
        }

        # Fetch task details
        tasks_url = f"{soc_url}details/tasks"
        tasks_response = requests.get(tasks_url, auth=(USERNAME, PASSWORD))
        if tasks_response.status_code == 200:
            try:
                tasks_root = ET.fromstring(tasks_response.content)
                output_data["tasks"] = [
                    task.findtext("statement", "").strip()
                    for task in tasks_root.findall("task")
                ]
            except ET.ParseError:
                st.error(f"Failed to parse tasks for SOC code {soc_code}.")

        soc_data.append(output_data)

        # Save data to a JSON file
        with open(os.path.join(OUTPUT_DIR, f"output_{soc_code}.json"), "w") as file:
            json.dump(output_data, file, indent=2)

    return soc_data

# Streamlit app
def main():
    st.title("Interactive SOC Data Dashboard")
    st.sidebar.header("Input Parameters")
    st.sidebar.write("Enter a Military Title or MOC Code to fetch SOC data.")

    keyword = st.sidebar.text_input("Military Title or MOC Code", "")
    if st.sidebar.button("Fetch Data"):
        if keyword:
            st.info(f"Fetching data for: {keyword}")
            clean_output_directory(OUTPUT_DIR)
            soc_data = fetch_soc_data(keyword)
            if soc_data:
                st.success(f"Data fetched successfully! {len(soc_data)} SOC records found.")
                st.subheader("SOC Data Results")

                # Display fetched data
                for record in soc_data:
                    st.markdown(f"### {record['title']} ({record['code']})")
                    st.markdown(f"**Description:** {record['description']}")
                    st.markdown("**Also Called:**")
                    st.write(record["also_called"])
                    st.markdown("**Tasks:**")
                    st.write(record["tasks"])
            else:
                st.warning("No data available for the given input.")
        else:
            st.error("Please enter a Military Title or MOC Code.")

    #st.sidebar.write("Built with 💻 by Streamlit.")

if __name__ == "__main__":
    main()

