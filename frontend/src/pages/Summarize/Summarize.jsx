import { useMemo, useState } from "react";
import {
  Container,
  Group,
  Title,
  Progress,
  Paper,
  Stack,
  Text,
  Button,
} from "@mantine/core";
import { useNavigate } from "react-router-dom";
import "./Summarize.css";

export default function Summarize() {
  const navigate = useNavigate();

  const chapters = useMemo(
    () => [
      {
        title: "Chapter 1",
        summary:
          "Dummy summary sentence one for Chapter 1. Dummy summary sentence two that adds a bit more detail. Dummy summary sentence three that wraps it up clearly.",
      },
      {
        title: "Chapter 2",
        summary:
          "Dummy summary sentence one for Chapter 2. Dummy summary sentence two that builds on the idea. Dummy summary sentence three that ends the recap.",
      },
      {
        title: "Chapter 3",
        summary:
          "Dummy summary sentence one for Chapter 3. Dummy summary sentence two with a key takeaway. Dummy summary sentence three with a quick conclusion.",
      },
      {
        title: "Chapter 4",
        summary:
          "Dummy summary sentence one for Chapter 4. Dummy summary sentence two highlighting what matters. Dummy summary sentence three to finish the overview.",
      },
      {
        title: "Chapter 5",
        summary:
          "Dummy summary sentence one for Chapter 5. Dummy summary sentence two explaining the main point. Dummy summary sentence three summarizing the chapter’s focus.",
      },
    ],
    []
  );

  const [index, setIndex] = useState(0);
  const total = chapters.length;
  const current = chapters[index];

  const progressValue = ((index + 1) / total) * 100;

  const goPrev = () => setIndex((i) => Math.max(0, i - 1));
  const goNext = () => setIndex((i) => Math.min(total - 1, i + 1));

  return (
    <main className="summarize-page">
      <Container size="md">
        {/* Header */}
        <Group justify="space-between" align="center" className="summarize-header">
          <Title order={1}>Summarize</Title>
          <Text className="summarize-counter">
            {index + 1} / {total}
          </Text>
        </Group>

        {}
        <Group align="center" gap="md" className="summarize-progress-row">
          <Text className="summarize-progress-label">Progress</Text>
          <Progress value={progressValue} className="summarize-progress" radius="xl" />
        </Group>

        {}
        <Paper withBorder radius="lg" p="xl" className="summarize-card">
          <Stack gap="sm">
            <Text fw={800} className="summarize-chapter-title">
              {current.title}
            </Text>
            <Text className="summarize-summary-text">{current.summary}</Text>
          </Stack>
        </Paper>

        {}
        <Group justify="space-between" className="summarize-nav">
          <Button variant="default" onClick={goPrev} disabled={index === 0}>
            Prev
          </Button>

          <Button onClick={goNext} disabled={index === total - 1}>
            Next
          </Button>
        </Group>

        {}
        <Group justify="flex-end" className="summarize-return">
          <Button variant="default" onClick={() => navigate("/dashboard")}>
            Return to Dashboard
          </Button>
        </Group>
      </Container>
    </main>
  );
}