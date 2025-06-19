"use client"

import { useState, useEffect } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { CheckCircle, Clock, XCircle, AlertTriangle, Lock } from "lucide-react"
import api from "@/lib/api"
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination"

interface Endpoint {
  endpoint_id: number
  name: string
  url: string
  method: string
  status: boolean
  health_status: boolean
  response_time?: number
  last_checked?: string
  status_code?: number
  error_message?: string
  failure_reason?: string
  is_healthy?: boolean
}

interface EndpointStatusTableProps {
  loading?: boolean
  endpoints?: any[]
}

export function EndpointStatusTable({ loading = false, endpoints = [] }: EndpointStatusTableProps) {
  const [endpointData, setEndpointData] = useState<Endpoint[]>([])
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 5

  useEffect(() => {
    if (endpoints && endpoints.length > 0) {
      setEndpointData(endpoints)
    } else {
      const fetchEndpointData = async () => {
        try {
          const data = await api.get('/analytics/endpoints/latest-health?page_size=1000')
          setEndpointData(data.endpoints || data)
        } catch (error) {
          console.error("Error fetching endpoint data:", error)
        }
      }

      if (!loading) {
        fetchEndpointData()
      }
    }
  }, [loading, endpoints])

  // Calculate pagination
  const totalPages = Math.ceil(endpointData.length / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const endIndex = startIndex + itemsPerPage
  const currentEndpoints = endpointData.slice(startIndex, endIndex)

  function normalizeHealthStatus(value: unknown): boolean {
    if (typeof value === 'boolean') return value;
    if (typeof value === 'string') return value.toLowerCase() === 'true';
    if (typeof value === 'number') return value === 1;
    return false;
  }

  if (loading) {
    return <div className="flex justify-center p-4">Loading endpoint data...</div>
  }

  return (
    <div className="space-y-4">
      <div className="rounded-md border">
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
            {currentEndpoints.map((endpoint: Endpoint) => {
              const normalizedHealthStatus = normalizeHealthStatus(endpoint.health_status);
              return (
                <TableRow 
                  key={endpoint.endpoint_id}
                  className={!normalizedHealthStatus ? "bg-red-50/50" : ""}
                >
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
                    {normalizedHealthStatus !== undefined ? (
                      <div className="flex items-center">
                        {normalizedHealthStatus ? (
                          <>
                            <CheckCircle className="mr-2 h-4 w-4 text-green-500" />
                            <span>Healthy</span>
                          </>
                        ) : (
                          <>
                            <XCircle className="mr-2 h-4 w-4 text-red-500" />
                            <span>Unhealthy</span>
                          </>
                        )}
                      </div>
                    ) : (
                      <div className="flex items-center">
                        <AlertTriangle className="mr-2 h-4 w-4 text-yellow-500" />
                        <span>Unknown</span>
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    {endpoint.response_time ? `${endpoint.response_time} ms` : "N/A"}
                  </TableCell>
                  <TableCell>
                    {endpoint.status_code ? (
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
                    )}
                  </TableCell>
                  <TableCell>
                    {endpoint.status_code === 200 ? (
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
              )
            })}
          </TableBody>
        </Table>
      </div>

      {totalPages > 1 && (
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious 
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                className={currentPage === 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
              />
            </PaginationItem>
            
            {[...Array(totalPages)].map((_, index) => {
              const pageNumber = index + 1
              // Show first page, last page, current page, and pages around current page
              if (
                pageNumber === 1 ||
                pageNumber === totalPages ||
                (pageNumber >= currentPage - 1 && pageNumber <= currentPage + 1)
              ) {
                return (
                  <PaginationItem key={pageNumber}>
                    <PaginationLink
                      onClick={() => setCurrentPage(pageNumber)}
                      isActive={currentPage === pageNumber}
                    >
                      {pageNumber}
                    </PaginationLink>
                  </PaginationItem>
                )
              } else if (
                pageNumber === currentPage - 2 ||
                pageNumber === currentPage + 2
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
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                className={currentPage === totalPages ? "pointer-events-none opacity-50" : "cursor-pointer"}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}
    </div>
  )
}
