"use client"

import { Bar } from "react-chartjs-2"
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement } from "chart.js"
import { useState, useEffect } from "react"
import { Doughnut } from "react-chartjs-2"

// Register ChartJS components
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement)

interface ThreatIndicatorsChartProps {
  loading?: boolean
  indicators?: any
}

interface ChartData {
  labels: string[]
  datasets: {
    data: number[]
    backgroundColor: string[]
    borderColor: string[]
    borderWidth: number
  }[]
}

// Threat indicator configuration
const THREAT_INDICATORS = {
  sql_injection: {
    label: "SQL Injection",
    color: "rgba(239, 68, 68, 0.7)",   // Red
    borderColor: "rgba(239, 68, 68, 1)",
  },
  xss_attempts: {
    label: "XSS Attempts",
    color: "rgba(234, 179, 8, 0.7)",   // Yellow
    borderColor: "rgba(234, 179, 8, 1)",
  },
  path_traversal: {
    label: "Path Traversal",
    color: "rgba(59, 130, 246, 0.7)",  // Blue
    borderColor: "rgba(59, 130, 246, 1)",
  },
  unauthorized_access: {
    label: "Unauthorized Access",
    color: "rgba(16, 185, 129, 0.7)",  // Green
    borderColor: "rgba(16, 185, 129, 1)",
  },
  rate_limit_violations: {
    label: "Rate Limit Violations",
    color: "rgba(139, 92, 246, 0.7)",  // Purple
    borderColor: "rgba(139, 92, 246, 1)",
  },
  suspicious_ips: {
    label: "Suspicious IPs",
    color: "rgba(249, 115, 22, 0.7)",  // Orange
    borderColor: "rgba(249, 115, 22, 1)",
  },
}

export function ThreatIndicatorsChart({ loading = false, indicators }: ThreatIndicatorsChartProps) {
  const [chartData, setChartData] = useState<ChartData>({
    labels: [],
    datasets: [{
      data: [],
      backgroundColor: [],
      borderColor: [],
      borderWidth: 1
    }]
  })

  useEffect(() => {
    if (indicators) {
      const data: ChartData = {
        labels: Object.keys(THREAT_INDICATORS).map(key => THREAT_INDICATORS[key as keyof typeof THREAT_INDICATORS].label),
        datasets: [
          {
            data: Object.keys(THREAT_INDICATORS).map(key => indicators[key as keyof typeof indicators] || 0),
            backgroundColor: Object.keys(THREAT_INDICATORS).map(key => THREAT_INDICATORS[key as keyof typeof THREAT_INDICATORS].color),
            borderColor: Object.keys(THREAT_INDICATORS).map(key => THREAT_INDICATORS[key as keyof typeof THREAT_INDICATORS].borderColor),
            borderWidth: 1,
          },
        ],
      }
      setChartData(data)
    }
  }, [indicators])

  if (loading) {
    return <div className="flex justify-center p-4">Loading threat indicators...</div>
  }

  return (
    <div className="h-[300px]">
      <Doughnut
        data={chartData}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: "right",
            },
          },
        }}
      />
    </div>
  )
}
