from dotenv import load_dotenv
load_dotenv()
import re
import os
import pandas as pd
import pdfplumber
from rapidfuzz import fuzz
import streamlit as st
from openai import OpenAI

API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_KEY = API_KEY
client = OpenAI(api_key=OPENAI_API_KEY)

st.set_page_config(page_title="Spare Parts Hub", page_icon="🚗", layout="wide")
PDF_PATH = r"C:\Users\duncan\project\Global_Car_Spare_Parts_Catalogue_REBUILT (1).pdf"

RTCCO_INSTRUCTIONS = """You are a professional automotive spare-parts AI assistant.
Always identify vehicle make, model, year, fuel type and requested spare part.
Search the available PDF inventory before giving an answer.
Only recommend parts that exist in the inventory.
If an exact or suitable catalogue match is found, return the catalogue result.
If no matching part is found in the PDF inventory, do not invent a part, price, stock, supplier or part number.
For a no-match response, return exactly:
Sorry, this service is currently unavailable.
Do not add any additional explanation to the no-match response."""

MAKES = ["Toyota","Honda","Ford","Chevrolet","BMW","Nissan","Hyundai","Kia","Mazda","Mercedes","Volkswagen","Subaru","Mitsubishi","Isuzu","Lexus"]
MODELS = ["Corolla","Camry","Hilux","RAV4","Yaris","Civic","Accord","CR-V","Fit","Ranger","Focus","Explorer","Golf","Passat","CX-5","Forester","Outback"]
PART_KEYWORDS = ["oil filter","air filter","fuel filter","brake pads","brake pad","brake discs","brake disc","oil pump","water pump","alternator","starter","radiator","turbocharger","clutch","shock absorber","headlight","tail light","spark plug","fan belt","timing belt","control arm","wheel bearing","ball joint"]

def clean_text(text):
    if text is None: return ""
    return re.sub(r"\s+", " ", str(text).replace("\n"," ").replace("\r"," ")).strip()

def clean_part_name(text):
    text = clean_text(text)
    text = re.sub(r"\s*(?:KSh|KES|Sh|\$)\s*[\d,]+(?:\s*[-–]\s*[\d,]+)?\+?", "", text, flags=re.I)
    return clean_text(re.sub(r"\b\d+\s*(?:available|in stock|stock)\b", "", text, flags=re.I))

def extract_price(text):
    text = clean_text(text)
    m = re.search(r"(?:KSh|KES|Sh|\$)\s*[\d,]+(?:\s*[-–]\s*[\d,]+)?\+?", text, re.I)
    if m: return m.group(0).strip()
    m = re.search(r"\b[\d,]+\s*[-–]\s*[\d,]+\+?\b", text)
    return "KSh " + m.group(0) if m else ""

def extract_stock(text):
    m = re.search(r"\b(\d+)\s*(?:available|in stock|stock)\b", clean_text(text), re.I)
    try: return int(m.group(1)) if m else 0
    except: return 0

def find_value(text, values):
    text = clean_text(text)
    for value in values:
        if re.search(rf"\b{re.escape(value)}\b", text, re.I): return value
    return ""

def find_make(text): return find_value(text, MAKES)
def find_model(text): return find_value(text, MODELS)

def find_fuel(text):
    text = clean_text(text)
    if re.search(r"\bpetrol\b", text, re.I): return "Petrol"
    if re.search(r"\bdiesel\b", text, re.I): return "Diesel"
    return ""

def find_part(text):
    return find_value(text, sorted(PART_KEYWORDS, key=len, reverse=True)).title()

def normalise(text):
    text = clean_text(text).lower().replace("petrol/diesel", "petrol")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", text)).strip()

def get_ai_intent(query):
    make, model, fuel, part, year = find_make(query), find_model(query), find_fuel(query), find_part(query), None
    m = re.search(r"\b(19\d{2}|20\d{2})\b", query)
    if m: year = int(m.group(1))

    if API_KEY and API_KEY != "PASTE_YOUR_OPENAI_API_KEY_HERE":
        try:
            response = client.responses.create(
                model="gpt-4o-mini",
                input=[
                    {"role":"system","content":RTCCO_INSTRUCTIONS},
                    {"role":"user","content":f"""Extract the vehicle and spare part.

Customer request:
{query}

Return exactly:

MAKE=
MODEL=
YEAR=
FUEL=
PART=

Example:
MAKE=Toyota
MODEL=Corolla
YEAR=
FUEL=Petrol
PART=Oil Filter

Do not include Toyota in PART.
Do not include Corolla in PART.
Do not include Petrol in PART."""}
                ]
            )
            text = response.output_text.strip()

            patterns = {
                "make": r"MAKE\s*=\s*(.*)",
                "model": r"MODEL\s*=\s*(.*)",
                "fuel": r"FUEL\s*=\s*(.*)",
                "part": r"PART\s*=\s*(.*)"
            }
            for key, pattern in patterns.items():
                m = re.search(pattern, text, re.I)
                if m:
                    value = m.group(1).strip()
                    if value.lower() not in ("none","unknown","any",""):
                        if key == "make": make = value
                        elif key == "model": model = value
                        elif key == "fuel": fuel = value
                        else: part = value

            m = re.search(r"YEAR\s*=\s*(.*)", text, re.I)
            if m:
                y = re.search(r"(19\d{2}|20\d{2})", m.group(1))
                if y: year = int(y.group(1))
        except Exception:
            pass

    if not part: part = find_part(query) or query
    for value in (make, model, fuel):
        if value: part = re.sub(rf"\b{re.escape(value)}\b", "", part, flags=re.I)
    if year: part = re.sub(rf"\b{year}\b", "", part)
    part = re.sub(r"\b(do you have|do you sell|can you find|can i get|i need|i want|looking for|please|show me|give me)\b", "", part, flags=re.I)
    detected = find_part(part)
    if detected: part = detected
    return {"make":make,"model":model,"year":year,"fuel":fuel,"part_name":clean_text(part)}

