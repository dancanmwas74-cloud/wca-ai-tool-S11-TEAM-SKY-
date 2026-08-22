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
