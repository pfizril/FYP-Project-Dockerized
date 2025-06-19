import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { APIClient, defaultClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight, Activity, Clock, TrendingUp } from 'lucide-react';

interface Endpoint {
  endpoint_id: number;
  path: string;
  method: string;
  status: boolean;
  health_status: boolean;
  response_time?: number;
  last_checked?: string;
  status_code?: number;
  error_message?: string;
  failure_reason?: string;
  description?: string;
  parameters?: any;
  response_schema?: any;
  discovered_at?: string;
}

interface ServerData {
  server: {
    id: number;
    name: string;
    base_url: string;
    status: string;
  };
  endpoints: Endpoint[];
}

interface AnalyticsData {
  metrics: {
    total_endpoints: number;
    healthy_endpoints: number;
    unhealthy_endpoints: number;
    average_response_time: number;
  };
  endpoints: Array<{
    id: number;
    path: string;
    method: string;
    status: string;
    last_checked: string;
    response_time: number;
    status_code: number;
    error_message?: string;
    failure_reason?: string;
  }>;
  health_history: Array<{
    id: number;
    discovered_endpoint_id: number;
    status: boolean;
    is_healthy: boolean;
    response_time: number;
    checked_at: string;
    status_code: number;
    error_message: string | null;
    failure_reason: string | null;
  }>;
}

interface PerformanceAnalytics {
  time_range: string;
  data: {
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
    };
    slowest_endpoints: Array<{
      endpoint: string;
      method: string;
      path: string;
      average_response_time: number;
      total_checks: number;
      success_rate: number;
    }>;
  };
  summary: {
    total_health_checks: number;
    overall_average_response_time: number;
    time_period_start: string;
    time_period_end: string;
  };
}

interface TrafficSummary {
  total_requests_24h: number;
  total_requests_7d: number;
  most_hit_endpoint: {
    path: string;
    method: string;
    request_count: number;
    avg_response_time: number;
  };
  average_response_time: number;
  top_endpoints: Array<{
    path: string;
    method: string;
    request_count: number;
    avg_response_time: number;
  }>;
}

interface RemoteServerSimpleDashboardProps {
  serverId: number;
  client?: APIClient;
}

