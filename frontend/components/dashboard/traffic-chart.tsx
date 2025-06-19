"use client"

import { useState, useEffect } from "react"
import { Bar } from "react-chartjs-2"
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js"
import api from "@/lib/api"
import { Skeleton } from "@/components/ui/skeleton"

// Register ChartJS components
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

interface TrafficChartProps {
  loading?: boolean
}

interface ChartData {
  labels: string[]
  datasets: {
    label: string
    data: number[]
    backgroundColor: string
    borderColor: string
    borderWidth: number
    borderRadius?: number
  }[]
}

interface ChartOptions {
  responsive: boolean
  maintainAspectRatio: boolean
  plugins: {
    legend: {
      position: 'top'
    }
    tooltip: {
      mode: 'index'
      intersect: boolean
    }
  }
  scales: {
    y: {
      type: 'linear'
      beginAtZero: boolean
      grid: {
        display: boolean
      }
      title: {
        display: boolean
        text: string
      }
    }
    x: {
      grid: {
        display: boolean
      }
      ticks: {
        maxRotation: number
        minRotation: number
      }
    }
  }
  interaction: {
    mode: 'nearest'
    axis: 'x'
    intersect: boolean
  }
}

export function TrafficChart({ loading = false }: TrafficChartProps) {
  const [chartData, setChartData] = useState<ChartData>({
    labels: [],
    datasets: [],
  })

  useEffect(() => {
    const fetchTrafficData = async () => {
      try {
        const data = await api.get('/analytics/traffic-insights')
        
        // Process the data from the backend
        const trafficData = data || []
        const labels = trafficData.map((item: any) => item.endpoint)
        const requestCounts = trafficData.map((item: any) => item.request_count)

        setChartData({
          labels: labels,
          datasets: [
            {
              label: "Request Count",
              data: requestCounts,
              backgroundColor: "rgba(59, 130, 246, 0.7)", // Blue color for bars
              borderColor: "rgba(59, 130, 246, 1)",
              borderWidth: 1,
              borderRadius: 4,
            },
          ],
        })
      } catch (error) {
        console.error("Error fetching traffic data:", error)
        // Set default empty data on error
        setChartData({
          labels: ['No Data'],
          datasets: [
            {
              label: "Request Count",
              data: [0],
              backgroundColor: "rgba(59, 130, 246, 0.7)",
              borderColor: "rgba(59, 130, 246, 1)",
              borderWidth: 1,
              borderRadius: 4,
            },
          ],
        })
      }
    }

    if (!loading) {
      fetchTrafficData()
    }
  }, [loading])

  const options: ChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
      },
      tooltip: {
        mode: 'index',
        intersect: false,
      },
    },
    scales: {
      y: {
        type: 'linear',
        beginAtZero: true,
        grid: {
          display: true,
        },
        title: {
          display: true,
          text: "Request Count"
        }
      },
      x: {
        grid: {
          display: false,
        },
        ticks: {
          maxRotation: 45,
          minRotation: 45,
        }
      },
    },
    interaction: {
      mode: 'nearest',
      axis: 'x',
      intersect: false,
    },
  }

  if (loading) {
    return (
      <div className="h-[300px] flex items-center justify-center">
        <Skeleton className="h-[300px] w-full" />
      </div>
    )
  }

  return (
    <div className="h-[300px]">
      <Bar data={chartData} options={options} />
    </div>
  )
}
