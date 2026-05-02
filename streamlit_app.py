import streamlit as st
from pypdf import PdfReader, PdfWriter
import io
import zipfile  # Needed for the "Download All" feature
import re
from datetime import datetime

# --- STUDENT NAME EXTRACTION ---
def get_student_name(pdf_bytes):
    """
    Attempts to extract the student name from the first page of the PDF chunk.
    Adjust the logic inside to match your specific PDF layout.
    """
    reader = PdfReader(io.BytesIO(pdf_bytes))
    first_page_text = reader.pages[0].extract_text()
    
    # OPTION A: Look for a specific label like "Student Name: John Doe"
    # match = re.search(r"Name:\s*(.*)", first_page_text)
    # if match:
    #     name = match.group(1).strip()
    
    # OPTION B: Just grab the first non-empty line (Common for headers)
    lines = [line.strip() for line in first_page_text.split('\n') if line.strip()]
    name = lines[0] if lines else "Unknown_Student"

    # Sanitize the name for filenames (remove invalid characters)
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    return name.replace(" ", "_")

# --- SPLIT LOGIC ---

def split_and_merge(pdf_bytes, num_titles, pages_per_student, break_pages_check):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    all_pages = list(reader.pages)
    remaining = all_pages[num_titles:]
    
    students = []
    i = 0
    while i < len(remaining):
        chunk = remaining[i:i + pages_per_student]
        i += pages_per_student
        if break_pages_check:
            i += 1
            
        if chunk:
            writer = PdfWriter()
            for page in chunk:
                writer.add_page(page)
            buf = io.BytesIO()
            writer.write(buf)
            chunk_bytes = buf.getvalue()
            
            # Identify the student
            raw_name = get_student_name(chunk_bytes)
            
            students.append({
                "name": raw_name,
                "bytes": chunk_bytes
            })
    return students

# --- ZIP LOGIC ---

def create_zip(student_list):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for student in student_list:
            # Filename is now based on the extracted name
            file_name = f"{student['name']}.pdf"
            zip_file.writestr(file_name, student['bytes'])
    return zip_buffer.getvalue()

# Get todays date for naming zip folder
today_date = datetime.now().astimezone().strftime("%Y-%m-%d")

if "pdf_accepted" not in st.session_state:
    st.session_state.pdf_accepted = False
if "students" not in st.session_state:
    st.session_state.students = []

if not st.session_state.pdf_accepted:
    st.title("Student Report Splitter")
    
    left, center, right = st.columns(3, vertical_alignment="bottom")
    num_titles = left.number_input('Number of title pages', 0, 10, value=1)
    pages_per_student = center.number_input('Pages per student', 1, 10, value=2)
    break_pages = right.checkbox('Page breaks?')

    st.text_input(
        'Folder name', 
        placeholder=f"split_reports_{today_date}", 
        key="folder_name_key"
    )

    upload, accept = st.columns([2,1], vertical_alignment="bottom")
    uploaded = upload.file_uploader("Upload a report", type="pdf")

    if uploaded is not None:
        st.pdf(uploaded)
    if accept.button("Continue", type="primary", icon=":material/check_small:", disabled=(uploaded is None)):
        pdf_bytes = uploaded.read()
        bar = st.progress(0, text="Splitting PDF...")
        st.session_state.students = split_and_merge(pdf_bytes, num_titles, pages_per_student, break_pages)
        st.session_state.pdf_accepted = True
        st.session_state.accepted_filename = uploaded.name
        bar.progress(100, text="Done!")
        st.rerun()

else:
    st.title("Review Split Files")
    
    col_msg, col_zip = st.columns([2, 1], vertical_alignment="center")
    col_msg.success(f"Identified {len(st.session_state.students)} students.")
    
    # Global ZIP Download
    folder_name = st.session_state.get("folder_name_key")
    if not folder_name:
        folder_name = f"split_reports_{today_date}"
    zip_data = create_zip(st.session_state.students)
    col_zip.download_button(
        label="Download All (ZIP)",
        data=zip_data,
        file_name=f'{folder_name}.zip',
        mime="application/zip",
        icon=":material/download:",
        type="primary",
        use_container_width=True
    )

    st.divider()

    # Pagination
    nav1, nav2, nav3 = st.columns([2, 1, 1], vertical_alignment="center")
    
    student_names = [s['name'] for s in st.session_state.students]
    selected_name = nav1.selectbox("Select Student", student_names)
    
    # Find the specific student data
    current_student = next(s for s in st.session_state.students if s['name'] == selected_name)

    if nav3.button("Start Over",
                   icon=":material/refresh:",
                   use_container_width=True):
        st.session_state.pdf_accepted = False
        st.session_state.students = []
        st.rerun()
    
    st.download_button(
        label=f"Download {selected_name}.pdf",
        data=current_student['bytes'],
        file_name=f"{current_student['name']}.pdf",
        icon=":material/download:",
        mime="application/pdf"
    )

    st.subheader(f"📄 Preview: {selected_name}.pdf")
    st.pdf(current_student['bytes'])