import os
import re
import json
import urllib.request
import pandas as pd
from typing import Dict, Any, List, Optional
from backend.app.schemas.schemas import (
    NLQueryResponse, NLQueryChartSpec, NLQueryFilterSpec, NLQueryClarification
)

# Common column name suffixes to strip for fuzzy matching
SUFFIXES = ["_nzsioc", "_code", "_name", "_category", "_id", " nzsioc", " code", " name", " category", " id"]

def detect_prompt_injection(question: str) -> bool:
    """
    Scans the question for common SQL or command injection signatures,
    or ignore instruction jailbreak attempts.
    """
    patterns = [
        r"\bdrop\b.*\btable\b",
        r"\bdrop\b.*\bdatabase\b",
        r"\bdelete\b.*\bfrom\b",
        r"\binsert\b.*\binto\b",
        r"\btruncate\b.*\btable\b",
        r"\balter\b.*\btable\b",
        r"\bselect\b.*\bfrom\b",
        r"\bunion\b.*\bselect\b",
        r"\bignore\b.*\binstructions\b",
        r"\bdelete\b.*\bdatabase\b"
    ]
    q_lower = question.lower()
    for pattern in patterns:
        if re.search(pattern, q_lower):
            return True
    return False

def query_llm(
    question: str,
    df_columns: List[str],
    column_stats: Dict[str, Any],
    api_key: str,
    provider: str
) -> Optional[NLQueryChartSpec]:
    """
    Queries an LLM (Gemini or OpenAI) to translate the question into a structured JSON chart spec.
    """
    schema_desc = []
    for col in df_columns:
        col_type = column_stats.get(col, {}).get("detected_type", "Unknown")
        top_vals = [t["value"] for t in column_stats.get(col, {}).get("top_frequent", [])]
        top_str = f" (Sample values: {', '.join(top_vals)})" if top_vals else ""
        schema_desc.append(f"- {col} (Type: {col_type}){top_str}")
        
    schema_text = "\n".join(schema_desc)
    
    prompt = f"""You are an expert data analysis parser.
Your task is to translate a user's natural language question into a structured JSON configuration representing a chart visualization specification.
The target JSON structure must match this schema:
{{
  "chart_type": "bar" | "line" | "pie" | "scatter" | "histogram",
  "x_axis": "<existing_column_name>",
  "y_axis": "<existing_column_name>" | null,
  "aggregation": "count" | "sum" | "average" | "median" | "min" | "max" | "none",
  "group_by": "<existing_column_name>" | null,
  "filters": [
    {{
      "column": "<existing_column_name>",
      "operator": "equals" | "not_equals" | "greater_than" | "greater_than_or_equal" | "less_than" | "less_than_or_equal" | "in",
      "value": <value>
    }}
  ],
  "title": "<auto_generated_chart_title>"
}}

Available Dataset Columns:
{schema_text}

Rules:
1. ONLY use column names that exactly exist in the dataset column list above.
2. If chart_type is "pie", "x_axis" must be a categorical column, and "aggregation" should usually be "count" or "sum"/"average" of a numeric column.
3. If chart_type is "scatter", both "x_axis" and "y_axis" must be numeric columns, and "aggregation" must be "none".
4. If chart_type is "histogram", "x_axis" must be numeric and "aggregation" must be "count" (Y-axis should be null).
5. If aggregation is "count", "y_axis" must be null. For other aggregations, "y_axis" is required and must be a Numeric column.
6. Automatically extract filters from the prompt.
7. Return ONLY the JSON object. Do not explain, do not add markdown backticks unless they enclose raw json.

Question: "{question}"
JSON:"""
    
    try:
        if provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json"
                }
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        else:  # openai
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a precise data analysis JSON parser."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                text = res_data["choices"][0]["message"]["content"].strip()
                
        # Parse JSON
        obj = json.loads(text)
        
        # Validation: check columns exist
        if obj.get("x_axis") not in df_columns:
            return None
        if obj.get("y_axis") and obj.get("y_axis") not in df_columns:
            obj["y_axis"] = None
        if obj.get("group_by") and obj.get("group_by") not in df_columns:
            obj["group_by"] = None
            
        # Clean filters
        valid_filters = []
        for f in obj.get("filters", []):
            if f.get("column") in df_columns:
                valid_filters.append(NLQueryFilterSpec(
                    column=f["column"],
                    operator=f.get("operator", "equals"),
                    value=f.get("value")
                ))
        obj["filters"] = valid_filters
        
        return NLQueryChartSpec(**obj)
        
    except Exception as e:
        print(f"LLM Adapter failed: {e}")
        return None

