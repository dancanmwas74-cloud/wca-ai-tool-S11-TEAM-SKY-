from dotenv import load_dotenv
import os
import json
import re
from datetime import datetime

import streamlit as st
import pdfplumber
import pandas as pd
from rapidfuzz import fuzz
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

PDF_PATH = "Global_Car_Spare_Parts_Catalogue_REBUILT (1).pdf"
OUTPUT_FILE = "spare_parts_output.json"

client = None

if API_KEY:
    client = OpenAI(api_key=API_KEY)

st.set_page_config(
    page_title="Spare Parts Hub",
    page_icon="🚗",
    layout="wide"
)

RTCCO_INSTRUCTIONS = """
You are a professional automotive spare-parts AI assistant.

Always identify:

vehicle make
vehicle model
vehicle year
fuel type
requested spare part

Search the available PDF inventory before giving an answer.

Only recommend parts that exist in the inventory.

If an exact or suitable catalogue match is found,
return the catalogue result.

If no matching part is found in the PDF inventory,
do not invent a part, price, stock, supplier or part number.

Return the extracted intent as JSON.

The JSON must contain:

make
model
year
fuel
part_name

Use null when information is not provided.

Normalize common automotive terms where appropriate.

Do not put the vehicle make, model, year or fuel inside part_name.
"""


def clean_text(value):
    if value is None:
        return ""

    value = str(value)
    value = value.replace("\n", " ")
    value = value.replace("\r", " ")
    value = value.replace("\t", " ")
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_value(value):
    value = clean_text(value)

    if not value:
        return ""

    return value.lower()


def clean_column_name(value):
    value = clean_text(value).lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)

    return value.strip("_")


def clean_part_name(value):
    value = clean_text(value)

    if not value:
        return ""

    value = re.sub(
        r"\b(?:KSh|KES|Sh|\$)\s*[\d,]+"
        r"(?:\s*[-–]\s*[\d,]+)?\+?",
        "",
        value,
        flags=re.IGNORECASE
    )

    value = re.sub(
        r"\b[\d,]+\s*[-–]\s*[\d,]+\+?\b",
        "",
        value
    )

    return clean_text(value)


def extract_price_from_text(value):
    value = clean_text(value)

    if not value:
        return ""

    match = re.search(
        r"\b(?:KSh|KES|Sh|\$)\s*[\d,]+"
        r"(?:\s*[-–]\s*[\d,]+)?\+?",
        value,
        flags=re.IGNORECASE
    )

    if match:
        return match.group(0).strip()

    match = re.search(
        r"\b[\d,]+\s*[-–]\s*[\d,]+\+?\b",
        value
    )

    if match:
        return "KSh " + match.group(0).strip()

    return ""


def extract_stock_from_text(value):
    value = clean_text(value)

    if not value:
        return ""

    patterns = [
        r"\b(\d+)\s*(?:available|in stock|stock)\b",
        r"\bstock\s*[:=-]?\s*(\d+)\b",
        r"\bavailable\s*[:=-]?\s*(\d+)\b"
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            value,
            flags=re.IGNORECASE
        )

        if match:
            return match.group(1)

    return ""


def detect_header(row):
    if not row:
        return False

    text = " ".join(
        clean_text(cell).lower()
        for cell in row
        if clean_text(cell)
    )

    if not text:
        return False

    header_words = [
        "make",
        "model",
        "vehicle",
        "year",
        "start year",
        "end year",
        "fuel",
        "part",
        "part name",
        "description",
        "price",
        "cost",
        "stock",
        "availability",
        "supplier"
    ]

    score = 0

    for word in header_words:
        if word in text:
            score += 1

    return score >= 1


def find_column(data, names):
    for name in names:
        if name in data:
            return data[name]

    return ""


