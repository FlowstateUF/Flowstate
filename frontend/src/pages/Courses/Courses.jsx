import { useRef, useState,useEffect } from 'react'
import notesImg from '../../assets/notes_.jpg'
import scantronImg from '../../assets/scantron.png'
import reportCardImg from '../../assets/reportcard.png'
import Navbar from "../../components/NavBar.jsx";
import './Courses.css'
import { authFetch } from "../../utils/authFetch";
import { useNavigate } from 'react-router-dom';

function Courses() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null)
  const [selectedFile, setSelectedFile] = useState(null)
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)

  useEffect(() => {
    async function loadMe() {
      const res = await authFetch("http://localhost:5001/api/me");

      if (!res.ok) {
        navigate("/login");
        return;
      }

      const me = await res.json().catch(() => null);
      console.log("Logged in as:", me);
    }

    loadMe();
  }, [navigate]);

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    navigate("/login");
  };

  const handleButtonClick = () => {
    setError('')
    fileInputRef.current?.click()
  }

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    const isPdf =
      file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')

    if (!isPdf) {
      setSelectedFile(null)
      setError('Please upload a PDF file.')
      e.target.value = ''
      return
    }

    setSelectedFile(file)
    setError('')
    uploadFile(file)
  }

  const uploadFile = async (file) => {
    const formData = new FormData()
    formData.append('file', file)

    try {
      setUploading(true)
      const response = await authFetch('http://localhost:5001/api/upload', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json().catch(() => ({}));

      if (response.ok) {
        setError('')
        setSelectedFile(null)
        if (fileInputRef.current) fileInputRef.current.value = ''
        // Show file?
        console.log('Upload successful:', data)
      } else {
        setError('Upload failed. Please try again.')
        console.error('Upload failed:', data)
      }
    } catch (err) {
      setError('Upload error')
      console.error('Upload error:', err)
    } finally {
      setUploading(false)
    }
  }

  return (
    <>
      <Navbar />
  
      <main className="content">
        <div className="center-stack">
          <div className="pill pill--welcome pill--cta">
            Welcome to Flowstate!
          </div>
  
          <button
            type="button"
            className="pill pill--upload pill--cta"
            onClick={handleButtonClick}
          >
            upload notes / textbook
          </button>

          <button type="button" className="pill pill--cta" onClick={logout}>
            logout
          </button>

          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf,.pdf"
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />
  
          {selectedFile && (
            <p className="status-text">
              Selected: <strong>{selectedFile.name}</strong>
            </p>
          )}
  
          {error && (
            <p className="status-text error-text">
              <strong>{error}</strong>
            </p>
          )}
  
          <div className="image-row">
            <img className="hover-card" src={notesImg} alt="Notes" />
            <img className="hover-card" src={scantronImg} alt="Scantron" />
            <img className="hover-card" src={reportCardImg} alt="Report card" />
          </div>
        </div>
      </main>
    </>
  );
}

export default Courses