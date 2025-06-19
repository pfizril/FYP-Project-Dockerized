"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ChartContainer } from "@/components/ui/chart"
import { Download, RefreshCw, Activity, Clock, AlertTriangle, TrendingUp, CheckCircle, XCircle, Search,Lock  } from "lucide-react"
import { useToast } from "@/components/ui/use-toast"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination"
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
} from "chart.js"
import { Line, Bar, Pie, Doughnut } from "react-chartjs-2"
import api from '@/lib/api'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend, ArcElement)

const API_BASE_URL = 'http://localhost:8000'

// Add these constants at the top after the API_BASE_URL
const TIMEOUT_DURATION = 15000; // 15 seconds
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // 1 second

// Helper function to get cookie value
function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(';').shift() || null;
  return null;
}

// Helper function to get auth headers
const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  const apiKey = localStorage.getItem('apiKey');

  if (!apiKey) {
    console.error('API Key not found in localStorage');
    return {
      'Content-Type': 'application/json',
      'X-API-KEY': '',
      'Authorization': `Bearer ${token || ''}`
    };
  }
  
  // Get CSRF token from cookies
  const csrfToken = getCookie('csrf_token');
  
  return {
    'Content-Type': 'application/json',
    'X-API-KEY': apiKey,
    'Authorization': `Bearer ${token || ''}`,
    ...(csrfToken && { 'X-CSRF-Token': csrfToken }),
  };
}

// Update the fetchWithTimeout function
const fetchWithTimeout = async (url: string, retries = MAX_RETRIES): Promise<any> => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_DURATION);

  try {
    const response = await api.get(url);
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (retries > 0 && (error instanceof Error && error.name === 'AbortError')) {
      // Wait before retrying
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
      return fetchWithTimeout(url, retries - 1);
    }
    throw error;
  }
};