def deterministic_parse(
    question: str,
    df: pd.DataFrame,
    column_stats: Dict[str, Any]
) -> NLQueryResponse:
    """
    Fall-back rule-based parsing engine mapping query keywords and column names.
    """
    q_clean = question.lower().strip()
    
    # Collect all column aliases to identify mentions
    alias_to_col = {}
    for col in df.columns:
        col_lower = col.lower()
        alias_to_col[col_lower] = col
        alias_to_col[col_lower.replace("_", " ")] = col
        alias_to_col[col_lower.replace(" ", "_")] = col
        for suffix in SUFFIXES:
            if col_lower.endswith(suffix):
                short = col_lower[:-len(suffix)]
                alias_to_col[short] = col
                alias_to_col[short.replace("_", " ")] = col
                alias_to_col[short.replace(" ", "_")] = col
                
    sorted_aliases = sorted(alias_to_col.keys(), key=len, reverse=True)
    
    # Check for mentions
    mentioned_any = False
    for alias in sorted_aliases:
        if re.search(rf'\b{re.escape(alias)}\b', q_clean):
            mentioned_any = True
            break

    # 1. Parse explicit filters (e.g. "Year equals 2018", "Value > 1000")
    filters = []
    operators_map = {
        "==": "equals",
        "=": "equals",
        "equals": "equals",
        "is": "equals",
        "!=": "not_equals",
        "is not": "not_equals",
        "not equal to": "not_equals",
        ">=": "greater_than_or_equal",
        "greater than or equal to": "greater_than_or_equal",
        "greater than or equal": "greater_than_or_equal",
        "<=": "less_than_or_equal",
        "less than or equal to": "less_than_or_equal",
        "less than or equal": "less_than_or_equal",
        ">": "greater_than",
        "greater than": "greater_than",
        "<": "less_than",
        "less than": "less_than",
        "in": "in"
    }
    
    temp_q = q_clean
    for alias in sorted_aliases:
        op_pattern = r"(?:==|=|equals|is\s+not|is|!=|>=|<=|>|<|greater\s+than\s+or\s+equal\s+to|less\s+than\s+or\s+equal\s+to|greater\s+than|less\s+than|in)"
        pattern = rf'\b{re.escape(alias)}\b\s*({op_pattern})\s*([\'"]?[a-zA-Z0-9_\-\.\s]+[\'"]?|\([^)]*\))'
        
        match = re.search(pattern, temp_q)
        if match:
            op_raw = match.group(1).strip()
            val_raw = match.group(2).strip().strip("'\"")
            
            op = operators_map.get(op_raw, "equals")
            col_name = alias_to_col[alias]
            
            filters.append(NLQueryFilterSpec(column=col_name, operator=op, value=val_raw))
            temp_q = temp_q.replace(match.group(0), "")
            
    # 2. Implicit values matching (matching search words to categorical values)
    for col in df.columns:
        if any(f.column == col for f in filters):
            continue
            
        col_type = column_stats.get(col, {}).get("detected_type", "")
        if col_type != "Numeric":
            top_vals = []
            if col in column_stats and "top_frequent" in column_stats[col]:
                top_vals = [t["value"] for t in column_stats[col]["top_frequent"]]
            else:
                try:
                    top_vals = [str(x) for x in df[col].dropna().unique()[:20]]
                except Exception:
                    top_vals = []
                    
            for val in top_vals:
                if len(val) < 3:
                    continue
                pattern = rf'\b{re.escape(val.lower())}\b'
                if re.search(pattern, temp_q):
                    filters.append(NLQueryFilterSpec(column=col, operator="equals", value=val))
                    temp_q = re.sub(pattern, "", temp_q)

    # 3. Extract Aggregation
    aggregation = "count"  # default
    agg_keywords = {
        "average": ["average", "mean", "avg", "average of", "mean of"],
        "sum": ["sum", "total", "sum of", "total of"],
        "median": ["median", "median of"],
        "min": ["minimum", "min", "minimum of", "min of"],
        "max": ["maximum", "max", "maximum of", "max of"],
        "count": ["count", "number of", "how many", "instances of", "occurrences of", "count of"]
    }
    
    chosen_agg = None
    for agg, keywords in agg_keywords.items():
        for keyword in keywords:
            if re.search(rf'\b{re.escape(keyword)}\b', temp_q):
                chosen_agg = agg
                temp_q = re.sub(rf'\b{re.escape(keyword)}\b', "", temp_q)
                break
        if chosen_agg:
            break
            
    if chosen_agg:
        aggregation = chosen_agg

    # 4. Extract columns mentioned in the query
    mentioned_cols = []
    temp_temp_q = temp_q
    matched_positions = []
    
    for alias in sorted_aliases:
        pattern = rf'\b{re.escape(alias)}\b'
        for m in re.finditer(pattern, temp_temp_q):
            col_name = alias_to_col[alias]
            matched_positions.append((m.start(), col_name))
            start, end = m.span()
            temp_temp_q = temp_temp_q[:start] + " " * (end - start) + temp_temp_q[end:]
            
    matched_positions.sort()
    mentioned_cols = [col_name for idx, col_name in matched_positions]

    # 5. Extract X-axis and Group-by candidates based on preceding prepositions
    x_axis = None
    y_axis = None
    group_by = None
    
    x_candidates = []
    group_candidates = []
    
    for alias in sorted_aliases:
        pattern_by = rf'\b(?:by|per|across|over|each|every|along)\s+{re.escape(alias)}\b'
        if re.search(pattern_by, temp_q):
            x_candidates.append(alias_to_col[alias])
            
        pattern_group = rf'\b(?:group|grouped|split|broken\s+down|color|segmented|categorized)\s+(?:by|on|with)?\s+{re.escape(alias)}\b'
        if re.search(pattern_group, temp_q):
            group_candidates.append(alias_to_col[alias])

    # Assign Group By
    if group_candidates:
        group_by = group_candidates[0]
        if group_by in mentioned_cols:
            mentioned_cols.remove(group_by)
            
    # Assign X-axis
    if x_candidates:
        cand = [c for c in x_candidates if c != group_by]
        if cand:
            x_axis = cand[0]
            if x_axis in mentioned_cols:
                mentioned_cols.remove(x_axis)

    # If X-axis is not defined yet, take the last mentioned column
    if not x_axis:
        if mentioned_cols:
            x_axis = mentioned_cols[-1]
            mentioned_cols.remove(x_axis)
            
    # If Y-axis is not defined, take the remaining column
    if not y_axis:
        if mentioned_cols:
            numeric_left = [c for c in mentioned_cols if column_stats.get(c, {}).get("detected_type") == "Numeric"]
            if numeric_left:
                y_axis = numeric_left[0]
            else:
                y_axis = mentioned_cols[0]

    # Defaults fallback if still None
    if not x_axis:
        cat_cols = [c for c in df.columns if column_stats.get(c, {}).get("detected_type") in ["Categorical", "Date/time", "Identifier"]]
        if cat_cols:
            x_axis = cat_cols[0]
        else:
            x_axis = df.columns[0]

    # If the user explicitly wanted a measure aggregation but we found no numeric column
    if aggregation in ["sum", "average", "median", "min", "max"] and not y_axis:
        return NLQueryResponse(
            question=question,
            status="ambiguous",
            interpretation="Could not resolve columns or chart intents in the query.",
            clarification=NLQueryClarification(
                reason=f"Aggregation '{aggregation}' was requested, but no valid numeric measure column could be identified.",
                suggested_columns=list(df.columns)[:5],
                suggested_charts=["bar", "line", "pie"]
            )
        )
            
    if aggregation != "count" and aggregation != "none" and not y_axis:
        numeric_cols = [c for c in df.columns if column_stats.get(c, {}).get("detected_type") == "Numeric" and c != x_axis]
        if numeric_cols:
            y_axis = numeric_cols[0]
        else:
            aggregation = "count"
            y_axis = None

    # Ambiguity check for vague queries with no chart or aggregation intents
    has_chart_keyword = any(k in q_clean for k in ["bar", "line", "pie", "scatter", "histogram", "plot", "chart", "trend", "distribution", "over time", "vs", "versus"])
    has_agg_keyword = chosen_agg is not None
    
    if not has_chart_keyword and not has_agg_keyword and len(question.strip().split()) <= 4:
        return NLQueryResponse(
            question=question,
            status="ambiguous",
            interpretation="Query is too vague.",
            clarification=NLQueryClarification(
                reason="I found the column reference but couldn't deduce the type of analysis or chart you want. Try asking 'Count records by Industry' or 'Show distribution of Industry'.",
                suggested_columns=list(df.columns)[:5],
                suggested_charts=["bar", "pie"]
            )
        )

    # 6. Resolve Chart Type
    chart_type = "bar"
    if any(k in q_clean for k in ["pie", "pie chart", "share of", "proportion of"]):
        chart_type = "pie"
    elif any(k in q_clean for k in ["scatter", "scatter plot", "correlation", " vs ", " versus "]):
        chart_type = "scatter"
        aggregation = "none"
        if not y_axis:
            numeric_cols = [c for c in df.columns if column_stats.get(c, {}).get("detected_type") == "Numeric" and c != x_axis]
            if numeric_cols:
                y_axis = numeric_cols[0]
    elif any(k in q_clean for k in ["histogram", "distribution of"]):
        x_type = column_stats.get(x_axis, {}).get("detected_type", "")
        if x_type == "Numeric":
            chart_type = "histogram"
        else:
            chart_type = "pie"  # Distribution of categorical column maps to Pie Chart
    elif any(k in q_clean for k in ["line", "line chart", "trend", "over time", "evolution"]):
        chart_type = "line"
    else:
        x_type = column_stats.get(x_axis, {}).get("detected_type", "")
        if x_type == "Date/time":
            chart_type = "line"
        else:
            chart_type = "bar"

    # Construct interpretation and title
    agg_label = f"{aggregation.capitalize()} of " if aggregation not in ["none", "count"] else ("Record Count of " if aggregation == "count" else "Raw Datapoints of ")
    y_label = f"{y_axis} " if y_axis else ""
    x_label = f"by {x_axis}"
    group_label = f" split by {group_by}" if group_by else ""
    filter_label = ""
    if filters:
        filter_parts = [f"{f.column} {f.operator} {f.value}" for f in filters]
        filter_label = f" where {', '.join(filter_parts)}"
        
    title = f"{agg_label}{y_label}{x_label}{group_label}".strip()
    interpretation = f"Parsed query as: {agg_label}{y_label}{x_label}{group_label}{filter_label}."
    
    spec = NLQueryChartSpec(
        chart_type=chart_type,
        x_axis=x_axis,
        y_axis=y_axis,
        aggregation=aggregation,
        group_by=group_by,
        filters=filters,
        title=title
    )
    
    return NLQueryResponse(
        question=question,
        status="success",
        interpretation=interpretation,
        chart_spec=spec
    )

