import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import ReactECharts from 'echarts-for-react';
import { 
  ArrowLeft, Database, Rows, Columns, FileText, 
  ShieldCheck, AlertTriangle, Info, LineChart, BarChart3, 
  HelpCircle, Activity, Sparkles, TrendingUp, ChevronRight, Brain,
  Save, Trash2, PieChart, ScatterChart, RefreshCw, Star
} from 'lucide-react';

const DatasetOverview = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  
  // Data states
  const [datasetData, setDatasetData] = useState(null);
  const [profileData, setProfileData] = useState(null);
  
  // Loading & View states
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'quality' | 'visualizations' | 'ask'
  const [selectedColumn, setSelectedColumn] = useState(null);


  // --- VISUALIZATION BUILDER STATES ---
  const [recommendations, setRecommendations] = useState([]);
  const [savedCharts, setSavedCharts] = useState([]);
  const [builderChartType, setBuilderChartType] = useState('bar');
  const [builderXAxis, setBuilderXAxis] = useState('');
  const [builderYAxis, setBuilderYAxis] = useState('');
  const [builderAggregate, setBuilderAggregate] = useState('none');
  const [builderGroupBy, setBuilderGroupBy] = useState('');
  const [builderTitle, setBuilderTitle] = useState('');
  
  const [queryDatapoints, setQueryDatapoints] = useState([]);
  const [queryLoading, setQueryLoading] = useState(false);
  const [queryError, setQueryError] = useState(null);
  const [saveLoading, setSaveLoading] = useState(false);

  // --- NATURAL LANGUAGE ASK YOUR DATA STATES ---
  const [nlQuestion, setNlQuestion] = useState('');
  const [nlLoading, setNlLoading] = useState(false);
  const [nlResponse, setNlResponse] = useState(null);
  const [nlError, setNlError] = useState(null);

  useEffect(() => {
    fetchWorkspaceData();
  }, [id]);

  const fetchWorkspaceData = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch preview rows & basic metadata
      const previewRes = await api.get(`/api/datasets/${id}`);
      setDatasetData(previewRes.data);
      
      // 2. Fetch full statistical profiling
      const profileRes = await api.get(`/api/datasets/${id}/profile`);
      setProfileData(profileRes.data);

      // 3. Fetch Recommendations
      const recsRes = await api.get(`/api/datasets/${id}/visualizations/recommendations`);
      setRecommendations(recsRes.data);

      // 4. Fetch Saved Charts
      const savedRes = await api.get(`/api/datasets/${id}/visualizations`);
      setSavedCharts(savedRes.data);
      
      // Pre-populate builder defaults from metadata columns
      if (previewRes.data.metadata.columns.length > 0) {
        setBuilderXAxis(previewRes.data.metadata.columns[0].name);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to fetch workspace data. The file may be corrupt or access was denied.");
    } finally {
      setLoading(false);
    }
  };

  const getConfigurationError = () => {
    const columns = datasetData?.metadata?.columns || [];
    if (columns.length === 0) return null;
    
    if (!builderXAxis) return "Please select an X-Axis variable.";

    const xCol = columns.find(c => c.name === builderXAxis);
    const yCol = builderYAxis ? columns.find(c => c.name === builderYAxis) : null;
    const xType = xCol ? xCol.detected_type : null;
    const yType = yCol ? yCol.detected_type : null;

    if (builderChartType === 'scatter') {
      if (!builderYAxis) {
        return "Scatter plot requires both X-Axis and Y-Axis variables. Please select a Y-Axis variable.";
      }
      if (xType !== 'Numeric' || yType !== 'Numeric') {
        return "Scatter plot requires both X-Axis and Y-Axis variables to be Numeric.";
      }
    }
    
    if (builderChartType === 'histogram') {
      if (xType !== 'Numeric') {
        return "Histogram requires a Numeric column on the X-axis.";
      }
    }
    
    if (builderChartType === 'pie') {
      const allowedPieTypes = ["Categorical", "Boolean", "Identifier", "Geographic candidate"];
      if (xType && !allowedPieTypes.includes(xType)) {
        return "Pie chart requires a categorical, boolean, or identifier dimension on the X-axis.";
      }
    }
    
    if (builderChartType === 'line') {
      const allowedLineTypes = ["Date/time", "Numeric", "Identifier"];
      if (xType && !allowedLineTypes.includes(xType)) {
        return "Line chart requires an ordered variable (Date/time or Numeric) on the X-axis.";
      }
      if (builderYAxis && yType !== 'Numeric' && builderAggregate !== 'count') {
        return "Line chart measures on the Y-axis must be Numeric unless doing a Count aggregation.";
      }
    }

    // General Aggregate validation
    if (builderAggregate !== 'none' && builderAggregate !== 'count') {
      if (!builderYAxis) {
        return `Y-axis column is required for '${builderAggregate}' aggregation.`;
      }
    }

    return null;
  };

  const handleChartTypeChange = (newType) => {
    setBuilderChartType(newType);
    
    const columns = datasetData?.metadata?.columns || [];
    const numericCols = columns.filter(c => c.detected_type === 'Numeric');
    const categoricalCols = columns.filter(c => 
      ['Categorical', 'Boolean', 'Identifier', 'Geographic candidate'].includes(c.detected_type)
    );
    const orderedCols = columns.filter(c => 
      ['Date/time', 'Numeric', 'Identifier'].includes(c.detected_type)
    );
    
    if (newType === 'pie') {
      setBuilderYAxis('');
      setBuilderAggregate('count');
      setBuilderGroupBy('');
      const currentXCol = columns.find(c => c.name === builderXAxis);
      if (!currentXCol || !['Categorical', 'Boolean', 'Identifier', 'Geographic candidate'].includes(currentXCol.detected_type)) {
        if (categoricalCols.length > 0) {
          setBuilderXAxis(categoricalCols[0].name);
        }
      }
    } else if (newType === 'scatter') {
      setBuilderAggregate('none');
      setBuilderGroupBy('');
      
      let nextX = builderXAxis;
      const currentXCol = columns.find(c => c.name === builderXAxis);
      if (!currentXCol || currentXCol.detected_type !== 'Numeric') {
        if (numericCols.length > 0) {
          nextX = numericCols[0].name;
          setBuilderXAxis(nextX);
        }
      }
      
      const currentYCol = columns.find(c => c.name === builderYAxis);
      if (!currentYCol || currentYCol.detected_type !== 'Numeric' || builderYAxis === nextX) {
        const remainingNumeric = numericCols.filter(c => c.name !== nextX);
        if (remainingNumeric.length > 0) {
          setBuilderYAxis(remainingNumeric[0].name);
        } else if (numericCols.length > 0) {
          setBuilderYAxis(numericCols[0].name);
        } else {
          setBuilderYAxis('');
        }
      }
    } else if (newType === 'histogram') {
      setBuilderYAxis('');
      setBuilderAggregate('none');
      setBuilderGroupBy('');
      
      const currentXCol = columns.find(c => c.name === builderXAxis);
      if (!currentXCol || currentXCol.detected_type !== 'Numeric') {
        if (numericCols.length > 0) {
          setBuilderXAxis(numericCols[0].name);
        }
      }
    } else if (newType === 'line') {
      const currentXCol = columns.find(c => c.name === builderXAxis);
      if (!currentXCol || !['Date/time', 'Numeric', 'Identifier'].includes(currentXCol.detected_type)) {
        if (orderedCols.length > 0) {
          setBuilderXAxis(orderedCols[0].name);
        }
      }
    }
  };

  // Run dynamic Pandas aggregations on control changes
  useEffect(() => {
    if (activeTab === 'visualizations' && builderXAxis) {
      const configError = getConfigurationError();
      if (configError) {
        setQueryDatapoints([]);
        setQueryError(configError);
      } else {
        triggerQuery();
      }
    }
  }, [activeTab, builderChartType, builderXAxis, builderYAxis, builderAggregate, builderGroupBy]);

  const triggerQuery = async () => {
    const configError = getConfigurationError();
    if (configError) {
      setQueryDatapoints([]);
      setQueryError(configError);
      return;
    }

    setQueryLoading(true);
    setQueryError(null);
    try {
      const payload = {
        x_axis: builderXAxis,
        y_axis: builderYAxis || null,
        aggregate: builderAggregate,
        group_by: builderGroupBy || null,
        chart_type: builderChartType
      };
      
      const res = await api.post(`/api/datasets/${id}/visualizations/query`, payload);
      setQueryDatapoints(res.data.datapoints);
      
      // Generate default title if not manually customized
      const aggLabel = builderAggregate !== 'none' ? `${builderAggregate} of ` : '';
      const yLabel = builderYAxis ? `${builderYAxis} ` : 'records ';
      const groupLabel = builderGroupBy ? `by ${builderGroupBy}` : '';
      setBuilderTitle(`${aggLabel}${yLabel}by ${builderXAxis} ${groupLabel}`.trim());
    } catch (err) {
      console.error(err);
      setQueryError("Query compilation failed. Please verify selected data axis and aggregation matches.");
    } finally {
      setQueryLoading(false);
    }
  };


  // Apply AI Recommendation directly into Builder Controls
  const applyRecommendation = (rec) => {
    setBuilderChartType(rec.chart_type);
    setBuilderXAxis(rec.x_axis);
    setBuilderYAxis(rec.y_axis || '');
    setBuilderAggregate(rec.aggregate || 'none');
    setBuilderGroupBy(rec.group_by || '');
    setBuilderTitle(rec.title);
  };

  // Navigate to Dashboard or Auto-create if missing
  const handleNavigateDashboard = async () => {
    try {
      const response = await api.get(`/api/dashboards?dataset_id=${id}`);
      if (response.data.length > 0) {
        navigate(`/dashboards/${response.data[0].id}`);
      } else {
        const createRes = await api.post('/api/dashboards', {
          dataset_id: id,
          title: `Dashboard – ${metadata?.filename || 'Untitled'}`,
          description: `Auto-generated reporting workspace for ${metadata?.filename || 'dataset'}`
        });
        navigate(`/dashboards/${createRes.data.id}`);
      }
    } catch (err) {
      console.error(err);
      alert("Failed to resolve dynamic dashboard link.");
    }
  };

  // Save Configured Chart Template
  const handleSaveChart = async () => {
    if (!builderTitle.trim()) return;
    setSaveLoading(true);
    try {
      const payload = {
        title: builderTitle,
        chart_type: builderChartType,
        x_axis: builderXAxis,
        y_axis: builderYAxis || null,
        aggregate: builderAggregate,
        group_by: builderGroupBy || null
      };
      await api.post(`/api/datasets/${id}/visualizations`, payload);
      
      // Refresh list
      const savedRes = await api.get(`/api/datasets/${id}/visualizations`);
      setSavedCharts(savedRes.data);
    } catch (err) {
      console.error(err);
      alert("Failed to save chart visual template.");
    } finally {
      setSaveLoading(false);
    }
  };

  // Delete Saved Chart Template
  const handleDeleteChart = async (chartId) => {
    if (!window.confirm("Are you sure you want to delete this saved chart template?")) return;
    try {
      await api.delete(`/api/datasets/${id}/visualizations/${chartId}`);
      setSavedCharts(savedCharts.filter(c => c.id !== chartId));
    } catch (err) {
      console.error(err);
      alert("Failed to delete saved chart template.");
    }
  };

  // --- NATURAL LANGUAGE ASK YOUR DATA HANDLERS & HELPERS ---
  const handleAskQuestion = async (forcedQuestion = null) => {
    const queryStr = forcedQuestion || nlQuestion;
    if (!queryStr.trim()) return;
    setNlLoading(true);
    setNlError(null);
    setNlResponse(null);
    try {
      const res = await api.post(`/api/datasets/${id}/ask`, { question: queryStr });
      if (res.data.status === 'success') {
        setNlResponse(res.data);
      } else {
        setNlError(res.data);
      }
    } catch (err) {
      console.error(err);
      setNlError({
        status: 'error',
        clarification: {
          reason: "Server request failed. Please check network connection and try again.",
          suggested_columns: [],
          suggested_charts: []
        }
      });
    } finally {
      setNlLoading(false);
    }
  };

  const getSuggestionChips = () => {
    if (!metadata || !metadata.columns || metadata.columns.length === 0) return [];
    const cols = metadata.columns;
    const numericCols = cols.filter(c => c.detected_type === 'Numeric');
    const categoricalCols = cols.filter(c => c.detected_type === 'Categorical');
    const chips = [];
    
    const countCol = categoricalCols.length > 0 ? categoricalCols[0].name : cols[0].name;
    chips.push(`Show record count by ${countCol}`);
    
    const lowCardCol = cols.find(c => c.detected_type === 'Categorical' && c.unique_count <= 10);
    if (lowCardCol) {
      chips.push(`Show distribution of ${lowCardCol.name}`);
    } else if (categoricalCols.length > 1) {
      chips.push(`Show distribution of ${categoricalCols[1].name}`);
    }
    
    if (numericCols.length > 0) {
      const numCol = numericCols[0].name;
      chips.push(`Show average ${numCol} by ${countCol}`);
    }
    
    if (categoricalCols.length > 0 && cols.find(c => c.name === 'Year')) {
      chips.push(`Show record count by Year for Level 4`);
    } else {
      chips.push(`Compare record counts across ${countCol}`);
    }
    
    return chips;
  };

  const getNLChartOption = () => {
    if (!nlResponse || !nlResponse.chart_spec || !nlResponse.chart_data || nlResponse.chart_data.length === 0) return {};
    
    const spec = nlResponse.chart_spec;
    const data = nlResponse.chart_data;
    const xCol = spec.x_axis;
    const yCol = spec.y_axis;
    const chartType = spec.chart_type;
    const title = spec.title;
    const groupBy = spec.group_by;
    
    if (groupBy) {
      const xLabels = Array.from(new Set(data.map(d => String(d[xCol]))));
      const groupItems = Array.from(new Set(data.map(d => String(d[groupBy]))));
      
      const seriesList = groupItems.map(item => {
        const seriesData = xLabels.map(label => {
          const matchedRow = data.find(
            d => String(d[xCol]) === label && String(d[groupBy]) === item
          );
          return matchedRow ? matchedRow.value : 0;
        });

        return {
          name: item,
          type: chartType === 'scatter' ? 'scatter' : (chartType === 'histogram' ? 'bar' : chartType),
          data: seriesData
        };
      });

      return {
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis', backgroundColor: '#0d0f1a', borderColor: '#1e293b', textStyle: { color: '#e2e8f0' } },
        legend: { data: groupItems, textStyle: { color: '#94a3b8' }, top: '0%' },
        grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
        xAxis: { type: 'category', data: xLabels, axisLabel: { color: '#94a3b8' } },
        yAxis: { type: 'value', axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#0f1122' } } },
        series: seriesList
      };
    }
    
    const xData = data.map(d => String(d[xCol]));
    
    if (chartType === 'pie') {
      const pieData = data.map(d => ({
        name: String(d[xCol]),
        value: d.value
      }));
      
      return {
        backgroundColor: 'transparent',
        tooltip: { trigger: 'item', formatter: '{b}: <b>{c} ({d}%)</b>', backgroundColor: '#0d0f1a', borderColor: '#1e293b', textStyle: { color: '#e2e8f0' } },
        legend: { textStyle: { color: '#94a3b8' }, type: 'scroll', top: '0%' },
        series: [{
          name: title,
          type: 'pie',
          radius: '50%',
          data: pieData,
          emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' } }
        }]
      };
    }
    
    if (chartType === 'scatter') {
      if (!yCol) return {};
      const scatterData = data.map(d => [d[xCol], d[yCol]]);
      return {
        backgroundColor: 'transparent',
        tooltip: { trigger: 'item', backgroundColor: '#0d0f1a', borderColor: '#1e293b', textStyle: { color: '#e2e8f0' } },
        grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
        xAxis: { type: 'value', name: xCol, axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#0f1122' } } },
        yAxis: { type: 'value', name: yCol, axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#0f1122' } } },
        series: [{
          type: 'scatter',
          symbolSize: 10,
          data: scatterData,
          itemStyle: { color: '#4a57ed' }
        }]
      };
    }
    
    const yData = data.map(d => d.value);
    
    return {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', backgroundColor: '#0d0f1a', borderColor: '#1e293b', textStyle: { color: '#e2e8f0' } },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
      xAxis: { type: 'category', data: xData, axisLabel: { color: '#94a3b8' } },
      yAxis: { type: 'value', axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#0f1122' } } },
      series: [{
        name: title,
        type: chartType === 'histogram' ? 'bar' : chartType,
        data: yData,
        itemStyle: {
          color: (chartType === 'bar' || chartType === 'histogram') ? {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: '#4a57ed' },
              { offset: 1, color: '#2a3bbf' }
            ]
          } : '#4a57ed',
          borderRadius: (chartType === 'bar' || chartType === 'histogram') ? [4, 4, 0, 0] : 0
        }
      }]
    };
  };

  // Helper: Format bytes
  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getBadgeColors = (type) => {
    switch (type) {
      case 'Numeric': return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      case 'Categorical': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'Date/time': return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
      case 'Boolean': return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'Identifier': return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20';
      default: return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
    }
  };

  const getScoreRating = (score) => {
    if (score >= 90) return { label: 'Excellent', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' };
    if (score >= 75) return { label: 'Good', color: 'text-blue-400 bg-blue-500/10 border-blue-500/20' };
    if (score >= 50) return { label: 'Fair', color: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20' };
    return { label: 'Poor (Needs Cleaning)', color: 'text-red-400 bg-red-500/10 border-red-500/20' };
  };

  const getDeductionMaxPenalty = (issueName) => {
    switch (issueName) {
      case 'Missing Values': return 30;
      case 'Duplicate Rows': return 20;
      case 'Constant Columns': return 15;
      case 'Statistical Outliers': return 15;
      case 'Format Type Conflicts': return 20;
      default: return 30;
    }
  };


  // ECharts Builder Mapping Option
  const getBuilderChartOption = () => {
    if (!queryDatapoints || queryDatapoints.length === 0) return {};
    
    // Group By Pivot Logic
    if (builderGroupBy) {
      const xLabels = Array.from(new Set(queryDatapoints.map(d => String(d[builderXAxis]))));
      const groupItems = Array.from(new Set(queryDatapoints.map(d => String(d[builderGroupBy]))));
      
      const seriesList = groupItems.map(item => {
        const seriesData = xLabels.map(label => {
          const matchedRow = queryDatapoints.find(
            d => String(d[builderXAxis]) === label && String(d[builderGroupBy]) === item
          );
          return matchedRow ? (matchedRow.value !== undefined ? matchedRow.value : matchedRow.count) : 0;
        });

        return {
          name: item,
          type: builderChartType === 'scatter' ? 'scatter' : builderChartType,
          data: seriesData
        };
      });

      return {
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis', backgroundColor: '#0d0f1a', borderColor: '#1e293b', textStyle: { color: '#e2e8f0' } },
        legend: { data: groupItems, textStyle: { color: '#94a3b8' }, top: '0%' },
        grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
        xAxis: { type: 'category', data: xLabels, axisLabel: { color: '#94a3b8' } },
        yAxis: { type: 'value', axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#0f1122' } } },
        series: seriesList
      };
    }

    // Standard Non-Grouped mapping
    const xData = queryDatapoints.map(d => String(d[builderXAxis]));
    
    if (builderChartType === 'pie') {
      const pieData = queryDatapoints.map(d => ({
        name: String(d[builderXAxis]),
        value: d.value !== undefined ? d.value : d.count
      }));
      
      return {
        backgroundColor: 'transparent',
        tooltip: { trigger: 'item', formatter: '{b}: <b>{c} ({d}%)</b>', backgroundColor: '#0d0f1a', borderColor: '#1e293b', textStyle: { color: '#e2e8f0' } },
        legend: { textStyle: { color: '#94a3b8' }, type: 'scroll', top: '0%' },
        series: [{
          name: builderTitle,
          type: 'pie',
          radius: '50%',
          data: pieData,
          emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' } }
        }]
      };
    }

    if (builderChartType === 'scatter') {
      if (!builderYAxis) return {};
      const scatterData = queryDatapoints.map(d => [d[builderXAxis], d[builderYAxis]]);
      return {
        backgroundColor: 'transparent',
        tooltip: { trigger: 'item', backgroundColor: '#0d0f1a', borderColor: '#1e293b', textStyle: { color: '#e2e8f0' } },
        grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
        xAxis: { type: 'value', name: builderXAxis, axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#0f1122' } } },
        yAxis: { type: 'value', name: builderYAxis, axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#0f1122' } } },
        series: [{
          type: 'scatter',
          symbolSize: 10,
          data: scatterData,
          itemStyle: { color: '#4a57ed' }
        }]
      };
    }

    // Default Bar or Line
    const yData = queryDatapoints.map(d => (d.value !== undefined ? d.value : d.count));
    
    return {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', backgroundColor: '#0d0f1a', borderColor: '#1e293b', textStyle: { color: '#e2e8f0' } },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
      xAxis: { type: 'category', data: xData, axisLabel: { color: '#94a3b8' } },
      yAxis: { type: 'value', axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#0f1122' } } },
      series: [{
        name: builderTitle,
        type: builderChartType,
        data: yData,
        itemStyle: {
          color: builderChartType === 'bar' ? {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: '#4a57ed' },
              { offset: 1, color: '#2a3bbf' }
            ]
          } : '#4a57ed',
          borderRadius: builderChartType === 'bar' ? [4, 4, 0, 0] : 0
        }
      }]
    };
  };

  // Static chart setups for overview dashboard
  const getMissingnessChartOption = () => {
    if (!profileData) return {};
    const cols = Object.keys(profileData.missingness);
    const data = cols.map(c => profileData.missingness[c].missing_percentage);

    return {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', formatter: '{b}: {c}% missing', backgroundColor: '#0d0f1a', borderColor: '#1e293b', textStyle: { color: '#e2e8f0' } },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
      xAxis: { type: 'category', data: cols, axisLabel: { color: '#94a3b8', fontSize: 10, rotate: 30 }, axisLine: { lineStyle: { color: '#1e293b' } } },
      yAxis: { type: 'value', max: 100, axisLabel: { color: '#94a3b8', formatter: '{value}%' }, splitLine: { lineStyle: { color: '#0f1122' } } },
      series: [{
        data: data,
        type: 'bar',
        barWidth: '40%',
        itemStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: '#707ff4' },
              { offset: 1, color: '#4a57ed' }
            ]
          },
          borderRadius: [4, 4, 0, 0]
        }
      }]
    };
  };

  const getCorrelationChartOption = () => {
    if (!profileData || !profileData.correlations || Object.keys(profileData.correlations).length === 0) return {};
    const cols = Object.keys(profileData.correlations);
    const data = [];
    
    cols.forEach((colX, i) => {
      cols.forEach((colY, j) => {
        const val = profileData.correlations[colX][colY];
        data.push([i, j, val !== null ? parseFloat(val.toFixed(2)) : 0]);
      });
    });

    return {
      backgroundColor: 'transparent',
      tooltip: {
        position: 'top',
        formatter: (params) => `${cols[params.data[0]]} vs ${cols[params.data[1]]}: <b>${params.data[2]}</b>`,
        backgroundColor: '#0d0f1a',
        borderColor: '#1e293b',
        textStyle: { color: '#e2e8f0' }
      },
      grid: { left: '3%', right: '4%', bottom: '15%', top: '5%', containLabel: true },
      xAxis: { type: 'category', data: cols, axisLabel: { color: '#94a3b8', fontSize: 10, rotate: 30 } },
      yAxis: { type: 'category', data: cols, axisLabel: { color: '#94a3b8', fontSize: 10 } },
      visualMap: {
        min: -1, max: 1, calculable: true, orient: 'horizontal', left: 'center', bottom: '0%',
        inRange: { color: ['#ef4444', '#f8fafc', '#4a57ed'] },
        textStyle: { color: '#94a3b8', fontSize: 10 }
      },
      series: [{
        name: 'Pearson Correlation',
        type: 'heatmap',
        data: data,
        label: { show: true, formatter: (params) => params.data[2], color: '#0f172a', fontSize: 9 }
      }]
    };
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#08090f]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-brand-500/20 border-t-brand-500 rounded-full animate-spin" />
          <span className="text-xs text-slate-500">Processing dataset profiling analytics...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-[#08090f]">
        <div className="glass-panel p-8 rounded-2xl text-center max-w-md border border-red-500/10">
          <h3 className="text-lg font-bold text-red-400 mb-2">Workspace Loading Failed</h3>
          <p className="text-xs text-slate-500 mb-6">{error}</p>
          <button 
            onClick={() => navigate('/dashboard')}
            className="px-4 py-2.5 bg-slate-900 border border-slate-800 text-xs font-semibold text-slate-200 rounded-xl transition cursor-pointer"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const { metadata } = datasetData;
  const { quality_report } = profileData;
  const scoreRating = getScoreRating(quality_report.score);

  return (
    <div className="flex min-h-screen bg-[#08090f]">
      
      {/* Left Sidebar Workspace Panel */}
      <aside className="w-64 border-r border-slate-900 bg-slate-950/40 shrink-0 hidden md:flex flex-col justify-between">
        <div>
          <div className="p-6 border-b border-slate-900">
            <button 
              onClick={() => navigate('/dashboard')}
              className="flex items-center gap-2 text-xs text-slate-400 hover:text-white transition cursor-pointer mb-5"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Dashboard</span>
            </button>
            
            <div className="flex items-center gap-2 truncate">
              <Database className="w-4 h-4 text-brand-400 shrink-0" />
              <span className="text-sm font-bold text-slate-200 truncate" title={metadata.filename}>
                {metadata.filename}
              </span>
            </div>
          </div>

          <nav className="p-4 space-y-1.5">
            <button
              onClick={() => setActiveTab('overview')}
              className={`w-full flex items-center gap-2.5 px-4 py-3 rounded-xl text-xs font-semibold transition cursor-pointer ${
                activeTab === 'overview' 
                  ? 'bg-brand-600/10 text-brand-400 border-l-2 border-brand-500' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/30'
              }`}
            >
              <Database className="w-4 h-4" />
              <span>Dataset Overview</span>
            </button>

            <button
              onClick={() => setActiveTab('quality')}
              className={`w-full flex items-center gap-2.5 px-4 py-3 rounded-xl text-xs font-semibold transition cursor-pointer ${
                activeTab === 'quality' 
                  ? 'bg-brand-600/10 text-brand-400 border-l-2 border-brand-500' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/30'
              }`}
            >
              <Activity className="w-4 h-4" />
              <span>Data Quality</span>
              <span className="ml-auto text-[10px] bg-slate-900 px-1.5 py-0.5 rounded text-slate-400">
                {quality_report.score}
              </span>
            </button>

            <button
              onClick={() => setActiveTab('visualizations')}
              className={`w-full flex items-center gap-2.5 px-4 py-3 rounded-xl text-xs font-semibold transition cursor-pointer ${
                activeTab === 'visualizations' 
                  ? 'bg-brand-600/10 text-brand-400 border-l-2 border-brand-500' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/30'
              }`}
            >
              <BarChart3 className="w-4 h-4" />
              <span>Smart Visualizations</span>
            </button>

            <button
              onClick={() => setActiveTab('ask')}
              className={`w-full flex items-center gap-2.5 px-4 py-3 rounded-xl text-xs font-semibold transition cursor-pointer ${
                activeTab === 'ask' 
                  ? 'bg-brand-600/10 text-brand-400 border-l-2 border-brand-500' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/30'
              }`}
            >
              <Sparkles className="w-4 h-4 text-purple-400" />
              <span>Ask Your Data</span>
            </button>
            
            {/* Analytics Modules */}
            <div className="pt-4 mt-4 border-t border-slate-900/50">
              <span className="px-4 text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-2">Analytics & Reporting</span>
              
              <button 
                onClick={handleNavigateDashboard}
                className="w-full flex items-center gap-2.5 px-4 py-3 rounded-xl text-xs font-semibold transition cursor-pointer text-slate-400 hover:text-slate-200 hover:bg-slate-900/30"
              >
                <TrendingUp className="w-4 h-4 text-brand-400" />
                <span>Interactive Dashboard</span>
              </button>

              <button 
                onClick={() => navigate(`/datasets/${id}/insights`)}
                className="w-full flex items-center gap-2.5 px-4 py-3 rounded-xl text-xs font-semibold transition cursor-pointer text-slate-400 hover:text-slate-200 hover:bg-slate-900/30"
              >
                <Sparkles className="w-4 h-4 text-purple-400" />
                <span>Statistical Insights</span>
              </button>
            </div>
          </nav>
        </div>

        <div className="p-6 border-t border-slate-900 text-[10px] text-slate-600">
          <span>Project: DataViz AI v1.0</span>
        </div>
      </aside>

      {/* Workspace Viewport Area */}
      <main className="flex-1 overflow-y-auto max-h-screen py-8 px-6">
        
        {/* TAB 1: DATASET OVERVIEW */}
        {activeTab === 'overview' && (
          <div className="space-y-8 animate-fadeIn">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-2xl font-bold text-slate-100">Dataset Overview</h2>
                <p className="text-xs text-slate-500 mt-1">Ingested schema distributions and preview records</p>
              </div>
            </div>

            {/* KPI Cards Grid */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="glass-card p-4 rounded-xl flex items-center gap-3">
                <div className="p-2.5 bg-slate-900/80 border border-slate-800 rounded-lg"><Rows className="w-5 h-5 text-blue-400" /></div>
                <div>
                  <div className="text-xs text-slate-500">Rows Count</div>
                  <div className="text-lg font-bold text-slate-200">{metadata.row_count.toLocaleString()}</div>
                </div>
              </div>
              <div className="glass-card p-4 rounded-xl flex items-center gap-3">
                <div className="p-2.5 bg-slate-900/80 border border-slate-800 rounded-lg"><Columns className="w-5 h-5 text-emerald-400" /></div>
                <div>
                  <div className="text-xs text-slate-500">Columns Count</div>
                  <div className="text-lg font-bold text-slate-200">{metadata.col_count.toLocaleString()}</div>
                </div>
              </div>
              <div className="glass-card p-4 rounded-xl flex items-center gap-3">
                <div className="p-2.5 bg-slate-900/80 border border-slate-800 rounded-lg"><FileText className="w-5 h-5 text-purple-400" /></div>
                <div>
                  <div className="text-xs text-slate-500">File Storage Size</div>
                  <div className="text-lg font-bold text-slate-200">{formatBytes(metadata.file_size)}</div>
                </div>
              </div>
              <div className="glass-card p-4 rounded-xl flex items-center gap-3">
                <div className="p-2.5 bg-slate-900/80 border border-slate-800 rounded-lg"><Activity className="w-5 h-5 text-yellow-400" /></div>
                <div>
                  <div className="text-xs text-slate-500">Quality Score</div>
                  <div className="text-lg font-bold text-slate-200">{quality_report.score} / 100</div>
                </div>
              </div>
            </div>

            {/* Column Cards */}
            <section className="glass-panel p-6 rounded-2xl">
              <div className="mb-4 font-bold text-slate-200">Interactive Column Profiles</div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.values(profileData.column_stats).map((col, idx) => (
                  <div 
                    key={idx}
                    onClick={() => setSelectedColumn(col)}
                    className="p-4 rounded-xl bg-slate-950/40 border border-slate-900 hover:border-brand-500/30 hover:bg-slate-900/10 cursor-pointer transition-all"
                  >
                    <div className="flex justify-between items-start gap-2">
                      <span className="text-sm font-semibold text-slate-200 truncate">{col.name}</span>
                      <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold border ${getBadgeColors(col.detected_type)}`}>
                        {col.detected_type}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 mt-4 pt-3 border-t border-slate-900/80 text-xs">
                      <div>
                        <span className="text-slate-500 block">Unique Values</span>
                        <span className="text-slate-300 font-medium">{col.unique_count.toLocaleString()}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Missing Cells</span>
                        <span className="text-slate-300 font-medium">{col.missing_count}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* Charts Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="glass-panel p-6 rounded-2xl flex flex-col h-96">
                <h3 className="text-sm font-bold text-slate-200 mb-2">Null / Missing Rates per Column</h3>
                <div className="flex-1 min-h-0"><ReactECharts option={getMissingnessChartOption()} style={{ height: '100%', width: '100%' }} /></div>
              </div>
              <div className="glass-panel p-6 rounded-2xl flex flex-col h-96">
                <h3 className="text-sm font-bold text-slate-200 mb-2">Pearson Correlation Heatmap</h3>
                <div className="flex-1 min-h-0">
                  {Object.keys(profileData.correlations).length >= 2 ? (
                    <ReactECharts option={getCorrelationChartOption()} style={{ height: '100%', width: '100%' }} />
                  ) : (
                    <div className="h-full flex items-center justify-center text-xs text-slate-500">Heatmap requires 2+ numerical variables.</div>
                  )}
                </div>
              </div>
            </div>

            {/* Ingested Records Preview */}
            <section className="glass-panel p-6 rounded-2xl">
              <h3 className="text-base font-bold text-slate-200 mb-3">Ingested Records Preview</h3>
              <div className="overflow-x-auto border border-slate-900 rounded-xl">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-950/80 text-slate-400 font-semibold border-b border-slate-900">
                      <th className="py-3.5 px-4 w-12 border-r border-slate-900 text-center">#</th>
                      {metadata.columns.map((col, idx) => (
                        <th key={idx} className="py-3.5 px-4 font-semibold text-slate-300 border-r border-slate-900 last:border-0">{col.name}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {datasetData.preview_rows.map((row, rowIdx) => (
                      <tr key={rowIdx} className="hover:bg-slate-900/20 border-b border-slate-900 last:border-0">
                        <td className="py-3 px-4 text-slate-500 text-center border-r border-slate-900 bg-slate-950/20 font-mono">{rowIdx + 1}</td>
                        {metadata.columns.map((col, colIdx) => (
                          <td key={colIdx} className="py-3 px-4 text-slate-300 border-r border-slate-900 last:border-0 truncate max-w-[200px]">
                            {row[col.name] === null || row[col.name] === undefined ? <span className="text-slate-600 italic">null</span> : String(row[col.name])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        )}

        {/* TAB 2: DATA QUALITY REPORT */}
        {activeTab === 'quality' && (
          <div className="space-y-8 animate-fadeIn">
            <div>
              <h2 className="text-2xl font-bold text-slate-100">Data Quality Audit</h2>
              <p className="text-xs text-slate-500 mt-1">Transparent grading and automated warnings logs</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="glass-panel p-6 rounded-2xl flex flex-col items-center justify-center border-l-4 border-brand-500">
                <div className="relative w-36 h-36 flex items-center justify-center mb-4">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle cx="72" cy="72" r="60" stroke="#0f1122" strokeWidth="8" fill="transparent" />
                    <circle cx="72" cy="72" r="60" stroke="#4a57ed" strokeWidth="8" fill="transparent" strokeDasharray="377" strokeDashoffset={377 - (377 * quality_report.score) / 100} strokeLinecap="round" />
                  </svg>
                  <div className="absolute flex flex-col items-center">
                    <span className="text-3xl font-extrabold text-slate-100">{quality_report.score}</span>
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Quality Index</span>
                  </div>
                </div>
                <div className={`px-3 py-1 rounded-full text-xs font-bold border ${scoreRating.color}`}>Rating: {scoreRating.label}</div>
              </div>

              <div className="glass-panel p-6 rounded-2xl lg:col-span-2 space-y-4">
                <h3 className="text-sm font-bold text-slate-200">Deductions Breakdown</h3>
                <div className="space-y-3.5">
                  {quality_report.deductions.length === 0 ? (
                    <div className="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-4 py-3.5 rounded-xl">
                      <ShieldCheck className="w-4 h-4 shrink-0" />
                      <span>Perfect Score! No quality defects identified.</span>
                    </div>
                  ) : (
                    quality_report.deductions.map((ded, idx) => (
                      <div key={idx} className="space-y-1">
                        <div className="flex justify-between items-center text-xs">
                          <span className="font-semibold text-slate-300">{ded.issue}</span>
                          <span className="text-red-400 font-bold">-{ded.deduction} pts</span>
                        </div>
                        <div className="w-full bg-slate-950 rounded-full h-1.5 overflow-hidden">
                          <div className="bg-red-500 h-1.5 rounded-full" style={{ width: `${(ded.deduction / getDeductionMaxPenalty(ded.issue)) * 100}%` }} />
                        </div>
                        <span className="text-[10px] text-slate-500 block">{ded.explanation}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>

            <section className="glass-panel p-6 rounded-2xl">
              <h3 className="text-sm font-bold text-slate-200 mb-4">Diagnostics Warnings log</h3>
              <div className="space-y-3">
                {quality_report.issues_list.length === 0 ? (
                  <div className="text-center py-6 text-xs text-slate-500">No warnings logged. Dataset ready for visual analysis.</div>
                ) : (
                  quality_report.issues_list.map((issue, idx) => (
                    <div key={idx} className={`p-4 rounded-xl flex items-start gap-3 border ${issue.severity === 'warning' ? 'bg-yellow-500/5 border-yellow-500/10 text-yellow-300/90' : 'bg-blue-500/5 border-blue-500/10 text-blue-300/90'}`}>
                      {issue.severity === 'warning' ? <AlertTriangle className="w-4.5 h-4.5 text-yellow-400 shrink-0" /> : <Info className="w-4.5 h-4.5 text-blue-400 shrink-0" />}
                      <div className="text-xs">
                        <span className="font-bold text-[9px] mr-2 px-1.5 py-0.5 rounded bg-slate-900 text-slate-400">{issue.severity}</span>
                        <span>{issue.message}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </section>
          </div>
        )}

        {/* TAB 3: SMART VISUALIZATIONS BUILDER */}
        {activeTab === 'visualizations' && (
          <div className="space-y-8 animate-fadeIn">
            <div>
              <h2 className="text-2xl font-bold text-slate-100">Smart Visualizations</h2>
              <p className="text-xs text-slate-500 mt-1">AI-assisted recommendations and custom aggregation plot builder</p>
            </div>

            {/* AI Recommendation Cards Header */}
            <section className="glass-panel p-6 rounded-2xl">
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="w-4.5 h-4.5 text-brand-400" />
                <h3 className="text-sm font-bold text-slate-200">Recommended Visualizations</h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {recommendations.map((rec, idx) => (
                  <div 
                    key={idx}
                    onClick={() => applyRecommendation(rec)}
                    className="p-4 rounded-xl border border-slate-900 bg-slate-950/40 hover:bg-slate-900/10 hover:border-brand-500/30 transition-all cursor-pointer flex flex-col justify-between group"
                  >
                    <div>
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-xs font-bold text-brand-400 group-hover:text-brand-300 uppercase">{rec.chart_type}</span>
                        <Star className="w-3.5 h-3.5 text-yellow-400/40 group-hover:text-yellow-400 transition" />
                      </div>
                      <h4 className="text-xs font-bold text-slate-200 group-hover:text-white transition line-clamp-1">{rec.title}</h4>
                      <p className="text-[10px] text-slate-500 mt-2 leading-relaxed">{rec.reason}</p>
                    </div>
                    <div className="text-[10px] text-slate-400 mt-4 flex items-center gap-1 group-hover:text-brand-400 transition">
                      <span>Apply configuration</span>
                      <ChevronRight className="w-3 h-3" />
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* Interactive Builder Workspace */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* Controls Column */}
              <div className="glass-panel p-6 rounded-2xl space-y-4">
                <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">Builder Controls</h3>
                
                <div className="space-y-3.5 text-xs">
                  {/* Chart type */}
                  <div className="space-y-1">
                    <label className="text-slate-400 block font-medium">Chart Type</label>
                    <select 
                      value={builderChartType} 
                      onChange={(e) => handleChartTypeChange(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-900 rounded-xl px-3.5 py-2 text-slate-200 font-semibold focus:outline-none focus:border-brand-500"
                    >
                      <option value="bar">Bar Chart</option>
                      <option value="line">Line Chart</option>
                      <option value="scatter">Scatter Plot</option>
                      <option value="pie">Pie Chart</option>
                    </select>
                  </div>

                  {/* X-axis */}
                  <div className="space-y-1">
                    <label className="text-slate-400 block font-medium">X-Axis Variable</label>
                    <select 
                      value={builderXAxis} 
                      onChange={(e) => setBuilderXAxis(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-900 rounded-xl px-3.5 py-2 text-slate-200 font-semibold focus:outline-none focus:border-brand-500"
                    >
                      {metadata.columns.map((col, idx) => (
                        <option key={idx} value={col.name}>{col.name}</option>
                      ))}
                    </select>
                  </div>

                  {/* Y-axis */}
                  <div className="space-y-1">
                    <label className="text-slate-400 block font-medium">Y-Axis Variable (Values)</label>
                    <select 
                      value={builderYAxis} 
                      onChange={(e) => setBuilderYAxis(e.target.value)}
                      disabled={builderChartType === 'pie'}
                      className="w-full bg-slate-950 border border-slate-900 rounded-xl px-3.5 py-2 text-slate-200 font-semibold focus:outline-none focus:border-brand-500 disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <option value="">None (Occurrence Counts)</option>
                      {metadata.columns
                        .filter(col => col.detected_type === 'Numeric')
                        .map((col, idx) => (
                          <option key={idx} value={col.name}>{col.name}</option>
                        ))
                      }
                    </select>
                  </div>

                  {/* Aggregate */}
                  <div className="space-y-1">
                    <label className="text-slate-400 block font-medium">Arithmetic Aggregation</label>
                    <select 
                      value={builderAggregate} 
                      onChange={(e) => setBuilderAggregate(e.target.value)}
                      disabled={builderChartType === 'scatter'}
                      className="w-full bg-slate-950 border border-slate-900 rounded-xl px-3.5 py-2 text-slate-200 font-semibold focus:outline-none focus:border-brand-500 disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <option value="none">None (Raw Rows)</option>
                      <option value="sum">Sum</option>
                      <option value="average">Average</option>
                      <option value="min">Minimum</option>
                      <option value="max">Maximum</option>
                      <option value="count">Count Instances</option>
                    </select>
                  </div>

                  {/* Group By */}
                  <div className="space-y-1">
                    <label className="text-slate-400 block font-medium">Group / Color By</label>
                    <select 
                      value={builderGroupBy} 
                      onChange={(e) => setBuilderGroupBy(e.target.value)}
                      disabled={builderChartType === 'pie' || builderChartType === 'scatter'}
                      className="w-full bg-slate-950 border border-slate-900 rounded-xl px-3.5 py-2 text-slate-200 font-semibold focus:outline-none focus:border-brand-500 disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <option value="">None</option>
                      {metadata.columns
                        .filter(col => col.detected_type === 'Categorical' || col.detected_type === 'Numeric')
                        .map((col, idx) => (
                          <option key={idx} value={col.name}>{col.name}</option>
                        ))
                      }
                    </select>
                  </div>

                  {/* Save Configuration Title */}
                  <div className="space-y-1 pt-4 border-t border-slate-900/60">
                    <label className="text-slate-400 block font-medium">Visualization Title</label>
                    <input 
                      type="text"
                      value={builderTitle}
                      onChange={(e) => setBuilderTitle(e.target.value)}
                      placeholder="e.g. Sales Performance"
                      className="w-full bg-slate-950 border border-slate-900 rounded-xl px-3.5 py-2 text-slate-200 font-semibold focus:outline-none focus:border-brand-500"
                    />
                  </div>

                  <button
                    onClick={handleSaveChart}
                    disabled={saveLoading || !builderTitle.trim()}
                    className="w-full flex items-center justify-center gap-2 py-3 bg-brand-600 hover:bg-brand-500 disabled:bg-slate-800 disabled:text-slate-500 text-white font-bold rounded-xl transition cursor-pointer text-xs disabled:cursor-not-allowed mt-2"
                  >
                    <Save className="w-4 h-4" />
                    <span>{saveLoading ? 'Saving Visual...' : 'Save to Dashboard'}</span>
                  </button>

                </div>
              </div>

              {/* Chart Rendering Column */}
              <div className="glass-panel p-6 rounded-2xl lg:col-span-2 flex flex-col h-[480px]">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">{builderTitle || 'Interactive Visualizer'}</h3>
                  {queryLoading && <RefreshCw className="w-3.5 h-3.5 text-slate-500 animate-spin" />}
                </div>

                <div className="flex-1 min-h-0 relative">
                  {queryError ? (
                    <div className="absolute inset-0 flex items-center justify-center text-xs text-red-400/90 text-center px-6">{queryError}</div>
                  ) : queryDatapoints.length === 0 ? (
                    <div className="absolute inset-0 flex items-center justify-center text-xs text-slate-500">No chart datapoints. Change options to generate plot.</div>
                  ) : (
                    <ReactECharts 
                      option={getBuilderChartOption()} 
                      style={{ height: '100%', width: '100%' }}
                      key={`${builderChartType}-${builderXAxis}-${builderYAxis}-${builderAggregate}-${builderGroupBy}-${queryDatapoints.length}`}
                    />
                  )}
                </div>
              </div>

            </div>

            {/* List Saved Visualizations */}
            <section className="glass-panel p-6 rounded-2xl">
              <h3 className="text-sm font-bold text-slate-200 mb-4">Saved Visualizations Templates</h3>
              
              {savedCharts.length === 0 ? (
                <div className="text-center py-6 text-xs text-slate-500">No custom chart templates saved yet. Configure variables above and click "Save to Dashboard".</div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {savedCharts.map((chart, idx) => (
                    <div key={idx} className="p-4 rounded-xl border border-slate-900 bg-slate-950/40 flex justify-between items-start">
                      <div>
                        <span className="text-[9px] uppercase tracking-wider font-bold text-brand-400">{chart.chart_type}</span>
                        <h4 className="text-xs font-bold text-slate-200 mt-1">{chart.title}</h4>
                        <div className="flex flex-wrap gap-x-2 gap-y-1 mt-2 text-[10px] text-slate-500">
                          <span>X: {chart.x_axis}</span>
                          {chart.y_axis && <span>Y: {chart.y_axis}</span>}
                          {chart.aggregate !== 'none' && <span>({chart.aggregate})</span>}
                        </div>
                      </div>
                      
                      <button
                        onClick={() => handleDeleteChart(chart.id)}
                        className="text-red-400 hover:text-red-300 p-1.5 bg-slate-900/60 rounded-lg border border-slate-800 transition cursor-pointer"
                        title="Delete template"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </section>

          </div>
        )}

        {/* TAB 4: ASK YOUR DATA */}
        {activeTab === 'ask' && (
          <div className="space-y-8 animate-fadeIn">
            <div>
              <h2 className="text-2xl font-bold text-slate-100">Ask Your Data</h2>
            </div>

            {/* Input Bar Section */}
            <section className="glass-panel p-6 rounded-2xl space-y-4">
              <div className="flex gap-3">
                <div className="flex-1 relative">
                  <input
                    type="text"
                    value={nlQuestion}
                    onChange={(e) => setNlQuestion(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAskQuestion()}
                    placeholder="e.g. Show record count by Year"
                    className="w-full bg-slate-950 border border-slate-900 rounded-xl pl-4 pr-24 py-3.5 text-xs font-semibold text-slate-200 focus:outline-none focus:border-brand-500 placeholder-slate-600"
                    disabled={nlLoading}
                  />
                  <div className="absolute right-2 top-2 flex gap-1.5">
                    {nlQuestion && (
                      <button
                        onClick={() => {
                          setNlQuestion('');
                          setNlResponse(null);
                          setNlError(null);
                        }}
                        className="px-2.5 py-1.5 bg-slate-900 hover:bg-slate-800 text-[10px] font-bold text-slate-400 rounded-lg transition cursor-pointer"
                      >
                        Clear
                      </button>
                    )}
                    <button
                      onClick={() => handleAskQuestion()}
                      disabled={nlLoading || !nlQuestion.trim()}
                      className="px-4 py-1.5 bg-brand-600 hover:bg-brand-500 disabled:bg-slate-900 disabled:text-slate-600 text-xs font-bold text-white rounded-lg transition cursor-pointer disabled:cursor-not-allowed"
                    >
                      {nlLoading ? 'Analyzing...' : 'Ask'}
                    </button>
                  </div>
                </div>
              </div>

              {/* Dynamic suggestion chips */}
              <div className="space-y-2">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Suggested Questions</span>
                <div className="flex flex-wrap gap-2">
                  {getSuggestionChips().map((chip, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setNlQuestion(chip);
                        handleAskQuestion(chip);
                      }}
                      disabled={nlLoading}
                      className="px-3.5 py-2 bg-slate-950/60 hover:bg-brand-900/10 border border-slate-900 hover:border-brand-500/20 rounded-xl text-left text-xs font-medium text-slate-400 hover:text-brand-300 transition cursor-pointer"
                    >
                      {chip}
                    </button>
                  ))}
                </div>
              </div>
            </section>

            {/* Error or Validation or Clarification State */}
            {nlError && (
              <div className="space-y-4 animate-fadeIn">
                <div className="glass-panel p-6 border-l-4 border-yellow-500 rounded-2xl bg-yellow-500/5 text-yellow-200">
                  <div className="flex gap-3">
                    <AlertTriangle className="w-5 h-5 text-yellow-400 shrink-0 mt-0.5" />
                    <div className="space-y-1">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-yellow-400">Interpretation Flagged</h4>
                      <p className="text-xs text-slate-300 font-medium leading-relaxed">
                        {nlError.clarification?.reason || "I'm not sure how to visualize that question. Could you clarify?"}
                      </p>
                    </div>
                  </div>
                </div>

                {nlError.clarification && (nlError.clarification.suggested_columns?.length > 0 || nlError.clarification.suggested_charts?.length > 0) && (
                  <div className="glass-panel p-6 rounded-2xl space-y-4">
                    <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">Suggested refinements</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
                      {nlError.clarification.suggested_columns?.length > 0 && (
                        <div className="space-y-2">
                          <span className="text-slate-500 block font-medium">Try referencing these columns:</span>
                          <div className="flex flex-wrap gap-1.5">
                            {nlError.clarification.suggested_columns.map((col, idx) => (
                              <button
                                key={idx}
                                onClick={() => {
                                  const text = `Show record count by ${col}`;
                                  setNlQuestion(text);
                                  handleAskQuestion(text);
                                }}
                                className="px-2.5 py-1.5 bg-slate-900 border border-slate-800 text-slate-300 rounded-lg hover:border-brand-500/30 transition cursor-pointer"
                              >
                                {col}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                      {nlError.clarification.suggested_charts?.length > 0 && (
                        <div className="space-y-2">
                          <span className="text-slate-500 block font-medium">Try these chart types:</span>
                          <div className="flex flex-wrap gap-1.5">
                            {nlError.clarification.suggested_charts.map((ct, idx) => (
                              <span
                                key={idx}
                                className="px-2.5 py-1.5 bg-slate-900 border border-slate-800 text-slate-300 rounded-lg uppercase tracking-wider font-semibold text-[9px]"
                              >
                                {ct}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Success Results State */}
            {nlResponse && nlResponse.chart_spec && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fadeIn">
                
                {/* Visual rendering panel */}
                <div className="glass-panel p-6 rounded-2xl lg:col-span-2 flex flex-col h-[480px]">
                  <div className="flex justify-between items-center mb-4">
                    <div>
                      <span className="text-[10px] uppercase tracking-wider font-bold text-brand-400">
                        {nlResponse.chart_spec.chart_type} • {nlResponse.chart_spec.aggregation}
                      </span>
                      <h3 className="text-sm font-bold text-slate-200 mt-1">{nlResponse.chart_spec.title}</h3>
                    </div>
                    {nlResponse.interpretation && (
                      <span className="text-[10px] bg-slate-900 border border-slate-800 text-slate-400 px-3 py-1 rounded-lg">
                        {nlResponse.interpretation}
                      </span>
                    )}
                  </div>

                  <div className="flex-1 min-h-0 relative">
                    {nlResponse.chart_data?.length === 0 ? (
                      <div className="absolute inset-0 flex items-center justify-center text-xs text-slate-500">
                        The compiled aggregation returned no records.
                      </div>
                    ) : (
                      <ReactECharts
                        option={getNLChartOption()}
                        style={{ height: '100%', width: '100%' }}
                        key={`${nlResponse.chart_spec.chart_type}-${nlResponse.chart_spec.x_axis}-${nlResponse.chart_spec.y_axis}-${nlResponse.chart_spec.aggregation}-${nlResponse.chart_data.length}`}
                      />
                    )}
                  </div>
                </div>

                {/* Explanation narrative panel */}
                <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between">
                  <div className="space-y-5">
                    <div className="flex items-center gap-2 mb-2">
                      <Sparkles className="w-5 h-5 text-purple-400" />
                      <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">Factual Summary</h3>
                    </div>

                    <p className="text-xs text-slate-300 font-medium leading-relaxed bg-slate-950/40 p-4 rounded-xl border border-slate-900">
                      {nlResponse.insight?.summary || "No summary available."}
                    </p>

                    <div className="space-y-3">
                      <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Observed Takeaways</span>
                      <div className="space-y-2">
                        {nlResponse.insight?.observations?.map((obs, idx) => (
                          <div key={idx} className="p-3 bg-slate-900/40 border border-slate-950 rounded-xl text-xs text-slate-400 leading-normal flex gap-2">
                            <span className="text-brand-400 font-bold">•</span>
                            <span>{obs}</span>
                          </div>
                        ))}
                        {(!nlResponse.insight?.observations || nlResponse.insight.observations.length === 0) && (
                          <div className="text-xs text-slate-500 italic">No specific observations compiled.</div>
                        )}
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={async () => {
                      try {
                        const payload = {
                          title: nlResponse.chart_spec.title,
                          chart_type: nlResponse.chart_spec.chart_type,
                          x_axis: nlResponse.chart_spec.x_axis,
                          y_axis: nlResponse.chart_spec.y_axis || null,
                          aggregate: nlResponse.chart_spec.aggregation,
                          group_by: nlResponse.chart_spec.group_by || null
                        };
                        await api.post(`/api/datasets/${id}/visualizations`, payload);
                        alert("Visualization saved and pinned to dashboard!");
                        
                        // Refresh visualizations tab templates list
                        const savedRes = await api.get(`/api/datasets/${id}/visualizations`);
                        setSavedCharts(savedRes.data);
                      } catch (err) {
                        console.error(err);
                        alert("Failed to pin visual template.");
                      }
                    }}
                    className="w-full flex items-center justify-center gap-2 py-3 bg-brand-600 hover:bg-brand-500 text-white font-bold rounded-xl transition cursor-pointer text-xs mt-6"
                  >
                    <Save className="w-4 h-4" />
                    <span>Pin to Dashboard</span>
                  </button>

                </div>

              </div>
            )}
          </div>
        )}

      </main>

      {/* Detailed Column Inspector Modal */}
      {selectedColumn && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-lg glass-panel border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
            <div className="p-6 border-b border-slate-900 flex justify-between items-start">
              <div>
                <h4 className="text-base font-bold text-slate-200 truncate">{selectedColumn.name}</h4>
                <p className="text-[10px] text-slate-500 uppercase font-semibold mt-1">Column Profile Metrics</p>
              </div>
              <button 
                onClick={() => setSelectedColumn(null)}
                className="text-xs text-slate-500 hover:text-slate-300 border border-slate-800 hover:border-slate-700 px-2.5 py-1 rounded-lg cursor-pointer"
              >
                Close
              </button>
            </div>

            <div className="p-6 space-y-6 max-h-[70vh] overflow-y-auto">
              <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-900 flex justify-between items-center text-xs">
                <span className="text-slate-500 font-medium">Inferred Classification</span>
                <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold border ${getBadgeColors(selectedColumn.detected_type)}`}>
                  {selectedColumn.detected_type}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4 text-xs">
                <div className="p-3 bg-slate-950/20 border border-slate-900 rounded-xl">
                  <span className="text-slate-500 block">Unique Values</span>
                  <span className="text-sm font-bold text-slate-300 mt-1 block">{selectedColumn.unique_count.toLocaleString()}</span>
                </div>
                <div className="p-3 bg-slate-950/20 border border-slate-900 rounded-xl">
                  <span className="text-slate-500 block">Null / Empty Cells</span>
                  <span className="text-sm font-bold text-slate-300 mt-1 block">{selectedColumn.missing_count} ({selectedColumn.missing_percentage}%)</span>
                </div>
              </div>

              {selectedColumn.detected_type === 'Numeric' && 'min' in selectedColumn && (
                <div className="space-y-3.5 p-4 rounded-xl bg-slate-950/40 border border-slate-900">
                  <h5 className="text-xs font-bold text-slate-300 border-b border-slate-900/60 pb-2">Mathematical Distribution</h5>
                  <div className="grid grid-cols-2 gap-y-3 gap-x-6 text-xs">
                    <div className="flex justify-between border-b border-slate-900/40 pb-1"><span className="text-slate-500">Minimum Value</span><span className="font-semibold text-slate-300">{selectedColumn.min}</span></div>
                    <div className="flex justify-between border-b border-slate-900/40 pb-1"><span className="text-slate-500">Maximum Value</span><span className="font-semibold text-slate-300">{selectedColumn.max}</span></div>
                    <div className="flex justify-between border-b border-slate-900/40 pb-1"><span className="text-slate-500">Average Mean</span><span className="font-semibold text-slate-300">{selectedColumn.mean}</span></div>
                    <div className="flex justify-between border-b border-slate-900/40 pb-1"><span className="text-slate-500">Median Value</span><span className="font-semibold text-slate-300">{selectedColumn.median}</span></div>
                    <div className="flex justify-between border-b border-slate-900/40 pb-1"><span className="text-slate-500">Std Deviation</span><span className="font-semibold text-slate-300">{selectedColumn.std}</span></div>
                  </div>

                  <div className="pt-2">
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider block mb-2 font-semibold">Quartiles (Percentiles)</span>
                    <div className="grid grid-cols-3 gap-2 text-center text-xs">
                      <div className="p-2 bg-slate-900/60 rounded-lg"><span className="text-slate-500 block text-[9px]">25th (Q1)</span><span className="font-semibold text-slate-300">{selectedColumn.q25}</span></div>
                      <div className="p-2 bg-slate-900/60 rounded-lg"><span className="text-slate-500 block text-[9px]">50th (Q2)</span><span className="font-semibold text-slate-300">{selectedColumn.q50}</span></div>
                      <div className="p-2 bg-slate-900/60 rounded-lg"><span className="text-slate-500 block text-[9px]">75th (Q3)</span><span className="font-semibold text-slate-300">{selectedColumn.q75}</span></div>
                    </div>
                  </div>
                </div>
              )}

              {selectedColumn.top_frequent && (
                <div className="space-y-3.5 p-4 rounded-xl bg-slate-950/40 border border-slate-900">
                  <h5 className="text-xs font-bold text-slate-300 border-b border-slate-900/60 pb-2">Top Frequent Value Modes</h5>
                  <div className="space-y-2.5">
                    {selectedColumn.top_frequent.map((freq, idx) => (
                      <div key={idx} className="space-y-1">
                        <div className="flex justify-between text-xs">
                          <span className="font-medium text-slate-300 truncate pr-2">"{freq.value}"</span>
                          <span className="text-slate-500">{freq.count} ({freq.percentage}%)</span>
                        </div>
                        <div className="w-full bg-slate-950 rounded-full h-1">
                          <div className="bg-brand-500 h-1 rounded-full" style={{ width: `${freq.percentage}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default DatasetOverview;
