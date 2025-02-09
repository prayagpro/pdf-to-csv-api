import nest_asyncio
nest_asyncio.apply()

from fastapi import FastAPI, File, UploadFile, HTTPException
import pdfplumber
import pandas as pd
import pytesseract
import cv2
import os
from pdf2image import convert_from_path
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI()

# ✅ Define temporary directory for file storage (suitable for Render)
TEMP_DIR = Path("/tmp")
TEMP_DIR.mkdir(exist_ok=True)

# ✅ Function to check if a PDF contains selectable text
def is_text_based_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                return True  # Found text, so it's a text-based PDF
    return False  # No text found, it's likely a scanned PDF

# ✅ Function to extract tables from a text-based PDF
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

# ✅ Function to extract text from a scanned PDF using OCR
def extract_text_from_scanned_pdf(pdf_path, output_csv):
    images = convert_from_path(pdf_path)  # Convert PDF pages to images
    extracted_text = []

    for i, image in enumerate(images):
        image_path = TEMP_DIR / f"temp_page_{i}.png"
        image.save(image_path, "PNG")  # Save as image file
        img = cv2.imread(str(image_path))
        text = pytesseract.image_to_string(img)  # Apply OCR
        extracted_text.append(text)
        image_path.unlink()  # Clean up temp file

    df = pd.DataFrame({"Extracted_Text": extracted_text})
    df.to_csv(output_csv, index=False)
    return output_csv

# ✅ FastAPI route for PDF-to-CSV conversion
@app.post("/convert_pdf_to_csv/")
async def convert_pdf_to_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    # ✅ Fix: Save file properly in /tmp/
    pdf_path = TEMP_DIR / file.filename

    # ✅ Fix: Read and save file using async
    with open(pdf_path, "wb") as f:
        f.write(await file.read())

    output_csv = TEMP_DIR / f"{file.filename}.csv"

    try:
        if is_text_based_pdf(str(pdf_path)):
            result = extract_tables_from_pdf(str(pdf_path), str(output_csv))
        else:
            result = extract_text_from_scanned_pdf(str(pdf_path), str(output_csv))

        pdf_path.unlink()  # ✅ Delete temp PDF after processing

        if result:
            return FileResponse(str(output_csv), filename=output_csv.name, media_type="text/csv")
        else:
            return {"error": "No data extracted"}

    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}

# ✅ Root route for API status check
@app.get("/")
def read_root():
    return {"message": "Welcome to the PDF to CSV API!"}

# ✅ Run the FastAPI server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
