import os
import uuid
import pandas as pd
import numpy as np
from fastapi import UploadFile, HTTPException
from backend.app.core.config import settings

def save_uploaded_file(file: UploadFile) -> tuple[str, int]:
    """
    Saves an uploaded file to the local uploads directory.
    Returns a tuple of (saved_file_path, file_size_in_bytes).
    """
    # Sanitize file extension and name
    filename = os.path.basename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    
    if ext not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(status_code=400, detail="Unsupported file format. Only CSV and Excel (.xlsx, .xls) are allowed.")
        
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
    
    file_size = 0
    try:
        with open(file_path, "wb") as buffer:
            # Read chunk by chunk to limit memory spike
            while chunk := file.file.read(1024 * 1024):
                file_size += len(chunk)
                # Check file size limit
                if file_size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                    # Remove partially written file
                    buffer.close()
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    raise HTTPException(
                        status_code=400, 
                        detail=f"File exceeds maximum upload limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to write file to disk: {str(e)}")
        
    return file_path, file_size

def load_dataframe(file_path: str) -> pd.DataFrame:
    """
    Loads a Pandas DataFrame from the stored file. Handles parsing, encodings, and empty dataset verification.
    """
    resolved_path = file_path
    if not os.path.exists(resolved_path):
        # Resolve relative to backend folder
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        alt1 = os.path.join(backend_dir, file_path)
        alt2 = os.path.join(backend_dir, "uploads", os.path.basename(file_path))
        alt3 = os.path.join(os.path.dirname(backend_dir), "uploads", os.path.basename(file_path))
        
        if os.path.exists(alt1):
            resolved_path = alt1
        elif os.path.exists(alt2):
            resolved_path = alt2
        elif os.path.exists(alt3):
            resolved_path = alt3
        else:
            raise HTTPException(status_code=404, detail="Uploaded file not found.")
            
    ext = os.path.splitext(resolved_path)[1].lower()
    
    try:
        if ext == ".csv":
            # Attempt loading with different encodings
            encodings = ["utf-8", "latin1", "cp1252", "utf-16"]
            df = None
            last_err = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(resolved_path, encoding=encoding)
                    break
                except UnicodeDecodeError as err:
                    last_err = err
                    continue
                except pd.errors.EmptyDataError:
                    raise HTTPException(status_code=400, detail="The uploaded CSV file is empty.")
                except pd.errors.ParserError as pe:
                    raise HTTPException(status_code=400, detail=f"Invalid CSV structure or parsing error: {str(pe)}")
                    
            if df is None:
                raise HTTPException(status_code=400, detail=f"Unable to decode file. Encoding error: {str(last_err)}")
                
        else:  # Excel files
            try:
                # openpyxl engine handles xlsx/xls
                df = pd.read_excel(resolved_path)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid or corrupted Excel file: {str(e)}")
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file into dataframe: {str(e)}")

    if df.empty:
        raise HTTPException(status_code=400, detail="The dataset is empty (contains no rows).")
        
    # Replace NaN/inf with None to prevent JSON serialization errors
    df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
    return df

def infer_column_type(col_name: str, series: pd.Series) -> str:
    """
    Heuristic rule to classify columns into:
    - Numeric
    - Categorical
    - Boolean
    - Date/time
    - Text
    - Identifier
    - Geographic candidate
    """
    # Clean series of nulls for typing checks
    non_null_series = series.dropna()
    if non_null_series.empty:
        return "Text"  # Default if all values are null
        
    col_name_lower = col_name.lower()
    
    # 1. Identifier Check
    # Column contains 'id', 'key', 'code' and has highly unique values
    is_id_name = any(kw in col_name_lower for kw in ["id", "key", "code", "pk", "uuid"])
    unique_count = non_null_series.nunique()
    total_count = len(non_null_series)
    unique_ratio = unique_count / total_count if total_count > 0 else 0
    
    if is_id_name and (unique_ratio > 0.8 or pd.api.types.is_integer_dtype(non_null_series.dtype)):
        return "Identifier"
        
    # 2. Boolean Check
    # If pandas thinks it is bool, or if unique values are only subset of {0, 1, True, False, 'yes', 'no', 'true', 'false', 'y', 'n'}
    if pd.api.types.is_bool_dtype(non_null_series.dtype):
        return "Boolean"
        
    if unique_count <= 2:
        str_vals = {str(val).strip().lower() for val in non_null_series.unique()}
        bool_sets = [{"0", "1"}, {"true", "false"}, {"yes", "no"}, {"y", "n"}, {"t", "f"}]
        if any(str_vals.issubset(bset) for bset in bool_sets):
            return "Boolean"

    # 3. Geographic Check
    geo_keywords = ["country", "city", "state", "region", "province", "zip", "postal", "latitude", "longitude", "lat", "lon", "address"]
    if any(kw == col_name_lower or f"_{kw}" in col_name_lower or f"{kw}_" in col_name_lower for kw in geo_keywords):
        # We classify as geography only if the values are strings or lat/long floats
        if pd.api.types.is_numeric_dtype(non_null_series.dtype) or pd.api.types.is_object_dtype(non_null_series.dtype) or pd.api.types.is_string_dtype(non_null_series.dtype):
            return "Geographic candidate"

    # 4. Date/Time Check
    if pd.api.types.is_datetime64_any_dtype(non_null_series.dtype):
        return "Date/time"
        
    # Try parsing string as date if column name has date clues
    date_clues = ["date", "time", "created", "updated", "year", "month", "day", "timestamp"]
    if any(clue in col_name_lower for clue in date_clues):
        try:
            # If the column name represents a raw year and the data is numeric (e.g. 2020),
            # classify it as Numeric instead of temporal Date/time.
            is_raw_year = "year" in col_name_lower and pd.api.types.is_numeric_dtype(non_null_series.dtype)
            if not is_raw_year:
                # Check a sample of rows to see if they fit datetime format
                sample_size = min(100, len(non_null_series))
                sample = non_null_series.sample(sample_size, random_state=42)
                parsed = pd.to_datetime(sample, errors="coerce")
                if parsed.notna().sum() / sample_size > 0.8:  # 80% successfully parsed
                    return "Date/time"
        except Exception:
            pass

    # 5. Numeric Check
    if pd.api.types.is_numeric_dtype(non_null_series.dtype):
        return "Numeric"

    # 6. Categorical Check vs Text Check
    # If cardinality is low, or unique ratio is low (e.g. unique values repeated often)
    if unique_count < 50 or unique_ratio < 0.15:
        return "Categorical"

    return "Text"
