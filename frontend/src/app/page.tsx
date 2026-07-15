"use client";

import { useState, useRef, useEffect } from "react";
import { 
  Search, 
  MapPin, 
  Compass, 
  HelpCircle, 
  Loader2, 
  ExternalLink, 
  AlertTriangle, 
  CheckCircle,
  Briefcase,
  ChevronRight,
  Filter,
  Calendar,
  Building,
  Download
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

export default function NewSearch() {
  const [formData, setFormData] = useState({
    job_title: "",
    industry: "",
    location: "UK",
    radius: 25,
  });

  const tableRef = useRef<HTMLDivElement>(null);

  const [loading, setLoading] = useState(false);
  const [progressStep, setProgressStep] = useState<string>("");
  const [progressMessage, setProgressMessage] = useState<string>("");
  const [expandedTitles, setExpandedTitles] = useState<string[]>([]);
  const [scrapedCounts, setScrapedCounts] = useState<{ linkedin: number; indeed: number; cvlibrary: number } | null>(null);
  
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [siteFilter, setSiteFilter] = useState("all");

  useEffect(() => {
    if (progressStep === "completed" && tableRef.current) {
      setTimeout(() => {
        tableRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 100);
    }
  }, [progressStep]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setJobs([]);
    setWarnings([]);
    setProgressStep("validate");
    setProgressMessage("Validating search criteria...");
    setExpandedTitles([]);
    setScrapedCounts(null);

    const apiUrl = "http://localhost:8000";

    try {
      const response = await fetch(`${apiUrl}/api/search`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "ngrok-skip-browser-warning": "true",
        },
        body: JSON.stringify(formData),
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
        buffer = lines.pop() || ""; // Keep the last incomplete line in the buffer

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line);
            
            if (data.step) setProgressStep(data.step);
            if (data.message) setProgressMessage(data.message);
            
            if (data.step === "titles_list" && data.expanded) {
              setExpandedTitles(data.expanded);
            }
            
            if (data.step === "scraped_counts" && data.counts) {
              setScrapedCounts(data.counts);
            }
            
            if (data.step === "completed") {
              setJobs(data.jobs || []);
              setWarnings(data.warnings || []);
              setLoading(false);
            }
            
            if (data.step === "error") {
              throw new Error(data.message);
            }
          } catch (err) {
            console.error("Error parsing stream line:", err);
          }
        }
      }
    } catch (err: any) {
      setProgressStep("error");
      setProgressMessage(err.message || "An unexpected error occurred.");
      setLoading(false);
    }
  };

  const downloadExcel = () => {
    if (filteredJobs.length === 0) return;
    const headers = ["Job Title", "Company Name", "Job Site", "Location", "Date Posted", "Industry Match", "Job Type", "Match Reason", "Advert Link"];
    const csvContent = [
      headers.join(","),
      ...filteredJobs.map(j => [
        `"${j.job_title.replace(/"/g, '""')}"`,
        `"${j.company_name.replace(/"/g, '""')}"`,
        `"${j.job_website}"`,
        `"${j.location.replace(/"/g, '""')}"`,
        `"${j.date_posted}"`,
        `"${j.industry_match === true ? 'Yes' : j.industry_match === false ? 'No' : j.industry_match}"`,
        `"${(j.job_type || "Permanent").replace(/"/g, '""')}"`,
        `"${j.match_reason.replace(/"/g, '""')}"`,
        `"${j.job_url}"`
      ].join(","))
    ].join("\n");

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `JobPulse_${formData.job_title.replace(/\s+/g, '_')}_Results.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const filteredJobs = jobs.filter((job) => {
    const matchesSearch = 
      job.job_title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      job.company_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      job.location.toLowerCase().includes(searchTerm.toLowerCase());
      
    const matchesSite = siteFilter === "all" || job.job_website.toLowerCase() === siteFilter.toLowerCase();
    
    return matchesSearch && matchesSite;
  });

  return (
    <div className="flex-1 p-8 max-w-7xl mx-auto w-full flex flex-col gap-8">
      {/* Top Banner Header */}
      <div className="flex flex-col gap-2">
        <h2 className="text-3xl font-extrabold text-white tracking-tight">
          Vacancy Demand Verification
        </h2>
        <p className="text-gray-400 max-w-2xl">
          Search live UK job boards concurrently to verify market demand, expand related job titles, and filter out recruitment agency listings automatically.
        </p>
      </div>

      {/* Grid: Search controls & related terms */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Search Card */}
        <div className="lg:col-span-2 bg-[#111827] border border-[#1f2937] rounded-2xl p-6 shadow-xl relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-indigo-500 to-purple-600"></div>
          <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
            <Search className="h-5 w-5 text-indigo-400" /> Search Parameters
          </h3>

          <form onSubmit={handleSearch} className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Job Title</label>
              <div className="relative">
                <Briefcase className="absolute left-3.5 top-3.5 h-5 w-5 text-gray-500" />
                <input
                  type="text"
                  required
                  value={formData.job_title}
                  onChange={(e) => setFormData({ ...formData, job_title: e.target.value })}
                  placeholder="e.g. Estimator"
                  className="w-full bg-[#1b2333] border border-[#374151] rounded-xl py-3 pl-11 pr-4 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Industry / Sector</label>
              <div className="relative">
                <Compass className="absolute left-3.5 top-3.5 h-5 w-5 text-gray-500" />
                <input
                  type="text"
                  required
                  value={formData.industry}
                  onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
                  placeholder="e.g. Construction"
                  className="w-full bg-[#1b2333] border border-[#374151] rounded-xl py-3 pl-11 pr-4 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Location</label>
              <div className="relative">
                <MapPin className="absolute left-3.5 top-3.5 h-5 w-5 text-gray-500" />
                <input
                  type="text"
                  required
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  placeholder="e.g. London"
                  className="w-full bg-[#1b2333] border border-[#374151] rounded-xl py-3 pl-11 pr-4 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Search Radius (Miles)</label>
              <select
                value={formData.radius}
                onChange={(e) => setFormData({ ...formData, radius: parseInt(e.target.value) })}
                className="w-full bg-[#1b2333] border border-[#374151] rounded-xl py-3 px-4 text-white focus:outline-none focus:border-indigo-500 transition-colors"
              >
                <option value={5}>5 Miles</option>
                <option value={10}>10 Miles</option>
                <option value={15}>15 Miles</option>
                <option value={20}>20 Miles</option>
                <option value={25}>25 Miles</option>
                <option value={50}>50 Miles</option>
                <option value={100}>100 Miles</option>
              </select>
            </div>

            <div className="md:col-span-2 mt-2">
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-800/40 text-white font-medium py-3.5 rounded-xl transition-all duration-300 flex items-center justify-center gap-2.5 shadow-lg shadow-indigo-600/20"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    <span>Processing Search...</span>
                  </>
                ) : (
                  <>
                    <Search className="h-5 w-5" />
                    <span>Run Verification Search</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Right Side: Quick Info & Title expansion display */}
        <div className="bg-[#111827] border border-[#1f2937] rounded-2xl p-6 flex flex-col justify-between shadow-xl">
          <div>
            <h3 className="text-lg font-bold text-white mb-4">Title Expansion</h3>
            <p className="text-xs text-gray-400 leading-relaxed mb-4">
              To verify demand exhaustively, JobPulse automatically expands search queries to closely related variations (e.g. Senior/Lead roles) matching the target sector.
            </p>

            {expandedTitles.length > 0 ? (
              <div className="flex flex-wrap gap-2 mt-2 max-h-40 overflow-y-auto pr-1">
                {expandedTitles.map((title, i) => (
                  <span key={i} className="text-xs bg-[#1f2937] text-indigo-300 border border-[#374151] px-2.5 py-1.5 rounded-lg flex items-center gap-1 font-medium">
                    <ChevronRight className="h-3 w-3 text-indigo-400 shrink-0" /> {title}
                  </span>
                ))}
              </div>
            ) : (
              <div className="border border-dashed border-[#1f2937] rounded-xl p-6 text-center text-gray-500 text-xs my-4">
                No active search. Expansions display here when search starts.
              </div>
            )}
          </div>

          <div className="border-t border-[#1f2937] pt-4 mt-4">
            <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Filters Applied</h4>
            <div className="flex flex-col gap-1.5 text-xs text-gray-500">
              <span className="flex items-center gap-1.5"><CheckCircle className="h-3.5 w-3.5 text-emerald-500 shrink-0" /> UK Vacancies Only</span>
              <span className="flex items-center gap-1.5"><CheckCircle className="h-3.5 w-3.5 text-emerald-500 shrink-0" /> Posted in last 3 months</span>
              <span className="flex items-center gap-1.5"><CheckCircle className="h-3.5 w-3.5 text-emerald-500 shrink-0" /> Direct employer listings only</span>
            </div>
          </div>
        </div>
      </div>

      {/* Progress & Board Counters (Visible when loading or displaying logs) */}
      {loading && (
        <div className="bg-[#111827] border border-[#1f2937] rounded-2xl p-6 shadow-xl flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <Loader2 className="h-6 w-6 animate-spin text-indigo-400" />
            <div className="flex-1">
              <p className="text-sm font-semibold text-white">{progressMessage}</p>
              <p className="text-xs text-gray-500 uppercase tracking-wider font-mono mt-0.5">Pipeline Step: {progressStep}</p>
            </div>
          </div>

          {/* Detailed Counts & Badges */}
          {scrapedCounts && (
            <div className="flex flex-col gap-3 border-t border-[#1f2937] pt-4">
              <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1 font-mono">Platform Scraper Metrics</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {["linkedin", "indeed", "cvlibrary"].map((key) => {
                  const stat = (scrapedCounts as any)[key] || { found: 0, valid: 0, removed: 0, status: "idle", message: "Pending..." };
                  const name = key === "linkedin" ? "LinkedIn UK" : key === "indeed" ? "Indeed UK" : "CV-Library UK";
                  
                  let borderBg = "border-[#1f2937] bg-[#141b2b]";
                  let statusBadge = null;

                  if (stat.status === "success") {
                    borderBg = "border-emerald-500/20 bg-emerald-500/5";
                    statusBadge = <span className="text-xs font-bold text-emerald-400 flex items-center gap-1">✔ Active</span>;
                  } else if (stat.status === "failed") {
                    borderBg = "border-red-500/20 bg-red-500/5";
                    statusBadge = <span className="text-xs font-bold text-red-400 flex items-center gap-1">⚠ {stat.message || "Blocked"}</span>;
                  } else if (stat.status === "no_results") {
                    borderBg = "border-amber-500/20 bg-amber-500/5";
                    statusBadge = <span className="text-xs font-bold text-amber-400 flex items-center gap-1">⚠ No Results</span>;
                  }

                  return (
                    <div key={key} className={`border rounded-xl p-4 flex flex-col gap-2 transition-all ${borderBg}`}>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-bold text-white">{name}</span>
                        {statusBadge}
                      </div>
                      
                      {stat.status === "success" && (
                        <div className="grid grid-cols-3 gap-2 mt-1 text-center font-mono text-[11px]">
                          <div className="bg-[#1b2333]/55 rounded py-1 px-1.5 border border-[#1f2937]">
                            <span className="block text-gray-500 text-[9px] uppercase font-bold">Found</span>
                            <span className="text-white font-extrabold">{stat.found}</span>
                          </div>
                          <div className="bg-emerald-950/20 rounded py-1 px-1.5 border border-emerald-500/10">
                            <span className="block text-emerald-500/60 text-[9px] uppercase font-bold">Valid</span>
                            <span className="text-emerald-400 font-extrabold">{stat.valid}</span>
                          </div>
                          <div className="bg-red-950/20 rounded py-1 px-1.5 border border-red-500/10">
                            <span className="block text-red-400/60 text-[9px] uppercase font-bold">Filtered</span>
                            <span className="text-red-400 font-extrabold">{stat.removed}</span>
                          </div>
                        </div>
                      )}
                      
                      {stat.status === "failed" && (
                        <p className="text-xs text-gray-500 mt-1 leading-relaxed">
                          Crawlers hit bot protection protocols. System fallback is waiting or returns 0.
                        </p>
                      )}

                      {stat.status === "no_results" && (
                        <p className="text-xs text-gray-500 mt-1 leading-relaxed">
                          Scrape complete, but zero vacancies matched the criteria.
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Error or Warnings Alert */}
      {progressStep === "error" && (
        <div className="bg-red-950/20 border border-red-500/30 rounded-2xl p-5 flex items-start gap-3 shadow-lg">
          <AlertTriangle className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-red-200 text-sm">Search Run Failed</h4>
            <p className="text-xs text-red-300/80 mt-1">{progressMessage}</p>
          </div>
        </div>
      )}

      {warnings.length > 0 && (
        <div className="bg-amber-950/20 border border-amber-500/30 rounded-2xl p-5 flex flex-col gap-2 shadow-lg">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0" />
            <h4 className="font-semibold text-amber-200 text-sm">Board Notifications</h4>
          </div>
          <ul className="list-disc pl-8 text-xs text-amber-300/80 flex flex-col gap-1">
            {warnings.map((warn, index) => (
              <li key={index}>{warn}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Results Workspace */}
      {!loading && jobs.length > 0 && (
        <div ref={tableRef} className="bg-[#111827] border border-[#1f2937] rounded-2xl shadow-xl overflow-hidden flex flex-col gap-4 p-6 scroll-mt-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1f2937] pb-5">
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                Verified Vacancies <span className="text-xs bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-2 py-0.5 rounded-full font-bold">{filteredJobs.length}</span>
              </h3>
              <p className="text-xs text-gray-400 mt-1">Listing only direct employers. All recruitment agencies filtered out.</p>
            </div>

            {/* Filter controls */}
            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={downloadExcel}
                className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg text-xs font-semibold transition-colors border border-emerald-500/50 shadow-lg shadow-emerald-600/20"
              >
                <Download className="h-4 w-4" />
                Export CSV
              </button>

              {/* Site selector dropdown */}
              <select
                value={siteFilter}
                onChange={(e) => setSiteFilter(e.target.value)}
                className="bg-[#1b2333] border border-[#374151] rounded-lg py-2 px-3 text-xs text-white focus:outline-none focus:border-indigo-500 transition-colors"
              >
                <option value="all">All Sources</option>
                <option value="linkedin">LinkedIn</option>
                <option value="indeed">Indeed</option>
                <option value="cv-library">CV-Library</option>
              </select>
            </div>
          </div>

          {/* Table Container */}
          <div className="overflow-x-auto rounded-xl border border-[#1f2937]">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#1b2333] border-b border-[#1f2937] whitespace-nowrap">
                  <th className="px-3 py-3 text-xs font-bold uppercase tracking-wider text-gray-400">Job Title</th>
                  <th className="px-3 py-3 text-xs font-bold uppercase tracking-wider text-gray-400">Company Name</th>
                  <th className="px-3 py-3 text-xs font-bold uppercase tracking-wider text-gray-400">Job Site</th>
                  <th className="px-3 py-3 text-xs font-bold uppercase tracking-wider text-gray-400">Location</th>
                  <th className="px-3 py-3 text-xs font-bold uppercase tracking-wider text-gray-400">Date Posted</th>
                  <th className="px-3 py-3 text-xs font-bold uppercase tracking-wider text-gray-400">Industry Match</th>
                  <th className="px-3 py-3 text-xs font-bold uppercase tracking-wider text-gray-400">Job Type</th>
                  <th className="px-3 py-3 text-xs font-bold uppercase tracking-wider text-gray-400">Match Reason</th>
                  <th className="px-3 py-3 text-xs font-bold uppercase tracking-wider text-gray-400 text-right pr-4">Advert Link</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1f2937]">
                {filteredJobs.map((job, idx) => {
                  let badgeBg = "bg-indigo-500/10 text-indigo-300 border-indigo-500/20";
                  if (job.job_website.toLowerCase() === "linkedin") badgeBg = "bg-blue-500/10 text-blue-300 border-blue-500/20";
                  else if (job.job_website.toLowerCase() === "indeed") badgeBg = "bg-sky-500/10 text-sky-300 border-sky-500/20";

                  return (
                    <tr key={idx} className="hover:bg-[#151c2c] transition-colors duration-200">
                      <td className="px-3 py-3 font-semibold text-white text-sm max-w-[180px] break-words">
                        {job.job_title}
                      </td>
                      <td className="px-3 py-3 text-gray-300 text-sm whitespace-nowrap">
                        <div className="flex items-center gap-1.5 relative">
                          <Building className="h-3.5 w-3.5 text-gray-500 shrink-0" />
                          <details className="group cursor-pointer max-w-[120px]">
                            <summary className="truncate list-none [&::-webkit-details-marker]:hidden outline-none hover:text-white transition-colors">
                              {job.company_name}
                            </summary>
                            <div className="absolute top-full left-0 mt-1.5 whitespace-normal text-gray-300 leading-relaxed bg-[#111827] p-2 rounded border border-[#1f2937] shadow-lg z-20 min-w-[200px]">
                              {job.company_name}
                            </div>
                          </details>
                        </div>
                      </td>
                      <td className="px-3 py-3 text-xs whitespace-nowrap">
                        <span className={`px-2 py-1 rounded-md border font-semibold ${badgeBg}`}>
                          {job.job_website}
                        </span>
                      </td>
                      <td className="px-3 py-3 text-gray-300 text-sm max-w-[120px]">
                        <details className="group cursor-pointer relative">
                          <summary className="truncate list-none [&::-webkit-details-marker]:hidden outline-none hover:text-white transition-colors">
                            {job.location}
                          </summary>
                          <div className="absolute top-full left-0 mt-1.5 whitespace-normal text-gray-300 leading-relaxed bg-[#111827] p-2 rounded border border-[#1f2937] shadow-lg z-20 min-w-[200px]">
                            {job.location}
                          </div>
                        </details>
                      </td>
                      <td className="px-3 py-3 text-gray-400 text-xs whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <Calendar className="h-3.5 w-3.5 text-gray-600 shrink-0" />
                          <span>{job.date_posted}</span>
                        </div>
                      </td>
                      <td className="px-3 py-3 text-emerald-400 font-semibold text-xs whitespace-nowrap">
                        {job.industry_match === true ? "Yes" : job.industry_match === false ? "No" : job.industry_match}
                      </td>
                      <td className="px-3 py-3 text-gray-400 text-xs whitespace-nowrap">
                        {job.job_type || "Permanent"}
                      </td>
                      <td className="px-3 py-3 text-gray-400 text-xs max-w-[200px]">
                        <details className="group cursor-pointer">
                          <summary className="truncate list-none [&::-webkit-details-marker]:hidden outline-none hover:text-gray-300 transition-colors">
                            {job.match_reason}
                          </summary>
                          <div className="mt-1.5 whitespace-normal text-gray-300 leading-relaxed bg-[#111827] p-2 rounded border border-[#1f2937] shadow-lg relative z-10">
                            {job.match_reason}
                          </div>
                        </details>
                      </td>
                      <td className="px-3 py-3 text-right pr-4 whitespace-nowrap">
                        <a
                          href={job.job_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 bg-indigo-600/20 hover:bg-indigo-600 border border-indigo-500/30 hover:border-indigo-600 text-indigo-300 hover:text-white px-2 py-1 rounded-lg text-xs font-semibold transition-all duration-300"
                        >
                          Open <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* No jobs state */}
      {!loading && jobs.length === 0 && progressStep === "completed" && (
        <div className="bg-[#111827] border border-[#1f2937] rounded-2xl p-12 text-center shadow-xl">
          <HelpCircle className="h-12 w-12 text-gray-500 mx-auto mb-4" />
          <h3 className="text-lg font-bold text-white mb-2">No matching vacancies were found.</h3>
          <p className="text-sm text-gray-400 max-w-md mx-auto mb-4">
            Try adjusting your search criteria, widening the radius, or double-checking for spelling variations.
          </p>
          <div className="text-left text-xs bg-black/50 p-4 rounded border border-red-500 text-red-300 font-mono">
            <strong>DEBUG INFO:</strong><br />
            progressStep: {progressStep}<br />
            loading: {loading ? "true" : "false"}<br />
            jobs.length: {jobs.length}<br />
            filteredJobs.length: {filteredJobs.length}<br />
            If you see this, the React state has literally 0 jobs, but the backend log said it sent some! 
          </div>
        </div>
      )}
    </div>
  );
}
