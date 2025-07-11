import { NextResponse } from 'next/server'
import { cookies } from 'next/headers'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Helper function to get CSRF token from cookies
async function getCsrfToken() {
  const cookieStore = await cookies()
  return cookieStore.get('csrf_token')?.value
}

// Helper function to get auth headers
function getAuthHeaders(request: Request) {
  const token = request.headers.get('Authorization') || ''
  const apiKey = request.headers.get('X-API-KEY') || ''
  const csrfToken = request.headers.get('X-CSRF-Token') || ''

  return {
    'Content-Type': 'application/json',
    'Authorization': token,
    'X-API-KEY': apiKey,
    'X-CSRF-Token': csrfToken,
  }
}

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params
    const csrfToken = await getCsrfToken()
    const headers = getAuthHeaders(request)
    headers['X-CSRF-Token'] = csrfToken || ''
    
    const response = await fetch(`${API_BASE_URL}/remote-servers/${id}`, {
      headers,
      credentials: 'include',
    })

    const data = await response.json()

    if (!response.ok) {
      return NextResponse.json(
        { error: data.detail || 'Failed to fetch remote server' },
        { status: response.status }
      )
    }

    return NextResponse.json(data)
  } catch (error) {
    console.error('Error fetching remote server:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function PUT(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params
    const body = await request.json()
    const csrfToken = await getCsrfToken()
    const headers = getAuthHeaders(request)
    headers['X-CSRF-Token'] = csrfToken || ''

    const response = await fetch(`${API_BASE_URL}/remote-servers/${id}`, {
      method: 'PUT',
      headers,
      credentials: 'include',
      body: JSON.stringify(body),
    })

    const data = await response.json()

    if (!response.ok) {
      return NextResponse.json(
        { error: data.detail || 'Failed to update remote server' },
        { status: response.status }
      )
    }

    return NextResponse.json(data)
  } catch (error) {
    console.error('Error updating remote server:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function DELETE(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params
    const csrfToken = await getCsrfToken()
    const headers = getAuthHeaders(request)
    headers['X-CSRF-Token'] = csrfToken || ''

    const response = await fetch(`${API_BASE_URL}/remote-servers/${id}`, {
      method: 'DELETE',
      headers,
      credentials: 'include',
    })

    if (!response.ok) {
      const data = await response.json()
      return NextResponse.json(
        { error: data.detail || 'Failed to delete remote server' },
        { status: response.status }
      )
    }

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error deleting remote server:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
} 