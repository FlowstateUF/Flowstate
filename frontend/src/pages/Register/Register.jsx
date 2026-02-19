import React, { useState } from "react";
import "./Register.css";
import { useNavigate } from "react-router-dom";

export default function Register() {

  // store user input
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const navigate = useNavigate();

  // UI feedback
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  // runs when user clicks register
  const handleSubmit = async (e) => {
    e.preventDefault();

    setError("");
    setSuccess("");

    // simple frontend check
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setLoading(true);

    try {
      // send POST request to Flask backend
      const res = await fetch("http://localhost:5001/api/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },

        // body must match what Flask expects
        body: JSON.stringify({
          username: username,
          email: email,
          password: password
        })
      });

      const data = await res.json();

      // if backend validation failed
      if (!res.ok) {
        throw new Error(data.error || "Registration failed");
      }


      setSuccess("Account created! Redirecting to login...");
      
      // Route the user to login after registering
      setTimeout(() => {
        navigate("/login");
      }, 900);

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="register-page">
      <div className="register-box">

        <h1>Create Account</h1>

        <form onSubmit={handleSubmit}>

          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />

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

          <input
            type="password"
            placeholder="Confirm Password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
          />

          {error && <div className="error">{error}</div>}
          {success && <div className="success">{success}</div>}

          <button disabled={loading}>
            {loading ? "Creating..." : "Register"}
          </button>

        </form>
      </div>
    </div>
  );
}
