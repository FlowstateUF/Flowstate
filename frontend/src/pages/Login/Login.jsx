import React, { useState } from "react";
import "./Login.css"; // reuse same styling
import { useNavigate } from "react-router-dom";

export default function Login() {

  // store user input
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // UI feedback
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  // runs when user clicks login
  const handleSubmit = async (e) => {
    e.preventDefault();

    setError("");
    setLoading(true);

    try {
      // send POST request to Flask backend
      const res = await fetch("http://localhost:5001/api/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },

        // send login credentials
        body: JSON.stringify({
          email: email,
          password: password
        })
      });

      const data = await res.json();

      // backend rejected login
      if (!res.ok) {
        throw new Error(data.error || "Invalid email or password");
      }

      // login successful → go to homepage
      navigate("/");

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-box">

        <h1>Login</h1>

        <form onSubmit={handleSubmit}>

          <input
            type="text"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          {error && <div className="error">{error}</div>}

          <button disabled={loading}>
            {loading ? "Signing in..." : "Login"}
          </button>

        </form>

        {/* link to registration */}
        <p className="switch-text">
          Create new account{" "}
          <span onClick={() => navigate("/register")}>Sign up</span>
        </p>

      </div>
    </div>
  );
}