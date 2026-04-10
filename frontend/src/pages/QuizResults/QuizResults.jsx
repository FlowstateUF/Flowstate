import { useLocation, useNavigate } from "react-router-dom";
import { Alert, Button, Container, Divider, Group, Paper, Stack, Text, Title } from "@mantine/core";
import { IconLockOpen2 } from "@tabler/icons-react";

import "./QuizResults.css";

export default function QuizResults() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state;

  if (!state) {
    return (
      <main className="quiz-results-page">
        <Container size="md">
          <Paper withBorder radius="lg" p="xl">
            <Title order={2}>Results</Title>
            <Text mt="sm" opacity={0.8}>
              No results found.
            </Text>
            <Button mt="lg" onClick={() => navigate("/dashboard")}>
              Back to Dashboard
            </Button>
          </Paper>
        </Container>
      </main>
    );
  }

  const {
    assessmentType = "quiz",
    score,
    total,
    responses = [],
    textbook_id,
    chapter_id,
    chapter_title,
    difficulty,
    canRetake = assessmentType !== "pretest",
  } = state;

  const isPretest = assessmentType === "pretest";

  const goToDashboard = () => {
    navigate("/dashboard", {
      state: {
        textbookId: textbook_id,
        chapterId: chapter_id,
      },
    });
  };

  return (
    <main className="quiz-results-page">
      <Container size="md">
        <Paper withBorder radius="lg" p="xl" className="quiz-results-card">
          <Group justify="space-between" align="center">
            <div>
              <Title order={2}>{isPretest ? "Pretest Results" : "Quiz Results"}</Title>
              {chapter_title ? (
                <Text c="dimmed" mt={6}>
                  {chapter_title}
                </Text>
              ) : null}
            </div>
            <Text fw={700}>
              Score: {score} / {total}
            </Text>
          </Group>

          {isPretest ? (
            <Alert
              variant="light"
              color="teal"
              radius="lg"
              icon={<IconLockOpen2 size={18} />}
              mt="lg"
            >
              Your chapter baseline has been recorded. Quizzes are now unlocked for this chapter.
            </Alert>
          ) : null}

          <Divider my="md" />

          <Stack gap="md">
            {responses.map((response) => (
              <Paper key={response.questionIndex} withBorder radius="md" p="md">
                <Text fw={700}>{response.title}</Text>
                <Text opacity={0.8} mt={4}>
                  {response.prompt}
                </Text>

                <Text mt="sm">
                  <b>Your answer:</b> {response.selectedText || "No answer selected"}
                </Text>
                <Text>
                  <b>Correct answer:</b> {response.correctText}
                </Text>

                {response.explanation ? (
                  <Text mt="sm" opacity={0.85}>
                    <b>Why:</b> {response.explanation}
                  </Text>
                ) : null}

                {response.citation ? (
                  <Text size="sm" c="dimmed" mt={4}>
                    {response.citation}
                  </Text>
                ) : null}

                <Text mt="xs" c={response.isCorrect ? "green" : "red"}>
                  {response.isCorrect ? "Correct" : "Incorrect"}
                </Text>
              </Paper>
            ))}
          </Stack>

          <Group justify="flex-end" mt="lg">
            {canRetake ? (
              <Button
                onClick={() =>
                  navigate("/quiz", {
                    state: {
                      assessmentType: "quiz",
                      textbook_id,
                      chapter_id,
                      chapter_title,
                      difficulty,
                    },
                  })
                }
              >
                Retake Quiz
              </Button>
            ) : null}

            <Button variant={canRetake ? "filled" : "default"} onClick={goToDashboard}>
              Go to Dashboard
            </Button>
          </Group>
        </Paper>
      </Container>
    </main>
  );
}
