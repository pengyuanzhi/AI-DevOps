import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '../types/user'

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem('token'))

  const isLoggedIn = computed(() => !!token.value)
  const userRole = computed(() => user.value?.role || 'viewer')

  function setUser(userData: User) {
    user.value = userData
  }

  function setToken(tokenValue: string) {
    token.value = tokenValue
    localStorage.setItem('token', tokenValue)
  }

  function logout() {
    user.value = null
    token.value = null
    localStorage.removeItem('token')
  }

  function hasPermission(role: string): boolean {
    const roles = ['admin', 'maintainer', 'developer', 'viewer']
    const userRoleIndex = roles.indexOf(userRole.value)
    const requiredRoleIndex = roles.indexOf(role)
    return userRoleIndex >= 0 && userRoleIndex <= requiredRoleIndex
  }

  return {
    user,
    token,
    isLoggedIn,
    userRole,
    setUser,
    setToken,
    logout,
    hasPermission
  }
})
