"use client";

import React, { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { RefreshCw, Search, ChevronDown, ChevronRight, Calendar, Clock, FileText, Code } from "lucide-react";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { APIClient } from "@/lib/api-client";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const ITEMS_PER_PAGE = 10;

interface Endpoint {
  endpoint_id: number;
  name: string;
  url: string;
  method: string;
  status: boolean;
  health_status: boolean;
  response_time?: number;
  last_checked?: string;
  status_code?: number;
  error_message?: string;
  failure_reason?: string;
  path?: string;
  description?: string;
  parameters?: any;
  response_schema?: any;
  discovered_at?: string;
}

interface EndpointsResponse {
  endpoints: Endpoint[];
}

interface RemoteServer {
  id: number;
  name: string;
  base_url: string;
  api_key: string;
}

interface RemoteServerEndpointsTableProps {
  server: RemoteServer;
}

export function RemoteServerEndpointsTable({ server }: RemoteServerEndpointsTableProps) {
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [filteredEndpoints, setFilteredEndpoints] = useState<Endpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filterMethod, setFilterMethod] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

  // Pagination
  const totalPages = Math.ceil((filteredEndpoints?.length || 0) / ITEMS_PER_PAGE);
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
  const endIndex = startIndex + ITEMS_PER_PAGE;
  const currentEndpoints = filteredEndpoints?.slice(startIndex, endIndex) || [];

  // Fetch endpoints from remote server
  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const token = localStorage.getItem('token');
      const apiKey = server.api_key || localStorage.getItem('apiKey') || '';
      const response = await fetch(
        `${backendUrl}/remote-servers/${server.id}/discovered-endpoints?page_size=1000`,
        {
          headers: {
            'Content-Type': 'application/json',
            ...(apiKey ? { 'X-API-KEY': apiKey } : {}),
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
          },
          credentials: 'include',
        }
      );
      if (!response.ok) throw new Error('Failed to load endpoints data');
      const endpointsData = await response.json();
      setEndpoints(endpointsData.endpoints || endpointsData || []);
    } catch (err: any) {
      setError(err.message || "Failed to load endpoints data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!server) return;
    loadData();
  }, [server]);

  const handleRefresh = () => {
    loadData();
  };

  // Filter endpoints
  useEffect(() => {
    let filtered = (endpoints || []).filter(
      (endpoint) =>
        (endpoint.path ? endpoint.path.toLowerCase().includes(search.toLowerCase()) : false) ||
        (endpoint.description ? endpoint.description.toLowerCase().includes(search.toLowerCase()) : false)
    );
    if (filterMethod && filterMethod !== "all") {
      filtered = filtered.filter((endpoint) => endpoint.method === filterMethod);
    }
    setFilteredEndpoints(filtered);
    setCurrentPage(1);
  }, [endpoints, search, filterMethod]);

  const toggleRowExpansion = (endpointId: number) => {
    const newExpandedRows = new Set(expandedRows);
    if (newExpandedRows.has(endpointId)) {
      newExpandedRows.delete(endpointId);
    } else {
      newExpandedRows.add(endpointId);
    }
    setExpandedRows(newExpandedRows);
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return "N/A";
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return "Invalid Date";
    }
  };

  const renderJsonData = (data: any) => {
    if (!data) return <span className="text-muted-foreground">No data available</span>;
    return (
      <pre className="text-xs bg-muted p-2 rounded overflow-auto max-h-32">
        {JSON.stringify(data, null, 2)}
      </pre>
    );
  };

  // Calculate metrics
  const totalEndpoints = filteredEndpoints.length;
  const activeEndpoints = filteredEndpoints.filter(e => e.status).length;
  const healthyEndpoints = filteredEndpoints.filter(e => e.health_status).length;
  const responseTimes = filteredEndpoints.filter(e => e.response_time !== null && e.response_time !== undefined).map(e => e.response_time!);
  const avgResponseTime = responseTimes.length > 0 ? responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Remote Server Endpoints</h1>
          <p className="text-muted-foreground">Monitor endpoints for this remote server</p>
        </div>
        <div>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button 
                  variant="outline" 
                  size="icon" 
                  onClick={handleRefresh}
                  disabled={loading}
                >
                  <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Refresh endpoints data</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>

      {error && (
        <div className="text-red-500 font-medium p-2">{error}</div>
      )}

      {/* Metrics Summary */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Endpoints</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalEndpoints}</div>
            <p className="text-xs text-muted-foreground">
              Discovered endpoints
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Endpoints</CardTitle>
            <Code className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{activeEndpoints}</div>
            <p className="text-xs text-muted-foreground">
              Currently active
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Healthy Endpoints</CardTitle>
            <RefreshCw className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{healthyEndpoints}</div>
            <p className="text-xs text-muted-foreground">
              Passing health checks
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{avgResponseTime.toFixed(1)}ms</div>
            <p className="text-xs text-muted-foreground">
              Average across endpoints
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <div className="flex-1">
              <Label htmlFor="search">Search</Label>
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="search"
                  placeholder="Search endpoints by path or description..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-8"
                />
              </div>
            </div>
            <div className="w-48">
              <Label htmlFor="method-filter">Method</Label>
              <Select value={filterMethod} onValueChange={setFilterMethod}>
                <SelectTrigger>
                  <SelectValue placeholder="All Methods" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Methods</SelectItem>
                  <SelectItem value="GET">GET</SelectItem>
                  <SelectItem value="POST">POST</SelectItem>
                  <SelectItem value="PUT">PUT</SelectItem>
                  <SelectItem value="DELETE">DELETE</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Endpoints Table */}
      <Card>
        <CardHeader>
          <CardTitle>Endpoints ({filteredEndpoints?.length || 0})</CardTitle>
          <CardDescription>Status of monitored endpoints</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="h-8 w-8 animate-spin" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12"></TableHead>
                  <TableHead>Path</TableHead>
                  <TableHead>Method</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Discovered</TableHead>
                  <TableHead>Last Checked</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {currentEndpoints.map((endpoint) => (
                  <React.Fragment key={endpoint.endpoint_id}>
                    <TableRow>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => toggleRowExpansion(endpoint.endpoint_id)}
                          className="h-6 w-6 p-0"
                        >
                          {expandedRows.has(endpoint.endpoint_id) ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          )}
                        </Button>
                      </TableCell>
                      <TableCell className="font-mono text-sm max-w-xs truncate">
                        {endpoint.path}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{endpoint.method}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={endpoint.status ? "default" : "destructive"}>
                          {endpoint.status ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-xs truncate">
                        {endpoint.description || "No description"}
                      </TableCell>
                      <TableCell className="text-sm">
                        {formatDate(endpoint.discovered_at)}
                      </TableCell>
                      <TableCell className="text-sm">
                        {formatDate(endpoint.last_checked)}
                      </TableCell>
                    </TableRow>
                    {expandedRows.has(endpoint.endpoint_id) && (
                      <TableRow>
                        <TableCell colSpan={7} className="bg-muted/50">
                          <div className="p-4 space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                              {/* Parameters */}
                              <div>
                                <div className="flex items-center gap-2 mb-2">
                                  <Code className="h-4 w-4" />
                                  <h4 className="font-semibold">Parameters</h4>
                                </div>
                                {renderJsonData(endpoint.parameters)}
                              </div>
                              
                              {/* Response Schema */}
                              <div>
                                <div className="flex items-center gap-2 mb-2">
                                  <FileText className="h-4 w-4" />
                                  <h4 className="font-semibold">Response Schema</h4>
                                </div>
                                {renderJsonData(endpoint.response_schema)}
                              </div>
                            </div>
                            
                            {/* Health Information */}
                            <div className="border-t pt-4">
                              <h4 className="font-semibold mb-2">Health Information</h4>
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                                <div>
                                  <span className="text-muted-foreground">Response Time:</span>
                                  <div>{endpoint.response_time ? `${endpoint.response_time}ms` : "N/A"}</div>
                                </div>
                                <div>
                                  <span className="text-muted-foreground">Status Code:</span>
                                  <div>{endpoint.status_code || "N/A"}</div>
                                </div>
                                <div>
                                  <span className="text-muted-foreground">Health Status: </span>
                                  <Badge variant={endpoint.health_status ? "default" : "destructive"} className="text-xs">
                                    {endpoint.health_status ? "Healthy" : "Unhealthy"}
                                  </Badge>
                                </div>
                                <div>
                                  <span className="text-muted-foreground">Error Details:</span>
                                  <div className="space-y-1">
                                    {endpoint.status_code === 200 ? (
                                      <span className="text-xs text-green-600 font-medium">Success</span>
                                    ) : endpoint.status_code && endpoint.status_code !== 200 ? (
                                      <div className="space-y-1">
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
                                          </span>
                                        )}
                                        {endpoint.error_message && (
                                          <div className="text-xs text-muted-foreground truncate">
                                            {endpoint.error_message}
                                          </div>
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
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </React.Fragment>
                ))}
              </TableBody>
            </Table>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-4 flex justify-center">
              <Pagination>
                <PaginationContent>
                  <PaginationItem>
                    <PaginationPrevious
                      onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
                      className={currentPage === 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
                    />
                  </PaginationItem>
                  {/* First page */}
                  <PaginationItem>
                    <PaginationLink onClick={() => setCurrentPage(1)} isActive={currentPage === 1}>
                      1
                    </PaginationLink>
                  </PaginationItem>
                  {/* Ellipsis if needed */}
                  {currentPage > 3 && (
                    <PaginationItem>
                      <PaginationEllipsis />
                    </PaginationItem>
                  )}
                  {/* Current page and surrounding pages */}
                  {Array.from({ length: 3 }, (_, i) => currentPage - 1 + i)
                    .filter((page) => page > 1 && page < totalPages)
                    .map((page) => (
                      <PaginationItem key={page}>
                        <PaginationLink onClick={() => setCurrentPage(page)} isActive={currentPage === page}>
                          {page}
                        </PaginationLink>
                      </PaginationItem>
                    ))}
                  {/* Ellipsis if needed */}
                  {currentPage < totalPages - 2 && (
                    <PaginationItem>
                      <PaginationEllipsis />
                    </PaginationItem>
                  )}
                  {/* Last page */}
                  {totalPages > 1 && (
                    <PaginationItem>
                      <PaginationLink onClick={() => setCurrentPage(totalPages)} isActive={currentPage === totalPages}>
                        {totalPages}
                      </PaginationLink>
                    </PaginationItem>
                  )}
                  <PaginationItem>
                    <PaginationNext
                      onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
                      className={currentPage === totalPages ? "pointer-events-none opacity-50" : "cursor-pointer"}
                    />
                  </PaginationItem>
                </PaginationContent>
              </Pagination>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
} 