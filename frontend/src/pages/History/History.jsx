import { Container, Stack, Title, Text, SimpleGrid, Paper, Box } from "@mantine/core";
import { useNavigate } from "react-router-dom";
import NavBar from "../../components/NavBar";
import "./History.css";

const textbooks = [
  { id: "bio101", name: "BIO101 — Intro Biology" },
  { id: "chem2045", name: "CHM2045 — General Chemistry" },
  { id: "cis4301", name: "CIS4301 — Database Systems" },
];

export default function History() {
  const navigate = useNavigate();

  const goToBook = (bookId) => {

    navigate(`/dashboard?textbook=${encodeURIComponent(bookId)}`);
  };

  return (
    <>
      <NavBar isAuthed={true} />

      <main className="history-page">
        <Container size="lg">
          <Stack gap="md">
            <Box>
              <Title order={1} className="history-title">
                Welcome back!
              </Title>
              <Text c="dimmed" className="history-subtitle">
                Click on a textbook to continue your learning.
              </Text>
            </Box>

            <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="xl" className="history-grid">
              {textbooks.map((t) => (
                <Paper
                  key={t.id}
                  withBorder
                  radius="md"
                  className="history-book"
                  onClick={() => goToBook(t.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") goToBook(t.id);
                  }}
                >
                  {}
                  <div className="history-cover">
                    <div className="history-img-icon">
                      <svg width="64" height="64" viewBox="0 0 24 24" fill="none">
                        <path
                          d="M21 19V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2Z"
                          stroke="#9aa3ad"
                          strokeWidth="1.5"
                        />
                        <path
                          d="M8.5 10.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z"
                          fill="#9aa3ad"
                        />
                        <path
                          d="M21 16l-5.5-5.5a2 2 0 0 0-2.8 0L5 18"
                          stroke="#9aa3ad"
                          strokeWidth="1.5"
                        />
                      </svg>
                    </div>
                  </div>

                  {}
                  <Text fw={600} mt="sm" className="history-book-label">
                    {t.name}
                  </Text>
                </Paper>
              ))}
            </SimpleGrid>
          </Stack>
        </Container>
      </main>
    </>
  );
}
