import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import '@mantine/core/styles.css'
import './index.css'
import App from './App.jsx'
import Courses from './pages/Courses/Courses.jsx'
import Login from './pages/Login/Login.jsx'
import Register from './pages/Register/Register.jsx'
import Dashboard from './pages/Dashboard/Dashboard.jsx'
import Test from './pages/Test.jsx'
import About from './pages/About/About.jsx'
import Stats from "./pages/stats/stats.jsx";
import History from "./pages/History/History.jsx";
import Flash from "./pages/flash/flash.jsx";




/*
 * Each webpage route is defined here: examples below
 * - "/" goes to Home page (index route - default when at "/")
 * - "/login" goes to Login page
 * - "/register" goes to Register page
 * 
 * All routes share the same header from App.jsx for now
 * Additional routes can be added in a similiar fashion for different pages
 */

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <MantineProvider
    theme={{
      primaryColor: "blue",
      defaultRadius: "md",
      fontFamily: "Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif",
    }}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/login" element={<Login />} />

          {/* THIS IS A TEST ROUTE TO SEE LLM INTEGRATION */}
          <Route path="/test" element={<Test />} />

           {/* Will require logging in (once implemented) */}
          <Route path="/courses" element={<Courses />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/about" element={<About />} />
          <Route path="/stats" element={<Stats />} />
          <Route path="/history" element={<History />} />
          <Route path="/flash" element={<Flash />} />

        </Routes>
      </BrowserRouter>
    </MantineProvider>
  </StrictMode>,
)