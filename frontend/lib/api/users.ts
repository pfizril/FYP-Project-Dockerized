import { api } from '../api'

interface User {
  user_id: number
  user_name: string
  user_email: string
  user_role: string
}

interface ApiKeyResponse {
  api_key: string
}

export const users = {
  async getUsers(): Promise<User[]> {
    const response = await api.get<User[]>('/auth/users/list')
    return response.data
  },

  async updateUser(userId: number, userData: Partial<User>): Promise<User> {
    const response = await api.put<User>(`/auth/users/update/${userId}`, userData)
    return response.data
  },

  async getApiKey(userId: number): Promise<ApiKeyResponse> {
    const response = await api.get<ApiKeyResponse>(`/auth/api-keys/${userId}`)
    return response.data
  },

  async generateApiKey(userId: number): Promise<ApiKeyResponse> {
    const response = await api.post<ApiKeyResponse>(`/auth/api-keys/generate/${userId}`)
    return response.data
  }
} 