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
  SimpleGrid,
  Progress,
  Badge,
  Loader,
} from "@mantine/core";
import { useNavigate } from "react-router-dom";
import { useState, useEffect, useMemo } from "react";

import NavBar from "../../components/NavBar";
import "./Dashboard.css";

const API_BASE = "http://127.0.0.1:5001";

export default function Dashboard() {
  const navigate = useNavigate();

  const [selectedTextbook, setSelectedTextbook] = useState(null);
  const [selectedChapter, setSelectedChapter] = useState(null);
  const [selectedDifficulty, setSelectedDifficulty] = useState("1");

  const [textbooks, setTextbooks] = useState([]);
  const [chapters, setChapters] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);

  const selectedBookLabel = useMemo(() => {
    const o = textbooks.find((t) => t.value === selectedTextbook);
    return o?.label || "";
  }, [textbooks, selectedTextbook]);

  useEffect(() => {
    async function loadTextbooks() {
      const token = localStorage.getItem("access_token");
      if (!token) return;

      try {
        const res = await fetch(`${API_BASE}/api/textbooks`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        const data = await res.json();

        if (!res.ok) {
          console.error(data.error || "Failed to load textbooks");
          return;
        }

        const options = (data.textbooks || []).map((book) => ({
          value: book.id,
          label: book.display_title || book.title || "Untitled textbook",
        }));

        setTextbooks(options);

        if (options.length > 0) {
          setSelectedTextbook(options[0].value);
        }
      } catch (e) {
        console.error("Failed to load textbooks:", e);
      }
    }

    loadTextbooks();
  }, []);

  useEffect(() => {
    async function loadChapters() {
      if (!selectedTextbook) {
        setChapters([]);
        setSelectedChapter(null);
        return;
      }

      const token = localStorage.getItem("access_token");
      if (!token) return;

      try {
        const res = await fetch(
          `${API_BASE}/api/textbooks/${selectedTextbook}/chapters`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        const data = await res.json();

        if (!res.ok) {
          console.error(data.error || "Failed to load chapters");
          setChapters([]);
          setSelectedChapter(null);
          return;
        }

        const options = (data.chapters || []).map((ch) => ({
          value: ch.id,
          label: ch.title,
        }));

        setChapters(options);

        if (options.length > 0) {
          setSelectedChapter(options[0].value);
        } else {
          setSelectedChapter(null);
        }
      } catch (e) {
        console.error("Failed to load chapters:", e);
        setChapters([]);
        setSelectedChapter(null);
      }
    }

    loadChapters();
  }, [selectedTextbook]);

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
                    src={null}
                    alt="Textbook cover"
                    fallbackSrc="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Crect width='300' height='300' fill='%23e9ecef'/%3E%3Cpath d='M80 210l55-60 40 45 30-25 55 65H80z' fill='%23adb5bd'/%3E%3Ccircle cx='115' cy='120' r='18' fill='%23adb5bd'/%3E%3C/svg%3E"
                    height={180}
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

                    <Text c="dimmed" size="sm" mt={6}>
                      {selectedBookLabel
                        ? `${chapters.length} chapter${
                            chapters.length === 1 ? "" : "s"
                          } in this book`
                        : "Select a textbook to begin"}
                    </Text>
                  </Box>
                </Stack>

                <Stack gap="sm" className="dashboard-controls">
                  <Text fw={600}>Select the following to begin</Text>

                  <SimpleGrid cols={2} spacing="sm">
                    <Select
                      label="Chapters"
                      placeholder="Select chapter"
                      data={chapters}
                      value={selectedChapter}
                      onChange={setSelectedChapter}
                    />
                    <Select
                      label="Difficulty"
                      data={[
                        { value: "1", label: "1 - Recall" },
                        { value: "2", label: "2 - Understand" },
                        { value: "3", label: "3 - Apply" },
                        { value: "4", label: "4 - Analyze" },
                      ]}
                      value={selectedDifficulty}
                      onChange={setSelectedDifficulty}
                    />
                  </SimpleGrid>

                  <Group gap="sm" className="dashboard-actions">
                    <Button
                      radius="xl"
                      fullWidth
                      onClick={() => {
                        if (!selectedTextbook || !selectedChapter) {
                          alert("Select textbook and chapter first");
                          return;
                        }
                        const chapterObj = chapters.find(
                          (ch) => ch.value === selectedChapter
                        );
                        navigate("/Summarize", {
                          state: {
                            textbook_id: selectedTextbook,
                            chapter_title: chapterObj?.label,
                            chapter_id: selectedChapter,
                          },
                        });
                      }}
                    >
                      Summarize
                    </Button>

                    <Button
                      variant="light"
                      radius="xl"
                      fullWidth
                      onClick={() => {
                        if (!selectedTextbook || !selectedChapter) {
                          alert("Select textbook and chapter first");
                          return;
                        }
                        const chapterObj = chapters.find(
                          (ch) => ch.value === selectedChapter
                        );
                        navigate("/flash", {
                          state: {
                            textbook_id: selectedTextbook,
                            chapter_title: chapterObj?.label,
                            chapter_id: selectedChapter,
                            difficulty: selectedDifficulty,
                          },
                        });
                      }}
                    >
                      Flashcards
                    </Button>

                    <Button
                      radius="xl"
                      fullWidth
                      onClick={() => {
                        if (
                          !selectedTextbook ||
                          !selectedChapter ||
                          !selectedDifficulty
                        ) {
                          alert(
                            "Select textbook, chapter, and difficulty first"
                          );
                          return;
                        }
                        const chapterObj = chapters.find(
                          (ch) => ch.value === selectedChapter
                        );
                        navigate("/quiz", {
                          state: {
                            textbook_id: selectedTextbook,
                            chapter_title: chapterObj?.label,
                            chapter_id: selectedChapter,
                            difficulty: selectedDifficulty,
                          },
                        });
                      }}
                    >
                      Quizzes
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
