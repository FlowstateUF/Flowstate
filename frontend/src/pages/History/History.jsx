import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Badge,
  Box,
  Container,
  Group,
  Notification,
  Paper,
  Loader,
  RingProgress,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import NavBar from "../../components/NavBar";
import { authFetch } from "../../utils/authFetch";
import "./History.css";

const API_BASE = "http://localhost:5001";
const PENDING_STORAGE_KEY = "pendingTextbooks";
const POLL_INTERVAL_MS = 2500;
const COMPLETE_CARD_HOLD_MS = 1600;

const IN_FLIGHT_STATUSES = new Set([
  "queued",
  "uploading",
  "processing",
  "parsing",
  "generating_pretests",
  "pretest_generation",
]);

const CLICKABLE_STATUSES = new Set(["ready", "partial"]);

function BookPlaceholderIcon() {
  return (
    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M21 19V5a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2Z"
        stroke="#9aa3ad"
        strokeWidth="1.5"
      />
      <path d="M7 7h10" stroke="#9aa3ad" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M7 11h10" stroke="#9aa3ad" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M7 15h7" stroke="#9aa3ad" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M5 5.5A2.5 2.5 0 0 0 2.5 8v10A2.5 2.5 0 0 1 5 15.5h2V5.5H5Z" fill="#d8dee7" />
    </svg>
  );
}

function readPendingTextbooks() {
  try {
    const parsed = JSON.parse(localStorage.getItem(PENDING_STORAGE_KEY) || "[]");
    const deduped = new Map();

    for (const item of parsed) {
      if (item?.id) deduped.set(item.id, item);
    }

    return Array.from(deduped.values());
  } catch {
    return [];
  }
}

function writePendingTextbooks(nextValue) {
  localStorage.setItem(PENDING_STORAGE_KEY, JSON.stringify(nextValue));
}

function trimPdfExtension(value) {
  if (!value) return "Untitled Textbook";
  return String(value).replace(/\.pdf$/i, "");
}

function isInFlight(status) {
  return IN_FLIGHT_STATUSES.has(String(status || "").toLowerCase());
}

function clamp(number, min, max) {
  return Math.max(min, Math.min(max, number));
}

function normalizeTextbook(raw, { previous = {}, pending = {} } = {}) {
  return {
    id: raw.id,
    title: raw.title || raw.filename || pending.title || previous.title || "Untitled Textbook",
    status: raw.status || pending.status || previous.status || "processing",
    stage: raw.stage || raw.status || pending.stage || previous.stage || "processing",
    progress:
      typeof raw.progress_percent === "number"
        ? raw.progress_percent
        : typeof raw.progress === "number"
        ? raw.progress
        : typeof previous.progress === "number"
        ? previous.progress
        : typeof pending.progress === "number"
        ? pending.progress
        : null,
    stageLabel:
      raw.stage_label ||
      raw.stageLabel ||
      pending.stageLabel ||
      previous.stageLabel ||
      "",
    detail:
      raw.detail ||
      pending.detail ||
      previous.detail ||
      "",
    chapterCount:
      raw.chapter_count ??
      raw.chapterCount ??
      previous.chapterCount ??
      pending.chapterCount ??
      0,
    pretestsReady:
      raw.pretests_ready ??
      raw.pretestsReady ??
      previous.pretestsReady ??
      pending.pretestsReady ??
      0,
    createdAt:
      raw.created_at ||
      raw.createdAt ||
      previous.createdAt ||
      pending.createdAt ||
      pending.startedAt ||
      Date.now(),
    startedAt: pending.startedAt || previous.startedAt || Date.now(),
  };
}

function buildPendingOnlyTextbook(pending, previous = {}) {
  return {
    id: pending.id,
    title: pending.title || previous.title || "Untitled Textbook",
    status: pending.status || previous.status || "processing",
    stage: pending.stage || previous.stage || pending.status || "processing",
    progress:
      typeof pending.progress_percent === "number"
        ? pending.progress_percent
        : typeof pending.progress === "number"
        ? pending.progress
        : typeof previous.progress === "number"
        ? previous.progress
        : null,
    stageLabel:
      pending.stage_label ||
      pending.stageLabel ||
      previous.stageLabel ||
      "",
    detail:
      pending.detail ||
      previous.detail ||
      "",
    chapterCount: previous.chapterCount || 0,
    pretestsReady: previous.pretestsReady || 0,
    createdAt: pending.startedAt || previous.createdAt || Date.now(),
    startedAt: pending.startedAt || previous.startedAt || Date.now(),
  };
}

