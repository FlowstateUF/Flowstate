import { useLocation, useNavigate } from "react-router-dom";
import { Container, Paper, Title, Text, Stack, Group, Button, Divider } from "@mantine/core";
import "./QuizResults.css";

export default function QuizResults() {
  const location = useLocation();
  const navigate = useNavigate();

  const state = location.state;

  // for all yall backend ppl If user refreshes results page, router state is gone
  if (!state) {
    return (
      <main className="quiz-results-page">
        <Container size="md">
          <Paper withBorder radius="lg" p="xl">
            <Title order={2}>Quiz Results</Title>
            <Text mt="sm" opacity={0.8}>
              No results found (try taking the quiz again).
            </Text>
            <Button mt="lg" onClick={() => navigate("/quiz")}>
              Back to Quiz
            </Button>
          </Paper>
        </Container>
      </main>
    );
  }

  const { score, total, responses } = state;

  return (
    <main className="quiz-results-page">
      <Container size="md">
        <Paper withBorder radius="lg" p="xl" className="quiz-results-card">
          <Group justify="space-between" align="center">
            <Title order={2}>Quiz Results</Title>
            <Text fw={700}>
              Score: {score} / {total}
            </Text>
          </Group>

          <Divider my="md" />

          <Stack gap="md">
            {responses.map((r) => (
              <Paper key={r.questionIndex} withBorder radius="md" p="md">
                <Text fw={700}>{r.title}</Text>
                <Text opacity={0.8} mt={4}>
                  {r.prompt}
                </Text>

                <Text mt="sm">
                  <b>Your answer:</b> {r.selectedText}
                </Text>
                <Text>
                  <b>Correct answer:</b> {r.correctText}
                </Text>

                <Text mt="xs" c={r.isCorrect ? "green" : "red"}>
                  {r.isCorrect ? "Correct" : "Incorrect"}
                </Text>
              </Paper>
            ))}
          </Stack>

          <Group justify="flex-end" mt="lg">
            <Button variant="default" onClick={() => navigate("/quiz")}>
              Retake Quiz
            </Button>
            <Button onClick={() => navigate("/dashboard")}>Go to Dashboard</Button>
          </Group>
        </Paper>
      </Container>
    </main>
  );
}