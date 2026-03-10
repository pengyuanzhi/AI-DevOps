import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/DashboardView.vue'),
        meta: { title: '项目概览' }
      },
      {
        path: 'build',
        name: 'Build',
        component: () => import('../views/BuildView.vue'),
        meta: { title: '构建管理' }
      },
      {
        path: 'test',
        name: 'Test',
        component: () => import('../views/TestView.vue'),
        meta: { title: '测试管理' }
      },
      {
        path: 'test-quality',
        name: 'TestQuality',
        component: () => import('../views/TestQualityView.vue'),
        meta: { title: '测试和质量概览' }
      },
      {
        path: 'code-review',
        name: 'CodeReview',
        component: () => import('../views/CodeReviewView.vue'),
        meta: { title: '代码质量报告' }
      },
      {
        path: 'pipelines',
        name: 'Pipelines',
        component: () => import('../views/PipelinesView.vue'),
        meta: { title: 'CI/CD流水线' }
      },
      {
        path: 'pipelines/:id',
        name: 'PipelineDetail',
        component: () => import('../views/PipelineDetailView.vue'),
        meta: { title: '流水线详情' }
      },
      {
        path: 'ai-analysis',
        name: 'AIAnalysis',
        component: () => import('../views/AIAnalysisView.vue'),
        meta: { title: 'AI分析结果' }
      },
      {
        path: 'memory-safety',
        name: 'MemorySafety',
        component: () => import('../views/MemorySafetyView.vue'),
        meta: { title: '内存安全报告' }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('../views/SettingsView.vue'),
        meta: { title: '设置' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('../views/NotFoundView.vue')
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// 路由守卫
router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')

  if (to.meta.requiresAuth !== false && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router
