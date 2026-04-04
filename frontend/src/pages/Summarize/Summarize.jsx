import { useState, useEffect } from "react";
import {
  Container,
  Group,
  Title,
  Paper,
  Stack,
  Text,
  Button,
} from "@mantine/core";
import { useNavigate, useLocation } from "react-router-dom";
import "./Summarize.css";

function SummaryView({ value }) {
  if (value == null) return <Text>No summary yet.</Text>;

  if (typeof value === "string") {
    return (
      <Text className="summarize-summary-text" style={{ whiteSpace: "pre-wrap" }}>
        {value || "No summary yet."}
      </Text>
    );
  }

  const isObj = typeof value === "object" && !Array.isArray(value);

  if (isObj) {
    const keyConcepts = Array.isArray(value.key_concepts) ? value.key_concepts : null;
    const keyTerms = Array.isArray(value.key_terms) ? value.key_terms : null;
    const relationships = Array.isArray(value.relationships) ? value.relationships : null;

    const hasAny =
      (keyConcepts && keyConcepts.length) ||
      (keyTerms && keyTerms.length) ||
      (relationships && relationships.length);

    if (hasAny) {
      // regular bullet list for concepts + relationships
      const renderBulletList = (items) => (
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

      // separate renderer for key terms
      const renderTermList = (items) => (
        <Stack gap={6}>
          {items.map((it, idx) => {
            const term = typeof it === "object" ? it?.term ?? "" : "";
            const definition = typeof it === "object" ? it?.definition ?? "" : "";
            const citation = typeof it === "object" ? it?.citation : "";

            return (
              <Text key={idx} style={{ whiteSpace: "pre-wrap" }}>
                • <strong>{term}</strong>
                {definition ? `: ${definition}` : ""}
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
              {renderBulletList(keyConcepts)}
            </Stack>
          ) : null}

          {keyTerms?.length ? (
            <Stack gap="xs">
              <Text fw={700}>Key terms</Text>
              {renderTermList(keyTerms)}
            </Stack>
          ) : null}

          {relationships?.length ? (
            <Stack gap="xs">
              <Text fw={700}>Relationships</Text>
              {renderBulletList(relationships)}
            </Stack>
          ) : null}
        </Stack>
      );
    }
  }

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
  const location = useLocation();
  const { textbook_id, chapter_title, chapter_id } = location.state || {};

  const API_BASE = "http://127.0.0.1:5001";

  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function fetchSummary() {
    if (!textbook_id || !chapter_title) {
      setError("Missing textbook_id or chapter_title. Go back and select a textbook and chapter.");
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
      const res = await fetch(`${API_BASE}/api/generate/summary`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          textbook_id,
          chapter_title,
          chapter_id,
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

      const summaryValue =
        data.summary ??
        data.result?.summary ??
        data.output?.summary ??
        (typeof data.result === "string" ? data.result : null);

      if (summaryValue == null || summaryValue === "") {
        setError("Backend returned success but no summary field.");
        return;
      }

      setSummary(summaryValue);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchSummary();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [textbook_id, chapter_title, chapter_id]);

  return (
    <main className="summarize-page">
      <Container size="md">
        <Group justify="space-between" align="center" className="summarize-header">
          <Title order={1}>Summarize</Title>
        </Group>

        <Paper withBorder radius="lg" p="xl" className="summarize-card">
          <Stack gap="sm">
            <Text fw={800} className="summarize-chapter-title">
              {chapter_title || "Chapter"}
            </Text>

            {error ? (
              <Text c="red" style={{ whiteSpace: "pre-wrap" }}>
                {error}
              </Text>
            ) : loading ? (
              <Text>Generating summary…</Text>
            ) : (
              <SummaryView value={summary} />
            )}

            <Group justify="flex-end">
              <Button variant="light" onClick={fetchSummary} disabled={loading}>
                Regenerate
              </Button>
            </Group>
          </Stack>
        </Paper>

        <Group justify="flex-end" className="summarize-return">
          <Button variant="default" onClick={() => navigate("/dashboard")}>
            Return to Dashboard
          </Button>
        </Group>
      </Container>
    </main>
  );
}