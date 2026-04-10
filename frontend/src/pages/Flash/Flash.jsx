import { useEffect, useState, useRef } from "react";
import {
  Container,
  Group,
  Title,
  Text,
  Paper,
  ActionIcon,
  Button,
} from "@mantine/core";
import { IconInfoCircle, IconQuestionMark } from "@tabler/icons-react";
import { useLocation, useNavigate } from "react-router-dom";
import NavBar from "../../components/NavBar";
import "./flash.css";

export default function Flash() {
  const location = useLocation();
  const navigate = useNavigate();

  const { textbook_id, chapter_title, chapter_id, difficulty } = location.state || {};

  const API_BASE = "http://127.0.0.1:5001";

  const [flipped, setFlipped] = useState(false);
  const [cards, setCards] = useState([]);
  const [index, setIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [flashcardSetId, setFlashcardSetId] = useState(null);
  const sessionStartedAtRef = useRef(null);
  const sessionSentRef = useRef(false);

  const currentCard = cards[index] || null;

  async function fetchFlashcards() {
    if (!textbook_id || !chapter_title || !difficulty) {
      setError("Missing textbook, chapter, or difficulty. Go back and select a textbook and chapter.");
      return;
    }

    const token = localStorage.getItem("access_token");
    if (!token) {
      setError("No access token found. Please log in again.");
      return;
    }

    setLoading(true);
    setError("");
    setFlipped(false);
    setFlashcardSetId(null);
    sessionSentRef.current = false;

    try {
      const res = await fetch(`${API_BASE}/api/generate/flashcards`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          textbook_id,
          chapter_title,
          chapter_id,
          difficulty,
          num_cards: 5,
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

      // support a few possible response shapes
      const flashcards =
        data.flashcards ||
        data.cards ||
        data.result?.flashcards ||
        data.result?.cards ||
        [];

      if (!Array.isArray(flashcards) || flashcards.length === 0) {
        setError("Backend returned no flashcards.");
        setCards([]);
        return;
      }

      setCards(flashcards);
      setIndex(0);
      setFlashcardSetId(data.flashcard_set_id || null);
      sessionStartedAtRef.current = Date.now();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchFlashcards();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [textbook_id, chapter_title, chapter_id]);

  function goPrev() {
    setFlipped(false);
    setIndex((i) => Math.max(0, i - 1));
  }

  function goNext() {
    setFlipped(false);
    setIndex((i) => Math.min(cards.length - 1, i + 1));
  }

  async function recordFlashcardSession() {
    if (!flashcardSetId || sessionSentRef.current) return;
    const token = localStorage.getItem("access_token");
    if (!token) return;

    const started = sessionStartedAtRef.current;
    const timeStudied = Math.max(
      0,
      Math.floor((Date.now() - (started ?? Date.now())) / 1000)
    );

    try {
      const res = await fetch(`${API_BASE}/api/flashcard-sessions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          flashcard_set_id: flashcardSetId,
          time_studied: timeStudied,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        console.error("Flashcard session save failed:", err?.error || res.status);
        return;
      }
      sessionSentRef.current = true;
    } catch (e) {
      console.error("Flashcard session save failed:", e);
    }
  }

  async function handleReturnToDashboard() {
    await recordFlashcardSession();
    navigate("/dashboard");
  }

  return (
    <>
      <NavBar isAuthed={true} />

      <main className="flashpage">
        <Container size="md">
          {/* Header row */}
          <Group justify="space-between" align="center" className="flashpage-header">
            <Title order={1} className="flashpage-title">
              Flashcards
            </Title>

            <Group gap="xs">
              <ActionIcon variant="subtle" radius="xl" aria-label="Info">
                <IconInfoCircle size={20} />
              </ActionIcon>
              <ActionIcon variant="subtle" radius="xl" aria-label="Help">
                <IconQuestionMark size={20} />
              </ActionIcon>
            </Group>
          </Group>

          {chapter_title ? (
            <Text c="dimmed" mb="md">
              {chapter_title}
            </Text>
          ) : null}

          {error ? (
            <Paper withBorder radius="lg" p="xl">
              <Text c="red">{error}</Text>
            </Paper>
          ) : loading ? (
            <Paper withBorder radius="lg" p="xl">
              <Text>Generating flashcards…</Text>
            </Paper>
          ) : !currentCard ? (
            <Paper withBorder radius="lg" p="xl">
              <Text>No flashcards yet.</Text>
            </Paper>
          ) : (
            <>
              {/* Card */}
              <Paper
                withBorder
                radius="lg"
                className="flipcard-outer"
                onClick={() => setFlipped((f) => !f)}
              >
                <div className={`flipcard ${flipped ? "is-flipped" : ""}`}>
                  <div className="flipcard-face flipcard-front">
                    <Text fw={800} className="front-title">
                      Front
                    </Text>
                    <Text className="front-text">
                      {currentCard.question || currentCard.front || "No question"}
                    </Text>
                  </div>

                  <div className="flipcard-face flipcard-back">
                    <Text fw={800} className="back-title">
                      Back
                    </Text>
                    <Text className="back-text">
                      {currentCard.answer || currentCard.back || "No answer"}
                    </Text>
                  </div>
                </div>
              </Paper>

              <Text ta="center" c="dimmed" mt="md" className="flip-hint">
                click the card to flip
              </Text>

              <Group justify="space-between" mt="lg">
                <Button variant="default" onClick={goPrev} disabled={index === 0}>
                  Prev
                </Button>

                <Text c="dimmed">
                  {index + 1} / {cards.length}
                </Text>

                <Button onClick={goNext} disabled={index === cards.length - 1}>
                  Next
                </Button>
              </Group>

              <Group justify="flex-end" mt="md">
                <Button variant="light" onClick={fetchFlashcards} disabled={loading}>
                  Regenerate
                </Button>
              </Group>
            </>
          )}
          <Group justify="flex-end" className="flash-return">
            <Button variant="default" onClick={handleReturnToDashboard}>
              Return to Dashboard
            </Button>
          </Group>
        </Container>
      </main>
    </>
  );
}
