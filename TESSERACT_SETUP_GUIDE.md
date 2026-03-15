"""
Tesseract OCR Setup Guide for Smart Screenshot Analyzer
=========================================================

INSTALLATION OPTIONS:
=====================

OPTION 1: System Installation (Recommended)
--------------------------------------------
1. Download Tesseract OCR:
   Visit: https://github.com/UB-Mannheim/tesseract/wiki
   Or direct: https://github.com/UB-Mannheim/tesseract/wiki/releases

2. Run the installer:
   - tesseract-ocr-w64-setup-5.x.x.exe (64-bit)
   - Keep default installation path: C:\Program Files\Tesseract-OCR
   - Select additional languages if needed

3. Add to PATH (already done automatically by our script):
   - Path added: C:\Program Files\Tesseract-OCR

4. Verify installation:
   Open NEW PowerShell window and run:
   > tesseract --version

   Expected output:
   tesseract 5.x.x
   leptonica-1.x.x


OPTION 2: Manual Configuration in Python
-----------------------------------------
If you don't want to add to PATH, you can configure it in app.py:

Add this line at the top of app.py (after imports):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


OPTION 3: Use Cloud OCR API (No Installation Required)
-------------------------------------------------------
Replace local OCR with cloud APIs:

1. Google Cloud Vision API
2. AWS Textract
3. Azure Computer Vision

These require API keys but no local installation.


TESTING THE INSTALLATION:
==========================

After installing Tesseract, test it with:

1. Open NEW PowerShell window
2. Navigate to project folder
3. Run: python app.py
4. Open browser to http://127.0.0.1:5000
5. Click "Analyze Screenshot" button
6. Upload a test image
7. Click "Analyze"


TROUBLESHOOTING:
================

Error: "Tesseract is not installed or not in PATH"
Solution: 
- Make sure you restarted PowerShell after installation
- Check PATH: echo $env:Path
- Verify tesseract.exe exists in C:\Program Files\Tesseract-OCR\

Error: "Failed to analyze screenshot"
Solution:
- Check Flask console for detailed error messages
- Ensure image format is PNG, JPG, or WebP
- Try with a clear, high-contrast screenshot


FEATURE CAPABILITIES:
=====================

The Smart Screenshot Analyzer can:
✅ Extract text from UPI payment screenshots
✅ Detect transaction amount, date, ID, phone number
✅ Identify fake/manipulated screenshots
✅ Provide authenticity score (0-100%)
✅ Color-coded risk assessment
✅ Real-time analysis results


SUPPORTED IMAGE FORMATS:
========================
- PNG (recommended)
- JPG/JPEG
- WebP


BEST PRACTICES:
===============
1. Use high-resolution screenshots for better OCR accuracy
2. Ensure good contrast in the image
3. Avoid blurry or low-quality images
4. Crop to show only the relevant transaction details


For more help, check the Flask console logs during analysis.