function sortTextbooks(books) {
  return [...books].sort((a, b) => {
    const aBusy = isInFlight(a.status) || isInFlight(a.stage);
    const bBusy = isInFlight(b.status) || isInFlight(b.stage);

    if (aBusy && !bBusy) return -1;
    if (!aBusy && bBusy) return 1;

    const aTime = new Date(a.createdAt || a.startedAt || 0).getTime();
    const bTime = new Date(b.createdAt || b.startedAt || 0).getTime();

    return bTime - aTime;
  });
}

function getBookPresentation(book, showCompleteSplash) {
  const status = String(book.status || "").toLowerCase();
  const realValue =
    typeof book.progress === "number" ? clamp(Math.round(book.progress), 0, 100) : null;

  if (status === "failed") {
    return {
      value: 100,
      color: "red",
      badgeColor: "red",
      badgeText: "Failed",
      centerLabel: "!",
      description: book.detail || "Something went wrong while processing this textbook.",
    };
  }

  if (status === "partial") {
    return {
      value: 100,
      color: "yellow",
      badgeColor: "yellow",
      badgeText: "Partial",
      centerLabel: "100%",
      description: book.detail || "Most content is ready. Click to open it.",
    };
  }

  if (showCompleteSplash) {
    return {
      value: 100,
      color: "teal",
      badgeColor: "teal",
      badgeText: "Complete",
      centerLabel: "100%",
      description: "Processing complete. This textbook is ready.",
    };
  }

  if (status === "ready") {
    return {
      value: 100,
      color: "teal",
      badgeColor: "teal",
      badgeText: "Ready",
      centerLabel: "100%",
      description: book.detail || "Ready to use. Click to continue learning.",
    };
  }

  if (status === "generating_pretests" || status === "pretest_generation") {
    const value = realValue ?? 80;
    return {
      value,
      color: "violet",
      badgeColor: "violet",
      badgeText: "Pretest",
      centerLabel: `${value}%`,
      description:
        book.detail ||
        (book.chapterCount > 0
          ? `Generating pretests (${book.pretestsReady}/${book.chapterCount})`
          : "Generating pretests..."),
    };
  }

  const value = realValue ?? 5;

  return {
    value,
    color: "blue",
    badgeColor: "blue",
    badgeText: "Parsing",
    centerLabel: `${value}%`,
    description: book.detail || "Parsing textbook...",
  };
}