def extract_tables_from_page(page, page_number):
    records = []

    try:
        tables = page.extract_tables()
    except Exception:
        tables = []

    for table in tables:

        if not table:
            continue

        rows = []

        for row in table:

            if not row:
                continue

            cleaned_row = [
                clean_text(cell)
                for cell in row
            ]

            if any(cleaned_row):
                rows.append(cleaned_row)

        if not rows:
            continue

        header_index = None

        for index, row in enumerate(rows[:5]):

            if detect_header(row):
                header_index = index
                break

        if header_index is not None:

            header = rows[header_index]

            normalized_headers = [
                clean_column_name(item)
                for item in header
            ]

            for row in rows[header_index + 1:]:

                if not any(row):
                    continue

                if len(row) < len(normalized_headers):

                    row = row + (
                        [""] *
                        (
                            len(normalized_headers)
                            - len(row)
                        )
                    )

                row = row[:len(normalized_headers)]

                data = dict(
                    zip(
                        normalized_headers,
                        row
                    )
                )

                make = find_column(
                    data,
                    [
                        "make",
                        "vehicle_make",
                        "car_make",
                        "brand"
                    ]
                )

                model = find_column(
                    data,
                    [
                        "model",
                        "vehicle_model",
                        "car_model"
                    ]
                )

                fuel = find_column(
                    data,
                    [
                        "fuel",
                        "fuel_type",
                        "fueltype"
                    ]
                )

                part_name = find_column(
                    data,
                    [
                        "part",
                        "part_name",
                        "part_description",
                        "description",
                        "spare_part",
                        "item",
                        "product"
                    ]
                )

                year_start = find_column(
                    data,
                    [
                        "year",
                        "start_year",
                        "year_start",
                        "from_year"
                    ]
                )

                year_end = find_column(
                    data,
                    [
                        "end_year",
                        "year_end",
                        "to_year"
                    ]
                )

                price = find_column(
                    data,
                    [
                        "price",
                        "price_ksh",
                        "cost",
                        "amount"
                    ]
                )

                stock = find_column(
                    data,
                    [
                        "stock",
                        "availability",
                        "available"
                    ]
                )

                supplier = find_column(
                    data,
                    [
                        "supplier",
                        "vendor"
                    ]
                )

                combined_row = " ".join(row)

                if not price:
                    price = extract_price_from_text(
                        combined_row
                    )

                if not stock:
                    stock = extract_stock_from_text(
                        combined_row
                    )

                part_name = clean_part_name(
                    part_name
                )

                if not part_name:

                    non_empty = [
                        item
                        for item in row
                        if clean_text(item)
                    ]

                    if non_empty:

                        part_name = clean_part_name(
                            max(
                                non_empty,
                                key=len
                            )
                        )

                if not part_name and not make:
                    continue

                records.append(
                    {
                        "part_name": part_name,
                        "vehicle_make": clean_text(make),
                        "vehicle_model": clean_text(model),
                        "fuel": clean_text(fuel),
                        "year_start": clean_text(year_start),
                        "year_end": clean_text(
                            year_end or year_start
                        ),
                        "price": clean_text(price),
                        "stock": clean_text(stock),
                        "supplier": clean_text(supplier),
                        "pdf_page": page_number
                    }
                )

        else:

            for row in rows:

                if len(row) < 2:
                    continue

                row_text = " | ".join(
                    clean_text(cell)
                    for cell in row
                    if clean_text(cell)
                )

                if not row_text:
                    continue

                price = extract_price_from_text(
                    row_text
                )

                stock = extract_stock_from_text(
                    row_text
                )

                if not price and not stock:
                    continue

                known_makes = [
                    "Toyota",
                    "Honda",
                    "Ford",
                    "Chevrolet",
                    "BMW",
                    "Nissan",
                    "Hyundai",
                    "Kia",
                    "Mazda",
                    "Mercedes",
                    "Volkswagen",
                    "Subaru",
                    "Mitsubishi",
                    "Isuzu",
                    "Lexus"
                ]

                make = ""

                for known_make in known_makes:

                    if re.search(
                        rf"\b{re.escape(known_make)}\b",
                        row_text,
                        flags=re.IGNORECASE
                    ):
                        make = known_make
                        break

                non_empty = [
                    clean_text(cell)
                    for cell in row
                    if clean_text(cell)
                ]

                if not non_empty:
                    continue

                part_name = max(
                    non_empty,
                    key=len
                )

                part_name = clean_part_name(
                    part_name
                )

                if not part_name:
                    continue

                records.append(
                    {
                        "part_name": part_name,
                        "vehicle_make": make,
                        "vehicle_model": "",
                        "fuel": "",
                        "year_start": "",
                        "year_end": "",
                        "price": price,
                        "stock": stock,
                        "supplier": "",
                        "pdf_page": page_number
                    }
                )

    return records


