import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Container,
  Paper,
  Stack,
  Title,
  Text,
  Group,
  Button,
  Divider,
  Avatar,
} from "@mantine/core";

import NavBar from "../../components/NavBar";
import { authFetch } from "../../utils/authFetch";
import "./Account.css";

export default function Account() {
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
    return (
      <>
        <NavBar isAuthed={true} />
        <div className="account-loading">Loading...</div>
      </>
    );
  }

  return (
    <>
      <NavBar isAuthed={true} />

      <main className="account-page">
        <Container size="xl">
          <Paper withBorder radius="lg" p="xl" className="account-card">
            <Stack gap="lg">

              {/* Header */}
              <Group align="center" gap="md">
                <Avatar size="lg" radius="xl" color="blue" />
                <div>
                  <Title order={2}>Your Account</Title>
                  <Text c="dimmed" size="sm">
                    Profile information
                  </Text>
                </div>
              </Group>

              <Divider />

              {/* Info */}
              <Stack gap="md">
                <div className="account-infoSection">
                  <Text size="sm" c="dimmed">Username</Text>
                  <Text fw={600} size="lg">{user.username}</Text>
                </div>

                <div className="account-infoSection">
                  <Text size="sm" c="dimmed">Email</Text>
                  <Text fw={600} size="lg">{user.email}</Text>
                </div>
              </Stack>

              <Divider />

              {/* Logout */}
              <Group justify="flex-start" className="account-actionRow">
                <Button
                  color="red"
                  variant="light"
                  onClick={() => navigate("/login")}
                >
                  Log Out
                </Button>
              </Group>

            </Stack>
          </Paper>
        </Container>
      </main>
    </>
  );
}
