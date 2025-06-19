import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Activity, Clock, AlertCircle, Shield, RefreshCw, Loader2, History, Search, Lock, CheckCircle, XCircle, AlertTriangle, Download, TrendingUp } from "lucide-react";
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { APIClient, defaultClient } from '@/lib/api-client';
import { ChartContainer } from '@/components/charts/chart-container';
import { Pie, Bar, Line } from 'react-chartjs-2';
import { formatDistanceToNow } from 'date-fns';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { useToast } from '@/components/ui/use-toast';

interface Endpoint {
  id: number;
  path: string;
  method: string;
  status: string;
  last_checked: string;
  response_time: number;
  status_code: number;
  error_message?: string;
  failure_reason?: string;
}

interface EndpointHealth {
  id: number;
  discovered_endpoint_id: number;
  status: boolean;
  is_healthy: boolean;
  response_time: number;
  checked_at: string;
  status_code: number;
  error_message: string | null;
  failure_reason: string | null;
}

interface RemoteServerAnalytics {
  metrics: {
    total_endpoints: number;
    healthy_endpoints: number;
    unhealthy_endpoints: number;
    average_response_time: number;
  };
  endpoints: Endpoint[];
  health_history: EndpointHealth[];
}

interface PerformanceAnalytics {
  time_range: string;
  data: {
    average_response_time_by_day: Array<{
      date: string;
      average_response_time: number;
      count: number;
    }>;
    average_response_time_by_hour: Array<{
      hour: string;
      average_response_time: number;
      count: number;
    }>;
    slowest_endpoints: Array<{
      endpoint: string;
      method: string;
      path: string;
      average_response_time: number;
      total_checks: number;
      success_rate: number;
    }>;
    response_time_by_method: Record<string, {
      average_response_time: number;
      total_checks: number;
      success_rate: number;
      min_response_time: number;
      max_response_time: number;
    }>;
    traffic_correlation: {
      data: Array<{
        hour: string;
        traffic_volume: number;
        average_response_time: number;
        timestamp: string;
      }>;
      correlation_coefficient: number;
      interpretation: string;
    };
    traffic_trends: {
      daily: Array<{
        date: string;
        total_checks: number;
        successful_checks: number;
        failed_checks: number;
        success_rate: number;
        avg_response_time: number;
      }>;
      hourly: Array<{
        hour: string;
        total_checks: number;
        successful_checks: number;
        failed_checks: number;
        success_rate: number;
        avg_response_time: number;
        timestamp: string;
      }>;
      anomalies: {
        daily: Array<{
          index: number;
          type: string;
          timestamp: string;
          volume: number;
          z_score: number;
          severity: string;
        }>;
        hourly: Array<{
          index: number;
          type: string;
          timestamp: string;
          volume: number;
          z_score: number;
          severity: string;
        }>;
      };
    };
  };
  summary: {
    total_health_checks: number;
    time_period_start: string;
    time_period_end: string;
    overall_average_response_time: number;
  };
}

interface RemoteServerAnalyticsDashboardProps {
  serverId: number;
  client?: APIClient;
}

