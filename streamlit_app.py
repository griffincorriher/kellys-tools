import streamlit as st
from pypdf import PdfReader, PdfWriter
from pdf2image import convert_from_bytes
import io
uploaded = st.file_uploader("Upload a report", type="pdf")

if uploaded:
    reader = PdfReader(uploaded)
    pages = convert_from_bytes(uploaded.getvalue(), dpi=100)
