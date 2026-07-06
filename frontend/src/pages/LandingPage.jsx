import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, BarChart3, ShieldAlert, Sparkles, ArrowRight } from 'lucide-react';

const LandingPage = () => {
  const navigate = useNavigate();

  const features = [
    {
      icon: <Upload className="w-6 h-6 text-brand-400" />,
      title: "Zero-Config Ingestion",
      desc: "Drag and drop CSV or Excel files. We instantly parse types, sizes, and schema definitions."
    },
    {
      icon: <ShieldAlert className="w-6 h-6 text-yellow-400" />,
      title: "Explainable Quality Scoring",
      desc: "Get an instant 0-100 data quality score highlighting outliers, missing data, and structural conflicts."
    },
    {
      icon: <Sparkles className="w-6 h-6 text-purple-400" />,
      title: "Smart Visualizations",
      desc: "Our rule-based engine inspects columns cardinality to suggest beautiful, optimized charts."
    },
    {
      icon: <BarChart3 className="w-6 h-6 text-emerald-400" />,
      title: "Auto Dashboards",
      desc: "Synthesize complete reporting dashboards with key performance cards and charts in one click."
    }
  ];

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center px-4 overflow-hidden">
      {/* Background glow highlights */}
      <div className="glow-spot top-1/4 left-1/4 -translate-x-1/2 -translate-y-1/2" />
      <div className="glow-spot bottom-1/4 right-1/4 translate-x-1/2 translate-y-1/2" />

      {/* Hero Section */}
      <div className="relative z-10 text-center max-w-4xl mt-12 mb-16">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full glass-panel border border-brand-500/20 text-brand-300 text-xs font-semibold mb-6 animate-pulse-slow">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Automated Data Viz Platform</span>
        </div>

        <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-6 leading-tight font-sans">
          <span className="text-gradient">Turn Raw Data into</span> <br />
          <span className="text-gradient-brand">Interactive Dashboards</span>
        </h1>

        <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
          Upload CSV or Excel files. DataViz AI automatically profiles schemas, audits data quality, and recommends beautiful interactive visual charts with zero code.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <button
            onClick={() => navigate('/upload')}
            className="w-full sm:w-auto px-8 py-4 rounded-xl font-semibold bg-brand-600 hover:bg-brand-500 text-white shadow-lg shadow-brand-500/20 transition-all duration-300 flex items-center justify-center gap-2 group cursor-pointer"
          >
            <span>Upload Your Dataset</span>
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </button>
          
          <button
            onClick={() => {
              const el = document.getElementById('features-section');
              el?.scrollIntoView({ behavior: 'smooth' });
            }}
            className="w-full sm:w-auto px-8 py-4 rounded-xl font-semibold glass-panel border border-slate-700/50 hover:bg-slate-800/40 text-slate-300 transition-all cursor-pointer"
          >
            Learn More
          </button>
        </div>
      </div>

      {/* Features Grid Section */}
      <div id="features-section" className="relative z-10 w-full max-w-6xl py-12 border-t border-slate-900 mt-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-gradient">Engineered for Smart Analysis</h2>
          <p className="text-slate-400 mt-2">A complete backend profiling pipeline wrapped in a clean, visual interface.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((feat, idx) => (
            <div key={idx} className="glass-card p-6 rounded-2xl flex flex-col items-start text-left">
              <div className="p-3 bg-slate-900/60 rounded-xl mb-5 border border-slate-800">
                {feat.icon}
              </div>
              <h3 className="text-lg font-semibold text-slate-100 mb-2">{feat.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{feat.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="relative z-10 w-full text-center py-8 text-xs text-slate-500 border-t border-slate-900 mt-auto">
        <p>© 2026 DataViz AI. Built as a production-quality B.Tech Capstone Project.</p>
      </div>
    </div>
  );
};

export default LandingPage;