export default function History() {
  const navigate = useNavigate();

  const [textbooks, setTextbooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState("");
  const [toast, setToast] = useState(null);
  const [recentlyCompleted, setRecentlyCompleted] = useState({});

  const completionTimersRef = useRef({});

  const fetchTextbooks = useCallback(async () => {
    try {
      const response = await authFetch(`${API_BASE}/api/textbooks`);

      if (response.status === 401) {
        navigate("/login");
        return;
      }

      const payload = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(payload.error || "Could not load textbooks.");
      }

      const rawBooks = Array.isArray(payload) ? payload : payload.textbooks || [];
      const pendingList = readPendingTextbooks();

      setTextbooks((previousBooks) => {
        const previousById = Object.fromEntries(previousBooks.map((book) => [book.id, book]));
        const pendingById = Object.fromEntries(pendingList.map((book) => [book.id, book]));

        const mergedFromBackend = rawBooks.map((raw) =>
          normalizeTextbook(raw, {
            previous: previousById[raw.id],
            pending: pendingById[raw.id],
          })
        );

        const seenIds = new Set(mergedFromBackend.map((book) => book.id));

        const pendingOnly = pendingList
          .filter((pendingBook) => !seenIds.has(pendingBook.id))
          .map((pendingBook) => buildPendingOnlyTextbook(pendingBook, previousById[pendingBook.id]));

        return sortTextbooks([...mergedFromBackend, ...pendingOnly]);
      });

      setPageError("");
    } catch (error) {
      console.error("Failed to fetch textbooks:", error);

      const pendingList = readPendingTextbooks();
      if (pendingList.length > 0) {
        setTextbooks((previousBooks) => {
          const previousById = Object.fromEntries(previousBooks.map((book) => [book.id, book]));
          return sortTextbooks(
            pendingList.map((pendingBook) =>
              buildPendingOnlyTextbook(pendingBook, previousById[pendingBook.id])
            )
          );
        });
      }

      setPageError("Could not load your textbooks right now.");
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  const pollStatuses = useCallback(async (bookIds) => {
    if (!bookIds.length) return;

    const updates = await Promise.all(
      bookIds.map(async (bookId) => {
        try {
          const response = await authFetch(`${API_BASE}/api/textbooks/${bookId}/status`);

          if (!response.ok) return null;

          const payload = await response.json().catch(() => ({}));

          return {
            id: bookId,
            status: payload.status,
            stage: payload.stage || payload.status,
            progress:
              typeof payload.progress_percent === "number"
                ? payload.progress_percent
                : typeof payload.progress === "number"
                ? payload.progress
                : typeof payload.percent === "number"
                ? payload.percent
                : null,
            stageLabel: payload.stage_label || "",
            detail: payload.detail || "",
            chapterCount: payload.chapter_count ?? payload.chapterCount ?? 0,
            pretestsReady: payload.pretests_ready ?? payload.pretestsReady ?? 0,
          };

        } catch (error) {
          console.error(`Failed to poll textbook ${bookId}:`, error);
          return null;
        }
      })
    );

    const updateMap = Object.fromEntries(
      updates.filter(Boolean).map((update) => [update.id, update])
    );

    if (!Object.keys(updateMap).length) return;

    setTextbooks((previousBooks) =>
      sortTextbooks(
        previousBooks.map((book) =>
          updateMap[book.id] ? { ...book, ...updateMap[book.id] } : book
        )
      )
    );
  }, []);

  useEffect(() => {
    let active = true;

    async function boot() {
      try {
        const meResponse = await authFetch(`${API_BASE}/api/me`);
        if (!meResponse.ok) {
          navigate("/login");
          return;
        }

        if (active) {
          await fetchTextbooks();
        }
      } catch (error) {
        console.error("Failed to initialize textbooks page:", error);
        navigate("/login");
      }
    }

    boot();

    return () => {
      active = false;
    };
  }, [fetchTextbooks, navigate]);

  useEffect(() => {
    const activeBookIds = textbooks
      .filter((book) => isInFlight(book.status) || isInFlight(book.stage))
      .map((book) => book.id);

    if (!activeBookIds.length) return;

    pollStatuses(activeBookIds);

    const intervalId = window.setInterval(() => {
      pollStatuses(activeBookIds);
    }, POLL_INTERVAL_MS);

    return () => window.clearInterval(intervalId);
  }, [pollStatuses, textbooks]);

  useEffect(() => {
    if (!textbooks.length) return;

    const pendingList = readPendingTextbooks();
    if (!pendingList.length) return;

    const pendingIds = new Set(pendingList.map((book) => book.id));
    let nextPending = [...pendingList];
    let changed = false;

    textbooks.forEach((book) => {
      if (!pendingIds.has(book.id)) return;

      const status = String(book.status || "").toLowerCase();

      if (status === "ready" || status === "partial") {
        setToast({
          color: "teal",
          title: "Textbook ready",
          message: `${trimPdfExtension(book.title)} is ready to use.`,
        });

        setRecentlyCompleted((previous) => ({
          ...previous,
          [book.id]: true,
        }));

        if (completionTimersRef.current[book.id]) {
          window.clearTimeout(completionTimersRef.current[book.id]);
        }

        completionTimersRef.current[book.id] = window.setTimeout(() => {
          setRecentlyCompleted((previous) => {
            const next = { ...previous };
            delete next[book.id];
            return next;
          });
          delete completionTimersRef.current[book.id];
        }, COMPLETE_CARD_HOLD_MS);

        nextPending = nextPending.filter((pendingBook) => pendingBook.id !== book.id);
        changed = true;
      }

      if (status === "failed") {
        setToast({
          color: "red",
          title: "Upload failed",
          message: `${trimPdfExtension(book.title)} could not be processed.`,
        });

        nextPending = nextPending.filter((pendingBook) => pendingBook.id !== book.id);
        changed = true;
      }
    });

    if (changed) {
      writePendingTextbooks(nextPending);
    }
  }, [textbooks]);

  useEffect(() => {
    if (!toast) return;

    const timerId = window.setTimeout(() => {
      setToast(null);
    }, 4000);

    return () => window.clearTimeout(timerId);
  }, [toast]);

  useEffect(() => {
    return () => {
      Object.values(completionTimersRef.current).forEach((timerId) => {
        window.clearTimeout(timerId);
      });
    };
  }, []);

  const goToBook = (book) => {
    const status = String(book.status || "").toLowerCase();
    if (!CLICKABLE_STATUSES.has(status)) return;

    navigate(`/dashboard?textbook=${encodeURIComponent(book.id)}`, {
      state: {
        textbookId: book.id,
        textbookTitle: book.title,
        textbookStatus: book.status,
      },
    });
  };

  return (
    <>
      <NavBar isAuthed={true} />

      {toast && (
        <div className="history-toast">
          <Notification
            withCloseButton
            color={toast.color}
            title={toast.title}
            onClose={() => setToast(null)}
          >
            {toast.message}
          </Notification>
        </div>
      )}

      <main className="history-page">
        <Container size="lg">
          <Stack gap="md">
            <Box>
              <Title order={1} className="history-title">
                Welcome back!
              </Title>
              <Text c="dimmed" className="history-subtitle">
                Click on a textbook to continue your learning.
              </Text>
            </Box>

            {pageError && (
              <Paper withBorder radius="md" p="md">
                <Text c="red">{pageError}</Text>
              </Paper>
            )}

            {loading && textbooks.length === 0 ? (
              <div className="history-loadingCard">
                <div className="history-loadingInner">
                  <Loader size={56} />
                  <Text fw={700} className="history-loadingTitle">
                    Loading library...
                  </Text>
                  <Text c="dimmed" size="sm" className="history-loadingSubtitle">
                    Getting your textbooks ready.
                  </Text>
                </div>
              </div>
            ) : textbooks.length === 0 ? (

              <Paper withBorder radius="md" className="history-empty">
                <Text fw={600}>No textbooks yet</Text>
                <Text c="dimmed" size="sm" mt={6}>
                  Upload your first PDF from the Home page and it will appear here automatically.
                </Text>
              </Paper>
            ) : (
              <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="xl" className="history-grid">
                {textbooks.map((book) => {
                  const clickable = CLICKABLE_STATUSES.has(String(book.status || "").toLowerCase());
                  const showCompleteSplash = Boolean(recentlyCompleted[book.id]);
                  const presentation = getBookPresentation(book, showCompleteSplash);

                  return (
                    <Paper
                      key={book.id}
                      withBorder
                      radius="md"
                      className={[
                        "history-book",
                        !clickable ? "history-book--processing" : "",
                        String(book.status || "").toLowerCase() === "failed"
                          ? "history-book--failed"
                          : "",
                      ]
                        .filter(Boolean)
                        .join(" ")}
                      onClick={clickable ? () => goToBook(book) : undefined}
                      role={clickable ? "button" : undefined}
                      tabIndex={clickable ? 0 : -1}
                      onKeyDown={(e) => {
                        if (!clickable) return;
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          goToBook(book);
                        }
                      }}
                    >
                      <div
                        className={[
                          "history-cover",
                          !clickable || showCompleteSplash ? "history-cover--processing" : "",
                        ]
                          .filter(Boolean)
                          .join(" ")}
                      >
                        {clickable && !showCompleteSplash ? (
                          <div className="history-img-icon">
                            <BookPlaceholderIcon />
                          </div>
                        ) : (
                          <div className="history-progressWrap">
                            <RingProgress
                              size={128}
                              thickness={12}
                              roundCaps
                              sections={[
                                {
                                  value: presentation.value,
                                  color: presentation.color,
                                },
                              ]}
                              label={
                                <div className="history-progressLabelWrap">
                                  <span className="history-progressLabel">{presentation.centerLabel}</span>
                                </div>
                              }
                            />
                          </div>
                        )}
                      </div>

                      <Group justify="space-between" align="flex-start" gap="xs" mt="sm">
                        <Text fw={600} className="history-book-label">
                          {trimPdfExtension(book.title)}
                        </Text>

                        <Badge variant="light" color={presentation.badgeColor}>
                          {presentation.badgeText}
                        </Badge>
                      </Group>

                      <Text size="sm" c="dimmed" mt={6} className="history-book-statusText">
                        {presentation.description}
                      </Text>
                      {!clickable && (
                        <Text size="xs" c="dimmed" className="history-book-helperText">
                          This can take a few minutes.
                        </Text>
                      )}
                    </Paper>
                  );
                })}
              </SimpleGrid>
            )}
          </Stack>
        </Container>
      </main>
    </>
  );
}