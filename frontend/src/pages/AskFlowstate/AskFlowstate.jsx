import { useEffect, useRef, useState } from "react";
import {
  Badge,
  Button,
  Container,
  Group,
  Loader,
  Stack,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { IconArrowUp, IconMessageCircle2 } from "@tabler/icons-react";
import { useLocation, useNavigate } from "react-router-dom";

import NavBar from "../../components/NavBar";
import brain from "../../assets/generic_brain.png";
import { authFetch } from "../../utils/authFetch";
import "./AskFlowstate.css";

const API_BASE = "http://127.0.0.1:5001";
const CUSTOM_COVERS_STORAGE_KEY = "customTextbookCovers";
const CHAT_STORAGE_PREFIX = "askFloChat:";

function FloMark({ className = "" }) {
  return (
    <svg
      viewBox="0 0 64 64"
      aria-hidden="true"
      className={className}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M15 25C19 21 23 21 27 25C31 29 35 29 39 25C43 21 47 21 51 25"
        stroke="currentColor"
        strokeWidth="4"
        strokeLinecap="round"
      />
      <path
        d="M15 34C19 30 23 30 27 34C31 38 35 38 39 34C43 30 47 30 51 34"
        stroke="currentColor"
        strokeWidth="4"
        strokeLinecap="round"
        opacity="0.92"
      />
    </svg>
  );
}

function createIntroMessage(textbookTitle) {
  return {
    id: "intro",
    role: "assistant",
    citations: [],
    text: textbookTitle
      ? `I’m Flo. Ask me about ${textbookTitle}, and I’ll stay focused on the content from that textbook.`
      : "I’m Flo. Ask me about your textbook, and I’ll stay focused on the content from that book.",
  };
}

function getChatStorageKey(textbookId) {
  return `${CHAT_STORAGE_PREFIX}${textbookId}`;
}

function sanitizeStoredMessages(rawMessages, textbookTitle) {
  if (!Array.isArray(rawMessages) || rawMessages.length === 0) {
    return [createIntroMessage(textbookTitle)];
  }

  return rawMessages.map((message, index) => ({
    id: message.id || `${message.role || "assistant"}-${index}`,
    role: message.role === "user" ? "user" : "assistant",
    text: typeof message.text === "string" ? message.text : "",
    citations: Array.isArray(message.citations) ? message.citations : [],
  }));
}

export default function AskFlowstate() {
  const navigate = useNavigate();
  const location = useLocation();
  const { textbook_id, textbook_title } = location.state || {};

  const [customCovers] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(CUSTOM_COVERS_STORAGE_KEY) || "{}");
    } catch {
      return {};
    }
  });
  const [resolvedTextbookTitle, setResolvedTextbookTitle] = useState(textbook_title || "");
  const [messages, setMessages] = useState(() => [createIntroMessage(textbook_title)]);
  const [input, setInput] = useState("");
  const [isResponding, setIsResponding] = useState(false);
  const [isLoadingChatInfo, setIsLoadingChatInfo] = useState(Boolean(textbook_id));
  const [chatError, setChatError] = useState("");
  const [chatReady, setChatReady] = useState(true);
  const bottomRef = useRef(null);

  const selectedCover = textbook_id ? customCovers[textbook_id] : null;
  const hasConversation = messages.length > 1 || isResponding;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isResponding]);

  useEffect(() => {
    if (!textbook_id) {
      setIsLoadingChatInfo(false);
      return;
    }

    let active = true;

    async function loadChatInfo() {
      setIsLoadingChatInfo(true);
      setChatError("");

      const response = await authFetch(`${API_BASE}/api/textbooks/${textbook_id}/ask-flo`);

      if (response.status === 401) {
        navigate("/login");
        return;
      }

      const payload = await response.json().catch(() => ({}));
      if (!active) return;

      if (!response.ok) {
        setChatError(payload.error || "Could not load Ask Flo.");
        setChatReady(false);
        setIsLoadingChatInfo(false);
        return;
      }

      const nextTitle = payload.textbook_title || textbook_title || "";
      setResolvedTextbookTitle(nextTitle);
      setChatReady(Boolean(payload.can_chat));
      setChatError(
        payload.can_chat ? "" : "Ask Flo will be available once this textbook finishes processing."
      );

      try {
        const storedMessages = JSON.parse(
          localStorage.getItem(getChatStorageKey(textbook_id)) || "null"
        );
        setMessages(sanitizeStoredMessages(storedMessages, nextTitle));
      } catch {
        setMessages([createIntroMessage(nextTitle)]);
      }

      setIsLoadingChatInfo(false);
    }

    loadChatInfo().catch((error) => {
      console.error("Failed to load Ask Flo info:", error);
      if (!active) return;
      setChatError("Could not load Ask Flo.");
      setChatReady(false);
      setIsLoadingChatInfo(false);
    });

    return () => {
      active = false;
    };
  }, [navigate, textbook_id, textbook_title]);

  useEffect(() => {
    if (!textbook_id) return;

    try {
      localStorage.setItem(getChatStorageKey(textbook_id), JSON.stringify(messages));
    } catch {
      // Ignore local storage write failures.
    }
  }, [messages, textbook_id]);

  const handleSend = async () => {
    const nextQuestion = input.trim();
    if (!nextQuestion || isResponding || !textbook_id || !chatReady) return;

    const userMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      text: nextQuestion,
      citations: [],
    };

    setMessages((previous) => [...previous, userMessage]);
    setInput("");
    setIsResponding(true);
    setChatError("");

    try {
      const response = await authFetch(`${API_BASE}/api/textbooks/${textbook_id}/ask-flo/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: nextQuestion,
        }),
      });

      if (response.status === 401) {
        navigate("/login");
        return;
      }

      const payload = await response.json().catch(() => ({}));

      if (!response.ok) {
        const errorMessage = payload.error || "Flo could not answer that right now.";
        setChatError(errorMessage);
        setMessages((previous) => [
          ...previous,
          {
            id: `assistant-error-${Date.now()}`,
            role: "assistant",
            text: errorMessage,
            citations: [],
          },
        ]);
        return;
      }

      if (payload.textbook_title) {
        setResolvedTextbookTitle(payload.textbook_title);
      }

      setMessages((previous) => [
        ...previous,
        {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          text: payload.message || "I’m not sure this textbook clearly covers that.",
          citations: Array.isArray(payload.citations) ? payload.citations : [],
        },
      ]);
    } catch (error) {
      console.error("Ask Flo query failed:", error);
      setChatError("Flo could not answer that right now.");
      setMessages((previous) => [
        ...previous,
        {
          id: `assistant-error-${Date.now()}`,
          role: "assistant",
          text: "Flo could not answer that right now.",
          citations: [],
        },
      ]);
    } finally {
      setIsResponding(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      <NavBar isAuthed={true} />

      <main className="ask-page">
        <Container size="xl" className="ask-shell">
          {!textbook_id ? (
            <Stack gap="md" align="center" className="ask-empty">
              <IconMessageCircle2 size={34} stroke={1.8} />
              <Title order={3}>Select a textbook first</Title>
              <Text c="dimmed" ta="center">
                Open the dashboard, choose a textbook, and then launch Ask Flo from there.
              </Text>
              <Button onClick={() => navigate("/dashboard")}>Return to Dashboard</Button>
            </Stack>
          ) : (
            <>
              <div className="ask-page-header">
                <Group
                  align="center"
                  justify="space-between"
                  wrap="nowrap"
                  gap="xl"
                  className={`ask-header-row ${hasConversation ? "is-compact" : ""}`}
                >
                  <div className="ask-header-main">
                    <Group gap="sm" align="center">
                      <div className="ask-flo-iconWrap">
                        <FloMark className="ask-flo-icon" />
                      </div>
                      <div>
                        <Title order={1} className="ask-title">
                          Ask Flo
                        </Title>
                        <Text className="ask-subtitle">
                          Textbook-grounded AI tutor
                        </Text>
                      </div>
                    </Group>

                    <Group gap="sm" mt="md" className="ask-header-meta">
                      <Badge variant="white" color="blue">
                        Textbook-scoped
                      </Badge>
                      <Text className="ask-bookline">
                        Ask about concepts, definitions, examples, and explanations from{" "}
                        <span>{resolvedTextbookTitle || textbook_title || "your textbook"}</span>.
                      </Text>
                    </Group>
                  </div>

                  <div className="ask-mini-book">
                    <div className="ask-mini-book-art">
                      {selectedCover ? (
                        <img
                          src={selectedCover}
                          alt={textbook_title || "Textbook cover"}
                          className="ask-mini-book-cover"
                        />
                      ) : (
                        <img src={brain} alt="" className="ask-mini-book-fallback" />
                      )}
                    </div>

                    <Group gap="xs" className="ask-mini-book-meta">
                      <Text fw={700} size="sm">
                        {resolvedTextbookTitle || textbook_title}
                      </Text>
                    </Group>
                  </div>
                </Group>
              </div>

              <div className={`ask-chat-layout ${hasConversation ? "is-active" : "is-pristine"}`}>
                <div className="ask-messages">
                  {isLoadingChatInfo ? (
                    <div className="ask-status-row">
                      <Loader size="sm" />
                      <Text size="sm" c="dimmed">
                        Loading Ask Flo...
                      </Text>
                    </div>
                  ) : null}

                  {!isLoadingChatInfo && chatError ? (
                    <div className="ask-status-message">{chatError}</div>
                  ) : null}

                  {messages.map((message) => (
                    <div
                      key={message.id}
                      className={`ask-message ask-message-${message.role}`}
                    >
                      <div className="ask-message-label">
                        {message.role === "assistant" ? "Flo" : "You"}
                      </div>
                      <p>{message.text}</p>
                      {message.role === "assistant" && message.citations?.length ? (
                        <div className="ask-citations">
                          {message.citations.map((citation) => (
                            <span key={`${message.id}-${citation}`} className="ask-citation-chip">
                              {citation}
                            </span>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  ))}

                  {isResponding ? (
                    <div className="ask-message ask-message-assistant">
                      <div className="ask-message-label">Flo</div>
                      <p className="ask-typing">
                        <span />
                        <span />
                        <span />
                      </p>
                    </div>
                  ) : null}

                  <div ref={bottomRef} />
                </div>

                <div className="ask-input-wrap">
                  <Textarea
                    value={input}
                    onChange={(event) => setInput(event.currentTarget.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={
                      chatReady
                        ? "Ask something about this textbook..."
                        : "Ask Flo will unlock when this textbook is ready."
                    }
                    autosize
                    minRows={3}
                    maxRows={6}
                    disabled={isResponding || isLoadingChatInfo || !chatReady}
                    className="ask-input"
                  />

                  <Group justify="flex-end" align="center" mt="sm">
                    <Button
                      radius="xl"
                      rightSection={<IconArrowUp size={16} />}
                      onClick={handleSend}
                      disabled={!input.trim() || isResponding || isLoadingChatInfo || !chatReady}
                    >
                      Send
                    </Button>
                  </Group>
                </div>
              </div>
            </>
          )}
        </Container>
      </main>
    </>
  );
}
