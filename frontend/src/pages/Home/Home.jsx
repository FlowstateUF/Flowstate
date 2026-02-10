import { useRef, useState } from 'react'
import notesImg from '../../assets/notes_.jpg'
import scantronImg from '../../assets/scantron.png'
import reportCardImg from '../../assets/reportcard.png'
import './Home.css'

function Home() {
  const fileInputRef = useRef(null)
  const [selectedFile, setSelectedFile] = useState(null)
  const [error, setError] = useState('')

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
  }

  return (
    <main className="content">
      <div className="center-stack">
        <div className="pill pill--welcome pill--cta">Welcome to Flowstate!</div>

        <button
          type="button"
          className="pill pill--upload pill--cta"
          onClick={handleButtonClick}
        >
          upload notes / textbook
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
  )
}

export default Home