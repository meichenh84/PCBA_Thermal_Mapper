"""
=============================================================================
資料夾檔案自動分類與驗證模組 (folder_scanner.py)
=============================================================================
用途：
    掃描指定資料夾中的所有檔案，根據檔案內容自動分類為六種類型：
      - heat       : 熱力圖影像（.jpg/.jpeg/.png，HSV 高飽和度 + 高色調變異）
      - layout     : Layout 佈局圖影像（.jpg/.jpeg/.png，黑色像素比例 > 60%）
      - heatTemp   : 溫度數據（.csv/.xlsx，列數≥50 且數字佔比>90% 的寬數值矩陣，可容忍前幾行文字表頭）
      - layoutXY   : 元器件座標檔（.xlsx，含 RefDes, Orient., X, Y）
      - layoutLWT  : 元器件尺寸檔（.xlsx，含 RefDes, L, W, T, 对象描述）
      - testReport : 測試報告（.xlsx，含 HIGH 字眼的 sheet）

    同時提供驗證功能，檢查 Layout 數據檔案是否成對存在。

在整個應用中的角色：
    - 純邏輯層模組，不依賴 tkinter，不顯示任何 UI
    - 由 main.py (ResizableImagesApp) 呼叫，取得分類結果與警告訊息
    - 將檔案分類、影像辨識、欄位偵測等邏輯從 main.py 中解耦

關聯檔案：
    - main.py：呼叫本模組進行資料夾掃描與驗證
    - load_tempA.py：負責實際載入溫度數據（本模組僅負責分類）
=============================================================================
"""

import os
import cv2
import numpy as np
import pandas as pd
import openpyxl


# =============================================================================
# 影像辨識函式
# =============================================================================

def _cv2_imread_unicode(image_path):
    """讀取含有中文（Unicode）路徑的圖片檔案。

    解決 OpenCV 在 Windows 上無法直接讀取含中文字元路徑的問題，
    先用 NumPy 將檔案讀為位元組陣列，再用 cv2.imdecode 解碼為圖片。

    參數：
        image_path (str): 圖片檔案的完整路徑（可包含中文字元）

    回傳：
        numpy.ndarray 或 None: 成功時回傳 BGR 格式的圖片陣列，失敗時回傳 None
    """
    try:
        img_array = np.fromfile(image_path, dtype=np.uint8)
        image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return image
    except Exception as e:
        print(f"cv2_imread_unicode error: {e}")
        return None


def is_heat_image(image_path):
    """判斷指定圖片是否為熱力圖。

    透過分析 HSV 色彩空間的飽和度平均值和色調變異數來判定。
    熱力圖通常具有較高的色彩飽和度（>80）和較大的色調變化（>1000）。

    參數：
        image_path (str): 圖片檔案路徑

    回傳：
        bool: True 表示判定為熱力圖
    """
    try:
        image = _cv2_imread_unicode(image_path)
        if image is None:
            return False

        # 轉換為 HSV 色彩空間
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # 計算色彩飽和度平均值
        saturation = hsv[:, :, 1]
        avg_saturation = np.mean(saturation)

        # 計算色調變異數
        color_variance = np.var(hsv[:, :, 0])

        # 熱力圖通常有較高的飽和度和色調變化
        return avg_saturation > 80 and color_variance > 1000
    except:
        return False


def is_layout_image(image_path):
    """判斷指定圖片是否為 Layout 圖。

    透過計算灰階影像中黑色像素（亮度<50）的比例來判定。
    Layout 圖通常有超過 60% 的黑色背景。

    參數：
        image_path (str): 圖片檔案路徑

    回傳：
        bool: True 表示判定為 Layout 圖
    """
    try:
        image = _cv2_imread_unicode(image_path)
        if image is None:
            return False

        # 轉換為灰度圖
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 計算黑色像素的比例（閾值設為 50）
        black_pixels = np.sum(gray < 50)
        total_pixels = gray.shape[0] * gray.shape[1]
        black_ratio = black_pixels / total_pixels

        # 如果黑色像素比例超過 60%，判定為 Layout 圖
        return black_ratio > 0.6
    except:
        return False


