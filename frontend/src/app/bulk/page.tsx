"use client";

import { useState, useRef } from "react";
import { 
  Upload, 
  FileSpreadsheet, 
  Download, 
  Loader2, 
  CheckCircle2, 
  AlertTriangle, 
  ExternalLink,
  Table,
  Plus
} from "lucide-react";

interface JobItem {
  job_title: string;
  company_name: string;
  job_website: string;
  location: string;
  date_posted: string;
  industry_match: string | boolean;
  job_type?: string;
  job_url: string;
  match_reason: string;
}

export default function BulkSearch() {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [loading, setLoading] = useState(false);
  
  // Progress updates
  const [progressMessage, setProgressMessage] = useState("");
  const [progress, setProgress] = useState<{ current: number; total: number } | null>(null);
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [completedRowsCount, setCompletedRowsCount] = useState(0);
  const [successCount, setSuccessCount] = useState(0);
  const [failureCount, setFailureCount] = useState(0);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.name.endsWith(".xlsx") || droppedFile.name.endsWith(".xls")) {
        setFile(droppedFile);
      } else {
        alert("Please drop a valid Excel file (.xlsx or .xls)");
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleDownloadTemplate = () => {
    window.open(`${apiUrl}/api/bulk-template`, "_blank");
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setJobs([]);
    setWarnings([]);
    setProgress(null);
    setProgressMessage("Uploading Excel file...");
    setCompletedRowsCount(0);
    setSuccessCount(0);
    setFailureCount(0);

    const formData = new FormData();
    formData.append("file", file);

    const apiUrl = "http://localhost:8000";

    try {
      const response = await fetch(`${apiUrl}/api/bulk-search`, {
        method: "POST",
        body: formData,
      });

      if (!response.body) {
        throw new Error("No response stream available.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line);

            if (data.message) {
              setProgressMessage(data.message);
            }

            if (data.progress) {
              setProgress(data.progress);
            }

            if (data.step === "row_complete") {
              setCompletedRowsCount((prev) => prev + 1);
            }

            if (data.step === "completed") {
              setJobs(data.jobs || []);
              setWarnings(data.warnings || []);
              setSuccessCount(data.success_count || 0);
              setFailureCount(data.failure_count || 0);
              setLoading(false);
            }

            if (data.step === "error") {
              throw new Error(data.message);
            }
          } catch (err) {
            console.error("Stream parse error:", err);
          }
        }
      }
    } catch (err: any) {
      setProgressMessage(err.message || "An error occurred during processing.");
      setLoading(false);
    }
  };

  const downloadResultsCSV = () => {
    if (jobs.length === 0) return;

    // Build CSV Content
    const headers = ["Job Title", "Company Name", "Job Site", "Location", "Date Posted", "Industry Match", "Job Type", "Match Reason", "Advert Link"];
    const rows = jobs.map(j => [
      `"${j.job_title.replace(/"/g, '""')}"`,
      `"${j.company_name.replace(/"/g, '""')}"`,
      `"${j.job_website}"`,
      `"${j.location.replace(/"/g, '""')}"`,
      `"${j.date_posted}"`,
      `"${j.industry_match === true ? 'Yes' : j.industry_match === false ? 'No' : j.industry_match}"`,
      `"${(j.job_type || "Permanent").replace(/"/g, '""')}"`,
      `"${j.match_reason.replace(/"/g, '""')}"`,
      `"${j.job_url}"`
    ]);

    const csvContent = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", "JobPulse_Bulk_Search_Results.csv");
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="flex-1 p-8 max-w-7xl mx-auto w-full flex flex-col gap-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-col gap-2">
          <h2 className="text-3xl font-extrabold text-white tracking-tight">
            Bulk Verification Search
          </h2>
          <p className="text-gray-400 max-w-2xl">
            Upload an Excel document containing multiple roles, locations, and industries. JobPulse runs the search pipeline for each entry concurrently, and deduplicates the results into a single report.
          </p>
        </div>

        <button
          onClick={handleDownloadTemplate}
          className="inline-flex items-center gap-2 bg-[#141b2b] hover:bg-[#1f2937] border border-[#374151] hover:border-gray-500 text-gray-300 font-semibold py-3 px-5 rounded-xl transition-all duration-300 shadow-md"
        >
          <Download className="h-5 w-5 text-indigo-400" /> Download Template
        </button>
      </div>

      {/* Upload Zone & Form */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <form onSubmit={handleUploadSubmit} className="flex flex-col gap-6">
            <div
              onDragEnter={handleDrag}
              onDragOver={handleDrag}
              onDragLeave={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-2xl p-10 flex flex-col items-center justify-center cursor-pointer transition-all duration-300 relative overflow-hidden ${
                dragActive 
                  ? "border-indigo-500 bg-indigo-500/5 shadow-indigo-500/5 shadow-2xl" 
                  : "border-[#374151] bg-[#111827] hover:border-indigo-500/50 hover:bg-[#141b2b]"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".xlsx,.xls"
                onChange={handleFileChange}
              />
              <Upload className={`h-12 w-12 mb-4 transition-transform duration-300 ${dragActive ? "scale-110 text-indigo-400" : "text-gray-500"}`} />
              
              {file ? (
                <div className="text-center">
                  <p className="text-sm font-semibold text-white mb-1 flex items-center justify-center gap-2">
                    <FileSpreadsheet className="h-4 w-4 text-emerald-400" /> {file.name}
                  </p>
                  <p className="text-xs text-gray-500">{(file.size / 1024).toFixed(1)} KB • Click or drag to change file</p>
                </div>
              ) : (
                <div className="text-center">
                  <p className="text-sm font-semibold text-white mb-1">Drag & drop your Excel file here</p>
                  <p className="text-xs text-gray-500">Supports .xlsx and .xls formats</p>
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={loading || !file}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-800/40 text-white font-medium py-3.5 rounded-xl transition-all duration-300 flex items-center justify-center gap-2.5 shadow-lg shadow-indigo-600/20"
            >
              {loading ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  <span>Processing Bulk Job Orders...</span>
                </>
              ) : (
                <>
                  <FileSpreadsheet className="h-5 w-5" />
                  <span>Start Bulk Verification</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Info Card */}
        <div className="bg-[#111827] border border-[#1f2937] rounded-2xl p-6 flex flex-col justify-between shadow-xl">
          <div>
            <h3 className="text-base font-bold text-white mb-4">Bulk Guidelines</h3>
            <ul className="text-xs text-gray-400 flex flex-col gap-3 leading-relaxed list-disc pl-5">
              <li>Use the downloaded template to ensure matching column headers.</li>
              <li>Columns required: <strong className="text-white">Job Title, Industry, Location, Radius</strong>.</li>
              <li>Row level safety: If a row fails to scrape, JobPulse log lists the failure, bypasses, and proceeds automatically to successive rows.</li>
              <li>Bulk jobs are auto-deduplicated across search domains.</li>
            </ul>
          </div>

          <div className="border-t border-[#1f2937] pt-4 mt-6">
            <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 font-mono">Row Completion</h4>
            {progress ? (
              <div className="flex flex-col gap-2">
                <div className="flex justify-between text-xs font-semibold text-indigo-400">
                  <span>{progress.current} of {progress.total} Completed</span>
                  <span>{Math.round((progress.current / progress.total) * 100)}%</span>
                </div>
                <div className="w-full bg-[#1b2333] h-2 rounded-full overflow-hidden border border-[#374151]">
                  <div 
                    className="bg-indigo-600 h-full rounded-full transition-all duration-300"
                    style={{ width: `${(progress.current / progress.total) * 100}%` }}
                  ></div>
                </div>
              </div>
            ) : (
              <p className="text-xs text-gray-500 italic">No job processing active.</p>
            )}
          </div>
        </div>
      </div>

      {/* Progress / Status Logs */}
      {loading && (
        <div className="bg-[#111827] border border-[#1f2937] rounded-2xl p-6 shadow-xl flex items-center gap-4">
          <Loader2 className="h-6 w-6 animate-spin text-indigo-400 shrink-0" />
          <div>
            <p className="text-sm font-semibold text-white">{progressMessage}</p>
            {progress && (
              <p className="text-xs text-gray-500 font-mono mt-0.5">Processed {completedRowsCount} of {progress.total} rows</p>
            )}
          </div>
        </div>
      )}

      {/* Warnings alert for bulk entries */}
      {warnings.length > 0 && (
        <div className="bg-amber-950/20 border border-amber-500/30 rounded-2xl p-5 shadow-lg flex flex-col gap-2">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0" />
            <h4 className="font-semibold text-amber-200 text-sm">Processing Notes & Warnings</h4>
          </div>
          <ul className="list-disc pl-8 text-xs text-amber-300/80 flex flex-col gap-1 max-h-40 overflow-y-auto">
            {warnings.map((warn, index) => (
              <li key={index}>{warn}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Aggregate Results View */}
      {!loading && jobs.length > 0 && (
        <div className="bg-[#111827] border border-[#1f2937] rounded-2xl shadow-xl overflow-hidden flex flex-col gap-4 p-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1f2937] pb-5">
            <div>
              <h3 className="text-lg font-bold text-white flex flex-wrap items-center gap-2">
                Bulk Search Output 
                <span className="text-xs bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-2 py-0.5 rounded-full font-bold">{jobs.length} jobs verified</span>
                <span className="text-xs bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 px-2 py-0.5 rounded-full font-medium">{successCount} Succeeded</span>
                {failureCount > 0 && (
                  <span className="text-xs bg-red-500/10 text-red-300 border border-red-500/20 px-2 py-0.5 rounded-full font-medium">{failureCount} Failed</span>
                )}
              </h3>
              <p className="text-xs text-gray-400 mt-1">Showing aggregated and clean direct employer jobs from all successful queries.</p>
            </div>

            <button
              onClick={downloadResultsCSV}
              className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2.5 rounded-xl text-xs font-semibold transition-all duration-300 shadow-md"
            >
              <Download className="h-4 w-4" /> Export Report (CSV)
            </button>
          </div>

          <div className="overflow-x-auto rounded-xl border border-[#1f2937]">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#1b2333] border-b border-[#1f2937]">
                  <th className="px-5 py-4 text-xs font-bold uppercase tracking-wider text-gray-400">Job Title</th>
                  <th className="px-5 py-4 text-xs font-bold uppercase tracking-wider text-gray-400">Employer</th>
                  <th className="px-5 py-4 text-xs font-bold uppercase tracking-wider text-gray-400">Source</th>
                  <th className="px-5 py-4 text-xs font-bold uppercase tracking-wider text-gray-400">Location</th>
                  <th className="px-5 py-4 text-xs font-bold uppercase tracking-wider text-gray-400">Match Details</th>
                  <th className="px-5 py-4 text-xs font-bold uppercase tracking-wider text-gray-400 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1f2937]">
                {jobs.map((job, idx) => (
                  <tr key={idx} className="hover:bg-[#151c2c] transition-colors duration-200">
                    <td className="px-5 py-4 font-semibold text-white text-sm">
                      <div className="flex flex-col gap-0.5">
                        <span>{job.job_title}</span>
                        <span className="text-[10px] text-gray-500 font-medium font-mono">{job.job_type || "Permanent"}</span>
                      </div>
                    </td>
                    <td className="px-5 py-4 text-gray-300 text-sm">{job.company_name}</td>
                    <td className="px-5 py-4 text-xs">
                      <span className="px-2 py-1 rounded-md border font-semibold bg-[#1f2937] text-indigo-300 border-[#374151]">
                        {job.job_website}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-gray-300 text-sm">{job.location}</td>
                    <td className="px-5 py-4 text-gray-400 text-xs max-w-sm truncate" title={job.match_reason}>
                      {job.match_reason}
                    </td>
                    <td className="px-5 py-4 text-right">
                      <a
                        href={job.job_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 bg-indigo-600/20 hover:bg-indigo-600 border border-indigo-500/30 hover:border-indigo-600 text-indigo-300 hover:text-white px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-300"
                      >
                        Open Job <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
