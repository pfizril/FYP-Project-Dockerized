"use client"

import type React from "react"
import { useState, useEffect, useCallback } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Key, Edit, RefreshCw, Copy, Eye, EyeOff, ChevronLeft, ChevronRight } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { users } from "@/lib/api/users"
import { security } from "@/lib/api/security"

interface User {
  user_id: number
  user_name: string
  user_email: string
  user_role: string
}

interface ActivityItem {
  log_id: number
  activity_type: string
  detail: string
  timestamp: string
  client_ip: string
  user_name: string
  user_email: string
  status?: "success" | "warning" | "error" | "info"
}

interface ActivityResponse {
  activities: ActivityItem[]
  total: number
  page: number
  page_size: number
}

export function ModernUserManagement() {
  const [usersList, setUsersList] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [showApiKeyModal, setShowApiKeyModal] = useState(false)
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [apiKey, setApiKey] = useState<string | null>(null)
  const [showApiKey, setShowApiKey] = useState(false)
  const [activities, setActivities] = useState<ActivityItem[]>([])
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [formData, setFormData] = useState({
    user_name: "",
    user_email: "",
    user_role: "",
  })
  const { toast } = useToast()

  // Fetch users from backend
  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await users.getUsers()
      setUsersList(data)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch users'
      setError(errorMessage)
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive"
      })
    } finally {
      setLoading(false)
    }
  }, [toast])

  // Fetch activity data with pagination
  const fetchActivityData = useCallback(async () => {
    try {
      const data = await security.getActivityData(currentPage, pageSize)
      setActivities(data.activities)
      setTotalPages(Math.ceil(data.total / data.page_size))
    } catch (err) {
      console.error("Error fetching activity data:", err)
      setActivities([])
      toast({
        title: "Error",
        description: "Failed to fetch activity data",
        variant: "destructive"
      })
    }
  }, [currentPage, pageSize, toast])

  useEffect(() => {
    fetchUsers()
    fetchActivityData()
  }, [fetchUsers, fetchActivityData])

  const handleEditUser = (user: User) => {
    setSelectedUser(user)
    setFormData({
      user_name: user.user_name,
      user_email: user.user_email,
      user_role: user.user_role,
    })
    setShowModal(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedUser) return

    try {
      await users.updateUser(selectedUser.user_id, formData)
      
      toast({
        title: "Success",
        description: "User updated successfully",
      })

      setShowModal(false)
      fetchUsers() // Refresh the list
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update user'
      setError(errorMessage)
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive"
      })
    }
  }

  const handleApiKey = async (user: User) => {
    setSelectedUser(user)
    try {
      const data = await users.getApiKey(user.user_id)
      setApiKey(data.api_key)
      setShowApiKeyModal(true)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch API key'
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive"
      })
    }
  }

  const generateApiKey = async () => {
    if (!selectedUser) return

    try {
      const data = await users.generateApiKey(selectedUser.user_id)
      setApiKey(data.api_key)

      toast({
        title: "Success",
        description: "New API key generated successfully",
      })
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate API key'
      setError(errorMessage)
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive"
      })
    }
  }

  const copyApiKey = () => {
    if (apiKey) {
      navigator.clipboard.writeText(apiKey)
      toast({
        title: "Copied",
        description: "API key copied to clipboard",
      })
    }
  }

  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage)
  }

  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize)
    setCurrentPage(1) // Reset to first page when changing page size
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">User Management</h1>
          <p className="text-muted-foreground">Manage users, roles, and API keys</p>
        </div>
        <Button onClick={fetchUsers} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="users" className="space-y-4">
        <TabsList>
          <TabsTrigger value="users">Users & Roles</TabsTrigger>
          <TabsTrigger value="activity">Activity Logs</TabsTrigger>
        </TabsList>

        <TabsContent value="users" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Users ({usersList.length})</CardTitle>
              <CardDescription>Manage user accounts and permissions</CardDescription>
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
                      <TableHead>User ID</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {usersList.map((user) => (
                      <TableRow key={user.user_id}>
                        <TableCell className="font-mono">{user.user_id}</TableCell>
                        <TableCell className="font-medium">{user.user_name}</TableCell>
                        <TableCell>{user.user_email}</TableCell>
                        <TableCell>
                          <Badge variant={user.user_role === "Admin" ? "default" : "secondary"}>{user.user_role}</Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <Button variant="ghost" size="sm" onClick={() => handleEditUser(user)}>
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleApiKey(user)}>
                              <Key className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="activity" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Activity Logs</CardTitle>
              <CardDescription>Recent user activities and system events</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {activities.length === 0 ? (
                  <div className="text-center py-4 text-muted-foreground">
                    No recent activity to display
                  </div>
                ) : (
                  <>
                    <div className="space-y-4">
                      {activities.map((activity) => (
                        <div key={activity.log_id} className="flex items-center justify-between p-3 border rounded">
                          <div>
                            <p className="font-medium">{activity.detail}</p>
                            <div className="text-sm text-muted-foreground space-y-1">
                              <p>User: {activity.user_name} ({activity.user_email})</p>
                              <p>IP: {activity.client_ip}</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <Badge variant={activity.status === "error" ? "destructive" : "default"}>
                              {activity.status}
                            </Badge>
                            <p className="text-sm text-muted-foreground mt-1">
                              {new Date(activity.timestamp).toLocaleString()}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Pagination Controls */}
                    <div className="flex items-center justify-between pt-4">
                      <div className="flex items-center space-x-2">
                        <p className="text-sm text-muted-foreground">Rows per page</p>
                        <Select
                          value={pageSize.toString()}
                          onValueChange={(value) => handlePageSizeChange(Number(value))}
                        >
                          <SelectTrigger className="h-8 w-[70px]">
                            <SelectValue placeholder={pageSize} />
                          </SelectTrigger>
                          <SelectContent side="top">
                            {[10, 20, 30, 40, 50].map((size) => (
                              <SelectItem key={size} value={size.toString()}>
                                {size}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="flex items-center space-x-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handlePageChange(currentPage - 1)}
                          disabled={currentPage === 1}
                        >
                          <ChevronLeft className="h-4 w-4" />
                        </Button>
                        <div className="text-sm text-muted-foreground">
                          Page {currentPage} of {totalPages}
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handlePageChange(currentPage + 1)}
                          disabled={currentPage === totalPages}
                        >
                          <ChevronRight className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Edit User Modal */}
      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Edit User</DialogTitle>
            <DialogDescription>Update user information and permissions</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="name">Username</Label>
                <Input
                  id="name"
                  value={formData.user_name}
                  onChange={(e) => setFormData({ ...formData, user_name: e.target.value })}
                  required
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.user_email}
                  onChange={(e) => setFormData({ ...formData, user_email: e.target.value })}
                  required
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="role">Role</Label>
                <Select
                  value={formData.user_role}
                  onValueChange={(value) => setFormData({ ...formData, user_role: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Admin">Admin</SelectItem>
                    <SelectItem value="User">User</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowModal(false)}>
                Cancel
              </Button>
              <Button type="submit">Update User</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* API Key Modal */}
      <Dialog open={showApiKeyModal} onOpenChange={setShowApiKeyModal}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>API Key for {selectedUser?.user_name}</DialogTitle>
            <DialogDescription>Manage API key for this user account</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {apiKey ? (
              <div className="space-y-4">
                <div className="grid gap-2">
                  <Label>Current API Key</Label>
                  <div className="flex items-center gap-2">
                    <Input type={showApiKey ? "text" : "password"} value={apiKey} readOnly className="font-mono" />
                    <Button variant="outline" size="sm" onClick={() => setShowApiKey(!showApiKey)}>
                      {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                    <Button variant="outline" size="sm" onClick={copyApiKey}>
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <Alert>
                  <Key className="h-4 w-4" />
                  <AlertDescription>
                    Keep this API key secure. It provides access to your API endpoints.
                  </AlertDescription>
                </Alert>
              </div>
            ) : (
              <div className="text-center py-4">
                <p className="text-muted-foreground mb-4">No API key found for this user.</p>
                <Button onClick={generateApiKey}>
                  <Key className="mr-2 h-4 w-4" />
                  Generate API Key
                </Button>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowApiKeyModal(false)}>
              Close
            </Button>
            {apiKey && <Button onClick={generateApiKey}>Generate New Key</Button>}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
