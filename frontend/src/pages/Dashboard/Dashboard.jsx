import {
  Container,
  Paper,
  Group,
  Stack,
  Box,
  Title,
  Text,
  Image,
  Divider,
  Select,
  Button,
  Progress,
  Loader,
  ActionIcon,
  Tooltip,
  Badge,
} from "@mantine/core";
import { IconLock, IconMessageCircle, IconQuestionMark } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import NavBar from "../../components/NavBar";
import { authFetch } from "../../utils/authFetch";
import "./Dashboard.css";

const API_BASE = "http://127.0.0.1:5001";
const CUSTOM_COVERS_STORAGE_KEY = "customTextbookCovers";

function createEmptyPretestStatus() {
  return {
    loading: false,
    pretestReady: false,
    completed: false,
    questionCount: 0,
    attempt: null,
    error: "",
  };
}

export default function Dashboard() {
  const navigate = useNavigate();
  const location = useLocation();

  const preferredTextbookId =
    location.state?.textbookId ?? new URLSearchParams(location.search).get("textbook");
  const preferredChapterId = location.state?.chapterId ?? null;

  const [selectedTextbook, setSelectedTextbook] = useState(null);
  const [selectedChapter, setSelectedChapter] = useState(null);

  const [textbooks, setTextbooks] = useState([]);
  const [chapters, setChapters] = useState([]);
  const [loadingTextbooks, setLoadingTextbooks] = useState(true);
  const [loadingChapters, setLoadingChapters] = useState(false);
  const [pretestStatus, setPretestStatus] = useState(createEmptyPretestStatus);
  const [customCovers, setCustomCovers] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(CUSTOM_COVERS_STORAGE_KEY) || "{}");
    } catch {
      return {};
    }
  });

  const selectedChapterOption = chapters.find((chapter) => chapter.value === selectedChapter);
  const selectedTextbookOption = textbooks.find((book) => book.value === selectedTextbook);
  const quizLocked = !pretestStatus.completed;
  const canOpenPretest = pretestStatus.pretestReady || pretestStatus.completed;
  const selectedCover = selectedTextbook ? customCovers[selectedTextbook] : null;

  useEffect(() => {
    let active = true;

    async function loadTextbooks() {
      setLoadingTextbooks(true);
      const response = await authFetch(`${API_BASE}/api/textbooks`);

      if (response.status === 401) {
        navigate("/login");
        return;
      }

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        console.error(payload.error || "Failed to load textbooks");
        if (!active) return;
        setLoadingTextbooks(false);
        return;
      }

      const options = (payload.textbooks || []).map((book) => ({
        value: book.id,
        label: book.display_title || book.title || "Untitled textbook",
      }));

      if (!active) return;

      setTextbooks(options);

      const preferredOption = options.find((option) => option.value === preferredTextbookId);
      setSelectedTextbook(preferredOption?.value || null);
      setLoadingTextbooks(false);
    }

    loadTextbooks().catch((error) => {
      console.error("Failed to load textbooks:", error);
      if (!active) return;
      setLoadingTextbooks(false);
    });

    return () => {
      active = false;
    };
  }, [navigate, preferredTextbookId]);

  useEffect(() => {
    let active = true;

    async function loadChapters() {
      if (!selectedTextbook) {
        setChapters([]);
        setSelectedChapter(null);
        setLoadingChapters(false);
        return;
      }

      setLoadingChapters(true);
      const response = await authFetch(`${API_BASE}/api/textbooks/${selectedTextbook}/chapters`);

      if (response.status === 401) {
        navigate("/login");
        return;
      }

      const payload = await response.json().catch(() => ({}));

      if (!response.ok) {
        console.error(payload.error || "Failed to load chapters");
        if (!active) return;
        setChapters([]);
        setSelectedChapter(null);
        setLoadingChapters(false);
        return;
      }

      const options = (payload.chapters || []).map((chapter) => ({
        value: chapter.id,
        label: chapter.title,
      }));

      if (!active) return;

      setChapters(options);

      const matchingPreferredChapter =
        selectedTextbook === preferredTextbookId
          ? options.find((option) => option.value === preferredChapterId)
          : null;

      setSelectedChapter(matchingPreferredChapter?.value || null);
      setLoadingChapters(false);
    }

    loadChapters().catch((error) => {
      console.error("Failed to load chapters:", error);
      if (!active) return;
      setChapters([]);
      setSelectedChapter(null);
      setLoadingChapters(false);
    });

    return () => {
      active = false;
    };
  }, [navigate, preferredChapterId, preferredTextbookId, selectedTextbook]);

  useEffect(() => {
    let active = true;

    async function loadPretestStatus() {
      if (!selectedTextbook || !selectedChapter) {
        setPretestStatus(createEmptyPretestStatus());
        return;
      }

      setPretestStatus((previous) => ({
        ...previous,
        loading: true,
        error: "",
      }));

      const response = await authFetch(
        `${API_BASE}/api/textbooks/${selectedTextbook}/chapters/${selectedChapter}/pretest/status`
      );

      if (response.status === 401) {
        navigate("/login");
        return;
      }

      const payload = await response.json().catch(() => ({}));

      if (!active) return;

      if (!response.ok) {
        setPretestStatus({
          ...createEmptyPretestStatus(),
          error: payload.error || "Could not load pretest status.",
        });
        return;
      }

      setPretestStatus({
        loading: false,
        pretestReady: Boolean(payload.pretest_ready),
        completed: Boolean(payload.completed),
        questionCount: payload.question_count || 0,
        attempt: payload.attempt || null,
        error: payload.pretest_ready ? "" : "Pretest is not available for this chapter yet.",
      });
    }

    loadPretestStatus().catch((error) => {
      console.error("Failed to load pretest status:", error);
      if (!active) return;
      setPretestStatus({
        ...createEmptyPretestStatus(),
        error: "Could not load pretest status.",
      });
    });

    return () => {
      active = false;
    };
  }, [navigate, selectedChapter, selectedTextbook]);

  useEffect(() => {
    const handleStorage = () => {
      try {
        setCustomCovers(JSON.parse(localStorage.getItem(CUSTOM_COVERS_STORAGE_KEY) || "{}"));
      } catch {
        setCustomCovers({});
      }
    };

    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  const navigateWithChapter = (path, extraState = {}) => {
    if (!selectedTextbook || !selectedChapter) {
      return;
    }

    navigate(path, {
      state: {
        textbook_id: selectedTextbook,
        chapter_id: selectedChapter,
        chapter_title: selectedChapterOption?.label,
        ...extraState,
      },
    });
  };

  const navigateWithTextbook = (path, extraState = {}) => {
    if (!selectedTextbook) {
      return;
    }

    navigate(path, {
      state: {
        textbook_id: selectedTextbook,
        textbook_title: selectedTextbookOption?.label,
        ...extraState,
      },
    });
  };

  const handlePretestClick = () => {
    if (!canOpenPretest) {
      return;
    }

    navigateWithChapter("/pretest", {
      assessmentType: "pretest",
    });
  };

  const handleQuizClick = () => {
    if (!selectedTextbook || !selectedChapter || quizLocked) {
      return;
    }

    navigateWithChapter("/quiz", {
      assessmentType: "quiz",
    });
  };

  const handleAskFlowstateClick = () => {
    if (!selectedTextbook) {
      return;
    }

    navigateWithTextbook("/ask-flowstate", {
      entryPoint: "dashboard",
    });
  };

  return (
    <>
      <NavBar isAuthed={true} />

      <main className="dashboard-page">
        <Container size="lg">
          <Stack gap="xl">
            <Paper withBorder p="xl" radius="md" className="dashboard-card">
              <Group
                align="flex-start"
                gap="xl"
                wrap="nowrap"
                className="dashboard-top-row"
              >
                <Box className="dashboard-cover">
                  <Image
                    src={selectedCover || null}
                    alt="Textbook cover"
                    className="dashboard-cover-image"
                    fallbackSrc="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Crect width='300' height='300' fill='%23e9ecef'/%3E%3Cpath d='M80 210l55-60 40 45 30-25 55 65H80z' fill='%23adb5bd'/%3E%3Ccircle cx='115' cy='120' r='18' fill='%23adb5bd'/%3E%3C/svg%3E"
                    fit="cover"
                  />
                  {loadingTextbooks ? (
                    <div className="dashboard-cover-loader" aria-live="polite">
                      <Loader size="sm" />
                    </div>
                  ) : null}
                </Box>

                <Stack gap={10} className="dashboard-middle">
                  <Box className="dashboard-title-block">
                    <Select
                      label="Textbook"
                      placeholder="Select a textbook"
                      data={textbooks}
                      value={selectedTextbook}
                      onChange={setSelectedTextbook}
                      disabled={loadingTextbooks}
                      rightSection={loadingTextbooks ? <Loader size={14} /> : undefined}
                    />
                  </Box>

                  <Box className="dashboard-title-block">
                    <Select
                      label="Chapter"
                      placeholder={selectedTextbook ? "Select a chapter" : "Select a textbook first"}
                      data={chapters}
                      value={selectedChapter}
                      onChange={setSelectedChapter}
                      disabled={!selectedTextbook || loadingChapters}
                      rightSection={loadingChapters ? <Loader size={14} /> : undefined}
                    />
                  </Box>
                </Stack>

                <Stack gap="sm" className="dashboard-controls">
                  <Text fw={600} ta="center" className="dashboard-controls-title">
                    Select one of the following
                  </Text>

                  <Stack gap="sm" className="dashboard-primary-actions">
                    <Button
                      radius="xl"
                      fullWidth
                      leftSection={<IconMessageCircle size={16} />}
                      onClick={handleAskFlowstateClick}
                      disabled={!selectedTextbook}
                    >
                      Ask Flo
                    </Button>

                    <div className="dashboard-pretest-wrap">
                      <Button
                        radius="xl"
                        fullWidth
                        className="dashboard-pretest-button"
                        onClick={handlePretestClick}
                        disabled={
                          !selectedTextbook || !selectedChapter || pretestStatus.loading || !canOpenPretest
                        }
                      >
                        {pretestStatus.completed ? "View Baseline" : "Take Pretest"}
                      </Button>

                      <div className="dashboard-pretest-side">
                        {!pretestStatus.completed ? (
                          <Tooltip
                            multiline
                            w={220}
                            withArrow
                            label={`One-time pretest to gauge baseline knowledge.\n${pretestStatus.questionCount || 12} questions. One attempt only.`}
                          >
                            <ActionIcon
                              variant="transparent"
                              radius="xl"
                              aria-label="Pretest info"
                              className="dashboard-pretest-help"
                            >
                              <IconQuestionMark size={14} />
                            </ActionIcon>
                          </Tooltip>
                        ) : null}

                        {pretestStatus.loading ? <Loader size="sm" /> : null}
                      </div>
                    </div>

                    <Tooltip
                      multiline
                      w={220}
                      withArrow
                      disabled={!quizLocked}
                      label="Complete the chapter pretest to unlock quizzes."
                    >
                      <div className="dashboard-quiz-wrap">
                        <Button
                          radius="xl"
                          fullWidth
                          leftSection={quizLocked ? <IconLock size={16} /> : null}
                          onClick={handleQuizClick}
                          disabled={
                            !selectedTextbook ||
                            !selectedChapter ||
                            pretestStatus.loading ||
                            quizLocked
                          }
                        >
                          Quizzes
                        </Button>
                      </div>
                    </Tooltip>
                  </Stack>

                  {pretestStatus.error ? (
                    <Text size="sm" c="red" ta="center">
                      {pretestStatus.error}
                    </Text>
                  ) : null}

                  <Group gap="sm" className="dashboard-actions dashboard-actions-secondary">
                    <Button
                      variant="light"
                      fullWidth
                      radius="xl"
                      onClick={() => navigateWithChapter("/summarize")}
                      disabled={!selectedTextbook || !selectedChapter}
                    >
                      Summarize
                    </Button>

                    <Button
                      variant="light"
                      radius="xl"
                      fullWidth
                      onClick={() => navigateWithChapter("/flash")}
                      disabled={!selectedTextbook || !selectedChapter}
                    >
                      Flashcards
                    </Button>
                  </Group>

                </Stack>
              </Group>

              <Divider my="xl" />
            </Paper>

            <Paper
              withBorder
              p="xl"
              radius="md"
              className="dashboard-card dashboard-clickable"
              onClick={() => navigate("/stats")}
              role="button"
              tabIndex={0}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") navigate("/stats");
              }}
            >
              <Group
                align="stretch"
                gap="xl"
                wrap="nowrap"
                className="dashboard-bottom-row"
              >
                <Stack gap="md" className="dashboard-bottom-left">
                  <Box>
                    <Title order={2}>Learning Dashboard</Title>
                    <Group gap="sm" mt={6}>
                      <Text c="dimmed" size="sm">
                        Completion Rate:
                      </Text>
                      <Badge variant="light">xx%</Badge>
                    </Group>
                  </Box>

                  <Box>
                    <Text fw={700} size="lg" mb={6}>
                      Masteries
                    </Text>
                    <Progress value={60} radius="xl" />
                    <Progress value={40} radius="xl" mt="sm" />
                  </Box>

                  <Box>
                    <Text fw={700} size="lg" mb={6}>
                      Continue
                    </Text>
                    <Progress value={30} radius="xl" />
                    <Progress value={20} radius="xl" mt="sm" />
                  </Box>

                  <Text c="dimmed" size="sm">
                    Click to view stats →
                  </Text>
                </Stack>

                <Box className="dashboard-chart">
                  <Box className="dashboard-chart-inner">
                    <svg width="90%" height="70%" viewBox="0 0 500 250">
                      <polyline
                        fill="none"
                        stroke="white"
                        strokeWidth="4"
                        points="20,220 110,140 180,170 250,90 320,200 390,120 450,150 490,40"
                      />
                    </svg>
                  </Box>
                </Box>
              </Group>
            </Paper>
          </Stack>
        </Container>
      </main>
    </>
  );
}
