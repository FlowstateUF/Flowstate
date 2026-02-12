import { Outlet, useNavigate } from 'react-router-dom'
import gradLogo from './assets/grad_.png'
import './App.css'

/*
 * This component provides the shared content/formatting that appears on ALL pages.
 * - useNavigate() hook enables webpage routing
 */

function App() {
  const navigate = useNavigate()

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <img src={gradLogo} alt="Flowstate" className="brand-logo" />
          </div>

          <nav className="topbar-nav">
            <button type="button" className="nav-pill" onClick={() => navigate('/test')}>Test</button>
            <button type="button" className="nav-pill">Solutions</button>
            <button type="button" className="nav-pill">Our Mission</button>
          </nav>

          <div className="topbar-actions">
            <button type="button" className="get-started-btn">Get Started</button>
            <button type="button" className="login-btn" onClick={() => navigate('/login')}>
              log in
            </button>
          </div>
        </div>
      </header>
      <Outlet />
    </div>
  )
}

export default App