def parse_question(
    question: str,
    df: pd.DataFrame,
    column_stats: Dict[str, Any]
) -> NLQueryResponse:
    """
    Main entry point for parsing natural language queries.
    Checks security constraints, applies optional LLM parsing, or falls back to rules.
    """
    # 1. Security Check
    if detect_prompt_injection(question):
        return NLQueryResponse(
            question=question,
            status="error",
            interpretation="Security policy violation. Query rejected.",
            clarification=NLQueryClarification(
                reason="Your query was flagged as unsafe by the system security policy."
            )
        )
        
    # 2. Try LLM Adapter if API Keys are configured
    gemini_key = os.environ.get("GEMINI_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    
    spec = None
    if gemini_key:
        spec = query_llm(question, list(df.columns), column_stats, gemini_key, "gemini")
    elif openai_key:
        spec = query_llm(question, list(df.columns), column_stats, openai_key, "openai")
        
    if spec:
        filter_label = ""
        if spec.filters:
            filter_parts = [f"{f.column} {f.operator} {f.value}" for f in spec.filters]
            filter_label = f" where {', '.join(filter_parts)}"
            
        agg_label = f"{spec.aggregation.capitalize()} of " if spec.aggregation not in ["none", "count"] else ("Record Count of " if spec.aggregation == "count" else "Raw Datapoints of ")
        y_label = f"{spec.y_axis} " if spec.y_axis else ""
        x_label = f"by {spec.x_axis}"
        group_label = f" split by {spec.group_by}" if spec.group_by else ""
        
        interpretation = f"Parsed query (LLM) as: {agg_label}{y_label}{x_label}{group_label}{filter_label}."
        return NLQueryResponse(
            question=question,
            status="success",
            interpretation=interpretation,
            chart_spec=spec
        )
        
    # 3. Fallback to deterministic rules
    return deterministic_parse(question, df, column_stats)
