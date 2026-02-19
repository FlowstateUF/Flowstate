import { useState } from "react";

export default function Test() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);

  const handleGenerate = async () => {
    setLoading(true);
    setText("");

    try {
      const res = await fetch("http://localhost:5001/api/generate", {
        method: "POST",
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      setText(data.text ?? "");
    } catch (e) {
      setText("Error generating text.");
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{color: "black", padding: 32 }}>
      <h2>Test</h2>

        <button
        onClick={handleGenerate}
        disabled={loading}
        className="get-started-btn"
        >

        {loading ? "Generating..." : "Generate"}
      </button>

      <div style={{ marginTop: 20, whiteSpace: "pre-wrap" }}>
        {text}
      </div>
    </div>
  );
}


