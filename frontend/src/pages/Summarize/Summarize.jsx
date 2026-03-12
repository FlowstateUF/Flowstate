// import { useMemo, useState, useEffect } from "react";
// import {
//   Container,
//   Group,
//   Title,
//   Progress,
//   Paper,
//   Stack,
//   Text,
//   Button,
// } from "@mantine/core";
// import { useNavigate } from "react-router-dom";
// import "./Summarize.css";

// export default function Summarize() {
//   const navigate = useNavigate();

//   // HARDCODED STUFF
//   const API_BASE = "http://127.0.0.1:5001";
//   const TEXTBOOK_ID = "213aab0a-dfbf-4157-aa7a-31bb0ade2561";

//   const chapters = useMemo(
//     () => [
//       {
//         title: "1. Why Data Structures Matter",
//         summary:
//           "Dummy summary sentence one for Chapter 1. Dummy summary sentence two that adds a bit more detail. Dummy summary sentence three that wraps it up clearly.",
//       },
//       {
//         title: "The Array: The Foundational Data Structure",
//         summary:
//           "Dummy summary sentence one for Chapter 2. Dummy summary sentence two that builds on the idea. Dummy summary sentence three that ends the recap.",
//       },
//       {
//         title: "Chapter 3",
//         summary:
//           "Dummy summary sentence one for Chapter 3. Dummy summary sentence two with a key takeaway. Dummy summary sentence three with a quick conclusion.",
//       },
//       {
//         title: "Chapter 4",
//         summary:
//           "Dummy summary sentence one for Chapter 4. Dummy summary sentence two highlighting what matters. Dummy summary sentence three to finish the overview.",
//       },
//       {
//         title: "Chapter 5",
//         summary:
//           "Dummy summary sentence one for Chapter 5. Dummy summary sentence two explaining the main point. Dummy summary sentence three summarizing the chapter’s focus.",
//       },
//     ],
//     []
//   );

//   const [index, setIndex] = useState(0);
//   const total = chapters.length;
//   const current = chapters[index];

//   const [summaries, setSummaries] = useState(() => ({}));
//   const [loading, setLoading] = useState(false);
//   const [error, setError] = useState("");

//   const progressValue = ((index + 1) / total) * 100;

//   const goPrev = () => setIndex((i) => Math.max(0, i - 1));
//   const goNext = () => setIndex((i) => Math.min(total - 1, i + 1));

//   return (
//     <main className="summarize-page">
//       <Container size="md">
//         {/* Header */}
//         <Group justify="space-between" align="center" className="summarize-header">
//           <Title order={1}>Summarize</Title>
//           <Text className="summarize-counter">
//             {index + 1} / {total}
//           </Text>
//         </Group>

//         {}
//         <Group align="center" gap="md" className="summarize-progress-row">
//           <Text className="summarize-progress-label">Progress</Text>
//           <Progress value={progressValue} className="summarize-progress" radius="xl" />
//         </Group>

//         {}
//         <Paper withBorder radius="lg" p="xl" className="summarize-card">
//           <Stack gap="sm">
//             <Text fw={800} className="summarize-chapter-title">
//               {current.title}
//             </Text>
//             <Text className="summarize-summary-text">{current.summary}</Text>
//           </Stack>
//         </Paper>

//         {}
//         <Group justify="space-between" className="summarize-nav">
//           <Button variant="default" onClick={goPrev} disabled={index === 0}>
//             Prev
//           </Button>

//           <Button onClick={goNext} disabled={index === total - 1}>
//             Next
//           </Button>
//         </Group>

//         {}
//         <Group justify="flex-end" className="summarize-return">
//           <Button variant="default" onClick={() => navigate("/dashboard")}>
//             Return to Dashboard
//           </Button>
//         </Group>
//       </Container>
//     </main>
//   );
// }

import { useMemo, useState, useEffect } from "react";
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

