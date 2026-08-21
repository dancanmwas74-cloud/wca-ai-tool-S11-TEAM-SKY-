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
- **GitHub** – Version control and project hosting

