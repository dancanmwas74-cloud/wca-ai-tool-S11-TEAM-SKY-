# group-project

# Spare Parts Price & Availability AI
An AI-powered application that helps users find car spare parts, prices, and availability using natural English language searches.

# Objective
The main objective of this project is to make finding car spare parts faster, easier, and more convenient by allowing users to search for parts and obtain price and availability information through a conversational AI assistant.

# How It Works
1. User enters a spare-parts request.
2. OpenAI API interprets the request.
3. The system searches the PDF catalogue.
4. RapidFuzz finds the closest match.
5. The application displays the part, vehicle, price, match percentage, and availability.
   
# Technologies Used
  1. Python - Main programming language
  2. OpenAI API - AI integration for natural-language understanding
  3. Streamlit - Web application interface
  4. Pandas - Inventory data management and processing
  5. PDFPlumber - Extracts spare-part information from the PDF catalogue
  6. RapidFuzz - Fuzzy text matching for finding the closest spare-part match
  7. REST API -Retrieves spare-part information
  8. GitHub -Version control and project hosting

# How to Run
1.Install the required packages:
2.pip install -r requirements.txt
3.Run the application:
4.streamlit run app.py

# Disclaimer
Users should verify important information before purchasing.




