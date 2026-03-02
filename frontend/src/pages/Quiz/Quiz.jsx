import { useMemo, useState } from "react";
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
import { useNavigate } from "react-router-dom";
import "./Quiz.css";

export default function Quiz() {
  const navigate = useNavigate();

  const questions = useMemo(
    () => [
      {
        title: "Question 1",
        prompt:
          "Dummy question text: answer question one.",
        choices: [
          "Dummy answer A: one.",
          "Dummy answer B: two.",
          "Dummy answer C: three.",
          "Dummy answer D: four.",
        ],
        correctIndex: 0,
      },
      {
        title: "Question 2",
        prompt:
          "Dummy question text: answer question two",
        choices: [
          "Dummy answer A: IP addresses.",
          "Dummy answer B: HTTP requests automatically.",
          "Dummy answer C: download.",
          "Dummy answer D: routers.",
        ],
        correctIndex: 0,
      },
      {
        title: "Question 3",
        prompt:
          "Dummy question text: answer question three",
        choices: [
          "Dummy answer A: HTTP request.",
          "Dummy answer B: browser cache.",
          "Dummy answer C: server.",
          "Dummy answer D: CDN.",
        ],
        correctIndex: 0,
      },
      {
        title: "Question 4",
        prompt:
          "Dummy question text: answer question four.",
        choices: [
          "Dummy answer A: Serving content.",
          "Dummy answer B: Increasing packet.",
          "Dummy answer C: Disabling images.",
          "Dummy answer D: Forcing every request.",
        ],
        correctIndex: 0,
      },
      {
        title: "Question 5",
        prompt:
          "Dummy question text: answer question five",
        choices: [
          "Dummy answer A: Forwards packets.",
          "Dummy answer B: Converts analog.",
          "Dummy answer C: Frames CRC.",
          "Dummy answer D: Renders HTML.",
        ],
        correctIndex: 0,
      },
    ],
    []
  );

  const [index, setIndex] = useState(0);
  const [selectedByIndex, setSelectedByIndex] = useState({}); // { [qIndex]: choiceIndex }

  const total = questions.length;
  const current = questions[index];
  const progressValue = ((index + 1) / total) * 100;

  const selectedChoice = selectedByIndex[index];

  const goPrev = () => setIndex((i) => Math.max(0, i - 1));
  const goNext = () => setIndex((i) => Math.min(total - 1, i + 1));

  const selectChoice = (choiceIdx) => {
    setSelectedByIndex((prev) => ({ ...prev, [index]: choiceIdx }));
  };

  const answeredCount = Object.keys(selectedByIndex).length;
  const allAnswered = answeredCount === total;

  const handleSubmit = () => {

    const responses = questions.map((q, qIndex) => {
      const chosen = selectedByIndex[qIndex];
      return {
        questionIndex: qIndex,
        title: q.title,
        prompt: q.prompt,
        selectedIndex: chosen,
        selectedText: q.choices[chosen],
        correctIndex: q.correctIndex,
        correctText: q.choices[q.correctIndex],
        isCorrect: chosen === q.correctIndex,
      };
    });

    const score = responses.reduce((acc, r) => acc + (r.isCorrect ? 1 : 0), 0);

    // Log user responses
    console.log("QUIZ SUBMISSION:", { score, total, responses });


    navigate("/quiz/results", {
      state: { score, total, responses },
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

        {}
        <Group align="center" gap="md" className="quiz-progress-row">
          <Text className="quiz-progress-label">Progress</Text>
          <Progress value={progressValue} className="quiz-progress" radius="xl" />
        </Group>

        {}
        <Paper withBorder radius="lg" p="xl" className="quiz-card">
          <Stack gap="sm">
            <Text fw={700} className="quiz-question-title">
              {current.title}
            </Text>
            <Text className="quiz-question-text">{current.prompt}</Text>
          </Stack>
        </Paper>

        {}
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

        {}
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
      </Container>
    </main>
  );
}