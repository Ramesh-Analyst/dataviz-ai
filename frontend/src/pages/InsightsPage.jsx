import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { 
  ArrowLeft, Brain, TrendingUp, AlertTriangle, 
  Info, ShieldCheck, Activity, HelpCircle, Star 
} from 'lucide-react';

const InsightsPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [insights, setInsights] = useState([]);
  const [dataset, setDataset] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchInsights();
  }, [id]);

  const fetchInsights = async () => {
    setLoading(true);
    setError(null);
    try {
      const insightRes = await api.get(`/api/datasets/${id}/insights`);
      setInsights(insightRes.data);
      
      const datasetRes = await api.get(`/api/datasets/${id}`);
      setDataset(datasetRes.data);
    } catch (err) {
      console.error(err);
      setError("Failed to generate statistical insights narrative. Please check dataset permissions.");
    } finally {
      setLoading(false);
    }
  };

  const getInsightIcon = (type) => {
    switch (type) {
      case 'correlation': return <TrendingUp className="w-5 h-5 text-purple-400" />;
      case 'missingness': return <HelpCircle className="w-5 h-5 text-yellow-400" />;
      case 'outlier': return <AlertTriangle className="w-5 h-5 text-orange-400" />;
      case 'skewness': return <Activity className="w-5 h-5 text-blue-400" />;
      case 'constant': return <Info className="w-5 h-5 text-slate-400" />;
      case 'quality': return <ShieldCheck className="w-5 h-5 text-emerald-400" />;
      case 'cardinality': return <AlertTriangle className="w-5 h-5 text-amber-400" />;
      default: return <Star className="w-5 h-5 text-slate-400" />;
    }
  };

  const getSeverityColors = (severity) => {
    switch (severity) {
      case 'critical': return 'border-red-500/20 bg-red-500/5 text-red-400';
      case 'warning': return 'border-yellow-500/20 bg-yellow-500/5 text-yellow-400';
      case 'info': return 'border-blue-500/20 bg-blue-500/5 text-blue-400';
      default: return 'border-slate-900/60 bg-slate-950/20 text-slate-400';
    }
  };

  const getSeverityBadge = (severity) => {
    switch (severity) {
      case 'critical': return 'bg-red-500/10 text-red-400 border-red-500/20';
      case 'warning': return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
      case 'info': return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      default: return 'bg-slate-900 text-slate-500 border-slate-800';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#08090f] flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-10 h-10 border-2 border-brand-500/20 border-t-brand-500 rounded-full animate-spin mx-auto" />
          <p className="text-xs text-slate-500">Synthesizing statistical takeaways...</p>
        </div>
      </div>
    );
  }

  if (error || !dataset) {
    return (
      <div className="min-h-screen bg-[#08090f] py-16 px-4">
        <div className="max-w-md mx-auto glass-panel p-8 text-center rounded-2xl border border-slate-900">
          <Brain className="w-12 h-12 text-red-400/80 mx-auto mb-4" />
          <h2 className="text-lg font-bold text-slate-200">Unable to Profile</h2>
          <p className="text-xs text-slate-500 mt-2">{error || "The dataset could not be analyzed."}</p>
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

  return (
    <div className="min-h-screen bg-[#08090f] py-8 px-4 md:px-8 text-slate-200">
      <div className="max-w-4xl mx-auto">
        
        {/* Navigation & Header */}
        <header className="flex items-center gap-3.5 mb-8 pb-5 border-b border-slate-900">
          <button 
            onClick={() => navigate(`/datasets/${id}/overview`)}
            className="p-2.5 bg-slate-950/40 border border-slate-900 hover:border-slate-800 rounded-xl text-slate-400 hover:text-slate-200 transition cursor-pointer"
            title="Back to Overview"
          >
            <ArrowLeft className="w-4.5 h-4.5" />
          </button>

          <div>
            <div className="flex items-center gap-2">
              <Brain className="w-5 h-5 text-brand-400" />
              <h1 className="text-xl font-bold text-slate-100">Statistical Narrative Insights</h1>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">Automated analytical takeaways for {dataset.metadata.filename}</p>
          </div>
        </header>

        {insights.length === 0 ? (
          <div className="glass-panel p-16 text-center rounded-2xl border border-slate-900">
            <Brain className="w-12 h-12 text-slate-650 mx-auto mb-4" />
            <h3 className="text-base font-bold text-slate-300">No Insights Found</h3>
            <p className="text-xs text-slate-500 mt-2 max-w-sm mx-auto leading-relaxed">
              Your dataset appears to be completely uniform with no strong correlations, null cell skewness, or outlier records.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {insights.map((insight, idx) => (
              <div 
                key={idx} 
                className={`p-6 rounded-2xl border flex items-start gap-4 transition-all duration-300 ${getSeverityColors(insight.severity)}`}
              >
                <div className="p-3 bg-slate-950 border border-slate-900/60 rounded-xl shrink-0">
                  {getInsightIcon(insight.insight_type)}
                </div>

                <div className="flex-1 space-y-2">
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-[9px] uppercase tracking-wider font-bold text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-850">
                      {insight.insight_type}
                    </span>
                    <span className={`text-[9px] uppercase tracking-wider font-bold px-2 py-0.5 rounded border ${getSeverityBadge(insight.severity)}`}>
                      {insight.severity}
                    </span>
                  </div>

                  <p className="text-xs text-slate-200 leading-relaxed font-semibold">
                    {insight.message}
                  </p>

                  <div className="space-y-1.5 pt-2">
                    <div className="flex justify-between text-[10px] text-slate-500">
                      <span>Statistical significance / weight</span>
                      <span>{Math.round(insight.significance * 100)}%</span>
                    </div>
                    <div className="w-full bg-slate-950 border border-slate-900/40 rounded-full h-1.5">
                      <div 
                        className="bg-brand-500 h-1.5 rounded-full" 
                        style={{ width: `${Math.min(100, insight.significance * 100)}%` }} 
                      />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

      </div>
    </div>
  );
};

export default InsightsPage;