# =============================================================================
# 測試報告偵測函式
# =============================================================================

def is_test_report_xlsx(file_path):
    """判斷指定 .xlsx 檔案是否為測試報告。

    透過檢查檔案中的所有 sheet 名稱，若任一 sheet 名稱轉大寫後含有
    "HIGH" 字串，則判定為測試報告。

    參數：
        file_path (str): .xlsx 檔案的完整路徑

    回傳：
        bool: True 表示判定為測試報告
    """
    try:
        wb = openpyxl.load_workbook(file_path, read_only=True)
        sheet_names = wb.sheetnames
        wb.close()
        for name in sheet_names:
            if "HIGH" in name.upper():
                return True
        return False
    except Exception:
        return False


# =============================================================================
# Excel 檔案分類函式
# =============================================================================

def _check_temperature_matrix(df):
    """判斷 DataFrame 是否為溫度數據矩陣。

    判斷條件（全部通過才歸為溫度數據）：
        1. 列數 ≥ 50：溫度矩陣通常很寬（每列對應影像的一個像素寬度）
        2. 跳過表頭：從前 5 行中找到第一行數字佔比 > 80% 的位置作為數據起始行
        3. 數字佔比 > 90%：取數據起始行後 5 行，所有 cell 中能轉為數字的比例 > 90%

    參數：
        df (pandas.DataFrame): 已讀取的前 20 行資料（header=None）

    回傳：
        bool: True 表示判定為溫度數據
    """
    if df.empty or len(df.columns) < 50:
        return False

    # 在前 5 行中找到數據起始行（數字佔比 > 80%）
    data_start = None
    scan_rows = min(5, len(df))
    for i in range(scan_rows):
        row = df.iloc[i]
        numeric_count = 0
        for val in row:
            try:
                float(val)
                numeric_count += 1
            except (ValueError, TypeError):
                pass
        if len(row) > 0 and numeric_count / len(row) > 0.8:
            data_start = i
            break

    if data_start is None:
        return False

    # 從數據起始行取最多 5 行，檢查數字佔比 > 90%
    check_end = min(data_start + 5, len(df))
    check_df = df.iloc[data_start:check_end]
    if check_df.empty:
        return False

    total_cells = 0
    numeric_cells = 0
    for _, row in check_df.iterrows():
        for val in row:
            total_cells += 1
            try:
                float(val)
                numeric_cells += 1
            except (ValueError, TypeError):
                pass

    return total_cells > 0 and numeric_cells / total_cells > 0.9


def is_temperature_csv(file_path):
    """判斷指定 .csv 檔案是否為溫度數據。

    讀取前 20 行（自動偵測分隔符 tab/comma），再交由
    _check_temperature_matrix() 判斷是否為寬數值矩陣。

    參數：
        file_path (str): .csv 檔案的完整路徑

    回傳：
        bool: True 表示判定為溫度數據
    """
    try:
        df = None
        for encoding in ('utf-8', 'utf-8-sig', 'cp950', 'gbk'):
            for sep in ('\t', ','):
                try:
                    df = pd.read_csv(file_path, nrows=20, header=None,
                                     encoding=encoding, sep=sep)
                    if df is not None and len(df.columns) >= 50:
                        break
                except (UnicodeDecodeError, UnicodeError):
                    df = None
                    continue
                except Exception:
                    df = None
                    continue
            if df is not None and len(df.columns) >= 50:
                break

        if df is None:
            return False

        return _check_temperature_matrix(df)
    except Exception:
        return False


def is_temperature_xlsx(file_path):
    """判斷指定 .xlsx 檔案是否為溫度數據。

    讀取前 20 行，再交由 _check_temperature_matrix() 判斷是否為寬數值矩陣。

    參數：
        file_path (str): .xlsx 檔案的完整路徑

    回傳：
        bool: True 表示判定為溫度數據
    """
    try:
        df = pd.read_excel(file_path, nrows=20, header=None)
        return _check_temperature_matrix(df)
    except Exception:
        return False



