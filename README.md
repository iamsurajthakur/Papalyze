# Papalyze

#### Video Demo: [Watch the Demo](https://www.youtube.com/watch?v=jvtLTPMzDcw&t=12s)

#### GitHub Repository: [View on GitHub](https://github.com/iamsurajthakur/Papalyze)

#### Author: Suraj Thakur
#### Publish Date: 30 August, 2025

---

## Project Description

**PAPALYZE** is a web-based application designed to help educators and students analyze academic papers efficiently using modern AI and NLP technologies. This tool allows users to upload question papers and documents, extract meaningful content, predict topics, and provide insights through an interactive frontend.

Key features of the project include:  
- **File Upload and Management:** Users can upload multiple PDF or text documents for analysis.  
- **OCR Processing:** Scanned documents and images are processed using PyTesseract to extract text.  
- **NLP Analysis:** Extract keywords and predict topics using spaCy and custom NLP services.  
- **AI Integration:** Hugging Face Transformers are used to generate summaries and extract insights from text.  
- **Interactive Frontend:** Clean and responsive UI built with Tailwind CSS for intuitive document viewing.  
- **Secure Session Handling:** Analysis results are stored per session, ensuring privacy and data security.

The project demonstrates the integration of a modular Flask backend with a dynamic frontend, combining OCR, NLP, and AI components in a cohesive system.

---

## Project Architecture

The application follows a **modular Flask architecture using Blueprints**, separating functionality by component for maintainability and scalability. Key components include:

- **Blueprints:**  
  - `main` – handles primary pages and routing  
  - `auth` – authentication functionality (optional)  
  - `analyzer` – core paper analysis routes and templates  

- **Services Layer:**  
  - `summarize.py` – handles summary generation using Hugging Face Transformers  


- **Models and Database:**  
  - Database models are separated under `models/` for maintainable schema design  
  - Ready for future migrations and PostgreSQL integration  

- **Frontend Integration:**  
  - Tailwind CSS is compiled into `static/css/main.css`  
  - Templates organized under `templates/` with a base layout for consistent styling  

- **Utilities:**  
  - Helper functions and reusable utilities under `utils/`  

---

## Tech Stack

- **Backend Framework:** Python, Flask, Flask-Mail, SQLAlchemy  
- **Frontend:** HTML, CSS, JavaScript, Tailwind CSS  
- **Document Processing:** PyPDF2, pdf2image, Pillow, OpenCV, pytesseract  
- **Natural Language Processing:** NLTK, KeyBERT, Scikit-learn, Hugging Face Transformers  
- **Utilities:** uuid, datetime, pathlib, tempfile, os, regex  
- **Database:** SQLite / PostgreSQL  
- **Testing:** pytest

---

## How to Run
1. Clone the repository: `git clone <repo-url>`
2. Install dependencies: `pip install -r requirements.txt`
3. Install teserract OCR Engine: [tesseract](https://github.com/tesseract-ocr/tesseract)
4. Run: `python run.py`
