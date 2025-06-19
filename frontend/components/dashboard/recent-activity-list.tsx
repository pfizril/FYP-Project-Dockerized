"use client"

import { useState, useEffect } from "react"
import { AlertTriangle, CheckCircle, Clock, Key, LogIn, Shield, User, XCircle } from "lucide-react"
import { security } from "@/lib/api/security"

interface ActivityItem {
  log_id: number
  activity: string
  detail: string
  timestamp: string
  client_ip: string
  status?: "success" | "warning" | "error" | "info"
}

interface RecentActivityListProps {
  loading?: boolean
}

export function RecentActivityList({ loading = false }: RecentActivityListProps) {
  const [activities, setActivities] = useState<ActivityItem[]>([])

  useEffect(() => {
    const fetchActivityData = async () => {
      try {
        const data = await security.getActivityData()
        // Transform the data to match our ActivityItem interface
        const transformedActivities = data.activities.map((activity: any) => ({
          log_id: activity.log_id,
          activity: activity.activity_type || 'info',
          detail: activity.detail,
          timestamp: activity.timestamp,
          client_ip: activity.client_ip,
          status: activity.status || 'info'
        }))
        setActivities(transformedActivities)
      } catch (error) {
        console.error("Error fetching activity data:", error)
        setActivities([]) // Set empty array on error
      }
    }

    if (!loading) {
      fetchActivityData()
    }
  }, [loading])

  const getIcon = (type: string, status?: string) => {
    switch (type) {
      case "login":
        return <LogIn className="h-4 w-4" />
      case "endpoint":
        return status === "error" ? (
          <XCircle className="h-4 w-4 text-red-500" />
        ) : (
          <CheckCircle className="h-4 w-4 text-green-500" />
        )
      case "security":
        return <AlertTriangle className="h-4 w-4 text-amber-500" />
      case "api":
        return <Key className="h-4 w-4 text-blue-500" />
      case "user":
        return <User className="h-4 w-4 text-violet-500" />
      case "traffic":
        return status === "warning" ? (
          <AlertTriangle className="h-4 w-4 text-amber-500" />
        ) : (
          <Shield className="h-4 w-4 text-blue-500" />
        )
      default:
        return <Shield className="h-4 w-4" />
    }
  }

  if (loading) {
    return <div className="flex justify-center p-4">Loading activity data...</div>
  }

  if (activities.length === 0) {
    return (
      <div className="flex justify-center p-4 text-muted-foreground">
        No recent activity to display
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {activities.map((activity) => (
        <div key={activity.log_id} className="flex items-start space-x-4 rounded-md border p-4">
          <div className="rounded-full bg-muted p-2">{getIcon(activity.activity, activity.status)}</div>
          <div className="flex-1 space-y-1">
            <p className="text-sm font-medium">{activity.detail}</p>
            <div className="flex items-center text-xs text-muted-foreground">
              <Clock className="mr-1 h-3 w-3" />
              <span>{new Date(activity.timestamp).toLocaleString()}</span>
              {activity.client_ip && (
                <>
                  <span className="mx-1">•</span>
                  <User className="mr-1 h-3 w-3" />
                  <span>{activity.client_ip}</span>
                </>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
