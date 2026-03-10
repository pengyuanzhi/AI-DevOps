import request from './request'
import type { LoginRequest, LoginResponse, User } from '../types/user'

export const authApi = {
  /**
   * 用户登录
   */
  async login(data: LoginRequest): Promise<LoginResponse> {
    return request.post('/api/v1/auth/login', data)
  },

  /**
   * 用户登出
   */
  async logout(): Promise<void> {
    return request.post('/api/v1/auth/logout')
  },

  /**
   * 获取当前用户信息
   */
  async getCurrentUser(): Promise<User> {
    return request.get('/api/v1/auth/me')
  },

  /**
   * 刷新Token
   */
  async refreshToken(refreshToken: string): Promise<LoginResponse> {
    return request.post('/api/v1/auth/refresh', { refresh_token: refreshToken })
  }
}
