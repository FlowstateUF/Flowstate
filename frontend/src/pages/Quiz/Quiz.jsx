import { useState, useEffect } from "react";
import {
  Container,
  Paper,
  Group,
  Title,
  Progress,
  Text,
  Stack,
  SimpleGrid,
  Button,
  ActionIcon,
} from "@mantine/core";
import { IconInfoCircle, IconHelpCircle } from "@tabler/icons-react";
import { useNavigate, useLocation } from "react-router-dom";
import "./Quiz.css";

export default function Quiz() {
  const navigate = useNavigate();
  const location = useLocation();
  const { textbook_id, chapter_title, difficulty } = location.state || {};

  const API_BASE = "http://127.0.0.1:5001";

  const [questions, setQuestions] = useState([]);
  const [index, setIndex] = useState(0);
  const [selectedByIndex, setSelectedByIndex] = useState({}); // { [qIndex]: choiceIndex }
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const total = questions.length;
  const current = questions[index];
  const progressValue = total > 0 ? ((index + 1) / total) * 100 : 0;

  const selectedChoice = selectedByIndex[index];

  const goPrev = () => setIndex((i) => Math.max(0, i - 1));
  const goNext = () => setIndex((i) => Math.min(total - 1, i + 1));

  const selectChoice = (choiceIdx) => {
    setSelectedByIndex((prev) => ({ ...prev, [index]: choiceIdx }));
  };

  const answeredCount = Object.keys(selectedByIndex).length;
  const allAnswered = total > 0 && answeredCount === total;

  async function fetchQuiz() {
    if (!textbook_id || !chapter_title || !difficulty) {
      setError("Missing textbook, chapter, or difficulty. Go back and select them first.");
      return;
    }

    const token = localStorage.getItem("access_token");
    if (!token) {
      setError("No access token found. Please log in again.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/api/generate/quiz`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          textbook_id,
          chapter_title,
          difficulty,
          num_questions: 5,
        }),
      });

      const raw = await res.text();
      let data = {};

      try {
        data = raw ? JSON.parse(raw) : {};
      } catch {
        data = { error: raw || `Non-JSON response (${res.status})` };
      }

      if (!res.ok) {
        setError(data?.error || `Request failed (${res.status})`);
        return;
      }

      const fetchedQuestions = data.questions || [];

      if (!Array.isArray(fetchedQuestions) || fetchedQuestions.length === 0) {
        setError("Backend returned no quiz questions.");
        setQuestions([]);
        return;
      }

      const normalized = fetchedQuestions.map((q, qIndex) => ({
        title: `Question ${qIndex + 1}`,
        prompt: q.question,
        choices: [
          q.choices?.A ?? "",
          q.choices?.B ?? "",
          q.choices?.C ?? "",
          q.choices?.D ?? "",
        ],
        correctIndex: ["A", "B", "C", "D"].indexOf(q.correct_answer),
      }));

      setQuestions(normalized);
      setIndex(0);
      setSelectedByIndex({});
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchQuiz();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [textbook_id, chapter_title, difficulty]);

  const handleSubmit = () => {
    const responses = questions.map((q, qIndex) => {
      const chosen = selectedByIndex[qIndex];
      return {
        questionIndex: qIndex,
        title: q.title,
        prompt: q.prompt,
        selectedIndex: chosen,
        selectedText: chosen != null ? q.choices[chosen] : null,
        correctIndex: q.correctIndex,
        correctText: q.choices[q.correctIndex],
        isCorrect: chosen === q.correctIndex,
      };
    });

    const score = responses.reduce((acc, r) => acc + (r.isCorrect ? 1 : 0), 0);

    // Log user responses
    console.log("QUIZ SUBMISSION:", { score, total, responses });

    navigate("/quiz/results", {
      state: {
        score,
        total,
        responses,
        textbook_id,
        chapter_title,
        difficulty,
      },
    });
  };

  return (
    <main className="quiz-page">
      <Container size="md">
        {/* Header */}
        <Group justify="space-between" align="center" className="quiz-header">
          <Title order={1}>Quizzes</Title>

          <Group gap="xs">
            <ActionIcon variant="subtle" aria-label="Info">
              <IconInfoCircle size={18} />
            </ActionIcon>
            <ActionIcon variant="subtle" aria-label="Help">
              <IconHelpCircle size={18} />
            </ActionIcon>
          </Group>
        </Group>

        {chapter_title ? (
          <Text c="dimmed" mb="sm">
            {chapter_title}
          </Text>
        ) : null}

        {/* Loading / error / empty states */}
        {error ? (
          <Paper withBorder radius="lg" p="xl" className="quiz-card">
            <Text c="red">{error}</Text>
          </Paper>
        ) : loading ? (
          <Paper withBorder radius="lg" p="xl" className="quiz-card">
            <Text>Generating quiz…</Text>
          </Paper>
        ) : total === 0 ? (
          <Paper withBorder radius="lg" p="xl" className="quiz-card">
            <Text>No quiz questions yet.</Text>
          </Paper>
        ) : (
          <>
            {/* Progress */}
            <Group align="center" gap="md" className="quiz-progress-row">
              <Text className="quiz-progress-label">Progress</Text>
              <Progress value={progressValue} className="quiz-progress" radius="xl" />
            </Group>

            {/* Question card */}
            <Paper withBorder radius="lg" p="xl" className="quiz-card">
              <Stack gap="sm">
                <Text fw={700} className="quiz-question-title">
                  {current.title}
                </Text>
                <Text className="quiz-question-text">{current.prompt}</Text>
              </Stack>
            </Paper>

            {/* Answer choices */}
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="lg" className="quiz-answers">
              {current.choices.map((choice, choiceIdx) => {
                const isSelected = selectedChoice === choiceIdx;

                return (
                  <button
                    key={choiceIdx}
                    type="button"
                    className={`quiz-choice ${isSelected ? "selected" : ""}`}
                    onClick={() => selectChoice(choiceIdx)}
                  >
                    <Text className="quiz-choice-text">{choice}</Text>
                  </button>
                );
              })}
            </SimpleGrid>

            {/* Nav buttons */}
            <Group justify="space-between" className="quiz-nav">
              <Button variant="default" onClick={goPrev} disabled={index === 0}>
                Prev
              </Button>

              <Text className="quiz-counter">
                {index + 1} / {total} (answered {answeredCount}/{total})
              </Text>

              <Button onClick={goNext} disabled={index === total - 1}>
                Next
              </Button>
            </Group>

            {/* Submit */}
            <Group justify="flex-end" className="quiz-submit-row">
              <Button onClick={handleSubmit} disabled={!allAnswered}>
                Submit Quiz
              </Button>
            </Group>

            {!allAnswered && (
              <Text className="quiz-hint" ta="right">
                Answer all questions to submit.
              </Text>
            )}

            <Group justify="flex-end" mt="md">
              <Button variant="light" onClick={fetchQuiz} disabled={loading}>
                Regenerate
              </Button>
            </Group>
          </>
        )}
        <Group justify="flex-end" className="flash-return">
            <Button variant="default" onClick={() => navigate("/dashboard")}>
              Return to Dashboard
            </Button>
          </Group>
      </Container>
    </main>
  );
}