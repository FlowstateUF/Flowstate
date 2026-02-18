import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Anchor,
  Button,
  Checkbox,
  Container,
  Group,
  Paper,
  PasswordInput,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import brain from "../../assets/generic_brain.png";
import classes from "./Login.module.css";


export default function Login() {
  // store user input
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // UI feedback
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();

    setError("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:5001/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(data.error || "Invalid email or password");
      }

      navigate("/courses");
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={classes.wrapper}>
      {/* LEFT: login (not stretched) */}
      <div className={classes.left}>
      <Paper className={classes.form} radius="xl" withBorder shadow="sm">
          <Title order={2} className={classes.title}>
            Welcome back
          </Title>

          <form onSubmit={handleSubmit}>
            <TextInput
              label="Email address"
              placeholder="hello@gmail.com"
              size="lg"
              radius="xl"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />

            <PasswordInput
              label="Password"
              placeholder="Your password"
              mt="md"
              size="lg"
              radius="xl"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />

            <Checkbox label="Keep me logged in" mt="xl" size="md" />

            {error && (
              <Text c="red" size="sm" mt="sm">
                {error}
              </Text>
            )}

            <Button
              fullWidth
              mt="xl"
              size="lg"
              radius="xl"
              type="submit"
              loading={loading}
            >
              Login
            </Button>
          </form>

          <Text ta="center" mt="md">
            Don&apos;t have an account?{" "}
            <Anchor
              component="button"
              type="button"
              fw={500}
              onClick={() => navigate("/register")}
            >
              Register
            </Anchor>
          </Text>
        </Paper>
      </div>

      {/* RIGHT: marketing (logo + header) */}
      <div className={classes.right}>
        <div className={classes.rightInner}>
          <img src={brain} alt="Flowstate" className={classes.brandLogo} />

          <h1 className={classes.headline}>
            Get ready to enter a <span className={classes.accent}>flowstate</span>.
          </h1>

          <p className={classes.subhead}>
            Upload a textbook, generate practice, and track mastery across your courses.
          </p>

        </div>
      </div>
    </div>
  );
}