def get_rtcco_no_match_response(query, parsed):
    fallback = "Sorry, this service is currently unavailable."
    if not API_KEY or API_KEY == "PASTE_YOUR_OPENAI_API_KEY_HERE": return fallback
    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role":"system","content":RTCCO_INSTRUCTIONS},
                {"role":"user","content":f"""Customer question:
{query}

The PDF inventory was searched.
No matching catalogue result was found.

Identified information:
MAKE={parsed.get("make","")}
MODEL={parsed.get("model","")}
YEAR={parsed.get("year","")}
FUEL={parsed.get("fuel","")}
PART={parsed.get("part_name","")}

Because no matching catalogue result was found, respond exactly with:
Sorry, this service is currently unavailable.

Do not provide a price.
Do not provide stock information.
Do not recommend another part.
Do not invent information.
Do not explain why."""}
            ]
        )
        return response.output_text.strip() or fallback
    except Exception:
        return fallback

def extract_inventory_from_pdf(pdf_path):
    records = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables()
            
            if not tables or len(tables) == 0:
                settings = {
                    "vertical_strategy": "text", 
                    "horizontal_strategy": "text",
                    "snap_tolerance": 5
                }
                tables = page.extract_tables(table_settings=settings)
            
            if not tables: 
                text_lines = page.extract_text(layout=True)
                if text_lines:
                    for line in text_lines.split("\n"):
                        if not line.strip(): continue
                        cells = [c.strip() for c in re.split(r'\s{2,}', line) if c.strip()]
                        if len(cells) >= 3:
                            process_row_data(cells, line, page_number, records)
                continue

            for table in tables:
                if not table: continue
                for row in table:
                    if not row: continue
                    cells = [clean_text(c) for c in row if clean_text(c)]
                    if not cells: continue
                    raw_text = clean_text(" ".join(cells))
                    process_row_data(cells, raw_text, page_number, records)

    df = pd.DataFrame(records)
    if df.empty: return df
    columns = ["page","part_id","make","model","fuel","year_start","year_end","part_name","price","stock","supplier","raw_text"]
    for col in columns:
        if col not in df: df[col] = ""
    for col in ["make","model","fuel","part_name","supplier","raw_text"]:
        df[col] = df[col].apply(clean_text)
    df["year_start"] = pd.to_numeric(df["year_start"], errors="coerce")
    df["year_end"] = pd.to_numeric(df["year_end"], errors="coerce")
    df["stock"] = pd.to_numeric(df["stock"], errors="coerce").fillna(0).astype(int)
    return df

def process_row_data(cells, raw_text, page_number, records):
    lower = raw_text.lower()
    if any(x in lower for x in ("part_id","start_year","year_start")): return
    if "make" in lower and "model" in lower and "price" in lower: return

    make, model, fuel, part = find_make(raw_text), find_model(raw_text), find_fuel(raw_text), find_part(raw_text)
    years = re.findall(r"\b(?:19|20)\d{2}\b", raw_text)
    year_start = int(years[0]) if years else None
    year_end = int(years[1]) if len(years) > 1 else year_start
    price, stock = extract_price(raw_text), extract_stock(raw_text)

    if part:
        part_name = part
    else:
        cleaned = re.sub(r"\b(?:19|20)\d{2}\b", "", raw_text)
        cleaned = re.sub(r"(?:KSh|KES|Sh|\$)\s*[\d,]+(?:\s*[-–]\s*[\d,]+)?\+?", "", cleaned, flags=re.I)
        part_name = clean_part_name(cleaned)

    part_id = cells[0] if re.search(r"[A-Za-z0-9]", cells[0]) and len(cells[0]) <= 30 else ""
    supplier = ""
    pm = re.search(r"(?:KSh|KES|Sh|\$)\s*[\d,]+(?:\s*[-–]\s*[\d,]+)?\+?", raw_text, re.I)
    if pm: supplier = clean_text(raw_text[pm.end():])

    records.append({
        "page": page_number, "part_id": part_id, "make": make, "model": model, "fuel": fuel,
        "year_start": year_start, "year_end": year_end, "part_name": clean_part_name(part_name),
        "price": price, "stock": stock, "supplier": supplier, "raw_text": raw_text
    })

