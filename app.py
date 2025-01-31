import os
import cv2
import pandas as pd
import pytesseract
from fastapi import FastAPI, File, UploadFile
from pdf2image import convert_from_path
from fastapi.responses import FileResponse
import pdfplumber

app = FastAPI()

# Function to check if a PDF contains selectable text
def is_text_based_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                return True  # Found text, so it's a text-based PDF
    return False  # No text found, it's likely a scanned PDF

# Function to extract tables from a text-based PDF
def extract_tables_from_pdf(pdf_path, output_csv):
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            extracted_tables = page.extract_table()
            if extracted_tables:
                tables.extend(extracted_tables)
    
    if tables:
        df = pd.DataFrame(tables)
        df.to_csv(output_csv, index=False)
        return output_csv
    return None

# Function to extract text from a scanned PDF using OCR
def extract_text_from_scanned_pdf(pdf_path, output_csv):
    images = convert_from_path(pdf_path)  # Convert PDF pages to images
    extracted_text = []

    for i, image in enumerate(images):
        image_path = f"temp_page_{i}.png"
        image.save(image_path, "PNG")  # Save as image file
        img = cv2.imread(image_path)
        text = pytesseract.image_to_string(img)  # Apply OCR
        extracted_text.append(text)
        os.remove(image_path)  # Clean up temp file

    df = pd.DataFrame({"Extracted_Text": extracted_text})
    df.to_csv(output_csv, index=False)
    return output_csv

@app.post("/convert_pdf_to_csv/")
async def convert_pdf_to_csv(file: UploadFile = File(...)):
    pdf_path = f"temp_{file.filename}"
    
    # Save uploaded file
    with open(pdf_path, "wb") as f:
        f.write(file.file.read())

    output_csv = f"{file.filename}.csv"

    if is_text_based_pdf(pdf_path):
        result = extract_tables_from_pdf(pdf_path, output_csv)
    else:
        result = extract_text_from_scanned_pdf(pdf_path, output_csv)
    
    os.remove(pdf_path)  # Clean up the temporary file

    if result:
        return FileResponse(output_csv, filename=output_csv, media_type="text/csv")
    return {"error": "No data extracted"}