def classify_xlsx_file(file_path):
    """自動分類 .xlsx 檔案類型。

    根據欄位內容判斷是元器件座標檔 (layoutXY) 還是元器件尺寸檔 (layoutLWT)。

    歸類規則（寬鬆）：
        - layoutXY：同時含有 X, Y 欄位即歸類
          完整欄位：RefDes, Orient., X, Y
        - layoutLWT：同時含有 L, W, T 欄位即歸類
          完整欄位：RefDes, 对象描述, L, W, T
        - 都不符合：回傳 (None, cols)

    缺少 RefDes / Orient. / 对象描述 等欄位時仍可歸類，
    但 validate_layout_data() 會彈出警告提示缺少的欄位。

    參數：
        file_path (str): 檔案路徑

    回傳：
        tuple: (file_type, columns)
            - file_type (str 或 None): 'layoutXY' / 'layoutLWT' / None
            - columns (list): 該檔案的完整欄位名稱清單（供驗證使用）
    """
    try:
        if not file_path.lower().endswith('.xlsx'):
            return None, []
        df = pd.read_excel(file_path, nrows=1)
        cols = df.columns.tolist()
        if 'X' in cols and 'Y' in cols:
            return 'layoutXY', cols
        if 'L' in cols and 'W' in cols and 'T' in cols:
            return 'layoutLWT', cols
        return None, cols
    except:
        return None, []


# =============================================================================
# 資料夾掃描主函式
# =============================================================================

def scan_folder(folder_path):
    """掃描指定資料夾中的所有檔案，根據檔案內容自動分類。

    分類邏輯：
        1. 圖片檔 (.jpg/.jpeg/.png)：
           - 先判斷是否為 Layout 圖（黑色像素比例 > 60%）
           - 再判斷是否為熱力圖（HSV 高飽和度 + 高色調變異）
        2. 數據檔 (.csv/.xlsx)：
           - .xlsx 根據欄位內容判斷為 layoutXY / layoutLWT / testReport / heatTemp
           - .csv 第一行全為數字時歸類為 heatTemp（溫度數據）

    結果按修改時間排序（最新的在前）。

    參數：
        folder_path (str): 資料夾的完整路徑

    回傳：
        tuple: (folder_files, xlsx_columns_cache)
            - folder_files (dict): 各分類的檔案名稱列表
              {"heat": [...], "layout": [...], "heatTemp": [...],
               "layoutXY": [...], "layoutLWT": [...], "testReport": [...]}
            - xlsx_columns_cache (dict): 各 xlsx 檔案的欄位名稱快取
              {"filename.xlsx": ["col1", "col2", ...], ...}
    """
    folder_files = {"heat": [], "layout": [], "heatTemp": [], "layoutXY": [], "layoutLWT": [], "testReport": []}
    xlsx_columns_cache = {}

    if not folder_path or not os.path.isdir(folder_path):
        return folder_files, xlsx_columns_cache

    # 收集檔案資訊（檔案名稱和修改時間）
    file_info = {"heat": [], "layout": [], "heatTemp": [], "layoutXY": [], "layoutLWT": [], "testReport": []}

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if not os.path.isfile(file_path):
            continue

        # 取得檔案修改時間
        mtime = os.path.getmtime(file_path)

        # 圖片檔分類
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            # 先判斷是否為 Layout 圖，再判斷是否為熱力圖
            if is_layout_image(file_path):
                file_info["layout"].append((filename, mtime))
            elif is_heat_image(file_path):
                file_info["heat"].append((filename, mtime))

        # 數據檔分類
        elif filename.lower().endswith(('.csv', '.xlsx')):
            if filename.lower().endswith('.xlsx'):
                xlsx_type, cols = classify_xlsx_file(file_path)
                xlsx_columns_cache[filename] = cols
                if xlsx_type == 'layoutXY':
                    file_info["layoutXY"].append((filename, mtime))
                elif xlsx_type == 'layoutLWT':
                    file_info["layoutLWT"].append((filename, mtime))
                elif is_test_report_xlsx(file_path):
                    file_info["testReport"].append((filename, mtime))
                elif is_temperature_xlsx(file_path):
                    file_info["heatTemp"].append((filename, mtime))
            elif filename.lower().endswith('.csv'):
                if is_temperature_csv(file_path):
                    file_info["heatTemp"].append((filename, mtime))

    # 按修改時間排序（最新的在前）
    for category in file_info:
        file_info[category].sort(key=lambda x: x[1], reverse=True)
        folder_files[category] = [filename for filename, _ in file_info[category]]

    return folder_files, xlsx_columns_cache


