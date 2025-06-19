"use client"

import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Activity, Clock, AlertCircle } from "lucide-react";
import { OverviewMetricsCards } from "@/components/dashboard/overview-metrics-cards";
import { TrafficChart } from "@/components/dashboard/traffic-chart";
import { EndpointStatusTable } from "@/components/dashboard/endpoint-status-table";
import { ThreatIndicatorsChart } from "@/components/dashboard/threat-indicators-chart";
import { ResponseTimeChart } from "@/components/dashboard/response-time-chart";
import { RecentActivityList } from "@/components/dashboard/recent-activity-list";
import { Button } from "@/components/ui/button";
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { APIClient, defaultClient } from '@/lib/api-client';

interface OverviewMetrics {
  total_requests: number;
  failed_requests: number;
  total_4xx: number;
  total_5xx: number;
  avg_response_time: number;
}

interface TrafficInsight {
  endpoint: string;
  request_count: number;
  avg_response_time: number;
}

interface PerformanceTrend {
  hour: string;
  avg_response_time: number;
}

interface Endpoint {
  endpoint_id: number;
  name: string;
  url: string;
  method: string;
  status: boolean;
  health_status: boolean;
  response_time: number;
  last_checked: string;
  status_code: number;
  error_message?: string;
  failure_reason?: string;
  is_healthy?: boolean;
}

interface AnalyticsData {
  overview: OverviewMetrics;
  traffic: TrafficInsight[];
  performance: { performance_trends: PerformanceTrend[] };
  endpoints: Endpoint[];
  threatIndicators: {
    sql_injection: number;
    xss_attempts: number;
    path_traversal: number;
    unauthorized_access: number;
    rate_limit_violations: number;
    suspicious_ips: number;
  };
}

interface ModernDashboardProps {
  serverId: number;
  client?: APIClient;
}

export function ModernDashboard({ serverId, client }: ModernDashboardProps) {
  const router = useRouter()
  const { isAuthenticated, isLoading: authLoading } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null)

  useEffect(() => {
    // Check authentication
    if (!authLoading && !isAuthenticated) {
      console.log('Not authenticated, redirecting to login')
      router.push('/login')
      return
    }

    const loadData = async () => {
      if (authLoading) return // Don't load data while checking auth
      
      setLoading(true)
      setError(null)
      
      try {
        console.log('Starting to load dashboard data')
        const [overview, traffic, performance, endpoints, threatIndicators] = await Promise.all([
          (client?.get<OverviewMetrics>('/analytics/overview-metrics') || defaultClient.get<OverviewMetrics>('/analytics/overview-metrics')),
          (client?.get<TrafficInsight[]>('/analytics/traffic-insights') || defaultClient.get<TrafficInsight[]>('/analytics/traffic-insights')),
          (client?.get<{ performance_trends: PerformanceTrend[] }>('/analytics/performance-trends') || defaultClient.get<{ performance_trends: PerformanceTrend[] }>('/analytics/performance-trends')),
          (client?.get<{ endpoints: Endpoint[] }>('/analytics/endpoints/latest-health') || defaultClient.get<{ endpoints: Endpoint[] }>('/analytics/endpoints/latest-health')),
          (client?.get<{
            sql_injection: number;
            xss_attempts: number;
            path_traversal: number;
            unauthorized_access: number;
            rate_limit_violations: number;
            suspicious_ips: number;
          }>('/security/threat-indicators') || defaultClient.get<{
            sql_injection: number;
            xss_attempts: number;
            path_traversal: number;
            unauthorized_access: number;
            rate_limit_violations: number;
            suspicious_ips: number;
          }>('/security/threat-indicators'))
        ]);

        setAnalyticsData({
          overview,
          traffic,
          performance,
          endpoints: endpoints.endpoints || [],
          threatIndicators
        });
      } catch (err: any) {
        console.error("Error loading dashboard data:", err)
        if (err.response?.status === 401) {
          console.log('Unauthorized, redirecting to login')
          router.push('/login')
        } else {
          setError(err.message || "Failed to load dashboard data")
        }
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [router, isAuthenticated, authLoading, serverId, client])

  if (authLoading) {
    return <div>Loading...</div>
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-red-600 mb-2">Error Loading Dashboard</h2>
          <p className="text-gray-600">{error}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (loading) {
    return <div>Loading...</div>
  }

  if (!analyticsData) {
    return <div>No data available</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">Monitor your API endpoints, traffic, and security threats</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            <Clock className="mr-2 h-4 w-4" />
            Last updated: {new Date().toLocaleTimeString()}
          </Button>
        </div>
      </div>

      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="endpoints">Endpoints</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <OverviewMetricsCards loading={loading} metrics={analyticsData.overview} />

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-7">
            <Card className="lg:col-span-4">
              <CardHeader>
                <CardTitle>Traffic Analysis</CardTitle>
                <CardDescription>API request volume over time</CardDescription>
              </CardHeader>
              <CardContent>
                <TrafficChart loading={loading} />
              </CardContent>
            </Card>

            <Card className="lg:col-span-3">
              <CardHeader>
                <CardTitle>Response Time</CardTitle>
                <CardDescription>Average response time by endpoint (ms)</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponseTimeChart loading={loading} endpoints={analyticsData.endpoints} />
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-7">
            <Card className="lg:col-span-4">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <div className="space-y-1">
                  <CardTitle>Endpoint Health</CardTitle>
                  <CardDescription>Status of monitored endpoints</CardDescription>
                </div>
                <Badge variant="outline" className="ml-auto">
                  {analyticsData.endpoints.length} Total
                </Badge>
              </CardHeader>
              <CardContent>
                <EndpointStatusTable loading={loading} endpoints={analyticsData.endpoints} />
              </CardContent>
            </Card>

            <Card className="lg:col-span-3">
              <CardHeader>
                <CardTitle>Threat Indicators</CardTitle>
                <CardDescription>Security threats detected in the last 24h</CardDescription>
              </CardHeader>
              <CardContent>
                <ThreatIndicatorsChart loading={loading} indicators={analyticsData.threatIndicators} />
              </CardContent>
            </Card>
          </div>

        </TabsContent>

        <TabsContent value="endpoints" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Server Information</CardTitle>
              <CardDescription>Basic server details</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-medium">Name:</span>
                  <span>{analyticsData.endpoints[0].name}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="font-medium">Base URL:</span>
                  <span className="font-mono">{analyticsData.endpoints[0].url}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="font-medium">Status:</span>
                  <Badge variant={analyticsData.endpoints[0].status ? 'default' : 'destructive'}>
                    {analyticsData.endpoints[0].status ? 'Active' : 'Inactive'}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Discovered Endpoints</CardTitle>
              <CardDescription>List of discovered API endpoints</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {analyticsData.endpoints.map((endpoint) => (
                  <div key={endpoint.endpoint_id} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        <Badge variant="outline">{endpoint.method}</Badge>
                        <span className="font-mono">{endpoint.url}</span>
                      </div>
                      <Badge variant={endpoint.status ? 'default' : 'destructive'}>
                        {endpoint.status ? 'Active' : 'Inactive'}
                      </Badge>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      <div>Last checked: {new Date(endpoint.last_checked).toLocaleString()}</div>
                      <div>Response time: {endpoint.response_time}ms</div>
                      <div>Status code: {endpoint.status_code}</div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Security Overview</CardTitle>
              <CardDescription>Monitor security threats and vulnerabilities</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">
                This section provides detailed security monitoring and threat analysis tools. Switch to this tab to view
                comprehensive security information.
              </p>
              <Button>View Full Security Dashboard</Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