def extract_text_records(page, page_number):
    records = []

    try:
        text = page.extract_text()
    except Exception:
        text = None

    if not text:
        return records

    lines = [
        clean_text(line)
        for line in text.splitlines()
        if clean_text(line)
    ]

    known_makes = [
        "Toyota",
        "Honda",
        "Ford",
        "Chevrolet",
        "BMW",
        "Nissan",
        "Hyundai",
        "Kia",
        "Mazda",
        "Mercedes",
        "Volkswagen",
        "Subaru",
        "Mitsubishi",
        "Isuzu",
        "Lexus"
    ]

    known_fuels = [
        "Petrol",
        "Diesel",
        "Gasoline"
    ]

    part_keywords = [
        "oil filter",
        "air filter",
        "fuel filter",
        "brake pad",
        "brake pads",
        "brake disc",
        "brake discs",
        "oil pump",
        "water pump",
        "alternator",
        "starter",
        "radiator",
        "turbocharger",
        "clutch",
        "shock absorber",
        "headlight",
        "tail light",
        "spark plug",
        "fan belt",
        "timing belt",
        "control arm",
        "wheel bearing",
        "ball joint"
    ]

    for line in lines:

        price = extract_price_from_text(line)

        if not price:
            continue

        make = ""

        for known_make in known_makes:

            if re.search(
                rf"\b{re.escape(known_make)}\b",
                line,
                flags=re.IGNORECASE
            ):
                make = known_make
                break

        fuel = ""

        for known_fuel in known_fuels:

            if re.search(
                rf"\b{re.escape(known_fuel)}\b",
                line,
                flags=re.IGNORECASE
            ):
                fuel = known_fuel
                break

        part_name = ""

        for keyword in part_keywords:

            if keyword in line.lower():
                part_name = keyword.title()
                break

        if not part_name:
            part_name = clean_part_name(line)

        if not part_name:
            continue

        stock = extract_stock_from_text(line)

        records.append(
            {
                "part_name": part_name,
                "vehicle_make": make,
                "vehicle_model": "",
                "fuel": fuel,
                "year_start": "",
                "year_end": "",
                "price": price,
                "stock": stock,
                "supplier": "",
                "pdf_page": page_number
            }
        )

    return records


def extract_inventory_from_pdf(pdf_path):

    if not os.path.exists(pdf_path):

        raise FileNotFoundError(
            f"PDF inventory file was not found: {pdf_path}"
        )

    records = []

    with pdfplumber.open(pdf_path) as pdf:

        for page_number, page in enumerate(
            pdf.pages,
            start=1
        ):

            table_records = extract_tables_from_page(
                page,
                page_number
            )

            if table_records:

                records.extend(table_records)

            else:

                text_records = extract_text_records(
                    page,
                    page_number
                )

                if text_records:
                    records.extend(text_records)

    cleaned_records = []

    for record in records:

        part_name = clean_text(
            record.get("part_name")
        )

        make = clean_text(
            record.get("vehicle_make")
        )

        if not part_name and not make:
            continue

        record["part_name"] = part_name
        record["vehicle_make"] = make

        cleaned_records.append(record)

    unique_records = []
    seen = set()

    for record in cleaned_records:

        key = (
            normalize_value(
                record.get("part_name")
            ),
            normalize_value(
                record.get("vehicle_make")
            ),
            normalize_value(
                record.get("vehicle_model")
            ),
            normalize_value(
                record.get("fuel")
            ),
            normalize_value(
                record.get("year_start")
            ),
            normalize_value(
                record.get("year_end")
            ),
            normalize_value(
                record.get("price")
            )
        )

        if key in seen:
            continue

        seen.add(key)
        unique_records.append(record)

    if not unique_records:

        raise ValueError(
            "The PDF was found, but no catalogue records could be extracted."
        )

    return pd.DataFrame(unique_records)


def parse_json_response(text):

    if not text:

        raise ValueError(
            "The AI returned an empty response."
        )

    text = text.strip()

    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"^```\s*",
        "",
        text
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    try:

        return json.loads(text)

    except json.JSONDecodeError:

        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1:

            raise ValueError(
                "The AI returned invalid JSON."
            )

        return json.loads(
            text[start:end + 1]
        )


