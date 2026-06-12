import pandas as pd
from io import BytesIO, StringIO


def planning_lines_to_dataframe(lines):
    return pd.DataFrame(lines)


def export_planning_excel(lines):
    df = planning_lines_to_dataframe(lines)
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Planung")

    output.seek(0)
    return output


def export_planning_csv(lines):
    df = planning_lines_to_dataframe(lines)
    output = StringIO()
    df.to_csv(output, index=False, sep=";")
    output.seek(0)
    return output
