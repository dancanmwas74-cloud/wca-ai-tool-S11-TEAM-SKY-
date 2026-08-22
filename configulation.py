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