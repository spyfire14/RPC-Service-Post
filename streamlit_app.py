import streamlit as st
import requests
from datetime import datetime
import random
import csv
import base64
import os
from PIL import Image
from io import BytesIO




# Function to get upcoming livestreams (video IDs)
def get_upcoming_livestreams(api_key, channel_id, max_results=5):
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={channel_id}&eventType=upcoming&type=video&order=date&maxResults={max_results}&key={api_key}"
    response = requests.get(url)
    livestreams = []

    if response.status_code == 200:
        data = response.json()
        for item in data['items']:
            livestream = {
                'title': item['snippet']['title'],
                'video_id': item['id']['videoId'],
                'thumbnail_url': item['snippet']['thumbnails']['high']['url']  # Add this line to get the thumbnail URL
            }
            livestreams.append(livestream)
    return livestreams

# Function to get scheduled start times for each livestream video
def get_scheduled_start_times(api_key, video_ids):
    video_ids_str = ",".join(video_ids)
    url = f"https://www.googleapis.com/youtube/v3/videos?part=liveStreamingDetails&id={video_ids_str}&key={api_key}"
    response = requests.get(url)
    start_times = {}

    if response.status_code == 200:
        data = response.json()
        for item in data['items']:
            video_id = item['id']
            start_time = item['liveStreamingDetails'].get('scheduledStartTime')
            start_times[video_id] = start_time
    return start_times

# Function to generate random text
def generate_text(date, url, information):
    # Load history
    history = load_history()
    created_text = "No template available."

    try:
        selected_item = select_random_item(items, history, HISTORY_LIMIT)
        created_text = text_exchange(selected_item, date, url, information)
        save_history(selected_item)
    except ValueError as e:
        created_text = str(e)

    return created_text

# Function to load history from the CSV file
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, mode='r') as file:
        reader = csv.reader(file)
        return [row[0] for row in reader]

