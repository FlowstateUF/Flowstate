import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { authFetch } from "../../utils/authFetch";

function Account() {
  const [user, setUser] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    async function loadUser() {
      const res = await authFetch("http://localhost:5001/api/me");

      if (!res.ok) {
        navigate("/login");
        return;
      }

      const data = await res.json();
      setUser(data);
    }

    loadUser();
  }, [navigate]);

  if (!user) {
    return <div style={{ padding: "2rem" }}>Loading...</div>;
  }

  return (
    <div style={{ padding: "2rem" }}>
      <h2>Account</h2>
      <p><strong>Username:</strong> {user.username}</p>
      <p><strong>Email:</strong> {user.email}</p>
    </div>
  );
}

export default Account;
