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
  Loader,
} from "@mantine/core";
import { useState, useEffect, useMemo } from "react";
import { IconChecklist, IconLock, IconQuestionMark } from "@tabler/icons-react";
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
  const [dashboard, setDashboard] = useState(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);

  const selectedBookLabel = useMemo(() => {
    const o = textbooks.find((t) => t.value === selectedTextbook);
    return o?.label || "";
  }, [textbooks, selectedTextbook]);
  
  const [pretestStatus, setPretestStatus] = useState(createEmptyPretestStatus);
  const [customCovers, setCustomCovers] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(CUSTOM_COVERS_STORAGE_KEY) || "{}");
    } catch {
      return {};
    }
  });

  const selectedChapterOption = chapters.find((chapter) => chapter.value === selectedChapter);
  const quizLocked = !pretestStatus.completed;
  const canOpenPretest = pretestStatus.pretestReady || pretestStatus.completed;
  const selectedCover = selectedTextbook ? customCovers[selectedTextbook] : null;

  useEffect(() => {
    let active = true;

    async function loadTextbooks() {
      const response = await authFetch(`${API_BASE}/api/textbooks`);

      if (response.status === 401) {
        navigate("/login");
        return;
      }

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        console.error(payload.error || "Failed to load textbooks");
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
    }

    loadTextbooks().catch((error) => {
      console.error("Failed to load textbooks:", error);
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
        return;
      }

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
    }

    loadChapters().catch((error) => {
      console.error("Failed to load chapters:", error);
      if (!active) return;
      setChapters([]);
      setSelectedChapter(null);
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

  useEffect(() => {
    if (!selectedTextbook) {
      setDashboard(null);
      return;
    }

    const token = localStorage.getItem("access_token");
    if (!token) return;

    let cancelled = false;

    async function loadDashboard() {
      setDashboardLoading(true);
      try {
        const res = await fetch(
          `${API_BASE}/api/textbooks/${selectedTextbook}/dashboard`,
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        );
        const data = await res.json();
        if (!res.ok) {
          console.error(data.error || "Failed to load dashboard");
          if (!cancelled) setDashboard(null);
          return;
        }
        if (!cancelled) setDashboard(data);
      } catch (e) {
        console.error("Failed to load dashboard:", e);
        if (!cancelled) setDashboard(null);
      } finally {
        if (!cancelled) setDashboardLoading(false);
      }
    }

    loadDashboard();
    return () => {
      cancelled = true;
    };
  }, [selectedTextbook]);

  const avgChapterMastery = dashboard?.mastery?.avg_chapter_mastery_percent ?? 0;
  const streakDays = dashboard?.study?.streak_current_days ?? 0;
  const sessionCount7 = dashboard?.activity?.session_count_last_7 ?? 0;
  const chapterCount = dashboard?.mastery?.chapter_count ?? chapters.length;

  function openStats() {
    if (!selectedTextbook) return;
    navigate("/stats", {
      state: {
        textbook_id: selectedTextbook,
        textbook_label: selectedBookLabel,
      },
    });
  }

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
                </Box>

                <Stack gap={10} className="dashboard-middle">
                  <Box className="dashboard-title-block">
                    <Select
                      label="Textbook"
                      placeholder="Select a textbook"
                      data={textbooks}
                      value={selectedTextbook}
                      onChange={setSelectedTextbook}
                    />
                  </Box>

                  <Box className="dashboard-title-block">
                    <Select
                      label="Chapter"
                      placeholder={selectedTextbook ? "Select a chapter" : "Select a textbook first"}
                      data={chapters}
                      value={selectedChapter}
                      onChange={setSelectedChapter}
                      disabled={!selectedTextbook}
                    />
                  </Box>
                </Stack>

                <Stack gap="sm" className="dashboard-controls">
                  <Text fw={600}>Select the following to begin</Text>

                  <Stack gap={6} className="dashboard-pretest-row">
                    <div className="dashboard-pretest-actions">
                      <div className="dashboard-pretest-buttonWrap">
                        <Button
                          radius="xl"
                          leftSection={<IconChecklist size={16} />}
                          onClick={handlePretestClick}
                          disabled={
                            !selectedTextbook || !selectedChapter || pretestStatus.loading || !canOpenPretest
                          }
                        >
                          {pretestStatus.completed ? "View Baseline" : "Take Pretest"}
                        </Button>
                      </div>

                      <div className="dashboard-pretest-side">
                        <Tooltip
                          multiline
                          w={220}
                          withArrow
                          label={`One-time pretest to gauge baseline knowledge.\n${pretestStatus.questionCount || 12} questions. One attempt only.`}
                        >
                          <ActionIcon variant="subtle" radius="xl" aria-label="Pretest info">
                            <IconQuestionMark size={16} />
                          </ActionIcon>
                        </Tooltip>

                        {pretestStatus.loading ? <Loader size="sm" /> : null}
                      </div>
                    </div>

                    {pretestStatus.error ? (
                      <Text size="sm" c="red" ta="center">
                        {pretestStatus.error}
                      </Text>
                    ) : null}
                  </Stack>

                  <Group gap="sm" className="dashboard-actions">
                    <Button
                      radius="xl"
                      fullWidth
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

                    <Button
                      radius="xl"
                      fullWidth
                      leftSection={quizLocked ? <IconLock size={16} /> : null}
                      onClick={handleQuizClick}
                      disabled={
                        !selectedTextbook || !selectedChapter || pretestStatus.loading || quizLocked
                      }
                    >
                      Quizzes
                    </Button>
                  </Group>

                  {quizLocked ? (
                    <Text size="sm" c="dimmed" className="dashboard-lock-note">
                      Complete the chapter pretest to unlock quizzes.
                    </Text>
                  ) : null}
                </Stack>
              </Group>

              <Divider my="xl" />
            </Paper>

            <Paper
              withBorder
              p="xl"
              radius="md"
              className={`dashboard-card dashboard-learning-summary ${
                selectedTextbook ? "dashboard-clickable" : ""
              }`}
              onClick={selectedTextbook ? openStats : undefined}
              role={selectedTextbook ? "button" : undefined}
              tabIndex={selectedTextbook ? 0 : undefined}
              onKeyDown={
                selectedTextbook
                  ? (e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        openStats();
                      }
                    }
                  : undefined
              }
              aria-label={
                selectedTextbook
                  ? "Open full learning stats for this textbook"
                  : undefined
              }
            >
              <Group
                align="flex-start"
                justify="space-between"
                wrap="wrap"
                gap="lg"
              >
                <Stack gap="md" maw={560}>
                  <Box>
                    <Title order={2}>Learning dashboard</Title>
                  </Box>

                  {dashboardLoading ? (
                    <Loader size="sm" />
                  ) : (
                    <>
                      <Box>
                        <Group justify="space-between" mb={6}>
                          <Text fw={600} size="sm">
                            Progress
                          </Text>
                          <Badge variant="light" size="lg">
                            {avgChapterMastery}%
                          </Badge>
                        </Group>
                        <Progress
                          value={avgChapterMastery}
                          radius="xl"
                          size="md"
                          aria-label="Average chapter quiz mastery"
                        />
                        <Text c="dimmed" size="xs" mt={6}>
                          {chapterCount} chapter{chapterCount === 1 ? "" : "s"} ·{" "}
                          {sessionCount7} session
                          {sessionCount7 === 1 ? "" : "s"} (last 7 days)
                        </Text>
                      </Box>

                      <Group gap="xl">
                        <div>
                          <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                            Study streak
                          </Text>
                          <Text fw={800} size="xl">
                            {streakDays} day{streakDays === 1 ? "" : "s"}
                          </Text>
                        </div>
                      </Group>
                    </>
                  )}
                </Stack>

                <Box className="dashboard-learning-hint">
                  <Text fw={600} size="sm" c="dimmed">
                    View stats →
                  </Text>
                </Box>
              </Group>
            </Paper>
          </Stack>
        </Container>
      </main>
    </>
  );
}