def fallback_intent(query):

    text = clean_text(query)
    lower_text = text.lower()

    makes = [
        "Toyota",
        "Honda",
        "Ford",
        "Chevrolet",
        "BMW",
        "Nissan",
        "Hyundai",
        "Kia",
        "Mazda",
        "Mercedes",
        "Volkswagen",
        "Subaru",
        "Mitsubishi",
        "Isuzu",
        "Lexus"
    ]

    fuels = [
        "Petrol",
        "Diesel",
        "Gasoline"
    ]

    parts = [
        "oil filter",
        "air filter",
        "fuel filter",
        "brake pad",
        "brake pads",
        "brake disc",
        "brake discs",
        "oil pump",
        "water pump",
        "alternator",
        "starter",
        "radiator",
        "turbocharger",
        "clutch",
        "shock absorber",
        "headlight",
        "tail light",
        "spark plug",
        "fan belt",
        "timing belt",
        "control arm",
        "wheel bearing",
        "ball joint"
    ]

    make = None
    fuel = None
    part_name = None
    year = None
    model = None

    for item in makes:

        if re.search(
            rf"\b{re.escape(item)}\b",
            text,
            flags=re.IGNORECASE
        ):
            make = item
            break

    for item in fuels:

        if re.search(
            rf"\b{re.escape(item)}\b",
            text,
            flags=re.IGNORECASE
        ):
            fuel = item
            break

    for item in parts:

        if item in lower_text:

            part_name = item.title()
            break

    year_match = re.search(
        r"\b(19|20)\d{2}\b",
        text
    )

    if year_match:
        year = int(
            year_match.group(0)
        )

    model_text = lower_text

    if make:

        model_text = re.sub(
            rf"\b{re.escape(make.lower())}\b",
            " ",
            model_text
        )

    if fuel:

        model_text = re.sub(
            rf"\b{re.escape(fuel.lower())}\b",
            " ",
            model_text
        )

    if part_name:

        model_text = model_text.replace(
            part_name.lower(),
            " "
        )

    phrases_to_remove = [
        "do you have",
        "do you sell",
        "can i get",
        "i need",
        "looking for",
        "please",
        "available",
        "for",
        "a",
        "an",
        "the"
    ]

    for phrase in phrases_to_remove:

        model_text = re.sub(
            rf"\b{re.escape(phrase)}\b",
            " ",
            model_text
        )

    if year:

        model_text = model_text.replace(
            str(year),
            " "
        )

    model_text = re.sub(
        r"\s+",
        " ",
        model_text
    ).strip()

    if model_text:
        model = model_text.title()

    return {
        "make": make,
        "model": model,
        "year": year,
        "fuel": fuel,
        "part_name": part_name
    }


def openai_intent(query):

    fallback = fallback_intent(query)

    if not client:
        return fallback

    if not query.strip():

        raise ValueError(
            "Please enter a search query."
        )

    prompt = f"""
{RTCCO_INSTRUCTIONS}

Customer search:

{query}

Return ONLY valid JSON:

{{
    "make": null,
    "model": null,
    "year": null,
    "fuel": null,
    "part_name": null
}}
"""

    try:

        response = client.responses.create(
            model="gpt-4o-mini",
            input=prompt
        )

        return parse_json_response(
            response.output_text
        )

    except Exception:

        return fallback


def openai_validate(query, intent):

    if not client:
        return intent

    prompt = f"""
{RTCCO_INSTRUCTIONS}

Customer query:

{query}

First interpretation:

{json.dumps(
    intent,
    ensure_ascii=False
)}

Validate and correct the interpretation.

Return ONLY valid JSON:

{{
    "make": null,
    "model": null,
    "year": null,
    "fuel": null,
    "part_name": null
}}
"""

    try:

        response = client.responses.create(
            model="gpt-4o-mini",
            input=prompt
        )

        return parse_json_response(
            response.output_text
        )

    except Exception:

        return intent


def normalize_search_text(value):

    value = normalize_value(value)

    value = re.sub(
        r"\b(petrol|gasoline|diesel|fuel)\b",
        " ",
        value
    )

    value = re.sub(
        r"[^a-z0-9\s]",
        " ",
        value
    )

    return re.sub(
        r"\s+",
        " ",
        value
    ).strip()


def year_matches(
    intent_year,
    year_start,
    year_end
):

    if intent_year in [
        None,
        "",
        "null"
    ]:
        return True

    try:

        requested_year = int(
            str(intent_year)
        )

    except Exception:

        return True

    try:

        start = int(
            float(
                str(year_start)
            )
        )

    except Exception:

        return True

    try:

        end = int(
            float(
                str(year_end)
            )
        )

    except Exception:

        end = start

    return (
        start
        <= requested_year
        <= end
    )


