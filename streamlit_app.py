import streamlit as st
from pypdf import PdfReader, PdfWriter
import io
import zipfile
import re
from datetime import datetime
import streamlit_shadcn_ui as ui

# --- STUDENT NAME EXTRACTION ---
def get_student_name(pdf_bytes):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    first_page_text = reader.pages[0].extract_text()
    lines = [line.strip() for line in first_page_text.split('\n') if line.strip()]
    name = lines[0] if lines else "Unknown_Student"
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    return name.replace(" ", "_")

# --- SPLIT LOGIC ---
def split_and_merge(pdf_bytes, num_titles, pages_per_student, break_pages_check):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    all_pages = list(reader.pages)
    remaining = all_pages[num_titles:]

    if len(remaining) == 0:
        raise ValueError(
            f"No pages remain after removing {num_titles} title page(s). "
            f"The PDF only has {len(all_pages)} page(s)."
        )

    if len(remaining) < pages_per_student:
        raise ValueError(
            f"Only {len(remaining)} page(s) remain after title pages, "
            f"but {pages_per_student} pages per student is required."
        )

    students = []
    i = 0
    while i < len(remaining):
        chunk = remaining[i:i + pages_per_student]

        if len(chunk) < pages_per_student:
            break

        i += pages_per_student
        if break_pages_check:
            i += 1

        writer = PdfWriter()
        for page in chunk:
            writer.add_page(page)
        buf = io.BytesIO()
        writer.write(buf)
        chunk_bytes = buf.getvalue()

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
            file_name = f"{student['name']}.pdf"
            zip_file.writestr(file_name, student['bytes'])
    return zip_buffer.getvalue()

# --- SESSION STATE INIT ---
today_date = datetime.now().astimezone().strftime("%Y-%m-%d")

if "pdf_accepted" not in st.session_state:
    st.session_state.pdf_accepted = False
if "students" not in st.session_state:
    st.session_state.students = []
if "page" not in st.session_state:
    st.session_state.page = 0

# --- PAGE 1: UPLOAD ---
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

    upload, accept = st.columns([2, 1], vertical_alignment="bottom")
    uploaded = upload.file_uploader("Upload a report", type="pdf")

    if uploaded is not None:
        st.pdf(uploaded)

    if accept.button("Continue", type="primary", icon=":material/check_small:", disabled=(uploaded is None)):
        pdf_bytes = uploaded.read()
        bar = st.progress(0, text="Splitting PDF...")
        try:
            st.session_state.students = split_and_merge(pdf_bytes, num_titles, pages_per_student, break_pages)
            st.session_state.pdf_accepted = True
            st.session_state.accepted_filename = uploaded.name
            st.session_state.page = 0
            bar.progress(100, text="Done!")
            st.rerun()
        except ValueError as e:
            bar.empty()
            st.toast(str(e), icon="⚠️")

# --- PAGE 2: REVIEW ---
else:
    st.title("Review Split Files")

    total = len(st.session_state.students)

    col_msg, col_zip = st.columns([2, 1], vertical_alignment="center")
    col_msg.success(f"Identified {total} students", icon=":material/child_hat:")

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

    if col_zip.button("Start Over", icon=":material/refresh:", use_container_width=True):
        st.session_state.pdf_accepted = False
        st.session_state.students = []
        st.session_state.page = 0
        st.rerun()

    st.divider()

    p1, p2, p3 = st.columns(3)
    p1.button(
        "← Prev",
        disabled=st.session_state.page == 0,
        on_click=lambda: st.session_state.update(page=st.session_state.page - 1),
        use_container_width=True
    )
    p2.markdown(f"<p style='text-align:center; padding-top:8px'>{st.session_state.page + 1} / {total}</p>", unsafe_allow_html=True)
    p3.button(
        "Next →",
        disabled=st.session_state.page == total - 1,
        on_click=lambda: st.session_state.update(page=st.session_state.page + 1),
        use_container_width=True
    )

    current_student = st.session_state.students[st.session_state.page]
    selected_name = current_student['name']

    st.download_button(
        label=f"Download {selected_name}.pdf",
        data=current_student['bytes'],
        file_name=f"{current_student['name']}.pdf",
        icon=":material/download:",
        mime="application/pdf"
    )

    st.subheader(f"📄 Preview: {selected_name}.pdf")
    st.pdf(current_student['bytes'])