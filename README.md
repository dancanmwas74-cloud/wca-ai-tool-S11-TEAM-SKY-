# 🚗 Spare Parts Hub

Spare Parts Hub is an AI-powered application that helps users find car spare parts, prices, and availability using natural-language searches.

##  Objective

The objective is to make finding vehicle spare parts faster and easier by allowing users to search a PDF catalogue using conversational English.

##  How It Works

1. User enters a spare-parts request.
2. OpenAI interprets the request.
3. The system searches the PDF catalogue.
4. RapidFuzz finds the closest matching part.
5. The application displays the part, vehicle, price, match percentage, and availability.
6. A JSON response is generated and saved.

##  Technologies Used

- **Python** – Main programming language
- **OpenAI API** – Natural-language understanding
- **Streamlit** – Web application interface
- **Pandas** – Inventory data processing
- **PDFPlumber** – PDF catalogue extraction
- **RapidFuzz** – Fuzzy text matching
- **JSON** – Search-result storage
- **REST API** – API communication

  ## How to Run

1. Open the project in Visual Studio Code.
2. Create a virtual environment: `python -m venv venv`
3. Activate it: `venv\Scripts\Activate.ps1`
4. Install dependencies: `pip install -r requirements.txt`
5. Create `.env` and add: `OPENAI_API_KEY=your_api_key_here`
6. Place `Global_Car_Spare_Parts_Catalogue_REBUILT (1).pdf` in the project folder.
7. Run the app: `streamlit run app.py`
8. Open `http://localhost:8501` in your browser.

##  Disclaimer

The Spare Parts Hub may make mistakes. Users should verify vehicle compatibility, price, availability, and other important catalogue information before purchasing.

- **GitHub** – Version control and project hosting