def search_inventory(
    query,
    intent,
    inventory
):

    if inventory.empty:
        return []

    requested_make = normalize_value(
        intent.get("make")
    )

    requested_model = normalize_value(
        intent.get("model")
    )

    requested_fuel = normalize_value(
        intent.get("fuel")
    )

    requested_part = normalize_search_text(
        intent.get("part_name")
    )

    if not requested_part:
        return []

    exact_results = []
    fuzzy_results = []

    for _, row in inventory.iterrows():

        make = normalize_value(
            row.get("vehicle_make")
        )

        model = normalize_value(
            row.get("vehicle_model")
        )

        fuel = normalize_value(
            row.get("fuel")
        )

        part = normalize_search_text(
            row.get("part_name")
        )

        if requested_make:

            if requested_make not in make:
                continue

        if requested_model:

            if model and requested_model not in model:
                continue

        if requested_fuel:

            if fuel and requested_fuel not in fuel:
                continue

        if not year_matches(
            intent.get("year"),
            row.get("year_start"),
            row.get("year_end")
        ):
            continue

        if requested_part == part:

            score = 100

            exact_results.append(
                {
                    "part_name": clean_text(
                        row.get("part_name")
                    ),
                    "vehicle_make": clean_text(
                        row.get("vehicle_make")
                    ),
                    "vehicle_model": clean_text(
                        row.get("vehicle_model")
                    ),
                    "fuel": clean_text(
                        row.get("fuel")
                    ),
                    "year_start": clean_text(
                        row.get("year_start")
                    ),
                    "year_end": clean_text(
                        row.get("year_end")
                    ),
                    "price": clean_text(
                        row.get("price")
                    ),
                    "stock": None,
                    "availability": "is stock",
                    "supplier": clean_text(
                        row.get("supplier")
                    ),
                    "search_match": 100.0
                }
            )

            continue

        if requested_part in part:

            score = 100

            exact_results.append(
                {
                    "part_name": clean_text(
                        row.get("part_name")
                    ),
                    "vehicle_make": clean_text(
                        row.get("vehicle_make")
                    ),
                    "vehicle_model": clean_text(
                        row.get("vehicle_model")
                    ),
                    "fuel": clean_text(
                        row.get("fuel")
                    ),
                    "year_start": clean_text(
                        row.get("year_start")
                    ),
                    "year_end": clean_text(
                        row.get("year_end")
                    ),
                    "price": clean_text(
                        row.get("price")
                    ),
                    "stock": None,
                    "availability": "is stock",
                    "supplier": clean_text(
                        row.get("supplier")
                    ),
                    "search_match": 100.0
                }
            )

            continue

        score = fuzz.token_set_ratio(
            requested_part,
            part
        )

        if score < 55:
            continue

        fuzzy_results.append(
            {
                "part_name": clean_text(
                    row.get("part_name")
                ),
                "vehicle_make": clean_text(
                    row.get("vehicle_make")
                ),
                "vehicle_model": clean_text(
                    row.get("vehicle_model")
                ),
                "fuel": clean_text(
                    row.get("fuel")
                ),
                "year_start": clean_text(
                    row.get("year_start")
                ),
                "year_end": clean_text(
                    row.get("year_end")
                ),
                "price": clean_text(
                    row.get("price")
                ),
                "stock": None,
                "availability": "is stock",
                "supplier": clean_text(
                    row.get("supplier")
                ),
                "search_match": round(
                    float(score),
                    1
                )
            }
        )

    if exact_results:

        results = exact_results

    else:

        fuzzy_results.sort(
            key=lambda item: item["search_match"],
            reverse=True
        )

        results = fuzzy_results[:1]

    unique_results = []
    seen = set()

    for item in results:

        key = (
            item["part_name"].lower(),
            item["vehicle_make"].lower(),
            item["vehicle_model"].lower(),
            item["fuel"].lower(),
            item["price"].lower()
        )

        if key in seen:
            continue

        seen.add(key)
        unique_results.append(item)

    return unique_results


