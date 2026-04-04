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
} from "@mantine/core";
import { useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";

import NavBar from "../../components/NavBar";
import "./Dashboard.css";

export default function Dashboard() {
  const navigate = useNavigate();

  const API_BASE = "http://127.0.0.1:5001";

  const [selectedTextbook, setSelectedTextbook] = useState(null);
  const [selectedChapter, setSelectedChapter] = useState(null);
  const [selectedDifficulty, setSelectedDifficulty] = useState("1");

  const [textbooks, setTextbooks] = useState([]);
  const [chapters, setChapters] = useState([]);

  // load textbooks on page load
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

        // optional: auto-select first textbook
        if (options.length > 0) {
          setSelectedTextbook(options[0].value);
        }
      } catch (e) {
        console.error("Failed to load textbooks:", e);
      }
    }

    loadTextbooks();
  }, []);

  // load chapters whenever textbook changes
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

        // reset selected chapter when textbook changes
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

  return (
    <>
      <NavBar isAuthed={true} />

      <main className="dashboard-page">
        <Container size="lg">
          <Stack gap="xl">
            {/* Top card */}
            <Paper withBorder p="xl" radius="md" className="dashboard-card">
              <Group
                align="flex-start"
                gap="xl"
                wrap="nowrap"
                className="dashboard-top-row"
              >
                {/* Cover */}
                <Box className="dashboard-cover">
                  <Image
                    src={null}
                    alt="Textbook cover"
                    fallbackSrc="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Crect width='300' height='300' fill='%23e9ecef'/%3E%3Cpath d='M80 210l55-60 40 45 30-25 55 65H80z' fill='%23adb5bd'/%3E%3Ccircle cx='115' cy='120' r='18' fill='%23adb5bd'/%3E%3C/svg%3E"
                    height={180}
                    fit="cover"
                  />
                </Box>

                {/* Textbook dropdown + placeholder lines */}
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
                      author • date • etc
                    </Text>
                  </Box>

                  <Stack gap={8} className="dashboard-text-lines">
                    <Box className="dashboard-line" style={{ width: "85%" }} />
                    <Box className="dashboard-line" style={{ width: "70%" }} />
                    <Box className="dashboard-line" style={{ width: "55%" }} />
                  </Stack>
                </Stack>

                {/* Controls */}
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
                        const chapterObj = chapters.find((ch) => ch.value === selectedChapter);
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
                      if (!selectedTextbook || !selectedChapter || !selectedDifficulty) {
                        alert("Select textbook, chapter, and difficulty first");
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

            {/* Bottom card (hover blue border + click to stats) */}
            <Paper
              withBorder
              p="xl"
              radius="md"
              className="dashboard-card dashboard-clickable"
              onClick={() => navigate("/stats")}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") navigate("/stats");
              }}
            >
              <Group
                align="stretch"
                gap="xl"
                wrap="nowrap"
                className="dashboard-bottom-row"
              >
                {/* Left info */}
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

                {/* Chart placeholder */}
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