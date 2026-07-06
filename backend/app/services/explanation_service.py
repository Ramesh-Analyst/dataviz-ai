import pandas as pd
from typing import List, Dict, Any
from backend.app.schemas.schemas import NLQueryInsight, NLQueryChartSpec

def generate_insights(
    chart_spec: NLQueryChartSpec,
    datapoints: List[Dict[str, Any]]
) -> NLQueryInsight:
    """
    Generates factual summary and observations based on computed visualization datapoints.
    Stands on numerical calculations only and avoids hallucinated causal claims.
    """
    if not datapoints:
        return NLQueryInsight(
            summary="No data available to generate insights.",
            observations=[]
        )
        
    x_axis = chart_spec.x_axis
    y_axis = chart_spec.y_axis or "records"
    agg = chart_spec.aggregation
    
    # Convert points to DataFrame to perform clean metrics analysis
    df = pd.DataFrame(datapoints)
    
    if 'value' not in df.columns:
        return NLQueryInsight(
            summary=f"Analysis of {chart_spec.title}.",
            observations=["Aggregated data points could not be parsed for observations."]
        )
        
    df_clean = df.dropna(subset=['value'])
    if df_clean.empty:
        return NLQueryInsight(
            summary=f"Analysis of {chart_spec.title}.",
            observations=["No valid numeric values were returned for analysis."]
        )
        
    # Cast target value column to numeric
    df_clean['value'] = pd.to_numeric(df_clean['value'], errors='coerce')
    df_clean = df_clean.dropna(subset=['value'])
    
    if df_clean.empty:
        return NLQueryInsight(
            summary=f"Analysis of {chart_spec.title}.",
            observations=["No valid numeric values found in the query results."]
        )

    observations = []
    
    # 1. Extreme Value Analysis (Max & Min)
    total_val = float(df_clean['value'].sum())
    max_idx = df_clean['value'].idxmax()
    min_idx = df_clean['value'].idxmin()
    
    max_row = df_clean.loc[max_idx]
    min_row = df_clean.loc[min_idx]
    
    max_label = str(max_row[x_axis])
    max_val = float(max_row['value'])
    
    min_label = str(min_row[x_axis])
    min_val = float(min_row['value'])
    
    unique_cats_count = df_clean[x_axis].nunique()
    unique_vals_count = df_clean['value'].nunique()
    
    if unique_cats_count == 1:
        observations.append(f"Only one group '{max_label}' was analyzed, with a value of {max_val:,.2f}.")
    elif unique_vals_count == 1:
        observations.append(f"All analyzed categories have a uniform value of {max_val:,.2f}.")
    else:
        observations.append(f"The highest value is recorded for '{max_label}' at {max_val:,.2f}.")
        observations.append(f"The lowest value is recorded for '{min_label}' at {min_val:,.2f}.")
        
    # 2. Percentage Distribution Shares (Applicable to Count/Sum)
    if agg in ["count", "sum"] and total_val > 0:
        max_pct = (max_val / total_val) * 100
        if unique_cats_count > 1 and unique_vals_count > 1:
            observations.append(
                f"'{max_label}' represents the largest share at {max_pct:.1f}% of the total (total sum: {total_val:,.2f})."
            )
            
    # 3. Numeric / Temporal Trend Detection
    try:
        df_sorted = df_clean.copy()
        df_sorted[x_axis] = pd.to_numeric(df_sorted[x_axis], errors='raise')
        df_sorted = df_sorted.sort_values(by=x_axis)
        
        if len(df_sorted) >= 3:
            first_val = df_sorted.iloc[0]['value']
            last_val = df_sorted.iloc[-1]['value']
            
            if df_sorted[x_axis].std() > 0 and df_sorted['value'].std() > 0:
                corr = df_sorted[x_axis].corr(df_sorted['value'])
            else:
                corr = 0.0
            
            x_min = df_sorted.iloc[0][x_axis]
            x_max = df_sorted.iloc[-1][x_axis]
            
            if corr > 0.6:
                trend_desc = "shows a strong increasing trend"
            elif corr > 0.3:
                trend_desc = "shows a moderate increasing trend"
            elif corr < -0.6:
                trend_desc = "shows a strong decreasing trend"
            elif corr < -0.3:
                trend_desc = "shows a moderate decreasing trend"
            else:
                trend_desc = "remains relatively stable or fluctuates without a clear trend"
                
            observations.append(
                f"Between {x_min} and {x_max}, the value {trend_desc} (from {first_val:,.2f} to {last_val:,.2f})."
            )
    except Exception:
        pass
        
    # 4. Dimension Segmentation Insights
    if chart_spec.group_by and chart_spec.group_by in df_clean.columns:
        groups = df_clean[chart_spec.group_by].unique()
        observations.append(
            f"The data is segmented across {len(groups)} distinct categories in '{chart_spec.group_by}'."
        )
        
    # Construct descriptive summary header
    if agg == "count":
        summary = f"Summary of records count across {len(df_clean)} categories in '{x_axis}'."
    elif agg == "average":
        summary = f"Analysis of the average '{y_axis}' across '{x_axis}'."
    else:
        summary = f"Analysis of the {agg} '{y_axis}' across '{x_axis}'."
        
    return NLQueryInsight(
        summary=summary,
        observations=observations
    )
