import math
import pandas as pd
import numpy as np
from typing import Any

def clean_nans_for_json(obj: Any) -> Any:
    """
    Recursively replaces NaN, NaT, and infinity floats/NumPy values with standard Python None,
    making the structure fully compliant with standard JSON specification (no raw NaN/Infinity output).
    """
    if isinstance(obj, list):
        return [clean_nans_for_json(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: clean_nans_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, (np.float32, np.float64)):
        val = float(obj)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    elif isinstance(obj, (np.int32, np.int64)):
        return int(obj)
    elif str(type(obj)) == "<class 'pandas._libs.tslibs.nattype.NaTType'>":
        return None
    try:
        if pd.isna(obj):
            return None
    except Exception:
        pass
    return obj
