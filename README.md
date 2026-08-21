# 🚗 Spare Parts Hub

Spare Parts Hub is an AI-powered application that helps users find car spare parts, prices, and availability using natural English language searches.

##  Objective

The main objective of this project is to make finding car spare parts faster, easier, and more convenient by allowing users to search for parts and obtain price and availability information through a conversational AI assistant.

## How It Works

1. The user enters a spare-parts request.
2. The OpenAI API interprets the request.
3. The system searches the PDF spare-parts catalogue.
4. RapidFuzz finds the closest matching spare-part.
5. The application displays the matching part, vehicle, price, match percentage, and availability.
6. The application generates a structured JSON response containing the search status, customer query, extracted vehicle information, and catalogue match.

## Technologies Used

1. **Python** - Main programming language
2. **OpenAI API** - AI integration for natural-language understanding
3. **Streamlit** - Web application interface
4. **Pandas** - Inventory data management and processing
5. **PDFPlumber** - Extracts spare-part information from the PDF catalogue
6. **RapidFuzz** - Fuzzy text matching for finding the closest spare-part match
7. **JSON** - Structures and stores search results, extracted intent, and catalogue matches
8. **REST API** - Enables communication with external services
9. **GitHub** - Version control and project hosting

## How to Run

### 1. Install the required packages

```bash
pip install -r requirements.txt
