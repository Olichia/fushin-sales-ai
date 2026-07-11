from pathlib import Path

import pandas as pd


# 專案根目錄
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 原始資料資料夾
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


def inspect_excel_file(file_path: Path) -> None:
    """
    讀取一份 Excel 的所有工作表，
    並顯示每張工作表的基本資料品質資訊。
    """

    print("\n" + "=" * 80)
    print(f"檔案名稱：{file_path.name}")
    print(f"檔案路徑：{file_path}")
    print("=" * 80)

    if not file_path.exists():
        print(f"找不到檔案：{file_path}")
        return

    try:
        # sheet_name=None 代表讀取所有工作表
        sheets = pd.read_excel(
            file_path,
            sheet_name=None,
            engine="openpyxl",
        )

    except PermissionError:
        print("無法讀取檔案，請確認 Excel 檔案目前沒有被其他程式鎖定。")
        return

    except Exception as error:
        print(f"讀取 Excel 時發生錯誤：{error}")
        return

    print(f"工作表數量：{len(sheets)}")
    print(f"工作表名稱：{list(sheets.keys())}")

    for sheet_name, dataframe in sheets.items():
        print("\n" + "-" * 80)
        print(f"工作表：{sheet_name}")
        print("-" * 80)

        row_count, column_count = dataframe.shape

        print(f"資料列數：{row_count}")
        print(f"欄位數量：{column_count}")
        print(f"欄位名稱：{list(dataframe.columns)}")

        print("\n各欄缺值數：")
        missing_values = dataframe.isna().sum()
        print(missing_values.to_string())

        exact_duplicate_count = dataframe.duplicated().sum()

        print(f"\n完全重複列數：{exact_duplicate_count}")

        print("\n資料型別：")
        print(dataframe.dtypes.to_string())

        print("\n前 5 筆資料：")

        if dataframe.empty:
            print("此工作表沒有資料。")
        else:
            print(dataframe.head().to_string(index=False))


def main() -> None:
    """
    尋找 data/raw 內的所有 xlsx 檔案並逐一檢查。
    """

    print(f"原始資料位置：{RAW_DATA_DIR}")

    if not RAW_DATA_DIR.exists():
        print("找不到 data/raw 資料夾。")
        return

    excel_files = sorted(RAW_DATA_DIR.glob("*.xlsx"))

    if not excel_files:
        print("data/raw 資料夾內沒有找到任何 .xlsx 檔案。")
        return

    print(f"找到 {len(excel_files)} 份 Excel 檔案。")

    for file_path in excel_files:
        inspect_excel_file(file_path)


if __name__ == "__main__":
    main()