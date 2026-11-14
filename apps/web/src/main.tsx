import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// the website demo answers /api calls in the browser; desktop and dev builds never load it
if (import.meta.env.VITE_DEMO === "1") (await import("./demo/server")).startDemo()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
