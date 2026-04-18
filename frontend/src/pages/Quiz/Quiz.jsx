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
  Modal,
} from "@mantine/core";
import { useNavigate, useLocation } from "react-router-dom";

import brain from "../../assets/generic_brain.png";
import { authFetch } from "../../utils/authFetch";
import "./Quiz.css";

const API_BASE = "http://127.0.0.1:5001";
const ANSWER_LABELS = ["A", "B", "C", "D"];
const CONFIDENCE_OPTIONS = ["low", "medium", "high"];
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
    apiDifficulty: "2",
    description: "Adds more application and checks whether you can use the main ideas.",
  },
  {
    value: "hard",
    label: "Hard",
    apiDifficulty: "3",
    description: "Emphasizes applying and analyzing the chapter's most important concepts.",
  },
];

function formatQuestionType(type) {
  const value = (type || "").trim();
  if (!value) return "";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function normalizeQuizMode(difficulty) {
  const value = String(difficulty || "").trim().toLowerCase();
  if (value === "3" || value === "hard") return "hard";
  if (value === "2" || value === "medium") return "medium";
  return "easy";
}

function getQuizDifficultyBadgeColor(mode) {
  if (mode === "hard") return "red";
  if (mode === "medium") return "orange";
  return "green";
}

function renumberQuestions(questionList = []) {
  return questionList.map((question, questionIndex) => ({
    ...question,
    title: `Question ${questionIndex + 1}`,
  }));
}

function removeIndexFromMap(indexedValues, removedIndex) {
  const nextValues = {};

  Object.entries(indexedValues || {}).forEach(([key, value]) => {
    const numericKey = Number(key);
    if (Number.isNaN(numericKey) || numericKey === removedIndex) {
      return;
    }

    nextValues[numericKey > removedIndex ? numericKey - 1 : numericKey] = value;
  });

  return nextValues;
}

function normalizeQuestions(rawQuestions = []) {
  return renumberQuestions(rawQuestions.map((question) => ({
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
  })));
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
  const [confidenceByIndex, setConfidenceByIndex] = useState({});
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [savingDraft, setSavingDraft] = useState(false);
  const [error, setError] = useState("");
  const [quizId, setQuizId] = useState(null);
  const [reportedQuestions, setReportedQuestions] = useState([]);
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const sessionStartedAtRef = useRef(null);
  const [quizMode, setQuizMode] = useState(() => normalizeQuizMode(difficulty));
  const [quizStarted, setQuizStarted] = useState(isPretest);

  const selectedQuizMode =
    QUIZ_MODES.find((mode) => mode.value === quizMode) || QUIZ_MODES[0];
  const quizDifficulty = selectedQuizMode.apiDifficulty;

  const total = questions.length;
  const current = questions[index];
  const progressValue = total > 0 ? ((index + 1) / total) * 100 : 0;
  const selectedChoice = selectedByIndex[index];
  const selectedConfidence = confidenceByIndex[index] || null;
  const answeredCount = Object.keys(selectedByIndex).length;
  const confidenceCount = Object.keys(confidenceByIndex).length;
  const allAnswered = total > 0 && answeredCount === total;
  const allConfidencesSelected = total > 0 && confidenceCount === total;

  const goPrev = () => setIndex((currentIndex) => Math.max(0, currentIndex - 1));
  const goNext = () => setIndex((currentIndex) => Math.min(total - 1, currentIndex + 1));

  const selectChoice = (choiceIndex) => {
    setSelectedByIndex((previous) => ({ ...previous, [index]: choiceIndex }));
  };

  const selectConfidence = (confidence) => {
    setConfidenceByIndex((previous) => ({ ...previous, [index]: confidence }));
  };

  const openReportModal = () => {
    if (isPretest || !current || questions.length <= 1) return;
    setReportModalOpen(true);
  };

  const closeReportModal = () => {
    setReportModalOpen(false);
  };

  const reportCurrentQuestion = () => {
    if (isPretest || !current) return;

    if (questions.length <= 1) {
      return;
    }

    setReportedQuestions((previous) => [
      ...previous,
      {
        ...current,
        status: "reported",
      },
    ]);
    setQuestions((previous) => renumberQuestions(previous.filter((_, questionIndex) => questionIndex !== index)));
    setSelectedByIndex((previous) => removeIndexFromMap(previous, index));
    setConfidenceByIndex((previous) => removeIndexFromMap(previous, index));
    setIndex((previousIndex) => Math.max(0, Math.min(previousIndex, questions.length - 2)));
    setReportModalOpen(false);
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

  const buildConfidencePayload = () => {
    return questions.map((_, questionIndex) => confidenceByIndex[questionIndex] || null);
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
          num_questions: 10,
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
      setConfidenceByIndex({});
      setReportedQuestions([]);
      setQuizId(payload.quiz_id || null);
      sessionStartedAtRef.current = Date.now();
    } catch (fetchError) {
      setError(String(fetchError));
    } finally {
      setLoading(false);
    }
  }, [chapter_id, chapter_title, quizDifficulty, textbook_id]);

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
      setConfidenceByIndex({});
      setReportedQuestions([]);
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
    if (!allAnswered || !allConfidencesSelected) return;

    if (isPretest) {
      setSubmitting(true);
      setError("");

      try {
        const answers = questions.map((_, questionIndex) => {
          const selectedIndex = selectedByIndex[questionIndex];
          return selectedIndex != null ? ANSWER_LABELS[selectedIndex] : null;
        });
        const confidences = buildConfidencePayload();

        const response = await authFetch(
          `${API_BASE}/api/textbooks/${textbook_id}/chapters/${chapter_id}/pretest/submit`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ answers, confidences }),
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
        confidence: confidenceByIndex[questionIndex] || null,
      };
    });

    const reportedResponses = reportedQuestions.map((question, reportedIndex) => ({
      questionIndex: `reported-${reportedIndex}`,
      title: "Reported question",
      prompt: question.prompt,
      selectedIndex: null,
      selectedAnswer: null,
      selectedText: null,
      correctIndex: question.correctIndex,
      correctAnswer: question.correctAnswer,
      correctText: question.choices[question.correctIndex],
      isCorrect: false,
      citation: question.citation,
      explanation: question.explanation,
      type: question.type,
      confidence: null,
      isReported: true,
    }));

    const score = responses.reduce(
      (currentScore, response) => currentScore + (response.isCorrect ? 1 : 0),
      0
    );

    const answers = {};
    responses.forEach((r, qIndex) => {
      answers[String(qIndex)] = {
        answer: r.selectedAnswer || "",
        confidence: r.confidence,
      };
    });
    answers.__reported_count = reportedQuestions.length;

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

  navigate("/quiz/results", {
    state: buildResultState({
      assessmentType: "quiz",
      textbook_id,
      chapter_id,
      chapter_title,
      difficulty: quizDifficulty,
      score,
      total,
      responses: [...responses, ...reportedResponses],
    }),
  });
};

  return (
    <main className="quiz-page">
      <Container fluid className="quiz-shell">
        <Modal
          opened={reportModalOpen}
          onClose={closeReportModal}
          title="Report question?"
          centered
          radius="lg"
        >
          <Stack gap="lg">
            <Text size="sm">
              Report this question and skip it? Will not impact your quiz score.
            </Text>
            <Group justify="flex-end">
              <Button variant="default" onClick={closeReportModal}>
                Cancel
              </Button>
              <Button color="red" onClick={reportCurrentQuestion}>
                Report & skip
              </Button>
            </Group>
          </Stack>
        </Modal>

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
            <Badge
              variant="light"
              color={getQuizDifficultyBadgeColor(selectedQuizMode.value)}
            >
              {selectedQuizMode.label}
            </Badge>
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
                  <Stack gap={6} align="flex-end" className="quiz-question-meta">
                    {current.type ? (
                      <Badge
                        variant="light"
                        color={isPretest ? "orange" : "blue"}
                        className="quiz-question-type"
                      >
                        {formatQuestionType(current.type)}
                      </Badge>
                    ) : null}
                  </Stack>
                </Group>
                <Text className="quiz-question-text">{current.prompt}</Text>
                {!isPretest ? (
                  <Group justify="flex-end" className="quiz-question-actions">
                    <button
                      type="button"
                      className="quiz-report-link"
                      onClick={openReportModal}
                      disabled={questions.length <= 1}
                    >
                      Looks off?
                    </button>
                  </Group>
                ) : null}
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

            <div className="quiz-confidence-section">
              <Text className="quiz-confidence-label">Rate confidence</Text>
              <Group gap="sm" wrap="nowrap" className="quiz-confidence-options">
                {CONFIDENCE_OPTIONS.map((confidence) => {
                  const isSelected = selectedConfidence === confidence;

                  return (
                    <button
                      key={confidence}
                      type="button"
                      className={`quiz-confidence-btn ${isSelected ? "selected" : ""}`}
                      onClick={() => selectConfidence(confidence)}
                    >
                      {formatQuestionType(confidence)}
                    </button>
                  );
                })}
              </Group>
            </div>

            <Group justify="space-between" className="quiz-nav">
              <Button variant="default" onClick={goPrev} disabled={index === 0}>
                Prev
              </Button>

              <Text className="quiz-counter">
                {index + 1} / {total} (answered {answeredCount}/{total}, confidence {confidenceCount}/{total})
              </Text>

              <Button onClick={goNext} disabled={index === total - 1}>
                Next
              </Button>
            </Group>

            <Group justify="flex-end" className="quiz-submit-row">
              <Button
                onClick={handleSubmit}
                disabled={!allAnswered || !allConfidencesSelected || submitting}
              >
                {isPretest ? (submitting ? "Saving Baseline..." : "Submit Pretest") : "Submit Quiz"}
              </Button>
            </Group>

            {!allAnswered || !allConfidencesSelected ? (
              <Text className="quiz-hint" ta="right">
                {!allAnswered && !allConfidencesSelected
                  ? "Answer every question and rate confidence on each one to submit."
                  : !allAnswered
                    ? "Answer all questions to submit."
                    : "Rate confidence for every question to submit."}
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
