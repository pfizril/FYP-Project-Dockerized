"use client"

import { useEffect, useState, useCallback } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Activity, Shield, AlertTriangle, TrendingUp, Users, Download, RefreshCw, Eye, EyeOff, ChevronLeft, ChevronRight, ChevronDown, ChevronUp, Loader2 } from "lucide-react"
import { ChartContainer } from "@/components/ui/chart"
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  RadialLinearScale,
  Filler,
} from "chart.js"
import { Bar, Pie, Radar, Line } from "react-chartjs-2"
import { security } from "@/lib/api/security"

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  RadialLinearScale,
  Filler,
)

interface SecurityData {
  trafficAnalysis: {
    total_requests: number
    top_ips: Array<{ ip: string; request_count: number }>
    suspicious_ips: string[]
    method_distribution: Record<string, number>
    endpoint_hits: Record<string, number>
    timestamp: string
  }
  threatScores: Array<{
    ip: string
    score: number
    threat_type: string
    details: string
    timestamp: string
  }>
  attackedEndpoints: {
    total_attacks: number
    total_pages: number
    current_page: number
    page_size: number
    attacked_endpoints: Array<{
      attack_id: number
      endpoint: string
      method: string
      attack_type: string
      client_ip: string
      attack_count: number
      first_seen: string
      last_seen: string
      recommended_fix: string
      severity: string
      is_resolved: boolean
      resolution_notes: string | null
      created_at: string
      updated_at: string
    }>
    severity_distribution: Record<string, number>
    attack_type_distribution: Record<string, number>
    timestamp: string
  }
  threatIndicators: {
    sql_injection: number
    xss_attempts: number
    path_traversal: number
    unauthorized_access: number
    rate_limit_violations: number
    suspicious_ips: number
  }
  threatTrends: {
    timeframe: string
    timeInterval: string
    trend_data: Array<{
      timestamp: string
      total_threats: number
      sql_injection: number
      xss_attempts: number
      path_traversal: number
      unauthorized_access: number
      rate_limit_violations: number
      other_threats: number
    }>
    total_threats: number
    timestamp: string
  }
}

