export interface User {
  id: string
  gitlab_user_id: number
  username: string
  email: string
  role: 'admin' | 'maintainer' | 'developer' | 'viewer'
  created_at: string
  updated_at: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  user: User
  expires_in: number
}