function toDisplayText(value) {
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function SummaryView({ value }) {
  if (value == null) return <Text>No summary yet.</Text>;

  // Plain string summary
  if (typeof value === "string") {
    return (
      <Text className="summarize-summary-text" style={{ whiteSpace: "pre-wrap" }}>
        {value || "No summary yet."}
      </Text>
    );
  }

  // Expected object shape: { key_concepts: [{bullet, citation}], key_terms: [...], relationships: [...] }
  const isObj = typeof value === "object" && !Array.isArray(value);

  if (isObj) {
    const keyConcepts = Array.isArray(value.key_concepts) ? value.key_concepts : null;
    const keyTerms = Array.isArray(value.key_terms) ? value.key_terms : null;
    const relationships = Array.isArray(value.relationships) ? value.relationships : null;

    const hasAny = (keyConcepts && keyConcepts.length) || (keyTerms && keyTerms.length) || (relationships && relationships.length);

    if (hasAny) {
      const renderList = (items) => (
        <Stack gap={6}>
          {items.map((it, idx) => {
            const bullet = typeof it === "string" ? it : it?.bullet ?? it?.text ?? "";
            const citation = typeof it === "object" ? it?.citation : "";
            return (
              <Text key={idx} style={{ whiteSpace: "pre-wrap" }}>
                • {bullet}
                {citation ? ` (${citation})` : ""}
              </Text>
            );
          })}
        </Stack>
      );

      return (
        <Stack gap="md">
          {keyConcepts?.length ? (
            <Stack gap="xs">
              <Text fw={700}>Key concepts</Text>
              {renderList(keyConcepts)}
            </Stack>
          ) : null}

          {keyTerms?.length ? (
            <Stack gap="xs">
              <Text fw={700}>Key terms</Text>
              {renderList(keyTerms)}
            </Stack>
          ) : null}

          {relationships?.length ? (
            <Stack gap="xs">
              <Text fw={700}>Relationships</Text>
              {renderList(relationships)}
            </Stack>
          ) : null}
        </Stack>
      );
    }
  }

  // Fallback: unknown object/array shape → pretty JSON
  let pretty = "";
  try {
    pretty = JSON.stringify(value, null, 2);
  } catch {
    pretty = String(value);
  }

  return (
    <Text className="summarize-summary-text" style={{ whiteSpace: "pre-wrap" }}>
      {pretty}
    </Text>
  );
}

export default function Summarize() {
  const navigate = useNavigate();

  // HARDCODED STUFF
  const API_BASE = "http://127.0.0.1:5001";
  const TEXTBOOK_ID = "213aab0a-dfbf-4157-aa7a-31bb0ade2561";

  const chapters = useMemo(
    () => [
      { title: "1. Why Data Structures Matter" },
      { title: "The Array: The Foundational Data Structure" },
    ],
    []
  );

  const [index, setIndex] = useState(0);
  const total = chapters.length;

  const current = chapters[index] ?? null;
  const currentTitle = current?.title ?? "";

  // Store RAW summary values (string OR object)
  const [summaries, setSummaries] = useState(() => ({})); // { [title]: any }
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const progressValue = total > 0 ? ((index + 1) / total) * 100 : 0;

  const goPrev = () => setIndex((i) => Math.max(0, i - 1));
  const goNext = () => setIndex((i) => Math.min(total - 1, i + 1));

  async function fetchSummaryForChapter(chapterTitle, { force = false } = {}) {
    setError("");
    if (!chapterTitle) return;

    // cache unless forcing regeneration
    if (!force && summaries[chapterTitle]) return;

    const token = localStorage.getItem("access_token");
    if (!token) {
      setError("No access_token found in localStorage. Log in first.");
      return;
    }

    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/generate/summary`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          textbook_id: TEXTBOOK_ID,
          topic: chapterTitle,
        }),
      });

      // Defensive parse: backend might return non-JSON on errors
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

      // Accept common shapes; summary may be STRING or OBJECT
      const summaryValue =
        data.summary ??
        data.result?.summary ??
        data.output?.summary ??
        (typeof data.result === "string" ? data.result : "") ??
        "";

      if (summaryValue === "" || summaryValue == null) {
        setError("Backend returned success but no summary field.");
        return;
      }

      setSummaries((prev) => ({
        ...prev,
        [chapterTitle]: summaryValue,
      }));
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  // Auto-generate summary whenever chapter changes
  useEffect(() => {
    if (currentTitle) fetchSummaryForChapter(currentTitle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index, currentTitle]);

  const currentSummaryValue = currentTitle ? summaries[currentTitle] : null;
  const currentSummaryText = toDisplayText(currentSummaryValue);

  return (
    <main className="summarize-page">
      <Container size="md">
        {/* Header */}
        <Group justify="space-between" align="center" className="summarize-header">
          <Title order={1}>Summarize</Title>
          <Text className="summarize-counter">
            {total > 0 ? `${index + 1} / ${total}` : "0 / 0"}
          </Text>
        </Group>

        {/* Progress */}
        <Group align="center" gap="md" className="summarize-progress-row">
          <Text className="summarize-progress-label">Progress</Text>
          <Progress value={progressValue} className="summarize-progress" radius="xl" />
        </Group>

        {/* No chapters guard */}
        {!current ? (
          <Paper withBorder radius="lg" p="xl">
            <Text>No chapters available.</Text>
          </Paper>
        ) : (
          <Paper withBorder radius="lg" p="xl" className="summarize-card">
            <Stack gap="sm">
              <Text fw={800} className="summarize-chapter-title">
                {currentTitle}
              </Text>

              {error && (
                <Text c="red" style={{ whiteSpace: "pre-wrap" }}>
                  {error}
                </Text>
              )}

              {loading && !currentSummaryValue ? (
                <Text>Generating summary…</Text>
              ) : (
                <SummaryView value={currentSummaryValue} />
              )}

              <Group justify="flex-end">
                <Button
                  variant="light"
                  onClick={() => fetchSummaryForChapter(currentTitle, { force: true })}
                  disabled={loading}
                >
                  Regenerate
                </Button>
              </Group>
            </Stack>
          </Paper>
        )}

        {/* Navigation */}
        <Group justify="space-between" className="summarize-nav">
          <Button variant="default" onClick={goPrev} disabled={index === 0 || loading}>
            Prev
          </Button>

          <Button onClick={goNext} disabled={index === total - 1 || loading}>
            Next
          </Button>
        </Group>

        {/* Return */}
        <Group justify="flex-end" className="summarize-return">
          <Button variant="default" onClick={() => navigate("/dashboard")}>
            Return to Dashboard
          </Button>
        </Group>
      </Container>
    </main>
  );
}