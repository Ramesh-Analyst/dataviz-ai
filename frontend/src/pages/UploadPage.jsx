import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { uploadDataset } from '../services/api';
import { 
  Upload, FileSpreadsheet, AlertCircle, ArrowLeft, ArrowRight,
  Database, Rows, Columns, FileText, CheckCircle2 
} from 'lucide-react';

const UploadPage = () => {
  const navigate = useNavigate();
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState(null);
  
  // Loading & Upload states
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  
  // Result state
  const [datasetData, setDatasetData] = useState(null);

  // Helper: Format file bytes
  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Helper: Determine Badge Colors based on Detected Column Type
  const getTypeBadgeClass = (type) => {
    switch (type) {
      case 'Numeric': return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      case 'Categorical': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'Date/time': return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
      case 'Boolean': return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'Identifier': return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20';
      case 'Geographic candidate': return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
      default: return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
    }
  };

  // Drag handlers
  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  // Process selected file
  const processFile = async (selectedFile) => {
    const ext = selectedFile.name.split('.').pop().toLowerCase();
    if (!['csv', 'xlsx', 'xls'].includes(ext)) {
      setErrorMessage("Unsupported file type. Please upload a CSV or Excel file.");
      return;
    }

    setFile(selectedFile);
    setErrorMessage(null);
    setUploadProgress(0);
    setIsProcessing(true);
    setDatasetData(null);

    try {
      const data = await uploadDataset(selectedFile, (progress) => {
        setUploadProgress(progress);
      });
      setDatasetData(data);
    } catch (err) {
      console.error(err);
      const detail = err.response?.data?.detail || "Failed to process dataset. Ensure the format is correct.";
      setErrorMessage(detail);
      setFile(null);
    } finally {
      setIsProcessing(false);
    }
  };

  // Drop handler
  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  }, []);

  // Input change handler
  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  return (
    <div className="relative min-h-screen py-10 px-4 md:px-8">
      {/* Background radial spots */}
      <div className="glow-spot top-10 right-10" />
      
      <div className="max-w-7xl mx-auto relative z-10">
        
        {/* Navigation Header */}
        <header className="flex items-center justify-between mb-8 pb-5 border-b border-slate-900">
          <button 
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Home</span>
          </button>
          
          <div className="text-right">
            <h1 className="text-xl font-bold text-slate-200">DataViz AI Lab</h1>
            <p className="text-xs text-slate-500">Milestone 1 Workspace</p>
          </div>
        </header>

        {errorMessage && (
          <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <div>
              <h4 className="font-semibold text-sm">Upload Error</h4>
              <p className="text-xs text-red-400/90 mt-1">{errorMessage}</p>
            </div>
          </div>
        )}

        {/* Upload Container */}
        {!datasetData && (
          <div className="max-w-2xl mx-auto mt-10">
            <h2 className="text-2xl font-bold text-gradient text-center mb-2">Ingest Your Dataset</h2>
            <p className="text-sm text-slate-400 text-center mb-6">Select a CSV or Excel sheet to begin automated profiling and schema inference.</p>

            <form 
              onDragEnter={handleDrag} 
              onSubmit={(e) => e.preventDefault()}
              className={`relative h-64 rounded-2xl border-2 border-dashed flex flex-col items-center justify-center transition-all ${
                dragActive 
                  ? 'border-brand-500 bg-brand-500/5' 
                  : 'border-slate-800 bg-slate-950/20 hover:border-slate-700/60'
              }`}
            >
              <input 
                type="file" 
                id="dataset-input" 
                className="hidden" 
                accept=".csv, .xlsx, .xls"
                onChange={handleChange}
                disabled={isProcessing}
              />
              
              <label 
                htmlFor="dataset-input" 
                className="absolute inset-0 cursor-pointer flex flex-col items-center justify-center p-6 text-center"
              >
                {isProcessing ? (
                  <div className="flex flex-col items-center gap-4 w-4/5">
                    <FileSpreadsheet className="w-12 h-12 text-brand-400 animate-bounce" />
                    <div className="w-full bg-slate-900 rounded-full h-2.5 overflow-hidden">
                      <div 
                        className="bg-brand-500 h-2.5 rounded-full transition-all duration-300"
                        style={{ width: `${uploadProgress}%` }}
                      />
                    </div>
                    <span className="text-sm text-slate-300 font-medium">
                      {uploadProgress < 100 
                        ? `Uploading dataset... ${uploadProgress}%` 
                        : "Processing metadata and analyzing columns..."}
                    </span>
                  </div>
                ) : (
                  <>
                    <Upload className="w-10 h-10 text-slate-400 mb-4" />
                    <span className="text-sm font-semibold text-slate-200">Drag & drop your file here</span>
                    <span className="text-xs text-slate-500 mt-1.5">Supports CSV, XLSX, XLS up to 10MB</span>
                    <span className="mt-4 px-4 py-2 bg-slate-900 hover:bg-slate-850 border border-slate-800 hover:border-slate-700 rounded-lg text-xs font-semibold text-slate-300 transition-colors">
                      Browse Files
                    </span>
                  </>
                )}
              </label>

              {dragActive && (
                <div 
                  className="absolute inset-0 rounded-2xl" 
                  onDragEnter={handleDrag} 
                  onDragOver={handleDrag} 
                  onDragLeave={handleDrag} 
                  onDrop={handleDrop} 
                />
              )}
            </form>
          </div>
        )}

        {/* Results / Preview Section */}
        {datasetData && (
          <div className="space-y-8 animate-fadeIn">
            
            {/* Header / KPI overview */}
            <div className="flex flex-col lg:flex-row gap-6 justify-between items-start lg:items-center">
              <div>
                <div className="flex items-center gap-2.5">
                  <Database className="w-5 h-5 text-brand-400" />
                  <h2 className="text-2xl font-bold text-slate-100">{datasetData.metadata.filename}</h2>
                  <div className="flex items-center gap-1 text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-md text-xs font-semibold">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Loaded</span>
                  </div>
                </div>
                <p className="text-xs text-slate-500 mt-1">Uploaded on {new Date(datasetData.metadata.created_at).toLocaleString()}</p>
              </div>

              <div className="flex items-center gap-3">
                <button 
                  onClick={() => setDatasetData(null)}
                  className="px-4 py-2 bg-slate-900 border border-slate-850 hover:bg-slate-900 hover:border-slate-800 text-slate-300 rounded-xl text-xs font-semibold border transition cursor-pointer"
                >
                  Upload Another File
                </button>
                <button 
                  onClick={() => navigate(`/datasets/${datasetData.metadata.id}/overview`)}
                  className="px-5 py-2.5 bg-brand-600 hover:bg-brand-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-brand-500/10 transition cursor-pointer flex items-center gap-1.5"
                >
                  <span>Continue to Analysis Workspace</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Quick Stats Grid */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="glass-card p-4 rounded-xl flex items-center gap-3">
                <div className="p-2.5 bg-slate-900/80 border border-slate-800 rounded-lg">
                  <Rows className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <div className="text-xs text-slate-500">Rows Count</div>
                  <div className="text-lg font-bold text-slate-200">{datasetData.metadata.row_count.toLocaleString()}</div>
                </div>
              </div>

              <div className="glass-card p-4 rounded-xl flex items-center gap-3">
                <div className="p-2.5 bg-slate-900/80 border border-slate-800 rounded-lg">
                  <Columns className="w-5 h-5 text-emerald-400" />
                </div>
                <div>
                  <div className="text-xs text-slate-500">Columns Count</div>
                  <div className="text-lg font-bold text-slate-200">{datasetData.metadata.col_count.toLocaleString()}</div>
                </div>
              </div>

              <div className="glass-card p-4 rounded-xl flex items-center gap-3">
                <div className="p-2.5 bg-slate-900/80 border border-slate-800 rounded-lg">
                  <FileText className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <div className="text-xs text-slate-500">File Storage Size</div>
                  <div className="text-lg font-bold text-slate-200">{formatBytes(datasetData.metadata.file_size)}</div>
                </div>
              </div>

              <div className="glass-card p-4 rounded-xl flex items-center gap-3">
                <div className="p-2.5 bg-slate-900/80 border border-slate-800 rounded-lg">
                  <Database className="w-5 h-5 text-yellow-400" />
                </div>
                <div>
                  <div className="text-xs text-slate-500">Data Formats</div>
                  <div className="text-lg font-bold text-slate-200">
                    {datasetData.metadata.filename.split('.').pop().toUpperCase()}
                  </div>
                </div>
              </div>
            </div>

            {/* Columns Profiles Grid */}
            <section className="glass-panel p-6 rounded-2xl">
              <h3 className="text-base font-bold text-slate-200 mb-4 flex items-center gap-2">
                <span>Inferred Column Metadata</span>
                <span className="text-xs font-normal text-slate-500">({datasetData.metadata.columns.length} columns detected)</span>
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {datasetData.metadata.columns.map((col, idx) => (
                  <div key={idx} className="p-4 rounded-xl bg-slate-950/40 border border-slate-900 flex flex-col justify-between">
                    <div>
                      <div className="flex justify-between items-start gap-2">
                        <span className="text-sm font-semibold text-slate-200 truncate">{col.name}</span>
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold border ${getTypeBadgeClass(col.detected_type)}`}>
                          {col.detected_type}
                        </span>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-2 mt-4 pt-3 border-t border-slate-900/80 text-xs">
                        <div>
                          <span className="text-slate-500 block">Unique Values</span>
                          <span className="text-slate-300 font-medium">{col.unique_count !== null ? col.unique_count : 'N/A'}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block">Missing Cells</span>
                          <span className="text-slate-300 font-medium">
                            {col.missing_count !== null 
                              ? `${col.missing_count} (${((col.missing_count / datasetData.metadata.row_count) * 100).toFixed(1)}%)`
                              : '0'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* Tabular Preview */}
            <section className="glass-panel p-6 rounded-2xl">
              <h3 className="text-base font-bold text-slate-200 mb-3">Dataset Preview</h3>
              <p className="text-xs text-slate-500 mb-4">Rendering the first 10 rows of the imported dataset.</p>

              <div className="overflow-x-auto border border-slate-900 rounded-xl">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-950/80 text-slate-400 font-semibold border-b border-slate-900">
                      <th className="py-3.5 px-4 w-12 border-r border-slate-900 text-center">#</th>
                      {datasetData.metadata.columns.map((col, idx) => (
                        <th key={idx} className="py-3.5 px-4 font-semibold text-slate-300 border-r border-slate-900 last:border-0">
                          {col.name}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {datasetData.preview_rows.map((row, rowIdx) => (
                      <tr key={rowIdx} className="hover:bg-slate-900/20 border-b border-slate-900 last:border-0 transition-colors">
                        <td className="py-3 px-4 text-slate-500 text-center border-r border-slate-900 bg-slate-950/20 font-mono">
                          {rowIdx + 1}
                        </td>
                        {datasetData.metadata.columns.map((col, colIdx) => {
                          const val = row[col.name];
                          const isNull = val === null || val === undefined;
                          return (
                            <td key={colIdx} className="py-3 px-4 text-slate-300 border-r border-slate-900 last:border-0 truncate max-w-[200px]">
                              {isNull ? (
                                <span className="text-slate-600 italic">null</span>
                              ) : (
                                String(val)
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

          </div>
        )}

      </div>
    </div>
  );
};

export default UploadPage;