def build_output(
    query,
    intent,
    matches
):

    if matches:

        status = "success"

        message = (
            f"{len(matches)} matching part(s) found."
        )

    else:

        status = "no_match"

        message = (
            "No matching part was found "
            "in the PDF inventory."
        )

    return {
        "status": status,
        "message": message,
        "query": query,
        "intent": {
            "make": intent.get("make"),
            "model": intent.get("model"),
            "year": intent.get("year"),
            "fuel": intent.get("fuel"),
            "part_name": intent.get("part_name")
        },
        "matches": matches,
        "generated_at": datetime.now().isoformat(
            timespec="seconds"
        )
    }


def save_output(output):

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            indent=4,
            ensure_ascii=False
        )


def display_matches(matches):

    st.markdown(
        "### 📦 Available Parts"
    )

    if not matches:

        st.warning(
            "Sorry, no matching part was found "
            "in the PDF inventory."
        )

        return

    st.success(
        f"{len(matches)} matching part(s) found."
    )

    for item in matches:

        st.markdown(
            f"### {item['part_name']}"
        )

        st.write(
            f"**Vehicle:** "
            f"{item['vehicle_make']}"
        )

        if item["vehicle_model"]:

            st.write(
                f"**Model:** "
                f"{item['vehicle_model']}"
            )

        if item["fuel"]:

            st.write(
                f"**Fuel:** "
                f"{item['fuel']}"
            )

        if item["year_start"]:

            if (
                item["year_start"]
                == item["year_end"]
            ):

                st.write(
                    f"**Year:** "
                    f"{item['year_start']}"
                )

            else:

                st.write(
                    f"**Year:** "
                    f"{item['year_start']}-"
                    f"{item['year_end']}"
                )

        st.write(
            f"**Search match:** "
            f"{item['search_match']}%"
        )

        st.success(
            f"✅ {item['availability']}"
        )

        if item["price"]:

            st.markdown(
                f"### 💰 {item['price']}"
            )

        st.divider()


st.title(
    "🚗 Spare Parts Hub"
)

st.write(
    "Welcome to the Spare Parts Price & Availability AI Assistant"
)


if not os.path.exists(PDF_PATH):

    st.error(
        "❌ PDF inventory file was not found."
    )

    st.write(
        f"Expected file:\n\n{PDF_PATH}"
    )

    st.stop()


try:

    inventory = extract_inventory_from_pdf(
        PDF_PATH
    )

except Exception as error:

    st.error(
        f"❌ PDF inventory could not be loaded: {error}"
    )

    st.stop()


st.success(
    f"✅ PDF inventory loaded successfully "
    f"({len(inventory)} catalogue records)"
)


menu = st.radio(
    "Choose an option",
    [
        "Search",
        "Search JSON"
    ],
    horizontal=True
)


if menu == "Search":

    query = st.text_input(
        "Search",
        placeholder=(
            "e.g. Toyota Corolla Petrol Oil Filter"
        )
    )

    if query:

        try:

            with st.spinner(
                "Analysing your request..."
            ):

                first_intent = openai_intent(
                    query
                )

                validated_intent = openai_validate(
                    query,
                    first_intent
                )

                matches = search_inventory(
                    query,
                    validated_intent,
                    inventory
                )

                output = build_output(
                    query,
                    validated_intent,
                    matches
                )

                save_output(output)

            display_matches(matches)

        except ValueError as error:

            st.error(
                f"❌ {error}"
            )

        except Exception:

            st.error(
                "❌ The search could not be completed. "
                "Please check your search and try again."
            )

    else:

        st.info(
            "Enter a spare-parts search query to begin."
        )


else:

    st.markdown(
        "### 🧠 JSON Response"
    )

    if os.path.exists(OUTPUT_FILE):

        try:

            with open(
                OUTPUT_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                saved_output = json.load(file)

            st.json(saved_output)

            st.download_button(
                "⬇️ Download JSON",
                json.dumps(
                    saved_output,
                    indent=4,
                    ensure_ascii=False
                ),
                OUTPUT_FILE,
                "application/json"
            )

        except json.JSONDecodeError:

            st.error(
                "❌ The saved JSON file is invalid."
            )

        except Exception:

            st.error(
                "❌ Could not read the saved JSON."
            )

    else:

        st.info(
            "No JSON response is available yet. "
            "Perform a search first."
        )


st.caption(
    "⚠️ The Spare Parts Price & Availability AI may make mistakes. "
    "Customers should verify important information before purchasing."
)