export function RemoteServerSimpleDashboard({ serverId, client }: RemoteServerSimpleDashboardProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ServerData | null>(null);
  const [trafficSummary, setTrafficSummary] = useState<TrafficSummary | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);
      try {
        // Get server info
        const serverResult = client
          ? await client.get<any>(`/remote-servers/${serverId}`)
          : await defaultClient.get<any>(`/remote-servers/${serverId}`);
        
        // Get real discovered endpoints data
        const endpointsResult = client
          ? await client.get<Endpoint[]>(`/remote-servers/${serverId}/discovered-endpoints`)
          : await defaultClient.get<Endpoint[]>(`/remote-servers/${serverId}/discovered-endpoints`);
        
        // Get analytics data for traffic summary
        let trafficData: TrafficSummary | null = null;
        try {
          // Get analytics data
          const analyticsResult = client
            ? await client.get<AnalyticsData>(`/analytics/remote-servers/${serverId}/analytics`)
            : await defaultClient.get<AnalyticsData>(`/analytics/remote-servers/${serverId}/analytics`);
          
          // Get performance analytics for traffic trends
          const performanceResult = client
            ? await client.get<PerformanceAnalytics>(`/analytics/remote-servers/${serverId}/performance-analytics?time_range=7d`)
            : await defaultClient.get<PerformanceAnalytics>(`/analytics/remote-servers/${serverId}/performance-analytics?time_range=7d`);
          
          // Calculate traffic summary from available data
          const totalRequests7d = performanceResult.summary.total_health_checks;
          const totalRequests24h = performanceResult.data.traffic_trends.hourly
            .slice(-24) // Last 24 hours
            .reduce((sum, hour) => sum + hour.total_checks, 0);
          
          // Get most hit endpoint from slowest endpoints (assuming more checks = more hits)
          const mostHitEndpoint = performanceResult.data.slowest_endpoints.length > 0 
            ? performanceResult.data.slowest_endpoints[0] 
            : null;
          
          // Get top endpoints
          const topEndpoints = performanceResult.data.slowest_endpoints
            .slice(0, 3)
            .map(endpoint => ({
              path: endpoint.path,
              method: endpoint.method,
              request_count: endpoint.total_checks,
              avg_response_time: endpoint.average_response_time
            }));
          
          trafficData = {
            total_requests_24h: totalRequests24h,
            total_requests_7d: totalRequests7d,
            most_hit_endpoint: mostHitEndpoint ? {
              path: mostHitEndpoint.path,
              method: mostHitEndpoint.method,
              request_count: mostHitEndpoint.total_checks,
              avg_response_time: mostHitEndpoint.average_response_time
            } : {
              path: 'N/A',
              method: 'N/A',
              request_count: 0,
              avg_response_time: 0
            },
            average_response_time: performanceResult.summary.overall_average_response_time,
            top_endpoints: topEndpoints
          };
          
        } catch (analyticsErr) {
          console.warn('Analytics data not available:', analyticsErr);
          // Don't fail the entire load if analytics data is not available
        }
        
        setData({
          server: {
            id: serverResult.id,
            name: serverResult.name,
            base_url: serverResult.base_url,
            status: serverResult.status
          },
          endpoints: endpointsResult
        });
        
        setTrafficSummary(trafficData);
      } catch (err: any) {
        setError(err.message || 'Failed to load remote server data');
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [serverId, client]);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!data) return <div>No data available</div>;

  const { server, endpoints } = data;
  const healthyCount = endpoints.filter(e => e.health_status).length;
  const unhealthyCount = endpoints.length - healthyCount;

  // Calculate pagination
  const totalPages = Math.ceil(endpoints.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentEndpoints = endpoints.slice(startIndex, endIndex);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Remote Server Info</CardTitle>
          <CardDescription>Basic details for this remote server</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-medium">Name:</span>
              <span>{server.name}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="font-medium">Base URL:</span>
              <span className="font-mono">{server.base_url}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="font-medium">Status:</span>
              <Badge variant={server.status === 'active' ? 'default' : 'destructive'}>{server.status}</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="font-medium">Endpoints:</span>
              <span>{endpoints.length}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="font-medium">Healthy:</span>
              <span className="text-green-600 font-semibold">{healthyCount}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="font-medium">Unhealthy:</span>
              <span className="text-red-600 font-semibold">{unhealthyCount}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Traffic Summary Section */}
      {trafficSummary && (
        <Card>
          <CardHeader>
            <CardTitle>Traffic Summary</CardTitle>
            <CardDescription>Server load and usage insights</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <Activity className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">Total Requests (24h)</span>
                </div>
                <div className="text-2xl font-bold">{trafficSummary.total_requests_24h.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground">Last 24 hours</p>
              </div>
              
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">Total Requests (7d)</span>
                </div>
                <div className="text-2xl font-bold">{trafficSummary.total_requests_7d.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground">Last 7 days</p>
              </div>
              
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">Avg Response Time</span>
                </div>
                <div className="text-2xl font-bold">{trafficSummary.average_response_time.toFixed(2)} ms</div>
                <p className="text-xs text-muted-foreground">Across all endpoints</p>
              </div>
            </div>
            
            {/* Most Hit Endpoint */}
            {trafficSummary.most_hit_endpoint && trafficSummary.most_hit_endpoint.path !== 'N/A' && (
              <div className="mt-6 p-4 bg-muted/50 rounded-lg">
                <h4 className="font-medium mb-2">Most Hit Endpoint</h4>
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <Badge variant="outline">{trafficSummary.most_hit_endpoint.method}</Badge>
                    <span className="font-mono text-sm">{trafficSummary.most_hit_endpoint.path}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">Requests:</span>
                      <div className="font-semibold">{trafficSummary.most_hit_endpoint.request_count.toLocaleString()}</div>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Avg Response:</span>
                      <div className="font-semibold">{trafficSummary.most_hit_endpoint.avg_response_time.toFixed(2)} ms</div>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            {/* Top Endpoints */}
            {trafficSummary.top_endpoints && trafficSummary.top_endpoints.length > 0 && (
              <div className="mt-6">
                <h4 className="font-medium mb-3">Top Endpoints by Traffic</h4>
                <div className="space-y-2">
                  {trafficSummary.top_endpoints.map((endpoint, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
                      <div className="flex items-center space-x-2">
                        <Badge variant="outline" className="text-xs">{endpoint.method}</Badge>
                        <span className="font-mono text-sm">{endpoint.path}</span>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-semibold">{endpoint.request_count.toLocaleString()}</div>
                        <div className="text-xs text-muted-foreground">{endpoint.avg_response_time.toFixed(2)} ms</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Endpoints</CardTitle>
          <CardDescription>List of discovered endpoints for this remote server</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {currentEndpoints.map((endpoint) => (
              <div key={endpoint.endpoint_id} className="p-4 border rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <Badge variant="outline">{endpoint.method}</Badge>
                    <span className="font-mono">{endpoint.path}</span>
                  </div>
                  <Badge variant={endpoint.health_status ? 'default' : 'destructive'}>
                    {endpoint.health_status ? 'Healthy' : 'Unhealthy'}
                  </Badge>
                </div>
                <div className="text-sm text-muted-foreground">
                  <div>Last checked: {endpoint.last_checked ? new Date(endpoint.last_checked).toLocaleString() : 'Never'}</div>
                  <div>Response time: {endpoint.response_time ? `${endpoint.response_time}ms` : 'N/A'}</div>
                  <div>Status code: {endpoint.status_code || 'N/A'}</div>
                  {endpoint.description && (
                    <div>Description: {endpoint.description}</div>
                  )}
                </div>
              </div>
            ))}
            
            {/* Pagination Controls */}
            <div className="flex items-center justify-between mt-4">
              <div className="text-sm text-muted-foreground">
                Showing {startIndex + 1}-{Math.min(endIndex, endpoints.length)} of {endpoints.length} endpoints
              </div>
              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                  disabled={currentPage === 1}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="text-sm">
                  Page {currentPage} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                  disabled={currentPage === totalPages}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
} 