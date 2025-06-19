"use client"

import { useState, useEffect } from "react"
import { Bar } from "react-chartjs-2"
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from "chart.js"
import { Skeleton } from "@/components/ui/skeleton"

// Register ChartJS components
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

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

interface ResponseTimeChartProps {
  loading?: boolean
  endpoints?: Endpoint[]
}

interface ChartData {
  labels: string[]
  datasets: {
    label: string
    data: number[]
    backgroundColor: string
    borderColor: string
    borderWidth: number
    borderRadius: number
  }[]
}

export function ResponseTimeChart({ loading = false, endpoints = [] }: ResponseTimeChartProps) {
  const [chartData, setChartData] = useState<ChartData>({
    labels: [],
    datasets: [],
  })

  useEffect(() => {
    if (endpoints && endpoints.length > 0) {
      setChartData({
        labels: endpoints.map(endpoint => endpoint.name || endpoint.url || 'Unknown Endpoint'),
        datasets: [
          {
            label: "Response Time (ms)",
            data: endpoints.map(endpoint => endpoint.response_time || 0),
            backgroundColor: "rgba(99, 102, 241, 0.7)",
            borderColor: "rgba(99, 102, 241, 1)",
            borderWidth: 1,
            borderRadius: 4,
          },
        ],
      })
    } else if (!loading) {
      setChartData({
        labels: ['No Data'],
        datasets: [
          {
            label: "Response Time (ms)",
            data: [0],
            backgroundColor: "rgba(99, 102, 241, 0.7)",
            borderColor: "rgba(99, 102, 241, 1)",
            borderWidth: 1,
            borderRadius: 4,
          },
        ],
      })
    }
  }, [endpoints, loading])

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "top" as const,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: "Response Time (ms)",
        },
      },
      x: {
        ticks: {
          maxRotation: 45,
          minRotation: 45,
        },
      },
    },
  }

  if (loading) {
    return (
      <div className="h-[300px] flex items-center justify-center">
        <Skeleton className="h-[300px] w-full" />
      </div>
    )
  }

  if (chartData.labels.length === 0) {
    return <div className="flex justify-center p-4 text-muted-foreground">No response time data available.</div>
  }

  return (
    <div className="h-[300px]">
      <Bar data={chartData} options={options} />
    </div>
  )
}
