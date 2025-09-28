import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
// 添加这两行 - 导入你的CSS文件
import './styles/main.css'
import './styles/components.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)