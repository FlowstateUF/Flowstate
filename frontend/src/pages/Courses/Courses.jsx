import { useRef, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../../components/NavBar.jsx";
import { authFetch } from "../../utils/authFetch";
import "./Courses.css";

const HERO_BG =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1600' height='900'%3E%3Cdefs%3E%3ClinearGradient id='g' x1='0' y1='0' x2='1' y2='1'%3E%3Cstop stop-color='%230b1220'/%3E%3Cstop offset='1' stop-color='%231f2937'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='1600' height='900' fill='url(%23g)'/%3E%3Ccircle cx='350' cy='320' r='220' fill='%233186d6' opacity='0.25'/%3E%3Ccircle cx='1200' cy='520' r='260' fill='%23ffffff' opacity='0.10'/%3E%3C/svg%3E";
const TEXTBOOK_UPLOAD_LIMIT_MB = 50;
const TEXTBOOK_UPLOAD_LIMIT_BYTES = TEXTBOOK_UPLOAD_LIMIT_MB * 1000 * 1000;

function formatDisplayTitle(name = "") {
  return name.toLowerCase().endsWith(".pdf") ? name.slice(0, -4) : name;
}

// Builds the upload-limit message before we even send the file.
function buildUploadLimitMessage(fileSizeBytes) {
  if (typeof fileSizeBytes === "number" && fileSizeBytes > 0) {
    const fileSizeMb = fileSizeBytes / (1000 * 1000);
    return `This PDF is ${fileSizeMb.toFixed(1)} MB, but uploads are capped at ${TEXTBOOK_UPLOAD_LIMIT_MB} MB right now. Until founders update services, please upload a file under 50 MB.`;
  }

  return `Uploads are capped at ${TEXTBOOK_UPLOAD_LIMIT_MB} MB right now. Until founders update services, please upload a file under 50 MB.`;
}

function IconPaperMath() {
  return (
    <svg viewBox="0 0 120 90" role="img" aria-label="Paper with equations">
      <path
        d="M78 10 L92 24 L92 70 a10 10 0 0 1-10 10 H28 a10 10 0 0 1-10-10 V20 a10 10 0 0 1 10-10 Z"
        fill="rgba(255,255,255,0.10)"
        stroke="rgba(255,255,255,0.28)"
      />
      <path d="M78 10 V24 H92" fill="none" stroke="rgba(255,255,255,0.28)" />
      <path d="M34 36 H66" stroke="rgba(255,255,255,0.75)" strokeWidth="3" strokeLinecap="round" />
      <path d="M34 46 H56" stroke="rgba(255,255,255,0.55)" strokeWidth="3" strokeLinecap="round" />
      <path d="M34 56 H62" stroke="rgba(255,255,255,0.55)" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

function IconRedBookHomework() {
  return (
    <svg viewBox="0 0 120 90" role="img" aria-label="Red homework book">
      <path
        d="M28 22 a10 10 0 0 1 10-10 h40 a12 12 0 0 1 12 12 v44 a10 10 0 0 1-10 10 H38 a10 10 0 0 0-10 10 Z"
        fill="#b91c1c" opacity="0.9"
      />
      <path d="M28 22 a10 10 0 0 1 10-10 h6 v66 h-6 a10 10 0 0 0-10 10 Z" fill="#7f1d1d" opacity="0.95" />
      <text x="49" y="35" fontSize="10" fill="rgba(255,255,255,0.92)" fontFamily="Arial" fontWeight="700">STUDY</text>
      <text x="49" y="50" fontSize="10" fill="rgba(255,255,255,0.92)" fontFamily="Arial" fontWeight="700">GUIDE</text>
    </svg>
  );
}

function IconReportCardAPlus() {
  return (
    <svg viewBox="0 0 120 90" role="img" aria-label="Report card A plus">
      <rect x="26" y="14" width="68" height="66" rx="10" fill="rgba(255,255,255,0.12)" stroke="rgba(255,255,255,0.28)" />
      <path d="M36 40 H74" stroke="rgba(255,255,255,0.4)" strokeWidth="3" strokeLinecap="round" />
      <path d="M36 50 H80" stroke="rgba(255,255,255,0.4)" strokeWidth="3" strokeLinecap="round" />
      <path d="M36 60 H70" stroke="rgba(255,255,255,0.4)" strokeWidth="3" strokeLinecap="round" />
      <text x="50" y="35" fontSize="18" fill="rgba(255,255,255,0.9)" fontFamily="Arial" fontWeight="800">A+</text>
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
      }
    }
    loadMe();
  }, [navigate]);

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

    if (file.size > TEXTBOOK_UPLOAD_LIMIT_BYTES) {
      setSelectedFile(file);
      setError(buildUploadLimitMessage(file.size));
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

      if (!response.ok) {
        setError(data.error || "Upload failed. Please try again.");
        return;
      }

      setError("");
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";

      const existingReady =
        data.processing_status === "ready" || data.processing_status === "partial";

      const optimisticTextbook = {
        id: data.textbook_id,
        title: data.filename || file.name,
        display_title: data.display_title || formatDisplayTitle(data.filename || file.name),
        status: existingReady ? data.processing_status : "uploading",
        progress_percent: existingReady ? 100 : 10,
        stage_label: existingReady ? "Ready" : (data.status === "exists" ? "Processing" : "Uploading PDF"),
        detail: existingReady
          ? "Textbook already uploaded and ready to open."
          : (data.status === "exists"
              ? "This textbook is already in your library and is still processing."
              : "Uploading file and preparing processing..."),
        can_open: existingReady,
      };
      const existing = JSON.parse(localStorage.getItem("pendingTextbooks") || "[]");
      
      const nextPending = existing.filter((book) => book.id !== optimisticTextbook.id);

      nextPending.push({
        id: optimisticTextbook.id,
        title: optimisticTextbook.title,
        status: optimisticTextbook.status,
        stage: optimisticTextbook.status,
        progress: optimisticTextbook.progress_percent,
        stageLabel: optimisticTextbook.stage_label,
        detail: optimisticTextbook.detail,
        startedAt: Date.now(),
      });

      localStorage.setItem("pendingTextbooks", JSON.stringify(nextPending));

      navigate("/textbooks", {
        state: { uploadedTextbook: optimisticTextbook },
      });
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

      <section className="courses-hero" style={{ backgroundImage: `url("${HERO_BG}")` }}>
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
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf,.pdf"
              onChange={handleFileChange}
              style={{ display: "none" }}
            />
        </div>
      </section>

      <section className="courses-lower">
        <div className="courses-lowerInner">
          <div className="courses-lowerHeader">
            <h2>Tools you'll actually use</h2>
            <p>Build comprehension, track progress, and keep up the momentum.</p>
          </div>

          <div className="courses-cards">
            <div className="courses-serviceCard">
              <div className="courses-iconWrap"><IconPaperMath /></div>
              <div className="courses-serviceText">
                <h3>Summaries</h3>
                <p>Break down dense ideas into study ready explanations.</p>
              </div>
            </div>
            <div className="courses-serviceCard">
              <div className="courses-iconWrap"><IconRedBookHomework /></div>
              <div className="courses-serviceText">
                <h3>Practice</h3>
                <p>Generate quizzes and flashcards that target weak points.</p>
              </div>
            </div>
            <div className="courses-serviceCard">
              <div className="courses-iconWrap"><IconReportCardAPlus /></div>
              <div className="courses-serviceText">
                <h3>Progress</h3>
                <p>See what you've mastered and what might need more work.</p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

export default Courses;
