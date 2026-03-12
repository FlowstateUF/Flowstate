
import { useRef, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../../components/NavBar.jsx";
import { authFetch } from "../../utils/authFetch";
import "./Courses.css";

const HERO_BG =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1600' height='900'%3E%3Cdefs%3E%3ClinearGradient id='g' x1='0' y1='0' x2='1' y2='1'%3E%3Cstop stop-color='%230b1220'/%3E%3Cstop offset='1' stop-color='%231f2937'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='1600' height='900' fill='url(%23g)'/%3E%3Ccircle cx='350' cy='320' r='220' fill='%233186d6' opacity='0.25'/%3E%3Ccircle cx='1200' cy='520' r='260' fill='%23ffffff' opacity='0.10'/%3E%3Ctext x='50%25' y='55%25' dominant-baseline='middle' text-anchor='middle' font-family='Arial' font-size='44' fill='%2394a3b8'%3E%3C/text%3E%3C/svg%3E";

function IconPaperMath() {
  return (
    <svg viewBox="0 0 120 90" role="img" aria-label="Paper with equations">
      <rect
        x="18"
        y="10"
        width="70"
        height="70"
        rx="10"
        fill="#ffffff"
        opacity="0.12"
        stroke="rgba(255,255,255,0.22)"
      />
      <path
        d="M78 10 L92 24 L92 70 a10 10 0 0 1-10 10 H28 a10 10 0 0 1-10-10 V20 a10 10 0 0 1 10-10 Z"
        fill="rgba(255,255,255,0.10)"
        stroke="rgba(255,255,255,0.28)"
      />
      <path d="M78 10 V24 H92" fill="none" stroke="rgba(255,255,255,0.28)" />
      <path
        d="M34 36 H66"
        stroke="rgba(255,255,255,0.75)"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <path
        d="M34 46 H56"
        stroke="rgba(255,255,255,0.55)"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <path
        d="M34 56 H62"
        stroke="rgba(255,255,255,0.55)"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <text
        x="36"
        y="68"
        fontSize="10"
        fill="rgba(255,255,255,0.7)"
        fontFamily="Arial"
      >

      </text>
    </svg>
  );
}

function IconRedBookHomework() {
  return (
    <svg viewBox="0 0 120 90" role="img" aria-label="Red homework book">
      <path
        d="M28 22 a10 10 0 0 1 10-10 h40 a12 12 0 0 1 12 12 v44 a10 10 0 0 1-10 10 H38 a10 10 0 0 0-10 10 Z"
        fill="#b91c1c"
        opacity="0.9"
      />
      <path
        d="M28 22 a10 10 0 0 1 10-10 h6 v66 h-6 a10 10 0 0 0-10 10 Z"
        fill="#7f1d1d"
        opacity="0.95"
      />
      <path
        d=""
        fill="none"
        stroke="rgba(255,255,255,0.25)"
      />
      <text
        x="49"
        y="35"
        fontSize="10"
        fill="rgba(255,255,255,0.92)"
        fontFamily="Arial"
        fontWeight="700"
      >
        STUDY


      </text>
      <text
        x="49"
        y="50"
        fontSize="10"
        fill="rgba(255,255,255,0.92)"
        fontFamily="Arial"
        fontWeight="700"
      >
        GUIDE


      </text>

    </svg>
  );
}

function IconReportCardAPlus() {
  return (
    <svg viewBox="0 0 120 90" role="img" aria-label="Report card A plus">
      <rect
        x="26"
        y="14"
        width="68"
        height="66"
        rx="10"
        fill="rgba(255,255,255,0.12)"
        stroke="rgba(255,255,255,0.28)"
      />
      <path
        d=""
        stroke="rgba(255,255,255,0.5)"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <path
        d="M36 40 H74"
        stroke="rgba(255,255,255,0.4)"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <path
        d="M36 50 H80"
        stroke="rgba(255,255,255,0.4)"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <path
        d="M36 60 H70"
        stroke="rgba(255,255,255,0.4)"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <text
        x="50"
        y="35"
        fontSize="18"
        fill="rgba(255,255,255,0.9)"
        fontFamily="Arial"
        fontWeight="800"
      >
        A+
      </text>
    </svg>
  );
}

function Courses() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);

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
    setError("");
    fileInputRef.current?.click();
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const isPdf =
      file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");

    if (!isPdf) {
      setSelectedFile(null);
      setError("Please upload a PDF file.");
      e.target.value = "";
      return;
    }

    setSelectedFile(file);
    setError("");
    uploadFile(file);
  };

  const uploadFile = async (file) => {
    const formData = new FormData();
    formData.append("file", file);

    try {
      setUploading(true);
      const response = await authFetch("http://localhost:5001/api/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json().catch(() => ({}));

      if (response.ok) {
        setError("");
        setSelectedFile(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
        console.log("Upload successful:", data);
      } else {
        setError("Upload failed. Please try again.");
        console.error("Upload failed:", data);
      }
    } catch (err) {
      setError("Upload error");
      console.error("Upload error:", err);
    } finally {
      setUploading(false);
    }
  };

  return (
    <>
      <Navbar />

      <section
        className="courses-hero"
        style={{ backgroundImage: `url("${HERO_BG}")` }}
      >
        <div className="courses-heroOverlay" />

        <div className="courses-heroInner">
          <div className="courses-heroLeft">
            <p className="courses-brand">FLOWSTATE</p>
            <h1 className="courses-heroTitle">Learn Smarter, Not Harder.</h1>
            <p className="courses-heroSub">
              Upload your textbook and get personalized quizzes, summaries, and
              progress tracking. Learning has never been this easy.
            </p>

            <button
              type="button"
              className="courses-primaryBtn"
              onClick={handleButtonClick}
              disabled={uploading}
            >
              {uploading ? "Uploading..." : "Get started (upload PDF)"}
            </button>

            {selectedFile && (
              <p className="courses-status">
                Selected: <strong>{selectedFile.name}</strong>
              </p>
            )}

            {error && (
              <p className="courses-status courses-error">
                <strong>{error}</strong>
              </p>
            )}
          </div>

          <div className="courses-heroCard">
            <h3 className="courses-cardTitle">Quick actions</h3>



            <button
              type="button"
              className="courses-cardBtn ghost"
              onClick={logout}
            >
              Logout
            </button>

            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf,.pdf"
              onChange={handleFileChange}
              style={{ display: "none" }}
            />
          </div>
        </div>
      </section>

      <section className="courses-lower">
        <div className="courses-lowerInner">
          <div className="courses-lowerHeader">
            <h2>Tools you’ll actually use</h2>
            <p>Build comprehension, track progress, and keep up the momentum.</p>
          </div>

          <div className="courses-cards">
            <div className="courses-serviceCard">
              <div className="courses-iconWrap">
                <IconPaperMath />
              </div>
              <div className="courses-serviceText">
                <h3>Summaries</h3>
                <p>Break down dense ideas into study ready explanations.</p>
              </div>
            </div>

            <div className="courses-serviceCard">
              <div className="courses-iconWrap">
                <IconRedBookHomework />
              </div>
              <div className="courses-serviceText">
                <h3>Practice</h3>
                <p>Generate quizzes and flashcards that target weak points.</p>
              </div>
            </div>

            <div className="courses-serviceCard">
              <div className="courses-iconWrap">
                <IconReportCardAPlus />
              </div>
              <div className="courses-serviceText">
                <h3>Progress</h3>
                <p>See what you’ve mastered and what might need more work.</p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

export default Courses;
