import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'

// 样式
import './index.css'

// 页面（占位符）
function LoginPage() {
  return <div style={{ padding: 100 }}><h1>登录页</h1></div>
}

function Dashboard() {
  return <div style={{ padding: 100 }}><h1>工作台</h1></div>
}

function Applications() {
  return <div style={{ padding: 100 }}><h1>用工申请</h1></div>
}

function WorkItems() {
  return <div style={{ padding: 100 }}><h1>工作项管理</h1></div>
}

function Users() {
  return <div style={{ padding: 100 }}><h1>用户管理</h1></div>
}

// 404 页面
function NotFound() {
  return (
    <div style={{ padding: 100, textAlign: 'center' }}>
      <h1>404</h1>
      <p>页面不存在</p>
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ConfigProvider locale={zhCN} theme={{ token: { colorPrimary: '#1890ff' } }}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<Dashboard />} />
          <Route path="/applications" element={<Applications />} />
          <Route path="/work-items" element={<WorkItems />} />
          <Route path="/users" element={<Users />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  </React.StrictMode>
)
