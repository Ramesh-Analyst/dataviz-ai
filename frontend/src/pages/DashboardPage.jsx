import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import ReactECharts from 'echarts-for-react';
import { 
  ArrowLeft, LayoutDashboard, Calendar, Filter, 
  Sparkles, RefreshCw, X, Sliders, ChevronDown
} from 'lucide-react';

const DashboardPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [dashboard, setDashboard] = useState(null);
  const [dataset, setDataset] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Global filters state: { colName: selectedValue }
  const [activeFilters, setActiveFilters] = useState({});
  const [filterPanelOpen, setFilterPanelOpen] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchInitialData();
  }, [id]);

  const fetchInitialData = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch dashboard metadata & widgets (initially unfiltered)
      const dashRes = await api.get(`/api/dashboards/${id}`);
      setDashboard(dashRes.data);
      
      const datasetId = dashRes.data.dataset_id;
      
      // 2. Fetch dataset metadata
      const datasetRes = await api.get(`/api/datasets/${datasetId}`);
      setDataset(datasetRes.data);
      
      // 3. Fetch deep profiling stats to get categorical levels (for filter options)
      const profileRes = await api.get(`/api/datasets/${datasetId}/profile`);
      setProfile(profileRes.data);
      
      // Initialize filters dictionary for categorical columns
      const initialFilters = {};
      datasetRes.data.metadata.columns.forEach(col => {
        if (col.detected_type === 'Categorical') {
          initialFilters[col.name] = '';
        }
      });
      setActiveFilters(initialFilters);
      
    } catch (err) {
      console.error(err);
      setError("Failed to fetch dashboard data. Make sure the dataset exists and you have access permissions.");
    } finally {
      setLoading(false);
    }
  };

  // Refetch dashboard data when filters change
  const applyFilters = async (updatedFilters) => {
    setRefreshing(true);
    try {
      // Clean filters (remove empty strings)
      const cleanFilters = {};
      Object.keys(updatedFilters).forEach(key => {
        if (updatedFilters[key] !== '') {
          cleanFilters[key] = updatedFilters[key];
        }
      });
      
      const filtersParam = encodeURIComponent(JSON.stringify(cleanFilters));
      const res = await api.get(`/api/dashboards/${id}?filters=${filtersParam}`);
      setDashboard(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setRefreshing(false);
    }
  };

  const handleFilterChange = (columnName, value) => {
    const nextFilters = { ...activeFilters, [columnName]: value };
    setActiveFilters(nextFilters);
    applyFilters(nextFilters);
  };

  const clearAllFilters = () => {
    const cleared = {};
    Object.keys(activeFilters).forEach(key => {
      cleared[key] = '';
    });
    setActiveFilters(cleared);
    applyFilters(cleared);
  };

  // Map widget points to ECharts options
  const getWidgetOption = (widget) => {
    const config = widget.chart_config;
    const points = widget.datapoints || [];
    
    if (!config || points.length === 0) return {};
    
    const chartType = config.chart_type;
    const xAxis = config.x_axis;
    const yAxis = config.y_axis;
    const groupBy = config.group_by;
    const title = widget.title || config.title;

    // Pivot grouped series
    if (groupBy) {
      const xLabels = Array.from(new Set(points.map(d => String(d[xAxis]))));
      const groupItems = Array.from(new Set(points.map(d => String(d[groupBy]))));
      
      const seriesList = groupItems.map(item => {
        const seriesData = xLabels.map(label => {
          const matchedRow = points.find(
            d => String(d[xAxis]) === label && String(d[groupBy]) === item
          );
          return matchedRow ? (matchedRow.value !== undefined ? matchedRow.value : matchedRow.count) : 0;
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
        legend: { data: groupItems, textStyle: { color: '#94a3b8' }, type: 'scroll', bottom: '0%' },
        grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
        xAxis: { type: 'category', data: xLabels, axisLabel: { color: '#94a3b8' } },
        yAxis: { type: 'value', axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#0f1122' } } },
        series: seriesList
      };
    }

    // Standard Non-Grouped
    const xData = points.map(d => String(d[xAxis]));
    
    if (chartType === 'pie') {
      const pieData = points.map(d => ({
        name: String(d[xAxis]),
        value: d.value !== undefined ? d.value : d.count
      }));
      
      return {
        backgroundColor: 'transparent',
        tooltip: { trigger: 'item', formatter: '{b}: <b>{c} ({d}%)</b>', backgroundColor: '#0d0f1a', borderColor: '#1e293b', textStyle: { color: '#e2e8f0' } },
        legend: { textStyle: { color: '#94a3b8' }, type: 'scroll', bottom: '0%' },
        series: [{
          name: title,
          type: 'pie',
          radius: '50%',
          center: ['50%', '42%'],
          data: pieData,
          emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' } }
        }]
      };
    }

    if (chartType === 'scatter') {
      const scatterData = points.map(d => [d[xAxis], d[yAxis]]);
      return {
        backgroundColor: 'transparent',
        tooltip: { trigger: 'item', backgroundColor: '#0d0f1a', borderColor: '#1e293b', textStyle: { color: '#e2e8f0' } },
        grid: { left: '3%', right: '4%', bottom: '10%', top: '10%', containLabel: true },
        xAxis: { type: 'value', name: xAxis, axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#0f1122' } } },
        yAxis: { type: 'value', name: yAxis, axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#0f1122' } } },
        series: [{
          type: 'scatter',
          symbolSize: 8,
          data: scatterData,
          itemStyle: { color: '#4a57ed' }
        }]
      };
    }

    // Bar or Line
    const yData = points.map(d => (d.value !== undefined ? d.value : d.count));
    
    return {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', backgroundColor: '#0d0f1a', borderColor: '#1e293b', textStyle: { color: '#e2e8f0' } },
      grid: { left: '3%', right: '4%', bottom: '10%', top: '10%', containLabel: true },
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

  if (loading) {
    return (
      <div className="min-h-screen bg-[#08090f] flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-10 h-10 border-2 border-brand-500/20 border-t-brand-500 rounded-full animate-spin mx-auto" />
          <p className="text-xs text-slate-500">Loading dynamic reporting dashboard...</p>
        </div>
      </div>
    );
  }

  if (error || !dashboard) {
    return (
      <div className="min-h-screen bg-[#08090f] py-16 px-4">
        <div className="max-w-md mx-auto glass-panel p-8 text-center rounded-2xl border border-slate-900">
          <Sliders className="w-12 h-12 text-red-400/80 mx-auto mb-4" />
          <h2 className="text-lg font-bold text-slate-200">Dashboard Unreachable</h2>
          <p className="text-xs text-slate-500 mt-2">{error || "The dashboard does not exist or has been deleted."}</p>
          <button 
            onClick={() => navigate('/dashboard')}
            className="mt-6 px-5 py-2.5 bg-slate-950 border border-slate-900 hover:bg-slate-900 text-xs font-semibold text-slate-300 rounded-xl transition cursor-pointer"
          >
            Return to Hub
          </button>
        </div>
      </div>
    );
  }

  const isFiltered = Object.values(activeFilters).some(v => v !== '');

  return (
    <div className="min-h-screen bg-[#08090f] text-slate-200">
      {/* Top Navbar */}
      <div className="border-b border-slate-900 bg-[#08090f]/80 backdrop-blur-md sticky top-0 z-30 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button 
            onClick={() => navigate(`/datasets/${dashboard.dataset_id}/overview`)}
            className="p-2 bg-slate-950 border border-slate-900 hover:border-slate-800 rounded-xl hover:text-slate-100 transition cursor-pointer"
            title="Back to Dataset"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[9px] uppercase tracking-wider font-bold text-brand-400 bg-brand-500/10 px-2 py-0.5 rounded-md border border-brand-500/20">Dashboard</span>
              <h1 className="text-base font-bold text-slate-100 truncate max-w-xs sm:max-w-md">{dashboard.title}</h1>
            </div>
            <p className="text-[10px] text-slate-500 truncate max-w-sm mt-0.5">{dashboard.description || 'Reporting dashboard'}</p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setFilterPanelOpen(!filterPanelOpen)}
            className={`px-3 py-2 border rounded-xl text-xs font-semibold flex items-center gap-2 cursor-pointer transition ${
              filterPanelOpen 
                ? 'bg-brand-600/10 border-brand-500/30 text-brand-300' 
                : 'bg-slate-950 border-slate-900 text-slate-400 hover:border-slate-800'
            }`}
          >
            <Filter className="w-3.5 h-3.5" />
            <span>Filters</span>
          </button>
          
          {refreshing && <RefreshCw className="w-4 h-4 text-brand-400 animate-spin" />}
        </div>
      </div>

      <div className="flex relative">
        {/* Global Filter Sidebar Panel */}
        <aside 
          className={`w-72 border-r border-slate-900 bg-[#08090f]/40 backdrop-blur-sm self-stretch transition-all duration-300 shrink-0 overflow-y-auto ${
            filterPanelOpen ? 'ml-0 opacity-100' : '-ml-72 opacity-0'
          }`}
          style={{ height: 'calc(100vh - 73px)' }}
        >
          <div className="p-6 space-y-6">
            <div className="flex justify-between items-center pb-3 border-b border-slate-900/60">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <Sliders className="w-3.5 h-3.5 text-brand-400" />
                <span>Global Filters</span>
              </span>
              {isFiltered && (
                <button 
                  onClick={clearAllFilters}
                  className="text-[10px] text-brand-400 hover:text-brand-300 font-bold transition flex items-center gap-0.5 cursor-pointer"
                >
                  <span>Clear</span>
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>

            <div className="space-y-5 text-xs">
              {dataset?.metadata.columns
                .filter(col => col.detected_type === 'Categorical')
                .map((col, colIdx) => {
                  const uniqueValues = profile?.column_stats[col.name]?.top_frequent?.map(f => f.value) || [];
                  
                  return (
                    <div key={colIdx} className="space-y-1.5">
                      <label className="text-slate-400 font-medium">{col.name}</label>
                      <div className="relative">
                        <select
                          value={activeFilters[col.name] || ''}
                          onChange={(e) => handleFilterChange(col.name, e.target.value)}
                          className="w-full bg-slate-950/80 border border-slate-900 hover:border-slate-800 rounded-xl px-3 py-2.5 text-slate-200 font-semibold focus:outline-none focus:border-brand-500 appearance-none cursor-pointer"
                        >
                          <option value="">All values</option>
                          {uniqueValues.map((val, valIdx) => (
                            <option key={valIdx} value={val}>{val}</option>
                          ))}
                        </select>
                        <ChevronDown className="absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                      </div>
                    </div>
                  );
                })
              }
              
              {dataset?.metadata.columns.filter(col => col.detected_type === 'Categorical').length === 0 && (
                <p className="text-[11px] text-slate-600 text-center py-4">No categorical columns detected to filter dataset.</p>
              )}
            </div>
          </div>
        </aside>

        {/* Dashboard Widgets Workspace Grid */}
        <main className="flex-1 p-6 md:p-8 overflow-y-auto" style={{ height: 'calc(100vh - 73px)' }}>
          {dashboard.widgets.length === 0 ? (
            <div className="glass-panel p-16 text-center rounded-2xl border border-slate-900 max-w-xl mx-auto mt-12">
              <Sparkles className="w-12 h-12 text-slate-700 mx-auto mb-4" />
              <h3 className="text-base font-bold text-slate-300">Dashboard is Empty</h3>
              <p className="text-xs text-slate-500 mt-2 max-w-sm mx-auto leading-relaxed">
                Configure dataset visual charts under the "Smart Visualizations" tab and save them to construct layout reports.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {dashboard.widgets.map((widget) => (
                <div 
                  key={widget.id} 
                  className="glass-card p-6 rounded-2xl border border-slate-900/60 bg-slate-950/20 flex flex-col h-[380px]"
                >
                  <div className="flex justify-between items-center mb-4 pb-2 border-b border-slate-900/40">
                    <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">{widget.title}</h3>
                    <span className="text-[9px] font-bold text-brand-400/80 bg-brand-500/5 px-2 py-0.5 rounded border border-brand-500/10 uppercase">
                      {widget.chart_config?.chart_type || widget.widget_type}
                    </span>
                  </div>

                  <div className="flex-1 min-h-0 relative">
                    {!widget.datapoints || widget.datapoints.length === 0 ? (
                      <div className="absolute inset-0 flex items-center justify-center text-xs text-slate-600">
                        No filtered datapoints fit dashboard criteria.
                      </div>
                    ) : (
                      <ReactECharts 
                        option={getWidgetOption(widget)} 
                        style={{ height: '100%', width: '100%' }}
                        key={`${widget.id}-${activeFilters ? JSON.stringify(activeFilters) : ''}`}
                      />
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default DashboardPage;