export function RemoteServerAnalyticsDashboard({ serverId, client }: RemoteServerAnalyticsDashboardProps) {
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analytics, setAnalytics] = useState<RemoteServerAnalytics | null>(null);
  const [performanceAnalytics, setPerformanceAnalytics] = useState<PerformanceAnalytics | null>(null);
  const [activeTab, setActiveTab] = useState("overview");
  const [lastScanTime, setLastScanTime] = useState<string | null>(null);
  const [scanFrequency, setScanFrequency] = useState("1d");
  const [performanceTimeRange, setPerformanceTimeRange] = useState("7d");
  const [trafficTrendsView, setTrafficTrendsView] = useState("daily");
  const { toast } = useToast();

  // Add new state variables for endpoint health table
  const [endpointHealthPage, setEndpointHealthPage] = useState(1);
  const [endpointHealthPageSize] = useState(5);
  const [endpointSearch, setEndpointSearch] = useState("");
  const [endpointStatusFilter, setEndpointStatusFilter] = useState("all");
  const [endpointMethodFilter, setEndpointMethodFilter] = useState("all");
  // Add new state for response time distribution pagination
  const [responseTimePage, setResponseTimePage] = useState(1);
  const [responseTimePageSize] = useState(5);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = client
        ? await client.get<RemoteServerAnalytics>(`/analytics/remote-servers/${serverId}/analytics`)
        : await defaultClient.get<RemoteServerAnalytics>(`/analytics/remote-servers/${serverId}/analytics`);
      setAnalytics(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  };

  const loadPerformanceData = async () => {
    try {
      const data = client
        ? await client.get<PerformanceAnalytics>(`/analytics/remote-servers/${serverId}/performance-analytics?time_range=${performanceTimeRange}`)
        : await defaultClient.get<PerformanceAnalytics>(`/analytics/remote-servers/${serverId}/performance-analytics?time_range=${performanceTimeRange}`);
      setPerformanceAnalytics(data);
    } catch (err: any) {
      console.error('Failed to load performance data:', err);
      // Don't set error state for performance data as it's not critical
    }
  };

  const runHealthScan = async () => {
    setScanning(true);
    try {
      await (client || defaultClient).post(`/remote-servers/${serverId}/run-health-scan`, {
        frequency: scanFrequency
      });
      setLastScanTime(new Date().toISOString());
      await loadData(); // Reload data after scan
    } catch (err: any) {
      setError(err.message || 'Failed to run health scan');
    } finally {
      setScanning(false);
    }
  };

  const exportHealthLogs = async () => {
    setExporting(true);
    try {
      // Get auth headers
      const token = localStorage.getItem('token');
      const apiKey = localStorage.getItem('apiKey');
      
      if (!token || !apiKey) {
        throw new Error('Authentication required. Please log in again.');
      }

      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_BASE_URL}/analytics/remote-servers/${serverId}/export-health-logs`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'X-API-KEY': apiKey,
        },
        credentials: 'include',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to export health logs');
      }

      // Get the filename from the Content-Disposition header
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `remote_server_health_logs_${serverId}_${new Date().toISOString().split('T')[0]}.csv`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename=(.+)/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }

      // Create a blob from the response
      const blob = await response.blob();
      
      if (blob.size === 0) {
        throw new Error('Received empty file');
      }
      
      // Create a download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.style.display = 'none';
      document.body.appendChild(a);
      
      a.click();
      
      // Cleanup
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }, 100);

      toast({
        title: "Success",
        description: "Remote server health logs exported successfully",
      });
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to export health logs';
      setError(errorMessage);
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setExporting(false);
    }
  };

  useEffect(() => {
    loadData();
    loadPerformanceData();
  }, [serverId, client, performanceTimeRange]);

  const handleEndpointHealthPageChange = (newPage: number) => {
    setEndpointHealthPage(newPage);
  };

  const handleEndpointSearchChange = (searchValue: string) => {
    setEndpointSearch(searchValue);
    setEndpointHealthPage(1);
  };

  const handleEndpointStatusFilterChange = (statusValue: string) => {
    setEndpointStatusFilter(statusValue);
    setEndpointHealthPage(1);
  };

  const handleEndpointMethodFilterChange = (methodValue: string) => {
    setEndpointMethodFilter(methodValue);
    setEndpointHealthPage(1);
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!analytics) return <div>No data available</div>;

  const { metrics, endpoints } = analytics;

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'bottom' as const } },
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Remote Server Analytics</h1>
          <p className="text-muted-foreground">Monitor remote server health and performance</p>
        </div>
        <div className="flex items-center gap-4">
          {lastScanTime && (
            <p className="text-sm text-muted-foreground">
              Last scan: {formatDistanceToNow(new Date(lastScanTime), { addSuffix: true, includeSeconds: true })}
            </p>
          )}
          <div className="flex items-center gap-2">
            <Select value={scanFrequency} onValueChange={setScanFrequency}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Select scan frequency" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1d">Every Day</SelectItem>
                <SelectItem value="1w">Every Week</SelectItem>
                <SelectItem value="1m">Every Month</SelectItem>
              </SelectContent>
            </Select>
            <Button 
              onClick={runHealthScan} 
              disabled={scanning || loading}
              variant="outline"
            >
              {scanning ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-2" />
              )}
              Run Health Scan
            </Button>
          </div>
          <Button 
            onClick={exportHealthLogs} 
            disabled={exporting || loading}
            variant="outline"
          >
            {exporting ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <Download className="h-4 w-4 mr-2" />
            )}
            Export Health Logs
          </Button>
          <Button onClick={() => loadData()} disabled={loading}>
            Refresh
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Endpoints</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.total_endpoints}</div>
            <p className="text-xs text-muted-foreground">Discovered endpoints</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Health Status</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {metrics.total_endpoints > 0 ? ((metrics.healthy_endpoints / metrics.total_endpoints) * 100).toFixed(1) : '0.0'}%
            </div>
            <p className="text-xs text-muted-foreground">
              {metrics.healthy_endpoints} healthy endpoints
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Unhealthy Endpoints</CardTitle>
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.unhealthy_endpoints}</div>
            <p className="text-xs text-muted-foreground">
              Endpoints requiring attention
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.average_response_time.toFixed(2)} ms</div>
            <p className="text-xs text-muted-foreground">Average endpoint response time</p>
          </CardContent>
        </Card>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="endpoints">Endpoints</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="health-logs">Health Logs</TabsTrigger>
        </TabsList>
        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Endpoint Health Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <ChartContainer config={{}} className="h-[300px]">
                  <Pie
                    data={{
                      labels: ["Healthy", "Unhealthy"],
                      datasets: [
                        {
                          data: [metrics.healthy_endpoints, metrics.unhealthy_endpoints],
                          backgroundColor: [
                            "rgba(75, 192, 192, 0.8)",
                            "rgba(255, 99, 132, 0.8)",
                          ],
                          borderColor: [
                            "rgba(75, 192, 192, 1)",
                            "rgba(255, 99, 132, 1)",
                          ],
                          borderWidth: 1,
                        },
                      ],
                    }}
                    options={chartOptions}
                  />
                </ChartContainer>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Response Time Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {/* Response Time Chart */}
                  <div>
                    <h3 className="text-lg font-semibold mb-4">Response Time Chart</h3>
                    <ChartContainer config={{}} className="h-[300px]">
                      <Bar
                        data={{
                          labels: endpoints
                            .slice((responseTimePage - 1) * responseTimePageSize, responseTimePage * responseTimePageSize)
                            .map(endpoint => `${endpoint.method} ${endpoint.path}`),
                          datasets: [
                            {
                              label: 'Response Time (ms)',
                              data: endpoints
                                .slice((responseTimePage - 1) * responseTimePageSize, responseTimePage * responseTimePageSize)
                                .map(endpoint => endpoint.response_time),
                              backgroundColor: 'rgba(75, 192, 192, 0.8)',
                              borderColor: 'rgba(75, 192, 192, 1)',
                              borderWidth: 1,
                            },
                          ],
                        }}
                        options={{
                          ...chartOptions,
                          scales: {
                            y: {
                              beginAtZero: true,
                              title: {
                                display: true,
                                text: 'Response Time (ms)'
                              }
                            },
                            x: {
                              ticks: {
                                maxRotation: 45,
                                minRotation: 45
                              }
                            }
                          },
                          plugins: {
                            ...chartOptions.plugins,
                            tooltip: {
                              callbacks: {
                                label: function(context) {
                                  return `Response Time: ${context.raw}ms`;
                                }
                              }
                            }
                          }
                        }}
                      />
                    </ChartContainer>
                  </div>

                  {/* Response Time List */}
                  <div>
                    <h3 className="text-lg font-semibold mb-4">Response Time Details</h3>
                    <div className="space-y-4">
                      {endpoints
                        .slice((responseTimePage - 1) * responseTimePageSize, responseTimePage * responseTimePageSize)
                        .map((endpoint) => (
                        <div key={endpoint.id} className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <Badge variant="outline">{endpoint.method}</Badge>
                            <span className="font-mono text-sm">{endpoint.path}</span>
                          </div>
                          <span className="text-sm font-medium">{endpoint.response_time}ms</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Pagination */}
                  {Math.ceil(endpoints.length / responseTimePageSize) > 1 && (
                    <div className="mt-4">
                      <Pagination>
                        <PaginationContent>
                          <PaginationItem>
                            <PaginationPrevious 
                              onClick={() => setResponseTimePage(prev => Math.max(1, prev - 1))}
                              className={responseTimePage === 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
                            />
                          </PaginationItem>
                          {[...Array(Math.ceil(endpoints.length / responseTimePageSize))].map((_, index) => {
                            const pageNumber = index + 1;
                            if (
                              pageNumber === 1 ||
                              pageNumber === Math.ceil(endpoints.length / responseTimePageSize) ||
                              (pageNumber >= responseTimePage - 1 && pageNumber <= responseTimePage + 1)
                            ) {
                              return (
                                <PaginationItem key={pageNumber}>
                                  <PaginationLink
                                    onClick={() => setResponseTimePage(pageNumber)}
                                    isActive={responseTimePage === pageNumber}
                                  >
                                    {pageNumber}
                                  </PaginationLink>
                                </PaginationItem>
                              );
                            } else if (
                              pageNumber === responseTimePage - 2 ||
                              pageNumber === responseTimePage + 2
                            ) {
                              return (
                                <PaginationItem key={pageNumber}>
                                  <PaginationEllipsis />
                                </PaginationItem>
                              );
                            }
                            return null;
                          })}
                          <PaginationItem>
                            <PaginationNext
                              onClick={() => setResponseTimePage(prev => Math.min(Math.ceil(endpoints.length / responseTimePageSize), prev + 1))}
                              className={responseTimePage === Math.ceil(endpoints.length / responseTimePageSize) ? "pointer-events-none opacity-50" : "cursor-pointer"}
                            />
                          </PaginationItem>
                        </PaginationContent>
                      </Pagination>
                      <div className="text-sm text-muted-foreground text-center mt-2">
                        Showing {((responseTimePage - 1) * responseTimePageSize) + 1} to {Math.min(responseTimePage * responseTimePageSize, endpoints.length)} of {endpoints.length} endpoints
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
        <TabsContent value="endpoints" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Endpoint Health Status</CardTitle>
              <CardDescription>Current health status of remote server endpoints</CardDescription>
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
                        placeholder="Search by path or method..."
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
                        setEndpointSearch("");
                        setEndpointStatusFilter("all");
                        setEndpointMethodFilter("all");
                        setEndpointHealthPage(1);
                      }}
                    >
                      Clear All Filters
                    </Button>
                  </div>
                )}
              </div>

              {analytics?.endpoints ? (
                <div className="space-y-4">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Endpoint</TableHead>
                        <TableHead>Method</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Response Time</TableHead>
                        <TableHead>Status Code</TableHead>
                        <TableHead>Last Checked</TableHead>
                        <TableHead>Error Message</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {analytics.endpoints
                        .filter(endpoint => {
                          const matchesSearch = endpointSearch === "" || 
                            endpoint.path.toLowerCase().includes(endpointSearch.toLowerCase()) ||
                            endpoint.method.toLowerCase().includes(endpointSearch.toLowerCase());
                          const matchesStatus = endpointStatusFilter === "all" || 
                            (endpointStatusFilter === "active" && endpoint.status === "true") ||
                            (endpointStatusFilter === "inactive" && endpoint.status !== "true");
                          const matchesMethod = endpointMethodFilter === "all" || 
                            endpoint.method === endpointMethodFilter;
                          return matchesSearch && matchesStatus && matchesMethod;
                        })
                        .slice((endpointHealthPage - 1) * endpointHealthPageSize, endpointHealthPage * endpointHealthPageSize)
                        .map((endpoint: Endpoint) => {
                          // Determine badge variant for status code
                          let statusCodeVariant: "default" | "secondary" | "destructive" = "secondary";
                          if (typeof endpoint.status_code === 'number') {
                            if (endpoint.status_code >= 200 && endpoint.status_code < 300) statusCodeVariant = "default";
                            else if (endpoint.status_code >= 400 && endpoint.status_code < 500) statusCodeVariant = "secondary";
                            else statusCodeVariant = "destructive";
                          }
                          return (
                            <TableRow key={endpoint.id} className={endpoint.status !== "true" ? "bg-red-50/50" : ""}>
                              <TableCell className="font-medium">
                                <div className="flex flex-col">
                                  <span className="font-mono">{endpoint.path}</span>
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
                                {endpoint.status === "true" ? (
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
                                {endpoint.status === "true" && typeof endpoint.response_time === 'number' ? `${endpoint.response_time} ms` : "N/A"}
                              </TableCell>
                              <TableCell>
                                {typeof endpoint.status_code === 'number' ? (
                                  <Badge variant={statusCodeVariant}>
                                    {endpoint.status_code}
                                  </Badge>
                                ) : (
                                  <Badge variant="secondary">503</Badge>
                                )}
                              </TableCell>
                              <TableCell>
                                <div className="flex items-center">
                                  <Clock className="mr-2 h-4 w-4 text-muted-foreground" />
                                  {endpoint.status === "true" && endpoint.last_checked ? 
                                    new Date(endpoint.last_checked).toLocaleString() : 
                                    "Never"
                                  }
                                </div>
                              </TableCell>
                              <TableCell>
                                {endpoint.status_code >= 200 && endpoint.status_code < 300 ? (
                                  <span className="text-xs text-green-600 font-medium">Success</span>
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
                                ) : (
                                  <span className="text-xs text-muted-foreground">N/A</span>
                                )}
                              </TableCell>
                            </TableRow>
                          );
                        })}
                    </TableBody>
                  </Table>
                  {/* Pagination */}
                  {Math.ceil(analytics.endpoints.length / endpointHealthPageSize) > 1 && (
                    <Pagination>
                      <PaginationContent>
                        <PaginationItem>
                          <PaginationPrevious 
                            onClick={() => handleEndpointHealthPageChange(endpointHealthPage - 1)}
                            className={endpointHealthPage === 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
                          />
                        </PaginationItem>
                        {[...Array(Math.ceil(analytics.endpoints.length / endpointHealthPageSize))].map((_, index) => {
                          const pageNumber = index + 1;
                          if (
                            pageNumber === 1 ||
                            pageNumber === Math.ceil(analytics.endpoints.length / endpointHealthPageSize) ||
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
                            );
                          } else if (
                            pageNumber === endpointHealthPage - 2 ||
                            pageNumber === endpointHealthPage + 2
                          ) {
                            return (
                              <PaginationItem key={pageNumber}>
                                <PaginationEllipsis />
                              </PaginationItem>
                            );
                          }
                          return null;
                        })}
                        <PaginationItem>
                          <PaginationNext
                            onClick={() => handleEndpointHealthPageChange(endpointHealthPage + 1)}
                            className={endpointHealthPage === Math.ceil(analytics.endpoints.length / endpointHealthPageSize) ? "pointer-events-none opacity-50" : "cursor-pointer"}
                          />
                        </PaginationItem>
                      </PaginationContent>
                    </Pagination>
                  )}
                  <div className="text-sm text-muted-foreground text-center">
                    Showing {((endpointHealthPage - 1) * endpointHealthPageSize) + 1} to {Math.min(endpointHealthPage * endpointHealthPageSize, analytics.endpoints.length)} of {analytics.endpoints.length} endpoints
                  </div>
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-muted-foreground">No endpoints found matching the current filters.</p>
                  <Button
                    variant="outline"
                    className="mt-2"
                    onClick={() => {
                      setEndpointSearch("");
                      setEndpointStatusFilter("all");
                      setEndpointMethodFilter("all");
                      setEndpointHealthPage(1);
                    }}
                  >
                    Clear Filters
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="performance" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Performance Analytics</CardTitle>
              <CardDescription>Comprehensive performance metrics and analysis</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4 mb-6">
                <Label htmlFor="time-range">Time Range:</Label>
                <Select value={performanceTimeRange} onValueChange={setPerformanceTimeRange}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Select time range" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="24h">Last 24 Hours</SelectItem>
                    <SelectItem value="7d">Last 7 Days</SelectItem>
                    <SelectItem value="30d">Last 30 Days</SelectItem>
                  </SelectContent>
                </Select>
                <Button onClick={loadPerformanceData} variant="outline" size="sm">
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Refresh
                </Button>
              </div>

              {performanceAnalytics ? (
                <div className="space-y-6">
                  {/* Summary Metrics */}
                  <div className="grid gap-4 md:grid-cols-3">
                    <Card>
                      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Health Checks</CardTitle>
                        <Activity className="h-4 w-4 text-muted-foreground" />
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold">{performanceAnalytics.summary?.total_health_checks ?? 'N/A'}</div>
                        <p className="text-xs text-muted-foreground">
                          {performanceAnalytics.summary?.time_period_start ? new Date(performanceAnalytics.summary.time_period_start).toLocaleDateString() : 'N/A'} - {performanceAnalytics.summary?.time_period_end ? new Date(performanceAnalytics.summary.time_period_end).toLocaleDateString() : 'N/A'}
                        </p>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Overall Avg Response</CardTitle>
                        <Clock className="h-4 w-4 text-muted-foreground" />
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold">{performanceAnalytics.summary?.overall_average_response_time !== undefined ? performanceAnalytics.summary.overall_average_response_time.toFixed(2) + ' ms' : 'N/A'}</div>
                        <p className="text-xs text-muted-foreground">Average across all endpoints</p>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Traffic Correlation</CardTitle>
                        <TrendingUp className="h-4 w-4 text-muted-foreground" />
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold">{(performanceAnalytics.data.traffic_correlation.correlation_coefficient * 100).toFixed(1)}%</div>
                        <p className="text-xs text-muted-foreground">
                          {performanceAnalytics.data.traffic_correlation.correlation_coefficient > 0.3 ? 'Strong positive correlation (higher traffic = slower responses)' : 
                           performanceAnalytics.data.traffic_correlation.correlation_coefficient > 0.1 ? 'Moderate positive correlation (higher traffic = slower responses)' : 
                           performanceAnalytics.data.traffic_correlation.correlation_coefficient > -0.1 ? 'Weak correlation (no clear relationship)' : 
                           performanceAnalytics.data.traffic_correlation.correlation_coefficient > -0.3 ? 'Moderate negative correlation (higher traffic = faster responses)' : 'Strong negative correlation (higher traffic = faster responses)'}
                        </p>
                      </CardContent>
                    </Card>
                  </div>

                  {/* Response Time by Day Chart */}
                  <Card>
                    <CardHeader>
                      <CardTitle>Average Response Time by Day</CardTitle>
                      <CardDescription>Daily performance trends</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <ChartContainer config={{}} className="h-[300px]">
                        <Bar
                          data={{
                            labels: performanceAnalytics.data.average_response_time_by_day.map(item => item.date),
                            datasets: [
                              {
                                label: 'Average Response Time (ms)',
                                data: performanceAnalytics.data.average_response_time_by_day.map(item => item.average_response_time),
                                backgroundColor: 'rgba(59, 130, 246, 0.8)',
                                borderColor: 'rgba(59, 130, 246, 1)',
                                borderWidth: 1,
                              },
                            ],
                          }}
                          options={{
                            ...chartOptions,
                            scales: {
                              y: {
                                beginAtZero: true,
                                title: {
                                  display: true,
                                  text: 'Response Time (ms)'
                                }
                              },
                              x: {
                                title: {
                                  display: true,
                                  text: 'Date'
                                }
                              }
                            }
                          }}
                        />
                      </ChartContainer>
                    </CardContent>
                  </Card>

                  {/* Response Time by Hour Chart */}
                  <Card>
                    <CardHeader>
                      <CardTitle>Average Response Time by Hour</CardTitle>
                      <CardDescription>Hourly performance patterns</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <ChartContainer config={{}} className="h-[300px]">
                        <Bar
                          data={{
                            labels: performanceAnalytics.data.average_response_time_by_hour.map(item => item.hour),
                            datasets: [
                              {
                                label: 'Average Response Time (ms)',
                                data: performanceAnalytics.data.average_response_time_by_hour.map(item => item.average_response_time),
                                backgroundColor: 'rgba(16, 185, 129, 0.8)',
                                borderColor: 'rgba(16, 185, 129, 1)',
                                borderWidth: 1,
                              },
                            ],
                          }}
                          options={{
                            ...chartOptions,
                            scales: {
                              y: {
                                beginAtZero: true,
                                title: {
                                  display: true,
                                  text: 'Response Time (ms)'
                                }
                              },
                              x: {
                                title: {
                                  display: true,
                                  text: 'Hour'
                                },
                                ticks: {
                                  maxRotation: 45,
                                  minRotation: 45
                                }
                              }
                            }
                          }}
                        />
                      </ChartContainer>
                    </CardContent>
                  </Card>

                  {/* Slowest Endpoints */}
                  <Card>
                    <CardHeader>
                      <CardTitle>Slowest Endpoints (Top 5)</CardTitle>
                      <CardDescription>Endpoints with highest average response times</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {performanceAnalytics.data.slowest_endpoints.map((endpoint, index) => (
                          <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                            <div className="flex items-center space-x-4">
                              <div className="flex items-center justify-center w-8 h-8 bg-red-100 text-red-600 rounded-full font-semibold">
                                {index + 1}
                              </div>
                              <div>
                                <div className="font-medium">{endpoint.method} {endpoint.path}</div>
                                <div className="text-sm text-muted-foreground">
                                  {endpoint.total_checks} checks • {endpoint.success_rate.toFixed(1)}% success rate
                                </div>
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="text-lg font-bold text-red-600">
                                {endpoint.average_response_time.toFixed(2)} ms
                              </div>
                              <div className="text-sm text-muted-foreground">Average</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Response Time by HTTP Method */}
                  <Card>
                    <CardHeader>
                      <CardTitle>Response Time by HTTP Method</CardTitle>
                      <CardDescription>Performance comparison across different HTTP methods</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {Object.entries(performanceAnalytics.data.response_time_by_method).map(([method, data]) => (
                          <div key={method} className="border rounded-lg p-4">
                            <div className="flex items-center justify-between mb-2">
                              <Badge variant="outline">{method}</Badge>
                              <span className="text-sm text-muted-foreground">{data.total_checks} checks</span>
                            </div>
                            <div className="space-y-2">
                              <div>
                                <span className="text-sm text-muted-foreground">Average:</span>
                                <div className="text-lg font-bold">{data.average_response_time.toFixed(2)} ms</div>
                              </div>
                              <div className="grid grid-cols-2 gap-2 text-sm">
                                <div>
                                  <span className="text-muted-foreground">Min:</span>
                                  <div>{data.min_response_time.toFixed(2)} ms</div>
                                </div>
                                <div>
                                  <span className="text-muted-foreground">Max:</span>
                                  <div>{data.max_response_time.toFixed(2)} ms</div>
                                </div>
                              </div>
                              <div>
                                <span className="text-sm text-muted-foreground">Success Rate:</span>
                                <div className="text-sm font-medium">{data.success_rate.toFixed(1)}%</div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Traffic Trends Over Time */}
                  {performanceAnalytics.data.traffic_trends && (
                    <Card>
                      <CardHeader>
                        <CardTitle>Traffic Trends Over Time</CardTitle>
                        <CardDescription>Request volume trends with anomaly detection</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-6">
                          {/* View Toggle */}
                          <div className="flex items-center gap-4">
                            <Label htmlFor="traffic-view">View:</Label>
                            <Select value={trafficTrendsView} onValueChange={setTrafficTrendsView}>
                              <SelectTrigger className="w-[180px]">
                                <SelectValue placeholder="Select view" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="daily">Daily Trends</SelectItem>
                                <SelectItem value="hourly">Hourly Trends</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>

                          {/* Traffic Volume Chart */}
                          <div>
                            <h3 className="text-lg font-semibold mb-4">
                              Request Volume - {trafficTrendsView === "daily" ? "Daily" : "Hourly"} View
                            </h3>
                            <ChartContainer config={{}} className="h-[300px]">
                              <Line
                                data={{
                                  labels: trafficTrendsView === "daily" 
                                    ? performanceAnalytics.data.traffic_trends.daily.map(item => item.date)
                                    : performanceAnalytics.data.traffic_trends.hourly.map(item => item.hour),
                                  datasets: [
                                    {
                                      label: 'Total Requests',
                                      data: trafficTrendsView === "daily"
                                        ? performanceAnalytics.data.traffic_trends.daily.map(item => item.total_checks)
                                        : performanceAnalytics.data.traffic_trends.hourly.map(item => item.total_checks),
                                      borderColor: 'rgba(59, 130, 246, 1)',
                                      backgroundColor: 'rgba(59, 130, 246, 0.1)',
                                      borderWidth: 2,
                                      fill: true,
                                      tension: 0.4,
                                    },
                                    {
                                      label: 'Successful Requests',
                                      data: trafficTrendsView === "daily"
                                        ? performanceAnalytics.data.traffic_trends.daily.map(item => item.successful_checks)
                                        : performanceAnalytics.data.traffic_trends.hourly.map(item => item.successful_checks),
                                      borderColor: 'rgba(16, 185, 129, 1)',
                                      backgroundColor: 'rgba(16, 185, 129, 0.1)',
                                      borderWidth: 2,
                                      fill: false,
                                      tension: 0.4,
                                    },
                                    {
                                      label: 'Failed Requests',
                                      data: trafficTrendsView === "daily"
                                        ? performanceAnalytics.data.traffic_trends.daily.map(item => item.failed_checks)
                                        : performanceAnalytics.data.traffic_trends.hourly.map(item => item.failed_checks),
                                      borderColor: 'rgba(239, 68, 68, 1)',
                                      backgroundColor: 'rgba(239, 68, 68, 0.1)',
                                      borderWidth: 2,
                                      fill: false,
                                      tension: 0.4,
                                    },
                                  ],
                                }}
                                options={{
                                  ...chartOptions,
                                  scales: {
                                    y: {
                                      beginAtZero: true,
                                      title: {
                                        display: true,
                                        text: 'Number of Requests'
                                      }
                                    },
                                    x: {
                                      title: {
                                        display: true,
                                        text: trafficTrendsView === "daily" ? 'Date' : 'Hour'
                                      },
                                      ticks: {
                                        maxRotation: 45,
                                        minRotation: 45
                                      }
                                    }
                                  },
                                  plugins: {
                                    ...chartOptions.plugins,
                                    tooltip: {
                                      callbacks: {
                                        afterBody: function(context) {
                                          const dataIndex = context[0].dataIndex;
                                          const data = trafficTrendsView === "daily"
                                            ? performanceAnalytics.data.traffic_trends.daily[dataIndex]
                                            : performanceAnalytics.data.traffic_trends.hourly[dataIndex];
                                          
                                          if (data) {
                                            return [
                                              `Success Rate: ${data.success_rate.toFixed(1)}%`,
                                              `Avg Response Time: ${data.avg_response_time.toFixed(2)}ms`
                                            ];
                                          }
                                          return [];
                                        }
                                      }
                                    }
                                  }
                                }}
                              />
                            </ChartContainer>
                          </div>

                          {/* Anomalies Summary */}
                          {performanceAnalytics.data.traffic_trends.anomalies && (
                            <div>
                              <h3 className="text-lg font-semibold mb-4">Traffic Anomalies Detected</h3>
                              <div className="grid gap-4 md:grid-cols-2">
                                {/* Daily Anomalies */}
                                <div className="space-y-3">
                                  <h4 className="font-medium text-sm text-muted-foreground">Daily Anomalies</h4>
                                  {performanceAnalytics.data.traffic_trends.anomalies.daily.length > 0 ? (
                                    <div className="space-y-2">
                                      {performanceAnalytics.data.traffic_trends.anomalies.daily.map((anomaly, index) => (
                                        <div key={index} className={`p-3 rounded-lg border ${
                                          anomaly.type === "spike" 
                                            ? "border-orange-200 bg-orange-50" 
                                            : "border-blue-200 bg-blue-50"
                                        }`}>
                                          <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                              <div className={`w-2 h-2 rounded-full ${
                                                anomaly.severity === "high" ? "bg-red-500" :
                                                anomaly.severity === "medium" ? "bg-yellow-500" : "bg-green-500"
                                              }`} />
                                              <span className="text-sm font-medium capitalize">
                                                {anomaly.type} ({anomaly.severity})
                                              </span>
                                            </div>
                                            <Badge variant="outline" className="text-xs">
                                              {anomaly.volume} requests
                                            </Badge>
                                          </div>
                                          <div className="text-xs text-muted-foreground mt-1">
                                            {anomaly.timestamp} • Z-score: {anomaly.z_score.toFixed(2)}
                                          </div>
                                        </div>
                                      ))}
                                    </div>
                                  ) : (
                                    <p className="text-sm text-muted-foreground">No daily anomalies detected</p>
                                  )}
                                </div>

                                {/* Hourly Anomalies */}
                                <div className="space-y-3">
                                  <h4 className="font-medium text-sm text-muted-foreground">Hourly Anomalies</h4>
                                  {performanceAnalytics.data.traffic_trends.anomalies.hourly.length > 0 ? (
                                    <div className="space-y-2">
                                      {performanceAnalytics.data.traffic_trends.anomalies.hourly.map((anomaly, index) => (
                                        <div key={index} className={`p-3 rounded-lg border ${
                                          anomaly.type === "spike" 
                                            ? "border-orange-200 bg-orange-50" 
                                            : "border-blue-200 bg-blue-50"
                                        }`}>
                                          <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                              <div className={`w-2 h-2 rounded-full ${
                                                anomaly.severity === "high" ? "bg-red-500" :
                                                anomaly.severity === "medium" ? "bg-yellow-500" : "bg-green-500"
                                              }`} />
                                              <span className="text-sm font-medium capitalize">
                                                {anomaly.type} ({anomaly.severity})
                                              </span>
                                            </div>
                                            <Badge variant="outline" className="text-xs">
                                              {anomaly.volume} requests
                                            </Badge>
                                          </div>
                                          <div className="text-xs text-muted-foreground mt-1">
                                            {anomaly.timestamp} • Z-score: {anomaly.z_score.toFixed(2)}
                                          </div>
                                        </div>
                                      ))}
                                    </div>
                                  ) : (
                                    <p className="text-sm text-muted-foreground">No hourly anomalies detected</p>
                                  )}
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Traffic Summary Stats */}
                          <div className="grid gap-4 md:grid-cols-3">
                            <Card>
                              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Total Requests</CardTitle>
                                <Activity className="h-4 w-4 text-muted-foreground" />
                              </CardHeader>
                              <CardContent>
                                <div className="text-2xl font-bold">
                                  {trafficTrendsView === "daily"
                                    ? performanceAnalytics.data.traffic_trends.daily.reduce((sum, item) => sum + item.total_checks, 0)
                                    : performanceAnalytics.data.traffic_trends.hourly.reduce((sum, item) => sum + item.total_checks, 0)
                                  }
                                </div>
                                <p className="text-xs text-muted-foreground">
                                  {trafficTrendsView === "daily" ? "Over selected days" : "Over selected hours"}
                                </p>
                              </CardContent>
                            </Card>
                            <Card>
                              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Avg Success Rate</CardTitle>
                                <CheckCircle className="h-4 w-4 text-muted-foreground" />
                              </CardHeader>
                              <CardContent>
                                <div className="text-2xl font-bold">
                                  {(() => {
                                    const data = trafficTrendsView === "daily"
                                      ? performanceAnalytics.data.traffic_trends.daily
                                      : performanceAnalytics.data.traffic_trends.hourly;
                                    const avgSuccessRate = data.reduce((sum, item) => sum + item.success_rate, 0) / data.length;
                                    return `${avgSuccessRate.toFixed(1)}%`;
                                  })()}
                                </div>
                                <p className="text-xs text-muted-foreground">
                                  Average across {trafficTrendsView === "daily" ? "days" : "hours"}
                                </p>
                              </CardContent>
                            </Card>
                            <Card>
                              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Anomalies Found</CardTitle>
                                <AlertTriangle className="h-4 w-4 text-muted-foreground" />
                              </CardHeader>
                              <CardContent>
                                <div className="text-2xl font-bold">
                                  {performanceAnalytics.data.traffic_trends.anomalies.daily.length + 
                                   performanceAnalytics.data.traffic_trends.anomalies.hourly.length}
                                </div>
                                <p className="text-xs text-muted-foreground">
                                  Spikes and dips detected
                                </p>
                              </CardContent>
                            </Card>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-muted-foreground">Loading performance data...</p>
                </div>
              )}
              <br></br>
              {/* Traffic Correlation Chart */}
              {performanceAnalytics && performanceAnalytics.data && performanceAnalytics.data.traffic_correlation && Array.isArray(performanceAnalytics.data.traffic_correlation.data) && performanceAnalytics.data.traffic_correlation.data.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Traffic vs Response Time Correlation</CardTitle>
                    <CardDescription>
                      Correlation between traffic volume and response times. 
                      {performanceAnalytics.data.traffic_correlation.interpretation}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ChartContainer config={{}} className="h-[300px]">
                      <Bar
                        data={{
                          labels: performanceAnalytics.data.traffic_correlation.data.map(item => item.hour),
                          datasets: [
                            {
                              label: 'Traffic Volume',
                              data: performanceAnalytics.data.traffic_correlation.data.map(item => item.traffic_volume),
                              backgroundColor: 'rgba(239, 68, 68, 0.8)',
                              borderColor: 'rgba(239, 68, 68, 1)',
                              borderWidth: 1,
                              yAxisID: 'y',
                            },
                            {
                              label: 'Average Response Time (ms)',
                              data: performanceAnalytics.data.traffic_correlation.data.map(item => item.average_response_time),
                              backgroundColor: 'rgba(168, 85, 247, 0.8)',
                              borderColor: 'rgba(168, 85, 247, 1)',
                              borderWidth: 1,
                              yAxisID: 'y1',
                            },
                          ],
                        }}
                        options={{
                          ...chartOptions,
                          scales: {
                            x: {
                              title: {
                                display: true,
                                text: 'Hour'
                              },
                              ticks: {
                                maxRotation: 45,
                                minRotation: 45
                              }
                            },
                            y: {
                              type: 'linear',
                              display: true,
                              position: 'left',
                              title: {
                                display: true,
                                text: 'Traffic Volume'
                              }
                            },
                            y1: {
                              type: 'linear',
                              display: true,
                              position: 'right',
                              title: {
                                display: true,
                                text: 'Response Time (ms)'
                              },
                              grid: {
                                drawOnChartArea: false,
                              },
                            },
                          }
                        }}
                      />
                    </ChartContainer>
                  </CardContent>
                </Card>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="health-logs" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Health Logs Export</CardTitle>
              <CardDescription>Export comprehensive health check logs for this remote server</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div className="bg-muted p-4 rounded-lg">
                  <h3 className="font-semibold mb-2">Export Information</h3>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>• Health check history for all discovered endpoints</li>
                    <li>• Response times and status codes</li>
                    <li>• Error messages and failure reasons</li>
                    <li>• Timestamps and endpoint details</li>
                    <li>• CSV format for easy analysis</li>
                  </ul>
                </div>
                
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold">Export Health Logs</h3>
                    <p className="text-sm text-muted-foreground">
                      Download a comprehensive CSV file containing all health check data for this remote server.
                    </p>
                  </div>
                  <Button 
                    onClick={exportHealthLogs} 
                    disabled={exporting || loading}
                    size="lg"
                  >
                    {exporting ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                      <Download className="h-4 w-4 mr-2" />
                    )}
                    Export Health Logs
                  </Button>
                </div>

                {analytics?.health_history && analytics.health_history.length > 0 && (
                  <div className="space-y-4">
                    <h3 className="font-semibold">Recent Health Checks</h3>
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                      {analytics.health_history.slice(0, 6).map((health) => (
                        <div key={health.id} className="border rounded-lg p-3">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-sm font-medium">Endpoint #{health.discovered_endpoint_id}</span>
                            <Badge variant={health.is_healthy ? "default" : "destructive"}>
                              {health.is_healthy ? "Healthy" : "Unhealthy"}
                            </Badge>
                          </div>
                          <div className="space-y-1 text-xs text-muted-foreground">
                            <div>Response Time: {health.response_time}ms</div>
                            <div>Status Code: {health.status_code}</div>
                            <div>Checked: {new Date(health.checked_at).toLocaleString()}</div>
                            {health.error_message && (
                              <div className="text-red-600 truncate" title={health.error_message}>
                                Error: {health.error_message}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                    <p className="text-sm text-muted-foreground text-center">
                      Showing latest 6 health checks. Export the full log for complete data.
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
} 