import { useCallback, useEffect, useState, useRef } from "react";
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
  Badge,
  Loader,
} from "@mantine/core";
import { useNavigate, useLocation } from "react-router-dom";

import brain from "../../assets/generic_brain.png";
import { authFetch } from "../../utils/authFetch";
import "./Quiz.css";

const API_BASE = "http://127.0.0.1:5001";
const ANSWER_LABELS = ["A", "B", "C", "D"];
const QUIZ_MODES = [
  {
    value: "easy",
    label: "Easy",
    apiDifficulty: "1",
    description: "Focuses on core terms, definitions, and foundational understanding.",
  },
  {
    value: "medium",
    label: "Medium",
    apiDifficulty: "3",
    description: "Adds more application and checks whether you can use the main ideas.",
  },
  {
    value: "hard",
    label: "Hard",
    apiDifficulty: "4",
    description: "Emphasizes applying and analyzing the chapter's most important concepts.",
  },
];

function formatQuestionType(type) {
  const value = (type || "").trim();
  if (!value) return "";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function normalizeQuestions(rawQuestions = []) {
  return rawQuestions.map((question, questionIndex) => ({
    title: `Question ${questionIndex + 1}`,
    prompt: question.question,
    choices: [
      question.choices?.A ?? "",
      question.choices?.B ?? "",
      question.choices?.C ?? "",
      question.choices?.D ?? "",
    ],
    correctIndex: ANSWER_LABELS.indexOf(question.correct_answer),
    correctAnswer: question.correct_answer,
    citation: question.citation || null,
    explanation: question.explanation || null,
    type: question.type || null,
  }));
}

function buildResultState({
  assessmentType,
  textbook_id,
  chapter_id,
  chapter_title,
  difficulty,
  score,
  total,
  responses,
}) {
  return {
    assessmentType,
    score,
    total,
    responses,
    textbook_id,
    chapter_id,
    chapter_title,
    difficulty,
    canRetake: assessmentType !== "pretest",
  };
}

async function readJson(response) {
  const raw = await response.text();

  try {
    return raw ? JSON.parse(raw) : {};
  } catch {
    return { error: raw || `Non-JSON response (${response.status})` };
  }
}

export default function Quiz() {
  const navigate = useNavigate();
  const location = useLocation();
  const {
    textbook_id,
    chapter_id,
    chapter_title,
    difficulty,
    assessmentType: assessmentTypeFromState,
  } = location.state || {};

  const assessmentType =
    assessmentTypeFromState === "pretest" || location.pathname === "/pretest"
      ? "pretest"
      : "quiz";
  const isPretest = assessmentType === "pretest";

  const [questions, setQuestions] = useState([]);
  const [index, setIndex] = useState(0);
  const [selectedByIndex, setSelectedByIndex] = useState({});
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [savingDraft, setSavingDraft] = useState(false);
  const [error, setError] = useState("");
  const [quizId, setQuizId] = useState(null);
  const sessionStartedAtRef = useRef(null);
  const [quizMode, setQuizMode] = useState(() => {
    if (difficulty === "4") return "hard";
    if (difficulty === "3") return "medium";
    return "easy";
  });
  const [quizStarted, setQuizStarted] = useState(isPretest);

  const selectedQuizMode =
    QUIZ_MODES.find((mode) => mode.value === quizMode) || QUIZ_MODES[0];
  const quizDifficulty = selectedQuizMode.apiDifficulty;

  const total = questions.length;
  const current = questions[index];
  const progressValue = total > 0 ? ((index + 1) / total) * 100 : 0;
  const selectedChoice = selectedByIndex[index];
  const answeredCount = Object.keys(selectedByIndex).length;
  const allAnswered = total > 0 && answeredCount === total;

  const goPrev = () => setIndex((currentIndex) => Math.max(0, currentIndex - 1));
  const goNext = () => setIndex((currentIndex) => Math.min(total - 1, currentIndex + 1));

  const selectChoice = (choiceIndex) => {
    setSelectedByIndex((previous) => ({ ...previous, [index]: choiceIndex }));
  };

  const goBackToDashboard = () => {
    navigate("/dashboard", {
      state: {
        textbookId: textbook_id,
        chapterId: chapter_id,
      },
    });
  };

  const buildAnswerPayload = () => {
    return questions.map((_, questionIndex) => {
      const selectedIndex = selectedByIndex[questionIndex];
      return selectedIndex != null ? ANSWER_LABELS[selectedIndex] : null;
    });
  };

  const restoreDraftState = (attempt) => {
    if (!attempt || attempt.status !== "in_progress") {
      return;
    }

    const draftAnswers = Array.isArray(attempt.draft_answers) ? attempt.draft_answers : [];
    const restoredSelections = {};

    draftAnswers.forEach((answer, questionIndex) => {
      const normalizedAnswer = typeof answer === "string" ? answer.toUpperCase() : null;
      const selectedIndex = ANSWER_LABELS.indexOf(normalizedAnswer);
      if (selectedIndex !== -1) {
        restoredSelections[questionIndex] = selectedIndex;
      }
    });

    setSelectedByIndex(restoredSelections);
    setIndex(Math.max(0, Number(attempt.current_question_index) || 0));
  };

  const saveDraftAndReturn = async () => {
    if (!isPretest) {
      goBackToDashboard();
      return;
    }

    if (!textbook_id || !chapter_id || !questions.length) {
      goBackToDashboard();
      return;
    }

    setSavingDraft(true);
    setError("");

    try {
      const response = await authFetch(
        `${API_BASE}/api/textbooks/${textbook_id}/chapters/${chapter_id}/pretest/progress`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            answers: buildAnswerPayload(),
            current_question_index: index,
          }),
        }
      );

      const payload = await readJson(response);

      if (response.status === 409 && payload.attempt) {
        navigate("/quiz/results", {
          replace: true,
          state: buildResultState({
            assessmentType: "pretest",
            textbook_id,
            chapter_id,
            chapter_title: chapter_title || payload.chapter_title,
            difficulty: quizDifficulty,
            score: payload.attempt.score,
            total: payload.attempt.total_questions,
            responses: payload.attempt.responses || [],
          }),
        });
        return;
      }

      if (!response.ok) {
        setError(payload?.error || `Request failed (${response.status})`);
        return;
      }

      goBackToDashboard();
    } catch (saveError) {
      setError(String(saveError));
    } finally {
      setSavingDraft(false);
    }
  };

  const fetchQuiz = useCallback(async () => {
    if (!textbook_id || !chapter_title || !quizDifficulty) {
      setError("Missing textbook, chapter, or difficulty. Go back and select them first.");
      return;
    }

    setLoading(true);
    setError("");
    setQuizId(null);

    try {
      const response = await authFetch(`${API_BASE}/api/generate/quiz`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          textbook_id,
          chapter_title,
          chapter_id,
          difficulty: quizDifficulty,
          num_questions: 5,
        }),
      });

      const payload = await readJson(response);

      if (!response.ok) {
        setError(payload?.error || `Request failed (${response.status})`);
        return;
      }

      const normalized = normalizeQuestions(payload.questions || []);

      if (!normalized.length) {
        setError("Backend returned no quiz questions.");
        setQuestions([]);
        return;
      }

      setQuestions(normalized);
      setIndex(0);
      setSelectedByIndex({});
    } catch (fetchError) {
      setError(String(fetchError));
    } finally {
      setLoading(false);
    }
  }, [chapter_title, quizDifficulty, textbook_id]);

  const fetchPretest = useCallback(async () => {
    if (!textbook_id || !chapter_id) {
      setError("Missing textbook or chapter. Go back and choose a chapter first.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await authFetch(
        `${API_BASE}/api/textbooks/${textbook_id}/chapters/${chapter_id}/pretest`
      );

      const payload = await readJson(response);

      if (!response.ok) {
        setError(payload?.error || `Request failed (${response.status})`);
        return;
      }

      if (payload.completed && payload.attempt) {
        navigate("/quiz/results", {
          replace: true,
          state: buildResultState({
            assessmentType: "pretest",
            textbook_id,
            chapter_id,
            chapter_title: payload.chapter_title || chapter_title,
            difficulty: quizDifficulty,
            score: payload.attempt.score,
            total: payload.attempt.total_questions,
            responses: payload.attempt.responses || [],
          }),
        });
        return;
      }

      const normalized = normalizeQuestions(payload.questions || []);

      if (!normalized.length) {
        setError("This chapter pretest is not ready yet.");
        setQuestions([]);
        return;
      }

      setQuestions(normalized);
      setIndex(0);
      setSelectedByIndex({});
      setQuizId(payload.pretest_id || null);
      sessionStartedAtRef.current = Date.now();
      restoreDraftState(payload.attempt);
    } catch (fetchError) {
      setError(String(fetchError));
    } finally {
      setLoading(false);
    }
  }, [chapter_id, chapter_title, navigate, quizDifficulty, textbook_id]);

  useEffect(() => {
    if (!isPretest && !quizStarted) {
      return;
    }

    if (isPretest) {
      fetchPretest();
      return;
    }

    fetchQuiz();
  }, [fetchPretest, fetchQuiz, isPretest, quizStarted]);

  const handleSubmit = async () => {
    if (!allAnswered) return;

    if (isPretest) {
      setSubmitting(true);
      setError("");

      try {
        const answers = questions.map((_, questionIndex) => {
          const selectedIndex = selectedByIndex[questionIndex];
          return selectedIndex != null ? ANSWER_LABELS[selectedIndex] : null;
        });

        const response = await authFetch(
          `${API_BASE}/api/textbooks/${textbook_id}/chapters/${chapter_id}/pretest/submit`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ answers }),
          }
        );

        const payload = await readJson(response);

        if (response.status === 409 && payload.attempt) {
          navigate("/quiz/results", {
            replace: true,
            state: buildResultState({
              assessmentType: "pretest",
              textbook_id,
              chapter_id,
              chapter_title: chapter_title || payload.chapter_title,
              difficulty: quizDifficulty,
              score: payload.attempt.score,
              total: payload.attempt.total_questions,
              responses: payload.attempt.responses || [],
            }),
          });
          return;
        }

        if (!response.ok) {
          setError(payload?.error || `Request failed (${response.status})`);
          return;
        }

        navigate("/quiz/results", {
          state: buildResultState({
            assessmentType: "pretest",
            textbook_id,
            chapter_id,
            chapter_title: chapter_title || payload.chapter_title,
            difficulty: quizDifficulty,
            score: payload.attempt.score,
            total: payload.attempt.total_questions,
            responses: payload.attempt.responses || [],
          }),
        });
      } catch (submitError) {
        setError(String(submitError));
      } finally {
        setSubmitting(false);
      }

      return;
    }

    const responses = questions.map((question, questionIndex) => {
      const selectedIndex = selectedByIndex[questionIndex];
      return {
        questionIndex,
        title: question.title,
        prompt: question.prompt,
        selectedIndex,
        selectedAnswer: selectedIndex != null ? ANSWER_LABELS[selectedIndex] : null,
        selectedText: selectedIndex != null ? question.choices[selectedIndex] : null,
        correctIndex: question.correctIndex,
        correctAnswer: question.correctAnswer,
        correctText: question.choices[question.correctIndex],
        isCorrect: selectedIndex === question.correctIndex,
        citation: question.citation,
        explanation: question.explanation,
        type: question.type,
      };
    });

    const letters = ["A", "B", "C", "D"];
    const answers = {};
    responses.forEach((r, qIndex) => {
      if (r.selectedIndex != null && r.selectedIndex >= 0 && r.selectedIndex < letters.length) {
        answers[String(qIndex)] = letters[r.selectedIndex];
      } else {
        answers[String(qIndex)] = "";
      }
    });

    const started = sessionStartedAtRef.current;
    const timeStudied = Math.max(
      0,
      Math.floor((Date.now() - (started ?? Date.now())) / 1000)
    );

    const token = localStorage.getItem("access_token");
    if (quizId && token) {
      try {
        const res = await fetch(`${API_BASE}/api/quiz-attempts`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            quiz_id: quizId,
            answers,
            score,
            total_questions: total,
            time_studied: timeStudied,
          }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          console.error("Quiz attempt save failed:", err?.error || res.status);
        }
      } catch (e) {
        console.error("Quiz attempt save failed:", e);
      }
    }
    
    const score = responses.reduce(
      (currentScore, response) => currentScore + (response.isCorrect ? 1 : 0),
      0
    );

  navigate("/quiz/results", {
    state: buildResultState({
      assessmentType: "quiz",
      textbook_id,
      chapter_id,
      chapter_title,
      difficulty: quizDifficulty,
      score,
      total,
      responses,
    }),
  });
};

  return (
    <main className="quiz-page">
      <Container fluid className="quiz-shell">
        <Group justify="space-between" align="center" className="quiz-header">
          <div>
            <Group gap="sm" align="center">
              <Title order={1}>{isPretest ? "Chapter Pretest" : "Quizzes"}</Title>
              {isPretest ? (
                <Badge color="orange" variant="light">
                  One-time baseline
                </Badge>
              ) : null}
            </Group>

            {chapter_title ? (
              <Text c="dimmed" mt={6}>
                {chapter_title}
              </Text>
            ) : null}

            {isPretest ? (
              <Text c="dimmed" size="sm" mt={4}>
                Complete this once to unlock chapter quizzes.
              </Text>
            ) : null}
          </div>
        </Group>

        {!isPretest && !quizStarted ? (
          <Paper withBorder radius="lg" p="xl" className="quiz-card quiz-setup-card">
            <Stack gap="xl">
              <Group align="flex-start" gap="md" wrap="nowrap" className="quiz-setup-header">
                <div className="quiz-setup-iconWrap" aria-hidden="true">
                  <img src={brain} alt="" className="quiz-setup-iconImage" />
                </div>

                <div className="quiz-setup-copy">
                  <Group gap="xs" align="center">
                    <Text fw={700} size="xl">
                      Choose difficulty
                    </Text>
                  </Group>
                  <Text c="dimmed" size="sm" mt={8}>
                    Pick the level you want before generating this chapter quiz.
                  </Text>
                </div>
              </Group>

              <SimpleGrid cols={3} spacing="md">
                {QUIZ_MODES.map((mode) => {
                  const isSelected = quizMode === mode.value;

                  return (
                    <button
                      key={mode.value}
                      type="button"
                      className={`quiz-mode-card ${isSelected ? "selected" : ""}`}
                      onClick={() => setQuizMode(mode.value)}
                    >
                      <Stack gap={8} className="quiz-mode-cardContent">
                        <Text fw={700} size="lg">
                          {mode.label}
                        </Text>
                        <Text size="sm" className="quiz-mode-description">
                          {mode.description}
                        </Text>
                      </Stack>
                    </button>
                  );
                })}
              </SimpleGrid>

              <Group justify="flex-end">
                <Button onClick={() => setQuizStarted(true)}>Start Quiz</Button>
              </Group>
            </Stack>
          </Paper>
        ) : null}

        {!isPretest && quizStarted ? (
          <Group justify="flex-end" className="quiz-config-row">
            <Badge variant="light">{selectedQuizMode.label}</Badge>
          </Group>
        ) : null}

        {error ? (
          <Paper withBorder radius="lg" p="xl" className="quiz-card">
            <Text c="red">{error}</Text>
          </Paper>
        ) : loading ? (
          <div className="quiz-loadingCard">
            <div className="quiz-loadingInner">
              <Loader size={56} />
              <Text fw={700} className="quiz-loadingTitle">
                {isPretest ? "Loading pretest..." : "Loading quiz..."}
              </Text>
            </div>
          </div>
        ) : !isPretest && !quizStarted ? null : total === 0 ? (
          <Paper withBorder radius="lg" p="xl" className="quiz-card">
            <Text>{isPretest ? "No pretest found for this chapter yet." : "No quiz questions yet."}</Text>
          </Paper>
        ) : (
          <>
            <Group align="center" gap="md" className="quiz-progress-row">
              <Text className="quiz-progress-label">Progress</Text>
              <Progress value={progressValue} className="quiz-progress" radius="xl" />
            </Group>

            <Paper withBorder radius="lg" p="xl" className="quiz-card">
              <Stack gap="sm">
                <Group
                  justify="space-between"
                  align="flex-start"
                  gap="sm"
                  className="quiz-question-header"
                >
                  <Text fw={700} className="quiz-question-title">
                    {current.title}
                  </Text>
                  {current.type ? (
                    <Badge
                      variant="light"
                      color={isPretest ? "orange" : "blue"}
                      className="quiz-question-type"
                    >
                      {formatQuestionType(current.type)}
                    </Badge>
                  ) : null}
                </Group>
                <Text className="quiz-question-text">{current.prompt}</Text>
              </Stack>
            </Paper>

            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="lg" className="quiz-answers">
              {current.choices.map((choice, choiceIndex) => {
                const isSelected = selectedChoice === choiceIndex;

                return (
                  <button
                    key={choiceIndex}
                    type="button"
                    className={`quiz-choice ${isSelected ? "selected" : ""}`}
                    onClick={() => selectChoice(choiceIndex)}
                  >
                    <Text className="quiz-choice-text">{choice}</Text>
                  </button>
                );
              })}
            </SimpleGrid>

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

            <Group justify="flex-end" className="quiz-submit-row">
              <Button onClick={handleSubmit} disabled={!allAnswered || submitting}>
                {isPretest ? (submitting ? "Saving Baseline..." : "Submit Pretest") : "Submit Quiz"}
              </Button>
            </Group>

            {!allAnswered ? (
              <Text className="quiz-hint" ta="right">
                Answer all questions to submit.
              </Text>
            ) : null}
          </>
        )}

        <Group justify="flex-end" className="flash-return">
          <Button
            variant="default"
            onClick={isPretest ? saveDraftAndReturn : goBackToDashboard}
            disabled={savingDraft || submitting}
          >
            {isPretest ? (savingDraft ? "Saving..." : "Save and Return") : "Return to Dashboard"}
          </Button>
        </Group>
      </Container>
    </main>
  );
}