// LogTable component
function LogTable({ logs, columns }: { logs: any[]; columns: string[] }) {
  if (!logs || logs.length === 0) return <div className="text-muted-foreground p-4">No logs found.</div>;
  return (
    <div className="overflow-x-auto max-h-72">
      <table className="min-w-full text-xs border rounded-lg">
        <thead>
          <tr className="bg-muted">
            {columns.map(col => (
              <th key={col} className="px-3 py-2 text-left capitalize">{col.replace(/_/g, ' ')}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {logs.map((log, idx) => (
            <tr key={idx} className="border-b">
              {columns.map(col => (
                <td key={col} className="px-3 py-2 font-mono">{log[col]?.toString() ?? '-'}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

type ThreatEvent = {
  timestamp: string;
  ip: string;
  threat_type: string;
  endpoint: string;
  status: string;
  score: number;
};

export function ModernSecurityDashboard() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState("overview")
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize] = useState(10)
  const [expandedVulnerabilities, setExpandedVulnerabilities] = useState<Set<number>>(new Set())
  const [timeframe, setTimeframe] = useState("24h")
  const [timeInterval, setTimeInterval] = useState("1h")
  const [securityData, setSecurityData] = useState<SecurityData>({
    trafficAnalysis: {
      total_requests: 0,
      top_ips: [],
      suspicious_ips: [],
      method_distribution: {},
      endpoint_hits: {},
      timestamp: "",
    },
    threatScores: [],
    attackedEndpoints: {
      total_attacks: 0,
      total_pages: 0,
      current_page: 1,
      page_size: pageSize,
      attacked_endpoints: [],
      severity_distribution: {},
      attack_type_distribution: {},
      timestamp: "",
    },
    threatIndicators: {
      sql_injection: 0,
      xss_attempts: 0,
      path_traversal: 0,
      unauthorized_access: 0,
      rate_limit_violations: 0,
      suspicious_ips: 0,
    },
    threatTrends: {
      timeframe: "",
      timeInterval: "",
      trend_data: [],
      total_threats: 0,
      timestamp: "",
    },
  })

  // Handler for opening full request log for an IP
  const [selectedIp, setSelectedIp] = useState<string | null>(null);
  const openIpLog = (ip: string) => setSelectedIp(ip);
  const closeIpLog = () => setSelectedIp(null);

  // Helper: Get threat score for an IP
  const getThreatScore = (ip: string) => {
    const threat = securityData.threatScores.find(t => t.ip === ip);
    return threat ? threat.score : null;
  };
  // Helper: Get anomaly type for an IP (example logic)
  const getAnomaly = (ip: string) => {
    const threat = securityData.threatScores.find(t => t.ip === ip);
    if (threat) return threat.threat_type.replace(/_/g, ' ');
    // fallback: check for rate-limit or suspicious_ips
    if (securityData.trafficAnalysis.suspicious_ips.includes(ip)) return 'Suspicious activity';
    return '';
  };
  // Helper: Get last seen (mocked as now for demo)
  const getLastSeen = (ip: string) => {
    const threat = securityData.threatScores.find(t => t.ip === ip);
    if (threat) return new Date(threat.timestamp).toLocaleString();
    return 'N/A';
  };

  // Main security data fetch
  const fetchSecurityData = useCallback(async (forceRefresh = false) => {
    if (loading) return;
  
    // Check if we need to refresh based on last refresh time
    const now = new Date();
    const lastRefreshTime = lastRefresh ? new Date(lastRefresh).getTime() : 0;
    const timeSinceLastRefresh = now.getTime() - lastRefreshTime;
    
    // Only refresh if forced or if it's been more than 5 minutes
    if (!forceRefresh && timeSinceLastRefresh < 5 * 60 * 1000) {
      return;
    }
  
    setLoading(true);
    setError(null);
  
    try {
      // Fetch data in parallel to reduce total request time
      const [trafficAnalysis, threatScores, threatIndicators, threatTrends, attackedEndpointsResponse] = await Promise.all([
        security.getTrafficAnalysis(),
        security.getThreatScores(),
        security.getThreatIndicators(),
        security.getThreatTrends(timeframe, timeInterval),
        security.getAttackedEndpoints(currentPage, pageSize)
      ]);
  
      setSecurityData(prev => ({
        ...prev,
        trafficAnalysis,
        threatScores: Array.isArray(threatScores?.threat_scores) ? threatScores.threat_scores : [],
        threatIndicators,
        threatTrends,
        attackedEndpoints: attackedEndpointsResponse
      }));
      
      setLastRefresh(new Date());
    } catch (err) {
      console.error("Error fetching security data", err);
      setError("Failed to fetch security data. Please check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }, [loading, lastRefresh, timeframe, timeInterval, currentPage, pageSize]);

  // Effect for main security data refresh
  useEffect(() => {
    fetchSecurityData();
    const intervalId = setInterval(() => {
      fetchSecurityData(false); // Pass false for normal refresh
    }, 5 * 60 * 1000); // 5 minutes
    return () => clearInterval(intervalId);
  }, []); // Keep empty dependencies to prevent recreation

  const handleRefresh = () => {
    fetchSecurityData(true); // Force refresh
  };
  
  const handleExportLogs = async () => {
    try {
      const blob = await security.exportLogs()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `security-logs-${new Date().toISOString()}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      console.error("Failed to export security logs", err)
      setError("Failed to export security logs. Please try again.")
    }
  }

  const handleExportThreatLogs = async () => {
    try {
      const blob = await security.exportThreatLogs()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `threat-logs-${new Date().toISOString()}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      console.error("Failed to export threat logs", err)
      setError("Failed to export threat logs. Please try again.")
    }
  }

  const handleExportTrafficLogs = async () => {
    try {
      const blob = await security.exportTrafficLogs()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `traffic-logs-${new Date().toISOString()}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      console.error("Failed to export traffic logs", err)
      setError("Failed to export traffic logs. Please try again.")
    }
  }

  // Detect theme (dark or light)
  const isDark = typeof window !== "undefined"
    ? document.documentElement.classList.contains("dark")
    : false;

  const axisColor = isDark ? "#fff" : "#222";
  const gridColor = isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.08)";
  const legendColor = isDark ? "#fff" : "#222";
  const tooltipBg = isDark ? "rgba(30,30,30,0.95)" : "rgba(255,255,255,0.95)";
  const tooltipText = isDark ? "#fff" : "#222";
  const tooltipBorder = isDark ? "#fff" : "#222";

  // Chart data preparation
  const methodDistributionData = {
    labels: Object.keys(securityData.trafficAnalysis.method_distribution),
    datasets: [
      {
        label: "Request Methods",
        data: Object.values(securityData.trafficAnalysis.method_distribution),
        backgroundColor: [
          "rgba(54, 162, 235, 0.8)",  // Blue
          "rgba(255, 99, 132, 0.8)",  // Pink
          "rgba(75, 192, 192, 0.8)",  // Teal
          "rgba(255, 206, 86, 0.8)",  // Yellow
          "rgba(153, 102, 255, 0.8)", // Purple
        ],
        borderColor: [
          "rgba(54, 162, 235, 1)",
          "rgba(255, 99, 132, 1)",
          "rgba(75, 192, 192, 1)",
          "rgba(255, 206, 86, 1)",
          "rgba(153, 102, 255, 1)",
        ],
        borderWidth: 1,
      },
    ],
  }

  const topIpsData = {
    labels: securityData.trafficAnalysis.top_ips.map((ip) => ip.ip),
    datasets: [
      {
        label: "Request Count",
        data: securityData.trafficAnalysis.top_ips.map((ip) => ip.request_count),
        backgroundColor: "rgba(54, 162, 235, 0.8)",
        borderColor: "rgba(54, 162, 235, 1)",
        borderWidth: 1,
      },
    ],
  }

  // Aggregate threat scores by type for Radar chart
  const aggregatedThreatScores = securityData.threatScores.reduce((acc, threat) => {
    acc[threat.threat_type] = (acc[threat.threat_type] || 0) + threat.score;
    return acc;
  }, {} as Record<string, number>);

  // Prepare Bar chart data for threat scores
  const barThreatScoreData = {
    labels: Object.keys(aggregatedThreatScores).map(type => type.replace(/_/g, " ")),
    datasets: [
      {
        label: "Threat Type Score",
        data: Object.values(aggregatedThreatScores),
        backgroundColor: [
          "rgba(255, 99, 132, 0.7)",
          "rgba(255, 159, 64, 0.7)",
          "rgba(255, 205, 86, 0.7)",
          "rgba(75, 192, 192, 0.7)",
          "rgba(54, 162, 235, 0.7)",
          "rgba(153, 102, 255, 0.7)",
          "rgba(201, 203, 207, 0.7)",
        ],
        borderColor: "rgba(255, 99, 132, 1)",
        borderWidth: 1,
        borderRadius: 8,
        maxBarThickness: 40,
      },
    ],
  }

  const barChartOptions = {
    indexAxis: "y", // Horizontal bar
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        backgroundColor: "hsl(var(--card))",
        titleColor: "hsl(var(--card-foreground))",
        bodyColor: "hsl(var(--muted-foreground))",
        borderColor: "hsl(var(--border))",
        borderWidth: 1,
      },
    },
    scales: {
      x: {
        beginAtZero: true,
        ticks: { color: "hsl(var(--muted-foreground))", font: { size: 14 } },
        grid: { color: "hsl(var(--border))" },
      },
      y: {
        ticks: { color: "hsl(var(--muted-foreground))", font: { size: 14 } },
        grid: { color: "hsl(var(--border))" },
      },
    },
  }

  // Threat trends line chart data
  const threatTrendsData = {
    labels: securityData.threatTrends.trend_data.map(item => {
      const date = new Date(item.timestamp);
      return securityData.threatTrends.timeInterval === "1h" 
        ? date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
        : date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }),
    datasets: [
      {
        label: "Total Threats",
        data: securityData.threatTrends.trend_data.map(item => item.total_threats),
        borderColor: "rgba(255, 99, 132, 1)",
        backgroundColor: "rgba(255, 99, 132, 0.1)",
        borderWidth: 2,
        fill: false,
        tension: 0.4,
      },
      {
        label: "SQL Injection",
        data: securityData.threatTrends.trend_data.map(item => item.sql_injection),
        borderColor: "rgba(255, 159, 64, 1)",
        backgroundColor: "rgba(255, 159, 64, 0.1)",
        borderWidth: 2,
        fill: false,
        tension: 0.4,
      },
      {
        label: "XSS Attempts",
        data: securityData.threatTrends.trend_data.map(item => item.xss_attempts),
        borderColor: "rgba(255, 205, 86, 1)",
        backgroundColor: "rgba(255, 205, 86, 0.1)",
        borderWidth: 2,
        fill: false,
        tension: 0.4,
      },
      {
        label: "Path Traversal",
        data: securityData.threatTrends.trend_data.map(item => item.path_traversal),
        borderColor: "rgba(153, 102, 255, 1)",
        backgroundColor: "rgba(153, 102, 255, 0.1)",
        borderWidth: 2,
        fill: false,
        tension: 0.4,
      },
      {
        label: "Unauthorized Access",
        data: securityData.threatTrends.trend_data.map(item => item.unauthorized_access),
        borderColor: "rgba(54, 162, 235, 1)",
        backgroundColor: "rgba(54, 162, 235, 0.1)",
        borderWidth: 2,
        fill: false,
        tension: 0.4,
      },
    ],
  }

  const lineChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "top" as const,
        labels: {
          font: { size: 14, weight: "bold" as const },
          color: legendColor,
          usePointStyle: true,
        },
      },
      tooltip: {
        backgroundColor: tooltipBg,
        titleColor: tooltipText,
        bodyColor: tooltipText,
        borderColor: tooltipBorder,
        borderWidth: 1,
        titleFont: { size: 16, weight: "bold" as const },
        bodyFont: { size: 14 },
        mode: 'index' as const,
        intersect: false,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: { 
          font: { size: 14, weight: "bold" as const },
          color: axisColor,
        },
        grid: {
          color: gridColor,
        },
      },
      x: {
        ticks: { 
          font: { size: 14, weight: "bold" as const },
          color: axisColor,
          maxRotation: 45,
        },
        grid: {
          color: gridColor,
        },
      },
    },
    interaction: {
      mode: 'nearest' as const,
      axis: 'x' as const,
      intersect: false,
    },
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "top" as const,
        labels: {
          font: { size: 12 },
          color: "hsl(var(--foreground))", // Use foreground color for better contrast
        },
      },
      tooltip: {
        backgroundColor: "hsl(var(--card))",
        titleColor: "hsl(var(--card-foreground))",
        bodyColor: "hsl(var(--muted-foreground))",
        borderColor: "hsl(var(--border))",
        borderWidth: 1,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: { 
          font: { size: 12 },
          color: "hsl(var(--muted-foreground))",
        },
        grid: {
          color: "hsl(var(--border))",
        },
      },
      x: {
        ticks: { 
          font: { size: 12 },
          color: "hsl(var(--muted-foreground))",
        },
        grid: {
          color: "hsl(var(--border))",
        },
      },
    },
  }

  const radarOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "top" as const,
        labels: {
          font: { size: 12 },
          color: "hsl(var(--foreground))",
        },
      },
      tooltip: {
        backgroundColor: "hsl(var(--card))",
        titleColor: "hsl(var(--card-foreground))",
        bodyColor: "hsl(var(--muted-foreground))",
        borderColor: "hsl(var(--border))",
        borderWidth: 1,
      },
    },
    scales: {
      r: {
        beginAtZero: true,
        min: 0,
        max: 100,
        ticks: {
          stepSize: 20,
          color: "hsl(var(--muted-foreground))",
        },
        grid: {
          color: "hsl(var(--border))",
        },
        angleLines: {
          color: "hsl(var(--border))",
        },
        pointLabels: {
          color: "hsl(var(--foreground))",
          font: { size: 12 },
        },
      },
    },
  }

  // Pie chart options for Method Distribution (no background, no grid)
  const pieChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "top" as const,
        labels: {
          font: { size: 12 },
          color: "hsl(var(--foreground))",
        },
      },
      tooltip: {
        backgroundColor: "hsl(var(--card))",
        titleColor: "hsl(var(--card-foreground))",
        bodyColor: "hsl(var(--muted-foreground))",
        borderColor: "hsl(var(--border))",
        borderWidth: 1,
      },
    },
    // Remove grid and background for Pie
    layout: {
      padding: 0,
    },
    backgroundColor: "transparent",
  };

  // Threat Indicator Bar Chart Data
  const threatIndicatorBarData = {
    labels: [
      "SQL Injection",
      "XSS Attempts",
      "Path Traversal",
      "Unauthorized Access",
      "Rate Limit Violations"
    ],
    datasets: [
      {
        label: "Threats",
        data: [
          securityData.threatIndicators.sql_injection,
          securityData.threatIndicators.xss_attempts,
          securityData.threatIndicators.path_traversal,
          securityData.threatIndicators.unauthorized_access,
          securityData.threatIndicators.rate_limit_violations
        ],
        backgroundColor: [
          "rgba(239, 68, 68, 0.7)",    // red
          "rgba(251, 146, 60, 0.7)",   // orange
          "rgba(253, 224, 71, 0.7)",   // yellow
          "rgba(220, 38, 38, 0.7)",    // dark red
          "rgba(168, 85, 247, 0.7)"    // purple
        ],
        borderRadius: 8,
        maxBarThickness: 40,
      }
    ]
  };

  const threatIndicatorBarOptions = {
    indexAxis: "y" as const,
    plugins: { legend: { display: false } },
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: { beginAtZero: true, ticks: { font: { size: 14 } } },
      y: { ticks: { font: { size: 14 } } }
    }
  };

  const handlePageChange = (newPage: number) => {
    if (newPage < 1 || newPage > securityData.attackedEndpoints.total_pages) return;
    setCurrentPage(newPage);
  };

  const toggleVulnerabilityExpansion = (index: number) => {
    const newExpanded = new Set(expandedVulnerabilities)
    if (newExpanded.has(index)) {
      newExpanded.delete(index)
    } else {
      newExpanded.add(index)
    }
    setExpandedVulnerabilities(newExpanded)
  }

  // Helper: Detect traffic spike from single IP
  const topIps = securityData.trafficAnalysis.top_ips;
  const totalRequests = securityData.trafficAnalysis.total_requests;
  const avgRequests = topIps.length > 0 ? topIps.reduce((sum, ip) => sum + ip.request_count, 0) / topIps.length : 0;
  const spikeIp = topIps.find(ip => ip.request_count > avgRequests * 3 && ip.request_count > 100); // arbitrary threshold

  // Prepare line chart data for request volume over time
  const trafficTrendData = {
    labels: securityData.trafficAnalysis.endpoint_hits ? Object.keys(securityData.trafficAnalysis.endpoint_hits) : [],
    datasets: [
      {
        label: "Total Requests",
        data: securityData.trafficAnalysis.endpoint_hits ? Object.values(securityData.trafficAnalysis.endpoint_hits) : [],
        borderColor: "rgba(54, 162, 235, 1)",
        backgroundColor: "rgba(54, 162, 235, 0.1)",
        borderWidth: 2,
        pointRadius: 3,
        tension: 0.4,
        fill: true,
      },
    ],
  };
  const trafficTrendOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {},
    },
    scales: {
      x: { ticks: { font: { size: 12 } } },
      y: { beginAtZero: true, ticks: { font: { size: 12 } } },
    },
  };

  // State for logs modal
  const [ipLogs, setIpLogs] = useState<any>(null);
  const [ipLogsLoading, setIpLogsLoading] = useState(false);
  const [ipLogsError, setIpLogsError] = useState<string | null>(null);
  const [ipLogsTab, setIpLogsTab] = useState("threat_logs");

  useEffect(() => {
    if (selectedIp) {
      setIpLogsLoading(true);
      setIpLogsError(null);
      security.getLogsByIp(selectedIp)
        .then(setIpLogs)
        .catch((err) => setIpLogsError(err.message || "Failed to fetch logs"))
        .finally(() => setIpLogsLoading(false));
    } else {
      setIpLogs(null);
      setIpLogsError(null);
    }
  }, [selectedIp]);

  // Threat Timeline/Feed state
  const [threatFilterIp, setThreatFilterIp] = useState("");
  const [threatFilterType, setThreatFilterType] = useState("");
  const [threatFilterScore, setThreatFilterScore] = useState("");
  const [threatFilterTime, setThreatFilterTime] = useState("");
  const [threatSort, setThreatSort] = useState<{ field: string; dir: "asc" | "desc" }>({ field: "timestamp", dir: "desc" });

  // Prepare threat event data (mock endpoint/status for demo)
  const threatEvents: ThreatEvent[] = securityData.threatScores.map((t) => ({
    timestamp: t.timestamp,
    ip: t.ip,
    threat_type: t.threat_type.replace(/_/g, " "),
    endpoint: t.details.match(/endpoint: ([^\s]+)/i)?.[1] || "/login",
    status: t.score > 70 ? "Active" : "Mitigated",
    score: t.score,
  }));

  // Filtering
  const filteredThreatEvents = threatEvents.filter(ev =>
    (!threatFilterIp || ev.ip.includes(threatFilterIp)) &&
    (!threatFilterType || ev.threat_type.toLowerCase().includes(threatFilterType.toLowerCase())) &&
    (!threatFilterScore || ev.score.toString().includes(threatFilterScore)) &&
    (!threatFilterTime || ev.timestamp.includes(threatFilterTime))
  );
  // Sorting
  const sortedThreatEvents = [...filteredThreatEvents].sort((a, b) => {
    const dir = threatSort.dir === "asc" ? 1 : -1;
    if (threatSort.field === "score") return (a.score - b.score) * dir;
    if (threatSort.field === "timestamp") return (new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()) * dir;
    return (a[threatSort.field] > b[threatSort.field] ? 1 : -1) * dir;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Security Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor threats, analyze traffic, and manage security across your API endpoints
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleExportThreatLogs}>
            <Download className="mr-2 h-4 w-4" />
            Export Threat Logs
          </Button>
          <Button variant="outline" onClick={handleExportTrafficLogs}>
            <Download className="mr-2 h-4 w-4" />
            Export Traffic Logs
          </Button>
          <Button variant="outline" onClick={handleExportLogs}>
            <Download className="mr-2 h-4 w-4" />
            Export All Logs
          </Button>
          <Button onClick={handleRefresh} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Overview Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Requests</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{securityData.trafficAnalysis.total_requests.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">Last 24 hours</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Suspicious IPs</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">
              {securityData.trafficAnalysis.suspicious_ips.length}
            </div>
            <p className="text-xs text-muted-foreground">Flagged for review</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Attacked Endpoints</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">
              {securityData.attackedEndpoints.attacked_endpoints
                .filter(result =>
                  !result.endpoint.includes('/test/health') && !result.endpoint.includes('/test/health-check')
                ).length}
            </div>
            <p className="text-xs text-muted-foreground">Endpoints under attack</p>
          </CardContent>
        </Card>
      </div>

      {/* Threat Indicators */}
      <Card>
        <CardHeader>
          <CardTitle>Active Threat Indicators</CardTitle>
          <CardDescription>Real-time security threats detected in the last 24 hours</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div className="flex items-center space-x-2">
              <Shield className="h-4 w-4 text-destructive" />
              <div>
                <p className="text-sm font-medium">SQL Injection</p>
                <p className="text-2xl font-bold">{securityData.threatIndicators.sql_injection}</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <AlertTriangle className="h-4 w-4 text-orange-500" />
              <div>
                <p className="text-sm font-medium">XSS Attempts</p>
                <p className="text-2xl font-bold">{securityData.threatIndicators.xss_attempts}</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Eye className="h-4 w-4 text-red-500" />
              <div>
                <p className="text-sm font-medium">Path Traversal</p>
                <p className="text-2xl font-bold">{securityData.threatIndicators.path_traversal}</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <EyeOff className="h-4 w-4 text-red-600" />
              <div>
                <p className="text-sm font-medium">Unauthorized Access</p>
                <p className="text-2xl font-bold">{securityData.threatIndicators.unauthorized_access}</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <TrendingUp className="h-4 w-4 text-yellow-500" />
              <div>
                <p className="text-sm font-medium">Rate Limit Violations</p>
                <p className="text-2xl font-bold">{securityData.threatIndicators.rate_limit_violations}</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Users className="h-4 w-4 text-orange-600" />
              <div>
                <p className="text-sm font-medium">Suspicious IPs</p>
                <p className="text-2xl font-bold">{securityData.threatIndicators.suspicious_ips}</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabs for detailed views */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="traffic">Traffic Analysis</TabsTrigger>
          <TabsTrigger value="threats">Threat Detection</TabsTrigger>
          <TabsTrigger value="trends">Threat Trends</TabsTrigger>
          <TabsTrigger value="attacked-endpoints">Attacked Endpoints</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Method Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <ChartContainer config={{}} className="h-[300px]">
                  <Pie data={methodDistributionData} options={pieChartOptions} />
                </ChartContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Real-Time Threat Indicators</CardTitle>
                <CardDescription>
                  Live breakdown of detected security threats in the last 24 hours
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[260px]">
                  <Bar data={threatIndicatorBarData} options={threatIndicatorBarOptions} />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Threat Trends Over Time */}
          <Card>
            <CardHeader>
              <CardTitle>Threat Trends Over Time</CardTitle>
              <CardDescription>
                Monitor threat patterns and identify security trends over the last 24 hours
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ChartContainer config={{}} className="h-[400px]">
                {securityData.threatTrends.trend_data.length > 0 ? (
                  <Line data={threatTrendsData} options={lineChartOptions} />
                ) : (
                  <div className="flex h-full items-center justify-center text-muted-foreground">
                    No threat trend data available
                  </div>
                )}
              </ChartContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="traffic" className="space-y-4">
          {/* Anomalous Traffic Patterns Section */}
          <Card>
            <CardHeader>
              <CardTitle>Anomalous Traffic Patterns</CardTitle>
              <CardDescription>
                Line chart of total request volume over time. Alerts highlight sudden spikes or drop-offs.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Alert for traffic spike from single IP */}
              {spikeIp && (
                <Alert variant="destructive" className="mb-4">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    Traffic spike detected from IP <span className="font-mono font-bold">{spikeIp.ip}</span> with {spikeIp.request_count} requests (avg: {Math.round(avgRequests)}).
                  </AlertDescription>
                </Alert>
              )}
              <div className="h-[260px]">
                <ChartContainer config={{}} className="h-full w-full">
                  <Line data={trafficTrendData} options={trafficTrendOptions} />
                </ChartContainer>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Suspicious IP Behavior Table</CardTitle>
              <CardDescription>
                Click a row to view the full request log for that IP
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm border rounded-lg">
                  <thead>
                    <tr className="bg-muted">
                      <th className="px-4 py-2 text-left">IP Address</th>
                      <th className="px-4 py-2 text-left">Total Requests</th>
                      <th className="px-4 py-2 text-left">Anomalies</th>
                      <th className="px-4 py-2 text-left">Last Seen</th>
                      <th className="px-4 py-2 text-left">Threat Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {securityData.trafficAnalysis.top_ips.map((ipObj, idx) => (
                      <tr
                        key={ipObj.ip}
                        className="hover:bg-blue-50 dark:hover:bg-blue-900 cursor-pointer border-b"
                        onClick={() => openIpLog(ipObj.ip)}
                      >
                        <td className="px-4 py-2 font-mono">{ipObj.ip}</td>
                        <td className="px-4 py-2">{ipObj.request_count}</td>
                        <td className="px-4 py-2">{getAnomaly(ipObj.ip)}</td>
                        <td className="px-4 py-2">{getLastSeen(ipObj.ip)}</td>
                        <td className="px-4 py-2 font-bold">{getThreatScore(ipObj.ip) ?? '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {/* Modal or drawer for full request log */}
              {selectedIp && (
                <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
                  <div className="bg-white dark:bg-zinc-900 rounded-lg shadow-lg p-6 w-full max-w-3xl relative">
                    <button className="absolute top-2 right-2 text-lg" onClick={closeIpLog}>&times;</button>
                    <h3 className="text-xl font-bold mb-2">Request Log for {selectedIp}</h3>
                    {ipLogsLoading ? (
                      <div className="flex items-center justify-center h-32"><Loader2 className="animate-spin h-8 w-8 text-blue-500" /></div>
                    ) : ipLogsError ? (
                      <div className="text-red-600">{ipLogsError}</div>
                    ) : ipLogs ? (
                      <Tabs value={ipLogsTab} onValueChange={setIpLogsTab} className="space-y-2">
                        <TabsList>
                          <TabsTrigger value="threat_logs">Threat Logs</TabsTrigger>
                          <TabsTrigger value="traffic_logs">Traffic Logs</TabsTrigger>
                          <TabsTrigger value="api_requests">API Requests</TabsTrigger>
                          <TabsTrigger value="activity_logs">Activity Logs</TabsTrigger>
                        </TabsList>
                        <TabsContent value="threat_logs">
                          <LogTable logs={ipLogs.threat_logs} columns={["created_at", "activity", "detail"]} />
                        </TabsContent>
                        <TabsContent value="traffic_logs">
                          <LogTable logs={ipLogs.traffic_logs} columns={["timestamp", "endpoint", "request_method"]} />
                        </TabsContent>
                        <TabsContent value="api_requests">
                          <LogTable logs={ipLogs.api_requests} columns={["timestamp", "endpoint", "method", "status_code", "response_time"]} />
                        </TabsContent>
                        <TabsContent value="activity_logs">
                          <LogTable logs={ipLogs.activity_logs} columns={["timestamp", "action", "user_id"]} />
                        </TabsContent>
                      </Tabs>
                    ) : (
                      <div className="text-muted-foreground">No logs found for this IP.</div>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Top IPs by Request Volume</CardTitle>
              </CardHeader>
              <CardContent>
                <ChartContainer config={{}} className="h-[300px]">
                  <Bar data={topIpsData} options={chartOptions} />
                </ChartContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Suspicious IPs</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {securityData.trafficAnalysis.suspicious_ips.length > 0 ? (
                    securityData.trafficAnalysis.suspicious_ips.map((ip, index) => (
                      <div key={index} className="flex items-center justify-between p-2 border rounded">
                        <span className="font-mono">{ip}</span>
                        <Badge variant="destructive">Suspicious</Badge>
                      </div>
                    ))
                  ) : (
                    <p className="text-center text-muted-foreground">No suspicious IPs detected</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="threats" className="space-y-4">
          {/* Recent Threat Events */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Threat Events</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {securityData.threatScores.length > 0 ? (
                  securityData.threatScores.map((threat, index) => (
                    <div key={index} className="flex items-center justify-between p-3 border rounded">
                      <div>
                        <p className="font-medium">{threat.ip}</p>
                        <p className="text-sm text-muted-foreground">{threat.details}</p>
                      </div>
                      <div className="text-right">
                        <Badge
                          variant={threat.score > 70 ? "destructive" : threat.score > 40 ? "secondary" : "default"}
                        >
                          Score: {threat.score}
                        </Badge>
                        <p className="text-xs text-muted-foreground mt-1">
                          {new Date(threat.timestamp).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-center text-muted-foreground">No threat events detected</p>
                )}
              </div>
            </CardContent>
          </Card>
          {/* Threat Timeline / Feed */}
          <Card>
            <CardHeader>
              <CardTitle>Threat Timeline / Feed</CardTitle>
              <CardDescription>
                View and filter recent threat events. Click column headers to sort.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2 mb-2">
                <input type="text" placeholder="Filter by IP" value={threatFilterIp} onChange={e => setThreatFilterIp(e.target.value)} className="px-2 py-1 border rounded text-xs" />
                <input type="text" placeholder="Filter by Type" value={threatFilterType} onChange={e => setThreatFilterType(e.target.value)} className="px-2 py-1 border rounded text-xs" />
                <input type="text" placeholder="Filter by Score" value={threatFilterScore} onChange={e => setThreatFilterScore(e.target.value)} className="px-2 py-1 border rounded text-xs" />
                <input type="text" placeholder="Filter by Time" value={threatFilterTime} onChange={e => setThreatFilterTime(e.target.value)} className="px-2 py-1 border rounded text-xs" />
              </div>
              <div className="overflow-x-auto max-h-80">
                <table className="min-w-full text-xs border rounded-lg">
                  <thead>
                    <tr className="bg-muted">
                      <th className="px-3 py-2 text-left cursor-pointer select-none" onClick={() => setThreatSort(s => ({ field: "timestamp", dir: s.field === "timestamp" ? (s.dir === "asc" ? "desc" : "asc") : "desc" }))}>
                        Timestamp{threatSort.field === "timestamp" ? (threatSort.dir === "asc" ? " ▲" : " ▼") : ""}
                      </th>
                      <th className="px-3 py-2 text-left cursor-pointer select-none" onClick={() => setThreatSort(s => ({ field: "ip", dir: s.field === "ip" ? (s.dir === "asc" ? "desc" : "asc") : "desc" }))}>
                        IP Address{threatSort.field === "ip" ? (threatSort.dir === "asc" ? " ▲" : " ▼") : ""}
                      </th>
                      <th className="px-3 py-2 text-left cursor-pointer select-none" onClick={() => setThreatSort(s => ({ field: "threat_type", dir: s.field === "threat_type" ? (s.dir === "asc" ? "desc" : "asc") : "desc" }))}>
                        Threat Type{threatSort.field === "threat_type" ? (threatSort.dir === "asc" ? " ▲" : " ▼") : ""}
                      </th>
                      <th className="px-3 py-2 text-left cursor-pointer select-none" onClick={() => setThreatSort(s => ({ field: "endpoint", dir: s.field === "endpoint" ? (s.dir === "asc" ? "desc" : "asc") : "desc" }))}>
                        Endpoint{threatSort.field === "endpoint" ? (threatSort.dir === "asc" ? " ▲" : " ▼") : ""}
                      </th>
                      <th className="px-3 py-2 text-left cursor-pointer select-none" onClick={() => setThreatSort(s => ({ field: "status", dir: s.field === "status" ? (s.dir === "asc" ? "desc" : "asc") : "desc" }))}>
                        Status{threatSort.field === "status" ? (threatSort.dir === "asc" ? " ▲" : " ▼") : ""}
                      </th>
                      <th className="px-3 py-2 text-left cursor-pointer select-none" onClick={() => setThreatSort(s => ({ field: "score", dir: s.field === "score" ? (s.dir === "asc" ? "desc" : "asc") : "desc" }))}>
                        Score{threatSort.field === "score" ? (threatSort.dir === "asc" ? " ▲" : " ▼") : ""}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedThreatEvents.length === 0 ? (
                      <tr><td colSpan={6} className="text-center text-muted-foreground py-4">No threat events found.</td></tr>
                    ) : (
                      sortedThreatEvents.map((ev, idx) => (
                        <tr key={idx} className="border-b">
                          <td className="px-3 py-2 font-mono whitespace-nowrap">{new Date(ev.timestamp).toLocaleString()}</td>
                          <td className="px-3 py-2 font-mono">{ev.ip}</td>
                          <td className="px-3 py-2">{ev.threat_type}</td>
                          <td className="px-3 py-2 font-mono">{ev.endpoint}</td>
                          <td className={`px-3 py-2 font-bold ${ev.status === "Active" ? "text-red-600" : "text-green-600"}`}>{ev.status}</td>
                          <td className="px-3 py-2 font-bold">{ev.score}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="trends" className="space-y-4">
          {/* Timeframe Controls */}
            <Card>
              <CardHeader>
              <CardTitle>Threat Trends Analysis</CardTitle>
                <CardDescription>
                Monitor threat patterns and identify security trends over time
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-4 mb-4">
                <div className="flex flex-col space-y-2">
                  <label className="text-sm font-medium">Timeframe</label>
                  <select 
                    value={timeframe} 
                    onChange={(e) => setTimeframe(e.target.value)}
                    className="px-3 py-2 border rounded-md text-sm"
                  >
                    <option value="24h">Last 24 Hours</option>
                    <option value="7d">Last 7 Days</option>
                    <option value="30d">Last 30 Days</option>
                  </select>
                </div>
                <div className="flex flex-col space-y-2">
                  <label className="text-sm font-medium">Interval</label>
                  <select 
                    value={timeInterval} 
                    onChange={(e) => setTimeInterval(e.target.value)}
                    className="px-3 py-2 border rounded-md text-sm"
                  >
                    <option value="1h">Hourly</option>
                    <option value="1d">Daily</option>
                  </select>
                </div>
                <div className="flex items-end">
                  <Button 
                    onClick={() => fetchSecurityData(true)}
                    disabled={loading}
                    variant="outline"
                    size="sm"
                  >
                    <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                    Refresh
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-4">
            {/* Detailed Threat Trends Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Threat Trends Analysis</CardTitle>
                <CardDescription>
                  Comprehensive view of security threats over time with detailed breakdown by threat type
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ChartContainer config={{}} className="h-[500px]">
                  {securityData.threatTrends.trend_data.length > 0 ? (
                    <Line data={threatTrendsData} options={lineChartOptions} />
                  ) : (
                    <div className="flex h-full items-center justify-center text-muted-foreground">
                      No threat trend data available
                    </div>
                  )}
                </ChartContainer>
              </CardContent>
            </Card>

            {/* Threat Trends Summary */}
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Threats (24h)</CardTitle>
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{securityData.threatTrends.total_threats}</div>
                  <p className="text-xs text-muted-foreground">
                    {securityData.threatTrends.timeframe} timeframe
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Peak Hour</CardTitle>
                  <Activity className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {securityData.threatTrends.trend_data.length > 0 
                      ? (() => {
                          const peakData = securityData.threatTrends.trend_data.reduce((max, current) => 
                            current.total_threats > max.total_threats ? current : max
                          );
                          const date = new Date(peakData.timestamp);
                          return securityData.threatTrends.timeInterval === "1h" 
                            ? date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
                            : date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                        })()
                      : "N/A"
                    }
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Highest threat activity
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Trend Direction</CardTitle>
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {securityData.threatTrends.trend_data.length > 2 
                      ? (() => {
                          const recent = securityData.threatTrends.trend_data.slice(-3);
                          const firstHalf = recent.slice(0, Math.ceil(recent.length / 2));
                          const secondHalf = recent.slice(Math.ceil(recent.length / 2));
                          const firstAvg = firstHalf.reduce((sum, item) => sum + item.total_threats, 0) / firstHalf.length;
                          const secondAvg = secondHalf.reduce((sum, item) => sum + item.total_threats, 0) / secondHalf.length;
                          return secondAvg > firstAvg ? "↗️ Increasing" : secondAvg < firstAvg ? "↘️ Decreasing" : "→ Stable";
                        })()
                      : "→ Stable"
                    }
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Threat activity trend
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Threat Type Breakdown */}
            <Card>
              <CardHeader>
                <CardTitle>Threat Type Distribution</CardTitle>
                <CardDescription>
                  Breakdown of threats by category over the selected timeframe
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {securityData.threatTrends.trend_data.length > 0 && (() => {
                    const totals = securityData.threatTrends.trend_data.reduce((acc, item) => ({
                      sql_injection: acc.sql_injection + item.sql_injection,
                      xss_attempts: acc.xss_attempts + item.xss_attempts,
                      path_traversal: acc.path_traversal + item.path_traversal,
                      unauthorized_access: acc.unauthorized_access + item.unauthorized_access,
                      rate_limit_violations: acc.rate_limit_violations + item.rate_limit_violations,
                      other_threats: acc.other_threats + item.other_threats,
                    }), {
                      sql_injection: 0,
                      xss_attempts: 0,
                      path_traversal: 0,
                      unauthorized_access: 0,
                      rate_limit_violations: 0,
                      other_threats: 0,
                    });

                    return [
                      { label: "SQL Injection", value: totals.sql_injection, color: "text-red-600" },
                      { label: "XSS Attempts", value: totals.xss_attempts, color: "text-orange-600" },
                      { label: "Path Traversal", value: totals.path_traversal, color: "text-yellow-600" },
                      { label: "Unauthorized Access", value: totals.unauthorized_access, color: "text-blue-600" },
                      { label: "Rate Limit Violations", value: totals.rate_limit_violations, color: "text-purple-600" },
                      { label: "Other Threats", value: totals.other_threats, color: "text-gray-600" },
                    ].map((item, index) => (
                      <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                        <div>
                          <p className="text-sm font-medium">{item.label}</p>
                          <p className={`text-2xl font-bold ${item.color}`}>{item.value}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-xs text-muted-foreground">
                            {securityData.threatTrends.total_threats > 0 
                              ? `${((item.value / securityData.threatTrends.total_threats) * 100).toFixed(1)}%`
                              : "0%"
                            }
                          </p>
                        </div>
                      </div>
                    ));
                  })()}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="attacked-endpoints" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Attacked Endpoints</CardTitle>
              <CardDescription>
                Detailed analysis of endpoints that have been attacked with security recommendations
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="space-y-3">
                  {securityData.attackedEndpoints.attacked_endpoints.length > 0 ? (
                    securityData.attackedEndpoints.attacked_endpoints
                      .map((attack, index) => ({ attack, index }))
                      .filter(({ attack }) =>
                        !attack.endpoint.includes('/test/health') && !attack.endpoint.includes('/test/health-check')
                      )
                      .map(({ attack, index }) => {
                          const isExpanded = expandedVulnerabilities.has(index)
                          
                          return (
                          <div key={attack.attack_id || index} className="border rounded-lg overflow-hidden border">
                              {/* Header */}
                              <div 
                                className="p-4 bg-muted hover:bg-muted/80 cursor-pointer flex items-center justify-between"
                                onClick={() => toggleVulnerabilityExpansion(index)}
                              >
                                <div className="flex-1">
                                  <div className="flex items-center gap-3">
                                    <div className="flex gap-2">
                                    <Badge 
                                      variant={attack.severity === 'high' ? 'destructive' : attack.severity === 'medium' ? 'secondary' : 'outline'}
                                    >
                                      {attack.severity.toUpperCase()}: {attack.attack_type}
                                    </Badge>
                                    <Badge variant="outline">
                                      {attack.attack_count} attacks
                                    </Badge>
                                    </div>
                                  </div>
                                <p className="font-medium text-sm mt-1 break-all">{attack.endpoint}</p>
                                <p className="text-xs text-muted-foreground mt-1">
                                  {attack.method} • {attack.client_ip} • Last seen: {new Date(attack.last_seen).toLocaleString()}
                                </p>
                                </div>
                                <div className="flex items-center gap-2">
                                  {isExpanded ? (
                                    <ChevronUp className="h-4 w-4 text-muted-foreground" />
                                  ) : (
                                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                  )}
                                </div>
                              </div>

                              {/* Expandable Content */}
                              {isExpanded && (
                                <div className="p-4 border-t bg-card">
                                  <div className="space-y-4">
                                  {/* Attack Details */}
                                      <div>
                                        <h4 className="font-semibold text-red-600 mb-2 flex items-center gap-2">
                                          <AlertTriangle className="h-4 w-4" />
                                      Attack Details
                                        </h4>
                                        <div className="space-y-2">
                                      <div className="p-3 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-md">
                                        <div className="font-medium text-red-800 dark:text-red-200">Attack Type: {attack.attack_type}</div>
                                        <div className="text-sm text-red-700 dark:text-red-300 mt-1">Client IP: {attack.client_ip}</div>
                                        <div className="text-sm text-red-700 dark:text-red-300">Method: {attack.method}</div>
                                        <div className="text-sm text-red-700 dark:text-red-300">First Seen: {new Date(attack.first_seen).toLocaleString()}</div>
                                        <div className="text-sm text-red-700 dark:text-red-300">Last Seen: {new Date(attack.last_seen).toLocaleString()}</div>
                                        <div className="text-sm text-red-700 dark:text-red-300">Total Attacks: {attack.attack_count}</div>
                                              </div>
                                            </div>
                                        </div>

                                  {/* Recommended Fix */}
                                      <div>
                                    <h4 className="font-semibold text-blue-600 mb-2 flex items-center gap-2">
                                      <Shield className="h-4 w-4" />
                                      Recommended Fix
                                        </h4>
                                    <div className="p-3 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-md">
                                      <div className="text-sm text-blue-700 dark:text-blue-300">{attack.recommended_fix}</div>
                                              </div>
                                            </div>

                                  {/* Resolution Status */}
                                  {attack.is_resolved && (
                                      <div>
                                      <h4 className="font-semibold text-green-600 mb-2 flex items-center gap-2">
                                          <Shield className="h-4 w-4" />
                                        Resolution Notes
                                        </h4>
                                      <div className="p-3 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-md">
                                        <div className="text-sm text-green-700 dark:text-green-300">{attack.resolution_notes || 'Attack has been resolved'}</div>
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              )}
                            </div>
                          )
                        })
                    ) : (
                      <div className="text-center py-8">
                        <Shield className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                      <p className="text-muted-foreground">No attacked endpoints found</p>
                      <p className="text-sm text-muted-foreground mt-1">All endpoints appear to be secure</p>
                      </div>
                    )}
                  </div>
                  
                  {/* Pagination Controls */}
                  <div className="flex items-center justify-between pt-4 border-t">
                    <div className="text-sm text-muted-foreground">
                    Page {securityData.attackedEndpoints.current_page} of {securityData.attackedEndpoints.total_pages}
                      <span className="ml-2">
                      ({securityData.attackedEndpoints.total_attacks} attacks detected)
                      </span>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handlePageChange(currentPage - 1)}
                        disabled={currentPage === 1}
                      >
                        <ChevronLeft className="h-4 w-4" />
                        Previous
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handlePageChange(currentPage + 1)}
                      disabled={currentPage === securityData.attackedEndpoints.total_pages}
                      >
                        Next
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
        </TabsContent>
      </Tabs>

      {lastRefresh && (
        <p className="text-sm text-muted-foreground text-center">Last updated: {lastRefresh.toLocaleString()}</p>
      )}
    </div>
  )
}