# =============================================================================
# Layout 數據驗證函式
# =============================================================================

def validate_layout_data(folder_files, xlsx_columns_cache):
    """驗證 Layout 數據檔案的完整性與欄位齊全度。

    檢查邏輯：
        1. 檔案配對檢查：
            - 兩者都沒有 → 不警告
            - 只有一方有 → 回傳缺檔警告
        2. 欄位完整性檢查（即使兩者都有也檢查）：
            - layoutXY 完整欄位：RefDes, Orient., X, Y
              缺少 RefDes 或 Orient. → 警告
            - layoutLWT 完整欄位：RefDes, 对象描述, L, W, T
              缺少 RefDes 或 对象描述 → 警告

    參數：
        folder_files (dict): scan_folder() 回傳的分類結果
        xlsx_columns_cache (dict): scan_folder() 回傳的欄位快取

    回傳：
        tuple: (warning_msg, warned_categories)
            - warning_msg (str 或 None): 警告訊息字串，若無問題則為 None
            - warned_categories (set): 有問題的分類名稱集合（如 {"layoutXY", "layoutLWT"}）
    """
    xy_files = folder_files.get("layoutXY", [])
    lwt_files = folder_files.get("layoutLWT", [])

    has_xy = len(xy_files) > 0
    has_lwt = len(lwt_files) > 0

    # 兩者都沒有 → 不警告
    if not has_xy and not has_lwt:
        return None, set()

    warnings = []
    warned_categories = set()

    # --- 檔案配對檢查 ---
    if has_xy and not has_lwt:
        warned_categories.add("layoutXY")
        warnings.append(
            f"\u2713 元器件座標：{xy_files[0]}\n"
            f"\u2717 元器件尺寸：未偵測到\n"
            f"   需要同時含有 L, W, T 欄位的 .xlsx 檔案"
        )
    elif has_lwt and not has_xy:
        warned_categories.add("layoutLWT")
        warnings.append(
            f"\u2717 元器件座標：未偵測到\n"
            f"   需要同時含有 X, Y 欄位的 .xlsx 檔案\n"
            f"\u2713 元器件尺寸：{lwt_files[0]}"
        )

    # --- 欄位完整性檢查 ---
    if has_xy:
        xy_cols = xlsx_columns_cache.get(xy_files[0], [])
        missing_xy = [f for f in ['RefDes', 'Orient.'] if f not in xy_cols]
        if missing_xy:
            warned_categories.add("layoutXY")
            warnings.append(
                f"\u2757 元器件座標 ({xy_files[0]}) 缺少欄位：{', '.join(missing_xy)}\n"
                f"   目前欄位：{', '.join(xy_cols)}\n"
                f"   完整欄位應為：RefDes, Orient., X, Y"
            )

    if has_lwt:
        lwt_cols = xlsx_columns_cache.get(lwt_files[0], [])
        missing_lwt = [f for f in ['RefDes', '对象描述'] if f not in lwt_cols]
        if missing_lwt:
            warned_categories.add("layoutLWT")
            warnings.append(
                f"\u2757 元器件尺寸 ({lwt_files[0]}) 缺少欄位：{', '.join(missing_lwt)}\n"
                f"   目前欄位：{', '.join(lwt_cols)}\n"
                f"   完整欄位應為：RefDes, 对象描述, L, W, T"
            )

    if not warnings:
        return None, set()

    msg = "Layout 數據檔案檢查結果：\n\n" + "\n\n".join(warnings)
    return msg, warned_categories