# Function to save a new selection to the history file
def save_history(selection):
    with open(HISTORY_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([selection])

# Function to select a random item that wasn't selected in the last 7 picks
def select_random_item(items, history, history_limit):
    available_items = [item for item in items if item not in history[-history_limit:]]
    if not available_items:
        raise ValueError("No items available to choose from. All items have been selected recently.")
    return random.choice(available_items)

# Function to replace placeholders in a text template
def text_exchange(number, date, link, information):
    input_file = rf"Templates/{number}.txt"
    content = "Template not found."
    try:
        with open(input_file, 'r') as file:
            content = file.read()
         # Convert the ISO formatted date string to a datetime object
        scheduled_date = datetime.fromisoformat(date)

        # Format the date as "17th November 2024"
        formatted_date = scheduled_date.strftime('%-d{} %B %Y').format('th' if 11 <= scheduled_date.day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(scheduled_date.day % 10, 'th'))

        content = content.replace("INSERTDATE", formatted_date)
        content = content.replace("INSERTLINK", link)
        if information.startswith("Morning"):
            content = content.replace("INSERTINFORMATION", f" our {information}")
        else:
            content = content.replace("INSERTINFORMATION", information)

    except FileNotFoundError:
        content = f"Template {input_file} not found."
    return content

# Function to crop black borders from an image
def crop_black_borders(image):
    width, height = image.size
    # Crop 50px from the top and 75px from the bottom
    cropped_image = image.crop((0, 45, width, height - 45))
    return cropped_image

# Function to create a download link for the cropped thumbnail
def create_download_link(url, filename):
    response = requests.get(url)
    if response.status_code == 200:
        image = Image.open(BytesIO(response.content))
        cropped_image = crop_black_borders(image)

        buffer = BytesIO()
        cropped_image.save(buffer, format="JPEG")
        b64 = base64.b64encode(buffer.getvalue()).decode()
        href = f'<a href="data:image/jpeg;base64,{b64}" download="{filename}">Download Thumbnail</a>'
        return href
    return None

# Fetch and crop the thumbnail image for display
def get_cropped_thumbnail(url):
    response = requests.get(url)
    if response.status_code == 200:
        image = Image.open(BytesIO(response.content))
        return crop_black_borders(image)
    return None

# Function to get list of txt files in numerical order
def get_txt_files(folder):
    txt_files = [f for f in os.listdir(folder) if f.endswith('.txt')]
    return sorted(txt_files, key=lambda x: int(x.split('.')[0]))

# Function to get the next available number for new file creation
def get_next_file_number(folder):
    txt_files = get_txt_files(folder)
    numbers = [int(f.split('.')[0]) for f in txt_files]
    return max(numbers, default=0) + 1

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.selectbox("Choose a page", ["Home", "Templates"])

if page == "Home":
    # Path to the CSV file to store history
    HISTORY_FILE = 'history.csv'
    HISTORY_LIMIT = 1

    # List of items to choose from
    items = ["1", "2", "3", "4", "5", "6", "7"]

    # Streamlit layout setup
    st.title("Select an Upcoming Livestream")

    # Replace with your actual YouTube API key and channel ID
    api_key = 'AIzaSyBXhL9oaOJSHUedwic7Pc9m0KZoKYXrj18'
    channel_id = 'UCFZoGU6sFvF9pgI2IDKglHw'

    # Fetch livestreams and scheduled start times
    livestreams = get_upcoming_livestreams(api_key, channel_id)
    video_ids = [livestream['video_id'] for livestream in livestreams]
    scheduled_times = get_scheduled_start_times(api_key, video_ids)

    if livestreams:
        options = [
            f"{livestream['title']} (Scheduled: {datetime.fromisoformat(scheduled_times[livestream['video_id']]).strftime('%Y-%m-%d %H:%M:%S')})"
            for livestream in livestreams if livestream['video_id'] in scheduled_times
        ]

        # Selectbox for livestream selection
        selected_stream = st.selectbox("Choose an upcoming livestream:", options)
        selected_index = options.index(selected_stream)
        selected_livestream = livestreams[selected_index]
        scheduled_time = scheduled_times[selected_livestream['video_id']]
        scheduled_date = datetime.fromisoformat(scheduled_time)
        livestream_url = f"https://www.youtube.com/watch?v={selected_livestream['video_id']}"
        thumbnail_url = selected_livestream['thumbnail_url']
        download_link = create_download_link(thumbnail_url, f"{selected_livestream['title']}_thumbnail.jpg")


        st.write("### Selected Livestream Details")
        col1, col2 = st.columns([0.6, 0.4])
        with col1:
            st.write("**Title:**", selected_livestream['title'])
            st.write("**Scheduled Start Time:**", scheduled_date.strftime('%Y-%m-%d %H:%M:%S'))
            st.write("**Watch Link:**", livestream_url)
        with col2:
            cropped_thumbnail = get_cropped_thumbnail(thumbnail_url)
            if cropped_thumbnail:
                st.image(cropped_thumbnail, caption="Thumbnail", use_column_width=True)

        

        service_leader = st.text_input("Enter the name of the person leading the service:")

        # Checkbox for first Sunday of the month
        is_first_sunday = scheduled_date.weekday() == 6 and 1 <= scheduled_date.day <= 7
        col3, col4 = st.columns([0.75, 0.25])
        with col3:
            st.write("Is this the first Sunday of the month?")
        with col4:
            st.checkbox("", value=is_first_sunday, disabled=False)

        # Random text generation button and text box
        if st.button("Random"):
            random_text = generate_text(scheduled_time, livestream_url, service_leader)
            st.session_state["random_text"] = random_text

        # Editable text area
        random_text = st.session_state.get("random_text", "")
        st.text_area("Editable Text Box", random_text, height=300)

        # Display the download link
        if download_link:
            st.markdown(download_link, unsafe_allow_html=True)
    else:
        st.write("No upcoming livestreams found.")

elif page == "Templates":
    # Define the folder containing your text files
    TXT_FOLDER = "Templates"

    # Ensure the folder exists
    if not os.path.exists(TXT_FOLDER):
        os.makedirs(TXT_FOLDER)

    # Sidebar for selecting, creating, or deleting a file
    st.sidebar.title("File Manager")

    # Use a session state variable to track selected file
    if "selected_file" not in st.session_state:
        st.session_state.selected_file = "Create New File"

    # Get the current list of text files
    txt_files = get_txt_files(TXT_FOLDER)
    txt_files.append("Create New File")  # Option to create a new file

    selected_file = st.sidebar.selectbox("Select or Create a File", txt_files)

    # Initialize variables for new file creation and file content
    new_file_name = None
    file_content = ""

    # Handle file selection or creation
    if selected_file == "Create New File":
        # Automatically suggest the next file number for the new file
        next_number = get_next_file_number(TXT_FOLDER)
        new_file_name = f"{next_number}.txt"
        file_content = st.text_area("File Content", "", height=300)

    else:
        # Load the content of the selected file
        file_path = os.path.join(TXT_FOLDER, selected_file)
        with open(file_path, 'r') as file:
            file_content = file.read()
        
        # Display an editable text area with the content of the selected file
        file_content = st.text_area("Edit File Content", file_content, height=300)

        # Option to delete the selected file
        if st.sidebar.button("Delete File"):
            os.remove(file_path)
            st.sidebar.success(f"File '{selected_file}' deleted successfully.")
            # Refresh the file list
            txt_files = get_txt_files(TXT_FOLDER)
            txt_files.append("Create New File")
            st.session_state.selected_file = "Create New File"  # Reset selection to create a new file

    # Save button for new files or changes to existing files
    if st.button("Save File"):
        if selected_file == "Create New File":
            file_path = os.path.join(TXT_FOLDER, new_file_name)
            with open(file_path, 'w') as file:
                file.write(file_content)
            st.success(f"New file '{new_file_name}' created successfully.")
        else:
            with open(file_path, 'w') as file:
                file.write(file_content)
            st.success(f"Changes saved to '{selected_file}'.")

    # Update the selected file in session state
    st.session_state.selected_file = selected_file

    # Optional: Show a list of all files with a download option
    st.sidebar.markdown("### Existing Files")
    for txt_file in get_txt_files(TXT_FOLDER):
        file_path = os.path.join(TXT_FOLDER, txt_file)
        with open(file_path, 'r') as file:
            file_data = file.read()
        st.sidebar.download_button(
            label=f"Download {txt_file}",
            data=file_data,
            file_name=txt_file,
            mime="text/plain"
        )