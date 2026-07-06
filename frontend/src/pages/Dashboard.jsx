import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { 
  Database, Plus, LogOut, Search, Calendar, 
  Trash2, ArrowRight, BarChart3, ShieldAlert 
} from 'lucide-react';

const Dashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [deleteLoadingId, setDeleteLoadingId] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDatasets();
  }, []);

  const fetchDatasets = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/api/datasets');
      setDatasets(response.data);
    } catch (err) {
      console.error(err);
      setError("Failed to retrieve dataset registry history.");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id, e) => {
    e.stopPropagation(); // Avoid card click triggers
    if (!window.confirm("Are you sure you want to permanently delete this dataset?")) return;
    
    setDeleteLoadingId(id);
    try {
      await api.delete(`/api/datasets/${id}`);
      setDatasets(datasets.filter(d => d.id !== id));
    } catch (err) {
      console.error(err);
      alert("Failed to delete dataset. Please try again.");
    } finally {
      setDeleteLoadingId(null);
    }
  };

  // Helper: Format bytes
  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  // Filter datasets by name search
  const filteredDatasets = datasets.filter(d => 
    d.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen py-8 px-4 md:px-8">
      <div className="max-w-7xl mx-auto">
        
        {/* Dashboard Header Banner */}
        <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8 pb-5 border-b border-slate-900">
          <div>
            <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
              <span>Welcome back,</span>
              <span className="text-gradient-brand">{user?.full_name || 'User'}</span>
            </h1>
            <p className="text-xs text-slate-500 mt-1">Manage and inspect your uploaded files</p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/upload')}
              className="px-4 py-2.5 bg-brand-600 hover:bg-brand-500 text-white rounded-xl text-xs font-semibold flex items-center gap-2 transition cursor-pointer shadow-lg shadow-brand-500/10"
            >
              <Plus className="w-4 h-4" />
              <span>Ingest Dataset</span>
            </button>
            
            <button
              onClick={logout}
              className="p-2.5 bg-slate-950/40 border border-slate-900 hover:border-slate-800 hover:bg-slate-900/40 rounded-xl text-slate-400 hover:text-red-400 transition cursor-pointer"
              title="Sign Out"
            >
              <LogOut className="w-4.5 h-4.5" />
            </button>
          </div>
        </header>

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
            {error}
          </div>
        )}

        {/* Dashboard Search & Stats */}
        <div className="flex flex-col md:flex-row gap-4 justify-between items-stretch md:items-center mb-6">
          <div className="relative flex-1 max-w-md">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
              <Search className="w-4 h-4" />
            </div>
            <input
              type="text"
              placeholder="Search datasets..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-slate-950/30 border border-slate-900 focus:border-slate-700 rounded-xl text-slate-100 text-xs focus:outline-none focus:ring-1 focus:ring-slate-700 transition"
            />
          </div>
          
          <div className="text-xs text-slate-500 self-center">
            Showing {filteredDatasets.length} of {datasets.length} datasets
          </div>
        </div>

        {/* List of Datasets */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map(n => (
              <div key={n} className="glass-panel p-6 rounded-2xl border border-slate-900 animate-pulse h-48 flex flex-col justify-between">
                <div className="space-y-3">
                  <div className="h-4 bg-slate-900 rounded w-2/3" />
                  <div className="h-3 bg-slate-900 rounded w-1/2" />
                </div>
                <div className="h-8 bg-slate-900 rounded-lg w-full" />
              </div>
            ))}
          </div>
        ) : filteredDatasets.length === 0 ? (
          <div className="glass-panel p-12 rounded-2xl border border-slate-900 text-center max-w-xl mx-auto mt-12">
            <Database className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-bold text-slate-300">No datasets found</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mt-2 leading-relaxed">
              {searchQuery 
                ? "No uploaded file matches your search query. Try typing another keyword." 
                : "You haven't loaded any spreadsheets yet. Ingest your first file to activate profiling metrics."
              }
            </p>
            {!searchQuery && (
              <button
                onClick={() => navigate('/upload')}
                className="mt-6 px-5 py-2.5 bg-slate-900 hover:bg-slate-850 border border-slate-800 hover:border-slate-700 text-xs font-semibold text-slate-200 rounded-xl transition cursor-pointer"
              >
                Ingest First File
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredDatasets.map((dataset) => (
              <div 
                key={dataset.id}
                onClick={() => navigate(`/datasets/${dataset.id}/overview`)}
                className="glass-card p-6 rounded-2xl flex flex-col justify-between cursor-pointer group"
              >
                <div>
                  <div className="flex justify-between items-start gap-3 mb-4">
                    <h3 className="text-base font-bold text-slate-200 group-hover:text-brand-300 transition truncate pr-2">
                      {dataset.filename}
                    </h3>
                    <button
                      onClick={(e) => handleDelete(dataset.id, e)}
                      disabled={deleteLoadingId === dataset.id}
                      className="p-1.5 bg-slate-950/20 border border-slate-900/60 hover:border-red-500/20 hover:bg-red-500/5 rounded-lg text-slate-500 hover:text-red-400 transition"
                      title="Delete dataset"
                    >
                      {deleteLoadingId === dataset.id ? (
                        <div className="w-3.5 h-3.5 border border-slate-500/30 border-t-red-400 rounded-full animate-spin" />
                      ) : (
                        <Trash2 className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>

                  <div className="grid grid-cols-3 gap-2 py-3 border-y border-slate-900/50 text-center">
                    <div>
                      <span className="text-[10px] text-slate-500 block uppercase">Rows</span>
                      <span className="text-xs font-semibold text-slate-300">{dataset.row_count.toLocaleString()}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-500 block uppercase">Cols</span>
                      <span className="text-xs font-semibold text-slate-300">{dataset.col_count}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-500 block uppercase">Size</span>
                      <span className="text-xs font-semibold text-slate-300">{formatBytes(dataset.file_size)}</span>
                    </div>
                  </div>
                </div>

                <div className="flex justify-between items-center mt-5 pt-1 text-[11px] text-slate-500">
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5" />
                    <span>{new Date(dataset.created_at).toLocaleDateString()}</span>
                  </span>
                  
                  <span className="text-brand-400 hover:text-brand-300 font-semibold flex items-center gap-1 group-hover:translate-x-0.5 transition-all">
                    <span>Inspect</span>
                    <ArrowRight className="w-3 h-3" />
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

      </div>
    </div>
  );
};

export default Dashboard;