def search_inventory(query, df):
    parsed = get_ai_intent(query)
    if df.empty: return parsed, []
    filtered = df.copy()

    for field in ("make","model","fuel"):
        value = parsed[field]
        if value:
            pattern = rf"\b{re.escape(value)}\b"
            matches = filtered[filtered["raw_text"].astype(str).str.contains(pattern, case=False, na=False, regex=True)]
            if matches.empty: return parsed, []
            filtered = matches

    if parsed["year"]:
        matches = filtered[(filtered["year_start"].isna() | (filtered["year_start"] <= parsed["year"])) & (filtered["year_end"].isna() | (filtered["year_end"] >= parsed["year"]))]
        if not matches.empty: filtered = matches

    requested = normalise(parsed["part_name"])
    if not requested: return parsed, []

    exact, fuzzy = [], []
    for _, row in filtered.iterrows():
        catalogue = normalise(row.get("part_name",""))
        raw = normalise(row.get("raw_text",""))
        if not catalogue: continue
        item = row.to_dict()

        if requested == catalogue or requested in catalogue:
            item["match_score"] = 100
            exact.append(item)
        elif requested in raw:
            item["match_score"] = 95
            exact.append(item)
        else:
            score = fuzz.token_set_ratio(requested, catalogue)
            if score >= 85:
                item["match_score"] = round(score, 1)
                fuzzy.append(item)

    results = exact if exact else sorted(fuzzy, key=lambda x:x.get("match_score",0), reverse=True)
    unique, seen = [], set()

    for item in results:
        key = tuple(normalise(item.get(k,"")) for k in ("make","model","fuel","part_name","price"))
        if key not in seen:
            seen.add(key)
            unique.append(item)

    def ranking(item):
        score = float(item.get("match_score",0))
        text = normalise(item.get("raw_text",""))
        for field in ("make","model","fuel"):
            if parsed[field] and normalise(parsed[field]) in text: score += 100
        if requested in normalise(item.get("part_name","")): score += 300
        return score

    unique.sort(key=ranking, reverse=True)
    return parsed, unique[:1]

st.title("🚗 Spare Parts Hub")
st.caption("Welcome to the Spare Parts Price & Availability AI Assistant")

if not API_KEY or API_KEY == "PASTE_YOUR_OPENAI_API_KEY_HERE":
    st.error("❌ Please enter your OpenAI API key.")
    st.stop()

if not os.path.exists(PDF_PATH):
    st.error("❌ The spare parts inventory could not be loaded.")
    st.stop()

try:
    df_inventory = extract_inventory_from_pdf(PDF_PATH)
except Exception as e:
    st.error(f"❌ Unable to read the PDF: {e}")
    st.stop()

if df_inventory.empty:
    st.error("❌ No spare parts were found in the PDF.")
    st.stop()

user_query = st.text_input("", placeholder="e.g. Do you have Toyota Corolla Petrol Oil Filter?")

if st.button("🔍 Search", type="primary"):
    if not user_query.strip():
        st.warning("Please enter a search query.")
    else:
        with st.spinner("🧠 Searching the catalogue..."):
            parsed, results = search_inventory(user_query, df_inventory)

        st.markdown("### 🧠 AI Intent Parsing")
        cols = st.columns(5)
        values = [
            ("Vehicle Make", parsed["make"] or "Any"),
            ("Vehicle Model", parsed["model"] or "Any"),
            ("Vehicle Year", parsed["year"] or "Any"),
            ("Fuel", parsed["fuel"] or "Any"),
            ("Extracted Part", parsed["part_name"] or "None")
        ]
        for col, (label, value) in zip(cols, values):
            col.metric(label, value)

        st.divider()
        st.markdown("### 📦 Available Parts")

        if not results:
            st.warning(get_rtcco_no_match_response(user_query, parsed))
        else:
            st.success(f"{len(results)} matching part(s) found.")
            for item in results:
                with st.container(border=True):
                    c1, c2 = st.columns([3,1])
                    with c1:
                        st.subheader(clean_part_name(item.get("part_name","Unknown Part")))
                        for key, label in (("make","Vehicle"),("model","Model"),("fuel","Fuel")):
                            if item.get(key): st.markdown(f"**{label}:** {item[key]}")
                        st.markdown(f"**Search match:** {item.get('match_score',0)}%")
                        stock = item.get("stock",0)
                        if stock > 0:
                            st.success(f"✅ is stock ({stock} available)")
                        else:
                            st.error("❌ Out of Stock")
                        supplier = clean_text(item.get("supplier",""))
                        if supplier: st.markdown(f"**Supplier:** {supplier}")
                    with c2:
                        st.markdown("### 💰")
                        price = item.get("price","")
                        st.markdown(f"### {price}" if price else "### Price N/A")

st.caption("⚠️ The Spare Parts Price & Availability AI may make mistakes. Customers should verify important information before purchasing.")
