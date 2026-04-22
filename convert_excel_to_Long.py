import pandas as pd

INPUT_FILE = "MECCA_Financial_Data.xlsx"
OUTPUT_FILE = "MECCA_Financial_Data_long.xlsx"

def convert_wide_to_long(input_path: str, output_path: str):
    xls = pd.ExcelFile(input_path)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for sheet in xls.sheet_names:
            try:
                # Sheet name should be the year: 2021, 2022, ...
                year = str(sheet).strip()

                df = pd.read_excel(input_path, sheet_name=sheet)

                if "Category" not in df.columns:
                    print(f"Skipping sheet '{sheet}': no 'Category' column.")
                    continue

                # Assume the other column is the year value (e.g., 2024)
                value_cols = [c for c in df.columns if c != "Category"]
                if not value_cols:
                    print(f"Skipping sheet '{sheet}': no value column.")
                    continue

                value_col = value_cols[0]

                out = pd.DataFrame({
                    "Type": "Income",          # You can later edit this for expenses if needed
                    "Category": df["Category"],
                    "Amount": df[value_col],
                })

                out.to_excel(writer, sheet_name=year, index=False)
                print(f"Converted sheet '{sheet}' -> '{year}' with {len(out)} rows.")

            except Exception as e:
                print(f"Error processing sheet '{sheet}': {e}")

    print(f"Done. New file written to: {output_path}")


if __name__ == "__main__":
    convert_wide_to_long(INPUT_FILE, OUTPUT_FILE)
