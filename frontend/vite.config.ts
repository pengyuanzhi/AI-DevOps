import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],

  // 基础路径（根路径部署）
  base: '/',

  // 路径别名
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },

  // 构建优化
  build: {
    // 代码分割
    rollupOptions: {
      output: {
        // 手动分块策略
        manualChunks: {
          // Vue核心库
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
          // UI库
          'element-plus': ['element-plus', '@element-plus/icons-vue'],
          // 图表库
          'echarts': ['echarts'],
          // 工具库
          'utils': ['axios']
        },
        // 输出文件命名
        chunkFileNames: 'js/[name]-[hash].js',
        entryFileNames: 'js/[name]-[hash].js',
        assetFileNames: '[ext]/[name]-[hash].[ext]'
      }
    },
    // 启用CSS代码分割
    cssCodeSplit: true,
    // 设置chunk大小警告限制
    chunkSizeWarningLimit: 1000,
    // 压缩配置
    minify: 'terser',
    terserOptions: {
      compress: {
        // 删除console
        drop_console: true,
        drop_debugger: true
      }
    }
  },

  // 开发服务器配置
  server: {
    port: 5173,
    open: true,
    // 代理配置（如需要）
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },

  // 依赖预构建
  optimizeDeps: {
    include: ['vue', 'vue-router', 'pinia', 'element-plus', 'axios', 'echarts']
  }
})