export function ModernAnalyticsPage() {
  const [activeTab, setActiveTab] = useState("overview")
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState(new Date())
  const [error, setError] = useState<string | null>(null)
  const { toast } = useToast()

  // State for all analytics data
  const [overviewMetrics, setOverviewMetrics] = useState<any>(null)
  const [trafficInsights, setTrafficInsights] = useState<any[]>([])
  const [requestsBreakdown, setRequestsBreakdown] = useState<any>(null)
  const [performanceTrends, setPerformanceTrends] = useState<any>(null)
  const [clientInsights, setClientInsights] = useState<any[]>([])

  // State for endpoint health data
  const [endpointHealthData, setEndpointHealthData] = useState<any>(null)
  const [endpointHealthPage, setEndpointHealthPage] = useState(1)
  const [endpointHealthPageSize] = useState(5)
  const [endpointSearch, setEndpointSearch] = useState("")
  const [endpointStatusFilter, setEndpointStatusFilter] = useState("all")
  const [endpointMethodFilter, setEndpointMethodFilter] = useState("all")

  // Add new state for health scan
  const [healthScanLoading, setHealthScanLoading] = useState(false)
  const [healthScanResults, setHealthScanResults] = useState<any>(null)

  // Add state for scan period
  const [scanPeriod, setScanPeriod] = useState("1_week")

  // Fetch all analytics data
  const fetchAnalyticsData = async () => {
    try {
      setLoading(true)
      setError(null)

      // Fetch all data in parallel with timeout handling
      const [
        overviewResponse,
        trafficResponse,
        breakdownResponse,
        performanceResponse,
        clientsResponse
      ] = await Promise.all([
        fetchWithTimeout('/analytics/overview-metrics'),
        fetchWithTimeout('/analytics/traffic-insights'),
        fetchWithTimeout('/analytics/requests-breakdown'),
        fetchWithTimeout('/analytics/performance-trends'),
        fetchWithTimeout('/analytics/client-insights')
      ])

      if (!overviewResponse || !trafficResponse || !breakdownResponse || 
          !performanceResponse || !clientsResponse) {
        throw new Error('Failed to fetch analytics data')
      }

      const [overview, traffic, breakdown, performance, clients] = [
        overviewResponse,
        trafficResponse,
        breakdownResponse,
        performanceResponse,
        clientsResponse
      ]

      setOverviewMetrics(overview)
      setTrafficInsights(traffic)
      setRequestsBreakdown(breakdown)
      setPerformanceTrends(performance)
      setClientInsights(clients.requests_by_client)
      setLastUpdated(new Date())
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch analytics data'
      setError(errorMessage)
      toast({
        title: "Error",
        description: errorMessage === 'AbortError' ? 
          'Request timed out. Please try again.' : 
          'Failed to fetch analytics data',
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  // Fetch endpoint health data
  const fetchEndpointHealthData = async (page: number = 1) => {
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: endpointHealthPageSize.toString(),
        search: endpointSearch,
        status_filter: endpointStatusFilter,
        method_filter: endpointMethodFilter
      })
      
      const response = await fetchWithTimeout(`/analytics/endpoints/latest-health?${params}`)
      if (response) {
        setEndpointHealthData(response)
      }
    } catch (err) {
      console.error('Error fetching endpoint health data:', err)
      // Don't show error toast for this as it's not critical
    }
  }

  // Update runHealthScan to send scanPeriod
  const runHealthScan = async () => {
    try {
      setHealthScanLoading(true)
      setError(null)
      const response = await api.post('/analytics/run-health-scan', { scan_period: scanPeriod })
      if (response.data) {
        setHealthScanResults(response.data)
        toast({
          title: "Success",
          description: "Health scan completed successfully",
        })
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to run health scan'
      setError(errorMessage)
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      })
    } finally {
      setHealthScanLoading(false)
    }
  }

  useEffect(() => {
    fetchAnalyticsData()
    fetchEndpointHealthData(1)
  }, [])

  // Watch for changes in filter states and trigger fetch
  useEffect(() => {
    fetchEndpointHealthData(endpointHealthPage)
  }, [endpointSearch, endpointStatusFilter, endpointMethodFilter, endpointHealthPage])

  const handleEndpointHealthPageChange = (newPage: number) => {
    setEndpointHealthPage(newPage)
  }

  const handleEndpointSearchChange = (searchValue: string) => {
    setEndpointSearch(searchValue)
    setEndpointHealthPage(1) // Reset to first page
  }

  const handleEndpointStatusFilterChange = (statusValue: string) => {
    setEndpointStatusFilter(statusValue)
    setEndpointHealthPage(1) // Reset to first page
  }

  const handleEndpointMethodFilterChange = (methodValue: string) => {
    setEndpointMethodFilter(methodValue)
    setEndpointHealthPage(1) // Reset to first page
  }

  const handleExportLogs = async () => {
    try {
      setLoading(true)
      console.log('Starting export API request logs...')
      
      // Get auth headers
      const headers = getAuthHeaders()
      console.log('Auth headers:', headers)
      
      // Verify we have the required headers
      if (!headers['X-API-KEY']) {
        console.error('API key is missing')
        toast({
          title: "Error",
          description: "API key is missing. Please log in again.",
          variant: "destructive",
        })
        return
      }
      
      console.log('Making request to:', `${API_BASE_URL}/analytics/export-logs`)
      const response = await fetch(`${API_BASE_URL}/analytics/export-logs`, {
        method: 'GET',
        headers: headers,
        credentials: 'include'
      })
      
      console.log('Response status:', response.status)
      console.log('Response headers:', Object.fromEntries(response.headers.entries()))
      
      if (response.status === 401) {
        throw new Error('Authentication failed. Please log in again.')
      }
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        console.error('Error response:', errorData)
        throw new Error(errorData.detail || 'Failed to export logs')
      }

      // Get the filename from the Content-Disposition header
      const contentDisposition = response.headers.get('Content-Disposition')
      console.log('Content-Disposition:', contentDisposition)
      
      let filename = 'api_request_logs.csv'
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename=(.+)/)
        if (filenameMatch) {
          filename = filenameMatch[1]
        }
      }
      console.log('Using filename:', filename)

      // Create a blob from the response
      const blob = await response.blob()
      console.log('Blob size:', blob.size)
      
      if (blob.size === 0) {
        throw new Error('Received empty file')
      }
      
      // Create a download link
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.style.display = 'none'
      document.body.appendChild(a)
      
      console.log('Triggering download...')
      a.click()
      
      // Cleanup
      setTimeout(() => {
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
        console.log('Cleanup completed')
      }, 100)

      toast({
        title: "Success",
        description: "API request logs exported successfully",
      })
    } catch (err) {
      console.error('Export error:', err)
      const errorMessage = err instanceof Error ? err.message : 'Failed to export logs'
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleExportHealthLogs = async () => {
    try {
      setLoading(true)
      console.log('Starting export health logs...')
      
      // Get auth headers
      const headers = getAuthHeaders()
      console.log('Auth headers:', headers)
      
      // Verify we have the required headers
      if (!headers['X-API-KEY']) {
        console.error('API key is missing')
        toast({
          title: "Error",
          description: "API key is missing. Please log in again.",
          variant: "destructive",
        })
        return
      }
      
      console.log('Making request to:', `${API_BASE_URL}/analytics/export-health-logs`)
      const response = await fetch(`${API_BASE_URL}/analytics/export-health-logs`, {
        method: 'GET',
        headers: headers,
        credentials: 'include'
      })
      
      console.log('Response status:', response.status)
      console.log('Response headers:', Object.fromEntries(response.headers.entries()))
      
      if (response.status === 401) {
        throw new Error('Authentication failed. Please log in again.')
      }
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        console.error('Error response:', errorData)
        throw new Error(errorData.detail || 'Failed to export health logs')
      }

      // Get the filename from the Content-Disposition header
      const contentDisposition = response.headers.get('Content-Disposition')
      console.log('Content-Disposition:', contentDisposition)
      
      let filename = 'health_logs.csv'
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename=(.+)/)
        if (filenameMatch) {
          filename = filenameMatch[1]
        }
      }
      console.log('Using filename:', filename)

      // Create a blob from the response
      const blob = await response.blob()
      console.log('Blob size:', blob.size)
      
      if (blob.size === 0) {
        throw new Error('Received empty file')
      }
      
      // Create a download link
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.style.display = 'none'
      document.body.appendChild(a)
      
      console.log('Triggering download...')
      a.click()
      
      // Cleanup
      setTimeout(() => {
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
        console.log('Cleanup completed')
      }, 100)

      toast({
        title: "Success",
        description: "Health logs exported successfully",
      })
    } catch (err) {
      console.error('Export error:', err)
      const errorMessage = err instanceof Error ? err.message : 'Failed to export health logs'
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    await fetchAnalyticsData()
    await fetchEndpointHealthData(endpointHealthPage)
  }

  // Chart configurations
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "top" as const,
        labels: { font: { size: 12 } },
      },
    },
    scales: {
      y: { beginAtZero: true },
      x: { ticks: { font: { size: 10 } } },
    },
  }

  // Custom chart options for traffic chart - optimized for readability
  const trafficChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "top" as const,
        labels: { 
          font: { size: 14 },
          padding: 20
        },
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleFont: { size: 14 },
        bodyFont: { size: 13 },
        padding: 12,
        cornerRadius: 8,
        displayColors: true,
      },
    },
    scales: {
      y: { 
        beginAtZero: true,
        ticks: { 
          font: { size: 12 },
          padding: 8,
          callback: function(value: any): string {
            return value.toLocaleString();
          }
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.1)',
          lineWidth: 1,
        },
        title: {
          display: true,
          text: 'Request Count',
          font: { size: 14 },
          padding: { top: 10, bottom: 10 }
        }
      },
      x: { 
        ticks: { 
          font: { size: 11 },
          maxRotation: 45,
          minRotation: 0,
          padding: 8,
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.05)',
          lineWidth: 1,
        },
        title: {
          display: true,
          text: 'API Endpoints',
          font: { size: 14 },
          padding: { top: 10, bottom: 10 }
        }
      },
    },
    layout: {
      padding: {
        top: 20,
        bottom: 20,
        left: 20,
        right: 20
      }
    },
    elements: {
      bar: {
        borderRadius: 6,
        borderSkipped: false,
      }
    },
    interaction: {
      intersect: false,
      mode: 'index' as const,
    },
  }

  const pieOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "right" as const,
        labels: { font: { size: 11 } },
      },
    },
  }

  // Chart data
  const requestVolumeData = {
    labels: ["Total", "Failed", "4xx", "5xx"],
    datasets: [
      {
        label: "Request Count",
        data: overviewMetrics ? [
          overviewMetrics.total_requests,
          overviewMetrics.failed_requests,
          overviewMetrics.total_4xx,
          overviewMetrics.total_5xx,
        ] : [],
        backgroundColor: [
          "rgba(54, 162, 235, 0.8)",  // Blue
          "rgba(255, 99, 132, 0.8)",  // Red
          "rgba(255, 159, 64, 0.8)",  // Orange
          "rgba(153, 102, 255, 0.8)", // Purple
        ],
        borderColor: [
          "rgba(54, 162, 235, 1)",
          "rgba(255, 99, 132, 1)",
          "rgba(255, 159, 64, 1)",
          "rgba(153, 102, 255, 1)",
        ],
        borderWidth: 1,
      },
    ],
  }

  const methodDistributionData = {
    labels: requestsBreakdown?.requests_by_method ? Object.keys(requestsBreakdown.requests_by_method) : [],
    datasets: [
      {
        data: requestsBreakdown?.requests_by_method ? Object.values(requestsBreakdown.requests_by_method) : [],
        backgroundColor: [
          "rgba(75, 192, 192, 0.8)",  // Teal
          "rgba(255, 205, 86, 0.8)",  // Yellow
          "rgba(54, 162, 235, 0.8)",  // Blue
          "rgba(153, 102, 255, 0.8)", // Purple
        ],
        borderColor: [
          "rgba(75, 192, 192, 1)",
          "rgba(255, 205, 86, 1)",
          "rgba(54, 162, 235, 1)",
          "rgba(153, 102, 255, 1)",
        ],
        borderWidth: 1,
      },
    ],
  }

  const performanceTrendsData = {
    labels: performanceTrends?.performance_trends ? 
      performanceTrends.performance_trends.map((d: any) =>
        new Date(d.hour).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      ) : [],
    datasets: [
      {
        label: "Avg Response Time (ms)",
        data: performanceTrends?.performance_trends ? 
          performanceTrends.performance_trends.map((d: any) => d.avg_response_time) : [],
        borderColor: "rgba(75, 192, 192, 1)",
        backgroundColor: "rgba(75, 192, 192, 0.2)",
        tension: 0.3,
        fill: true,
      },
    ],
  }

  const trafficByEndpointData = {
    labels: trafficInsights.map((i) => i.endpoint),
    datasets: [
      {
        label: "Request Count",
        data: trafficInsights.map((i) => i.request_count),
        backgroundColor: "rgba(54, 162, 235, 0.8)",
        borderColor: "rgba(54, 162, 235, 1)",
        borderWidth: 2,
        borderRadius: 6,
        borderSkipped: false,
        hoverBackgroundColor: "rgba(54, 162, 235, 1)",
        hoverBorderColor: "rgba(54, 162, 235, 1)",
        hoverBorderWidth: 3,
      },
    ],
  }

  const statusCodeData = {
    labels: requestsBreakdown?.requests_by_status ? Object.keys(requestsBreakdown.requests_by_status) : [],
    datasets: [
      {
        data: requestsBreakdown?.requests_by_status ? Object.values(requestsBreakdown.requests_by_status) : [],
        backgroundColor: [
          "rgba(90, 252, 144, 0.8)",  // =
          "rgba(251, 255, 0, 0.8)",  // 
          "rgba(252, 0, 0, 0.8)",  // 
          "rgba(255, 102, 0, 0.8)", // 
          "rgba(156, 0, 161, 0.8)",
          "rgba(0, 0, 0, 0.8)",
          "rgba(255, 255, 255, 0.8)",
        ],
        borderColor: [
          "rgb(192, 184, 75)",
          "rgba(255, 159, 64, 1)",
          "rgba(255, 99, 132, 1)",
          "rgba(153, 102, 255, 1)",
        ],
        borderWidth: 1,
      },
    ],
  }

  // After fetching endpoint health data, coerce health_status to boolean
  const processedEndpoints = endpointHealthData && endpointHealthData.endpoints
    ? endpointHealthData.endpoints.map((ep: any) => ({
        ...ep,
        health_status: ep.health_status === true || ep.health_status === "true"
      }))
    : [];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[50vh]">
        <RefreshCw className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-[50vh]">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-destructive mb-2">Error Loading Analytics</h2>
          <p className="text-muted-foreground mb-4">{error}</p>
          <Button onClick={handleRefresh}>Try Again</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">API Analytics</h1>
          <p className="text-muted-foreground">Monitor API performance and usage metrics</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleExportLogs}>
            <Download className="mr-2 h-4 w-4" />
            Export API Logs
          </Button>
          <Button variant="outline" onClick={handleExportHealthLogs}>
            <Download className="mr-2 h-4 w-4" />
            Export Health Logs
          </Button>
          <Button onClick={handleRefresh} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Overview Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Requests</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overviewMetrics?.total_requests.toLocaleString() || 0}</div>
            <p className="text-xs text-muted-foreground">All time</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overviewMetrics?.avg_response_time || 0}ms</div>
            <p className="text-xs text-muted-foreground">Last 24 hours</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Error Rate</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">
              {overviewMetrics ? Math.round((overviewMetrics.failed_requests / overviewMetrics.total_requests) * 100) : 0}%
            </div>
            <p className="text-xs text-muted-foreground">Failed requests</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {overviewMetrics ? Math.round(
                ((overviewMetrics.total_requests - overviewMetrics.failed_requests) /
                  overviewMetrics.total_requests) *
                  100,
              ) : 0}%
            </div>
            <p className="text-xs text-muted-foreground">Successful requests</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="traffic">Traffic</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="errors">Errors</TabsTrigger>
          <TabsTrigger value="clients">Clients</TabsTrigger>
          <TabsTrigger value="health">Health</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Request Volume</CardTitle>
              </CardHeader>
              <CardContent>
                <ChartContainer config={{}} className="h-[300px]">
                  <Bar data={requestVolumeData} options={chartOptions} />
                </ChartContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Response Time Trends</CardTitle>
              </CardHeader>
              <CardContent>
                <ChartContainer config={{}} className="h-[300px]">
                  <Line data={performanceTrendsData} options={chartOptions} />
                </ChartContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Requests by Method</CardTitle>
              </CardHeader>
              <CardContent>
                <ChartContainer config={{}} className="h-[300px]">
                  <Doughnut data={methodDistributionData} options={pieOptions} />
                </ChartContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Status Code Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <ChartContainer config={{}} className="h-[300px]">
                  <Pie data={statusCodeData} options={pieOptions} />
                </ChartContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="traffic" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-xl">Traffic by Endpoint</CardTitle>
              <CardDescription>
                Visual representation of API request volume across different endpoints. Hover over bars to see detailed information.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-6">
              <div className="w-full">
                <ChartContainer config={{}} className="h-[600px] w-full">
                  <Bar data={trafficByEndpointData} options={trafficChartOptions} />
                </ChartContainer>
              </div>
              
              
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Response Time Trends</CardTitle>
            </CardHeader>
            <CardContent>
              <ChartContainer config={{}} className="h-[400px]">
                <Line data={performanceTrendsData} options={chartOptions} />
              </ChartContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="errors" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Error Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <ChartContainer config={{}} className="h-[300px]">
                  <Pie
                    data={{
                      labels: ["2xx Success", "4xx Client Error", "5xx Server Error"],
                      datasets: [
                        {
                          data: [
                            overviewMetrics?.total_requests - overviewMetrics?.failed_requests,
                            overviewMetrics?.total_4xx,
                            overviewMetrics?.total_5xx,
                          ],
                          backgroundColor: [
                            "rgba(75, 192, 192, 0.8)",  // Teal for success
                            "rgba(255, 159, 64, 0.8)",  // Orange for client errors
                            "rgba(255, 99, 132, 0.8)",  // Red for server errors
                          ],
                          borderColor: [
                            "rgba(75, 192, 192, 1)",
                            "rgba(255, 159, 64, 1)",
                            "rgba(255, 99, 132, 1)",
                          ],
                          borderWidth: 1,
                        },
                      ],
                    }}
                    options={pieOptions}
                  />
                </ChartContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Error Details</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-3 border rounded">
                    <div>
                      <p className="font-medium">4xx Client Errors</p>
                      <p className="text-sm text-muted-foreground">Bad requests, unauthorized, not found</p>
                    </div>
                    <Badge variant="secondary">{overviewMetrics?.total_4xx || 0}</Badge>
                  </div>
                  <div className="flex items-center justify-between p-3 border rounded">
                    <div>
                      <p className="font-medium">5xx Server Errors</p>
                      <p className="text-sm text-muted-foreground">Internal server errors, service unavailable</p>
                    </div>
                    <Badge variant="destructive">{overviewMetrics?.total_5xx || 0}</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="clients" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Client Activity</CardTitle>
              <CardDescription>Top clients by request volume</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {clientInsights.map((client, index) => {
                  const percentOfTotal = ((client.count / overviewMetrics?.total_requests) * 100).toFixed(2)
                  return (
                    <div key={index} className="flex items-center justify-between p-3 border rounded">
                      <div>
                        <p className="font-mono font-medium">{client.client_ip}</p>
                        <p className="text-sm text-muted-foreground">{percentOfTotal}% of total traffic</p>
                      </div>
                      <div className="text-right">
                        <p className="font-bold">{client.count.toLocaleString()}</p>
                        <p className="text-sm text-muted-foreground">requests</p>
                      </div>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="health" className="space-y-4">
          <div className="flex flex-col sm:flex-row justify-between items-center mb-4 gap-2">
            <div className="flex items-center space-x-2">
              <Label htmlFor="scan-period">Scan Period:</Label>
              <Select value={scanPeriod} onValueChange={setScanPeriod}>
                <SelectTrigger id="scan-period" className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1_week">1 week</SelectItem>
                  <SelectItem value="1_month">1 month</SelectItem>
                  <SelectItem value="1_year">1 year</SelectItem>
                </SelectContent>
              </Select>
              <Button
                onClick={runHealthScan}
                disabled={healthScanLoading}
                className="flex items-center space-x-2"
              >
                {healthScanLoading ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <Activity className="h-4 w-4" />
                )}
                <span>{healthScanLoading ? "Running Scan..." : "Run Health Scan"}</span>
              </Button>
            </div>
          </div>

          {healthScanResults && (
            <Card>
              <CardHeader>
                <CardTitle>Health Scan Results</CardTitle>
                <CardDescription>
                  Last scan completed at {new Date().toLocaleString()}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div className="bg-muted p-4 rounded-lg">
                    <div className="text-sm font-medium">Total Endpoints</div>
                    <div className="text-2xl font-bold">{healthScanResults.summary.total_endpoints}</div>
                  </div>
                  <div className="bg-green-100 p-4 rounded-lg">
                    <div className="text-sm font-medium">Healthy Endpoints</div>
                    <div className="text-2xl font-bold text-green-600">{healthScanResults.summary.healthy_endpoints}</div>
                  </div>
                  <div className="bg-red-100 p-4 rounded-lg">
                    <div className="text-sm font-medium">Unhealthy Endpoints</div>
                    <div className="text-2xl font-bold text-red-600">{healthScanResults.summary.unhealthy_endpoints}</div>
                  </div>
                </div>

                <div className="space-y-4">
                  <h3 className="font-medium">Detailed Results</h3>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Endpoint</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Response Time</TableHead>
                        <TableHead>Details</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {healthScanResults.results.map((result: any, index: number) => (
                        <TableRow key={index}>
                          <TableCell className="font-mono">{result.url}</TableCell>
                          <TableCell>
                            <Badge variant={result.status ? "default" : "destructive"}>
                              {result.status ? "Healthy" : "Unhealthy"}
                            </Badge>
                          </TableCell>
                          <TableCell>{result.response_time}ms</TableCell>
                          <TableCell>
                            {result.status ? (
                              <span className="text-xs text-green-600 font-medium">Success</span>
                            ) : result.status_code && result.status_code !== 200 ? (
                              <div className="flex flex-col gap-1">
                                {result.failure_reason && (
                                  <span
                                    className={`
                                      inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold
                                      ${result.failure_reason === "authentication_required" ? "bg-red-100 text-red-700" : ""}
                                      ${result.failure_reason === "validation_error" ? "bg-yellow-100 text-yellow-800" : ""}
                                      ${result.failure_reason === "not_found" ? "bg-gray-100 text-gray-700" : ""}
                                      ${result.failure_reason === "server_error" ? "bg-red-200 text-red-900" : ""}
                                      ${result.failure_reason === "client_error" ? "bg-orange-100 text-orange-800" : ""}
                                      ${result.failure_reason === "forbidden" ? "bg-purple-100 text-purple-800" : ""}
                                      ${result.failure_reason === "method_not_allowed" ? "bg-blue-100 text-blue-800" : ""}
                                      ${result.failure_reason === "rate_limited" ? "bg-pink-100 text-pink-800" : ""}
                                      ${result.failure_reason === "timeout" ? "bg-indigo-100 text-indigo-800" : ""}
                                      ${result.failure_reason === "connection_error" ? "bg-slate-100 text-slate-800" : ""}
                                      ${result.failure_reason === "unknown_error" ? "bg-neutral-100 text-neutral-800" : ""}
                                    `}
                                  >
                                    {result.failure_reason.replace('_', ' ').toUpperCase()}
                                    {result.failure_reason === "authentication_required" && (
                                      <span className="ml-1"><Lock className="inline h-3 w-3" /></span>
                                    )}
                                    {result.failure_reason === "validation_error" && (
                                      <span className="ml-1"><AlertTriangle className="inline h-3 w-3" /></span>
                                    )}
                                    {result.failure_reason === "timeout" && (
                                      <span className="ml-1"><Clock className="inline h-3 w-3" /></span>
                                    )}
                                    {result.failure_reason === "connection_error" && (
                                      <span className="ml-1"><XCircle className="inline h-3 w-3" /></span>
                                    )}
                                  </span>
                                )}
                                {result.error_message && (
                                  <span
                                    className="text-xs text-muted-foreground truncate max-w-[180px] cursor-pointer"
                                    title={result.error_message}
                                  >
                                    {result.error_message}
                                  </span>
                                )}
                                {result.error && !result.failure_reason && (
                                  <span className="text-xs text-red-600">
                                    {result.error}
                                  </span>
                                )}
                                {!result.failure_reason && !result.error_message && !result.error && (
                                  <span className="text-xs text-muted-foreground">
                                    HTTP {result.status_code || "Unknown"} Error
                                  </span>
                                )}
                              </div>
                            ) : result.error ? (
                              <div className="text-sm text-red-600">
                                {result.error}
                              </div>
                            ) : (
                              <span className="text-xs text-muted-foreground">N/A</span>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Endpoint health table (with filters, pagination, etc.) */}
          <Card>
            <CardHeader>
              <CardTitle>Latest Endpoint Health Status</CardTitle>
              <CardDescription>Current health status of monitored endpoints</CardDescription>
            </CardHeader>
            <CardContent>
              {/* Search and Filter Controls */}
              <div className="mb-6 space-y-4">
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="space-y-2">
                    <Label htmlFor="endpoint-search">Search Endpoints</Label>
                    <div className="relative">
                      <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="endpoint-search"
                        placeholder="Search by name, URL, or description..."
                        value={endpointSearch}
                        onChange={(e) => handleEndpointSearchChange(e.target.value)}
                        className="pl-8"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="status-filter">Status Filter</Label>
                    <Select value={endpointStatusFilter} onValueChange={handleEndpointStatusFilterChange}>
                      <SelectTrigger>
                        <SelectValue placeholder="All Statuses" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Statuses</SelectItem>
                        <SelectItem value="active">Active Only</SelectItem>
                        <SelectItem value="inactive">Inactive Only</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="method-filter">Method Filter</Label>
                    <Select value={endpointMethodFilter} onValueChange={handleEndpointMethodFilterChange}>
                      <SelectTrigger>
                        <SelectValue placeholder="All Methods" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Methods</SelectItem>
                        <SelectItem value="GET">GET</SelectItem>
                        <SelectItem value="POST">POST</SelectItem>
                        <SelectItem value="PUT">PUT</SelectItem>
                        <SelectItem value="DELETE">DELETE</SelectItem>
                        <SelectItem value="PATCH">PATCH</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                {/* Active Filters Display */}
                {(endpointSearch || endpointStatusFilter !== "all" || endpointMethodFilter !== "all") && (
                  <div className="flex flex-wrap gap-2">
                    {endpointSearch && (
                      <Badge variant="secondary" className="flex items-center gap-1">
                        Search: {endpointSearch}
                        <button
                          onClick={() => handleEndpointSearchChange("")}
                          className="ml-1 hover:text-destructive"
                        >
                          ×
                        </button>
                      </Badge>
                    )}
                    {endpointStatusFilter !== "all" && (
                      <Badge variant="secondary" className="flex items-center gap-1">
                        Status: {endpointStatusFilter}
                        <button
                          onClick={() => handleEndpointStatusFilterChange("all")}
                          className="ml-1 hover:text-destructive"
                        >
                          ×
                        </button>
                      </Badge>
                    )}
                    {endpointMethodFilter !== "all" && (
                      <Badge variant="secondary" className="flex items-center gap-1">
                        Method: {endpointMethodFilter}
                        <button
                          onClick={() => handleEndpointMethodFilterChange("all")}
                          className="ml-1 hover:text-destructive"
                        >
                          ×
                        </button>
                      </Badge>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setEndpointSearch("")
                        setEndpointStatusFilter("all")
                        setEndpointMethodFilter("all")
                        setEndpointHealthPage(1)
                        fetchEndpointHealthData(1)
                      }}
                    >
                      Clear All Filters
                    </Button>
                  </div>
                )}
              </div>
              {endpointHealthData ? (
                <div className="space-y-4">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Endpoint</TableHead>
                        <TableHead>Method</TableHead>
                        <TableHead>Configured Status</TableHead>
                        <TableHead>Health Status</TableHead>
                        <TableHead>Response Time</TableHead>
                        <TableHead>Status Code</TableHead>
                        <TableHead>Error Details</TableHead>
                        <TableHead>Last Checked</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {processedEndpoints.map((endpoint: any) => (
                        <TableRow  key={endpoint.endpoint_id}
                        className={!endpoint.health_status ? "bg-red-50/50" : ""}>
                          <TableCell className="font-medium">
                            <div className="flex flex-col">
                              <span>{endpoint.name}</span>
                              <span className="text-xs text-muted-foreground">{endpoint.url}</span>
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge
                              variant={
                                endpoint.method === "GET"
                                  ? "secondary"
                                  : endpoint.method === "POST"
                                    ? "default"
                                    : endpoint.method === "PUT"
                                      ? "outline"
                                      : "destructive"
                              }
                            >
                              {endpoint.method}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {endpoint.status ? (
                              <div className="flex items-center">
                                <CheckCircle className="mr-2 h-4 w-4 text-green-500" />
                                <span>Active</span>
                              </div>
                            ) : (
                              <div className="flex items-center">
                                <XCircle className="mr-2 h-4 w-4 text-red-500" />
                                <span>Inactive</span>
                              </div>
                            )}
                          </TableCell>
                          <TableCell>
                            {endpoint.status ? (
                              endpoint.health_status ? (
                                <div className="flex items-center">
                                  <CheckCircle className="mr-2 h-4 w-4 text-green-500" />
                                  <span>Healthy</span>
                                </div>
                              ) : (
                                <div className="flex items-center">
                                  <XCircle className="mr-2 h-4 w-4 text-red-500" />
                                  <span>Unhealthy</span>
                                </div>
                              )
                            ) : (
                              <div className="flex items-center">
                                <XCircle className="mr-2 h-4 w-4 text-gray-500" />
                                <span>Disabled</span>
                              </div>
                            )}
                          </TableCell>
                          <TableCell>
                            {endpoint.status ? (
                              endpoint.health_status ? `${endpoint.response_time || 0} ms` : "N/A"
                            ) : (
                              "N/A"
                            )}
                          </TableCell>
                          <TableCell>
                            {endpoint.status ? (
                              endpoint.status_code ? (
                                <Badge
                                  variant={
                                    endpoint.status_code >= 200 && endpoint.status_code < 300
                                      ? "default"
                                      : endpoint.status_code >= 400 && endpoint.status_code < 500
                                      ? "secondary"
                                      : "destructive"
                                  }
                                >
                                  {endpoint.status_code}
                                </Badge>
                              ) : (
                                "N/A"
                              )
                            ) : (
                              <Badge variant="secondary">
                                503
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell>
                            {!endpoint.status ? (
                              <div className="flex flex-col gap-1">
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-700">
                                  ENDPOINT_DISABLED
                                  <span className="ml-1"><Lock className="inline h-3 w-3" /></span>
                                </span>
                                <span className="text-xs text-muted-foreground">
                                  Endpoint has been deactivated by user
                                </span>
                              </div>
                            ) : endpoint.status_code && endpoint.status_code !== 200 ? (
                              <div className="flex flex-col gap-1">
                                {endpoint.failure_reason && (
                                  <span
                                    className={`
                                      inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold
                                      ${endpoint.failure_reason === "authentication_required" ? "bg-red-100 text-red-700" : ""}
                                      ${endpoint.failure_reason === "validation_error" ? "bg-yellow-100 text-yellow-800" : ""}
                                      ${endpoint.failure_reason === "not_found" ? "bg-gray-100 text-gray-700" : ""}
                                      ${endpoint.failure_reason === "server_error" ? "bg-red-200 text-red-900" : ""}
                                      ${endpoint.failure_reason === "client_error" ? "bg-orange-100 text-orange-800" : ""}
                                      ${endpoint.failure_reason === "forbidden" ? "bg-purple-100 text-purple-800" : ""}
                                      ${endpoint.failure_reason === "method_not_allowed" ? "bg-blue-100 text-blue-800" : ""}
                                      ${endpoint.failure_reason === "rate_limited" ? "bg-pink-100 text-pink-800" : ""}
                                      ${endpoint.failure_reason === "timeout" ? "bg-indigo-100 text-indigo-800" : ""}
                                      ${endpoint.failure_reason === "connection_error" ? "bg-slate-100 text-slate-800" : ""}
                                      ${endpoint.failure_reason === "unknown_error" ? "bg-neutral-100 text-neutral-800" : ""}
                                    `}
                                  >
                                    {endpoint.failure_reason.replace('_', ' ').toUpperCase()}
                                    {endpoint.failure_reason === "authentication_required" && (
                                      <span className="ml-1"><Lock className="inline h-3 w-3" /></span>
                                    )}
                                    {endpoint.failure_reason === "validation_error" && (
                                      <span className="ml-1"><AlertTriangle className="inline h-3 w-3" /></span>
                                    )}
                                    {endpoint.failure_reason === "timeout" && (
                                      <span className="ml-1"><Clock className="inline h-3 w-3" /></span>
                                    )}
                                    {endpoint.failure_reason === "connection_error" && (
                                      <span className="ml-1"><XCircle className="inline h-3 w-3" /></span>
                                    )}
                                  </span>
                                )}
                                {endpoint.error_message && (
                                  <span
                                    className="text-xs text-muted-foreground truncate max-w-[180px] cursor-pointer"
                                    title={endpoint.error_message}
                                  >
                                    {endpoint.error_message}
                                  </span>
                                )}
                                {!endpoint.failure_reason && (
                                  <span className="text-xs text-muted-foreground">
                                    HTTP {endpoint.status_code} Error
                                  </span>
                                )}
                              </div>
                            ) : endpoint.status_code === 200 ? (
                              <span className="text-xs text-green-600 font-medium">Success</span>
                            ) : (
                              <span className="text-xs text-muted-foreground">N/A</span>
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center">
                              <Clock className="mr-2 h-4 w-4 text-muted-foreground" />
                              {endpoint.last_checked ? 
                                new Date(endpoint.last_checked).toLocaleString() : 
                                "Never"
                              }
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  {/* Pagination */}
                  {endpointHealthData.total_pages > 1 && (
                    <Pagination>
                      <PaginationContent>
                        <PaginationItem>
                          <PaginationPrevious 
                            onClick={() => handleEndpointHealthPageChange(endpointHealthPage - 1)}
                            className={endpointHealthPage === 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
                          />
                        </PaginationItem>
                        {[...Array(endpointHealthData.total_pages)].map((_, index) => {
                          const pageNumber = index + 1
                          // Show first page, last page, current page, and pages around current page
                          if (
                            pageNumber === 1 ||
                            pageNumber === endpointHealthData.total_pages ||
                            (pageNumber >= endpointHealthPage - 1 && pageNumber <= endpointHealthPage + 1)
                          ) {
                            return (
                              <PaginationItem key={pageNumber}>
                                <PaginationLink
                                  onClick={() => handleEndpointHealthPageChange(pageNumber)}
                                  isActive={endpointHealthPage === pageNumber}
                                >
                                  {pageNumber}
                                </PaginationLink>
                              </PaginationItem>
                            )
                          } else if (
                            pageNumber === endpointHealthPage - 2 ||
                            pageNumber === endpointHealthPage + 2
                          ) {
                            return (
                              <PaginationItem key={pageNumber}>
                                <PaginationEllipsis />
                              </PaginationItem>
                            )
                          }
                          return null
                        })}
                        <PaginationItem>
                          <PaginationNext
                            onClick={() => handleEndpointHealthPageChange(endpointHealthPage + 1)}
                            className={endpointHealthPage === endpointHealthData.total_pages ? "pointer-events-none opacity-50" : "cursor-pointer"}
                          />
                        </PaginationItem>
                      </PaginationContent>
                    </Pagination>
                  )}
                  <div className="text-sm text-muted-foreground text-center">
                    Showing {((endpointHealthPage - 1) * endpointHealthPageSize) + 1} to {Math.min(endpointHealthPage * endpointHealthPageSize, endpointHealthData.total)} of {endpointHealthData.total} endpoints
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="h-8 w-8 animate-spin" />
                </div>
              )}
              {/* No Results Message */}
              {endpointHealthData && endpointHealthData.total === 0 && (
                <div className="text-center py-8">
                  <p className="text-muted-foreground">No endpoints found matching the current filters.</p>
                  <Button
                    variant="outline"
                    className="mt-2"
                    onClick={() => {
                      setEndpointSearch("")
                      setEndpointStatusFilter("all")
                      setEndpointMethodFilter("all")
                      setEndpointHealthPage(1)
                      fetchEndpointHealthData(1)
                    }}
                  >
                    Clear Filters
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <p className="text-sm text-muted-foreground text-center">Last updated: {lastUpdated.toLocaleString()}</p>
    </div>
  )
}
