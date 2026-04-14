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
import raindrop from "../../assets/raindrop.png";
import { authFetch } from "../../utils/authFetch";
import "./AskFlowstate.css";

const API_BASE = "http://127.0.0.1:5001";
const CUSTOM_COVERS_STORAGE_KEY = "customTextbookCovers";
const CHAT_STORAGE_PREFIX = "askFloChat:";

function createIntroMessage(textbookTitle) {
  return {
    id: "intro",
    role: "assistant",
    citations: [],
    blocks: [],
    text: textbookTitle
      ? `I’m Flo. Ask me about ${textbookTitle}, and I’ll stay focused on the content from that textbook.`
      : "I’m Flo. Ask me about your textbook, and I’ll stay focused on the content from that book.",
  };
}

function getChatStorageKey(textbookId) {
  return `${CHAT_STORAGE_PREFIX}${textbookId}`;
}

function normalizeCitations(rawCitations) {
  if (!Array.isArray(rawCitations)) return [];

  return [...new Set(
    rawCitations.filter((citation) => typeof citation === "string" && citation.trim())
      .map((citation) => citation.trim())
  )];
}

function normalizeAnswerBlocks(rawBlocks, citations) {
  if (!Array.isArray(rawBlocks)) return [];

  const allowedTypes = new Set(["paragraph", "bullet", "heading"]);
  const citationSet = new Set(citations);

  return rawBlocks
    .filter((block) => block && typeof block === "object")
    .map((block) => {
      const type = allowedTypes.has(block.type) ? block.type : "paragraph";
      const text = typeof block.text === "string" ? block.text.trim() : "";
      const blockCitations = normalizeCitations(block.citations).filter((citation) => citationSet.has(citation));

      return {
        type,
        text,
        citations: blockCitations,
      };
    })
    .filter((block) => block.text);
}

function sanitizeStoredMessages(rawMessages, textbookTitle) {
  if (!Array.isArray(rawMessages) || rawMessages.length === 0) {
    return [createIntroMessage(textbookTitle)];
  }

  return rawMessages.map((message, index) => {
    const citations = normalizeCitations([
      ...(Array.isArray(message.citations) ? message.citations : []),
      ...(Array.isArray(message.blocks)
        ? message.blocks.flatMap((block) => (Array.isArray(block?.citations) ? block.citations : []))
        : []),
    ]);

    return {
      id: message.id || `${message.role || "assistant"}-${index}`,
      role: message.role === "user" ? "user" : "assistant",
      text: typeof message.text === "string" ? message.text : "",
      citations,
      blocks: normalizeAnswerBlocks(message.blocks, citations),
    };
  });
}

function buildAssistantMessage(id, text, rawCitations = [], rawBlocks = []) {
  const citations = normalizeCitations([
    ...(Array.isArray(rawCitations) ? rawCitations : []),
    ...(Array.isArray(rawBlocks)
      ? rawBlocks.flatMap((block) => (Array.isArray(block?.citations) ? block.citations : []))
      : []),
  ]);

  return {
    id,
    role: "assistant",
    text,
    citations,
    blocks: normalizeAnswerBlocks(rawBlocks, citations),
  };
}

function isHeading(line) {
  return /^\s{0,3}#{1,3}\s+/.test(line);
}

// Keeps a short window of chat so follow-ups make more sense.
function getMessageHistory(messages, limit = 6) {
  return messages
    .filter((message) => message.id !== "intro")
    .slice(-limit)
    .map((message) => ({
      role: message.role,
      text: message.text,
    }));
}

function buildCitationIndexMap(citations) {
  const indexMap = new Map();
  citations.forEach((citation, index) => {
    indexMap.set(citation, index + 1);
  });
  return indexMap;
}

// Shows tiny source markers that match the citation chips below.
function renderCitationMarkers(citations, citationIndexMap) {
  const indexes = [...new Set(
    (citations || [])
      .map((citation) => citationIndexMap.get(citation))
      .filter(Boolean)
  )];
  if (!indexes.length) return null;

  return (
    <sup className="ask-inline-citations" aria-label="Sources used in this answer">
      {indexes.map((index) => (
        <span key={`inline-citation-${index}`} className="ask-inline-citation">
          [{index}]
        </span>
      ))}
    </sup>
  );
}

function renderInlineMarkdown(text, keyPrefix) {
  const matches = [...(text || "").matchAll(/(\*\*([^*]+)\*\*|`([^`]+)`)/g)];
  if (!matches.length) return text;

  const parts = [];
  let cursor = 0;

  matches.forEach((match, index) => {
    const [fullMatch, , boldText, codeText] = match;
    const matchIndex = match.index ?? 0;

    if (matchIndex > cursor) {
      parts.push(text.slice(cursor, matchIndex));
    }

    if (boldText) {
      parts.push(
        <strong key={`${keyPrefix}-strong-${index}`}>
          {boldText}
        </strong>
      );
    } else if (codeText) {
      parts.push(
        <code key={`${keyPrefix}-code-${index}`}>
          {codeText}
        </code>
      );
    } else {
      parts.push(fullMatch);
    }

    cursor = matchIndex + fullMatch.length;
  });

  if (cursor < text.length) {
    parts.push(text.slice(cursor));
  }

  return parts;
}

function renderAssistantBlocks(blocks, citationIndexMap) {
  const renderedBlocks = [];
  let bulletRun = [];

  const flushBulletRun = () => {
    if (!bulletRun.length) return;

    renderedBlocks.push(
      <ul key={`bullet-run-${renderedBlocks.length}`}>
        {bulletRun.map((block, index) => (
          <li key={`bullet-${renderedBlocks.length}-${index}`}>
            {renderInlineMarkdown(block.text, `bullet-${renderedBlocks.length}-${index}`)}
            {renderCitationMarkers(block.citations, citationIndexMap)}
          </li>
        ))}
      </ul>
    );

    bulletRun = [];
  };

  blocks.forEach((block, index) => {
    if (block.type === "bullet") {
      bulletRun.push(block);
      return;
    }

    flushBulletRun();

    if (block.type === "heading") {
      renderedBlocks.push(
        <h4 key={`heading-${index}`} className="ask-message-heading">
          {renderInlineMarkdown(block.text, `heading-${index}`)}
          {renderCitationMarkers(block.citations, citationIndexMap)}
        </h4>
      );
      return;
    }

    renderedBlocks.push(
      <p key={`paragraph-${index}`}>
        {renderInlineMarkdown(block.text, `paragraph-${index}`)}
        {renderCitationMarkers(block.citations, citationIndexMap)}
      </p>
    );
  });

  flushBulletRun();
  return renderedBlocks;
}

function renderAssistantText(text, citations, citationIndexMap) {
  const lines = (text || "").split(/\r?\n/);
  const blocks = [];
  let index = 0;

  const isBullet = (line) => /^\s*[-*]\s+/.test(line);
  const isNumbered = (line) => /^\s*\d+\.\s+/.test(line);
  const isListLine = (line) => isBullet(line) || isNumbered(line);

  while (index < lines.length) {
    const line = lines[index].trim();

    if (!line) {
      index += 1;
      continue;
    }

    if (isHeading(line)) {
      const headingText = line.replace(/^\s{0,3}#{1,3}\s+/, "");
      blocks.push(
        <h4 key={`heading-${blocks.length}`} className="ask-message-heading">
          {renderInlineMarkdown(headingText, `heading-${blocks.length}`)}
        </h4>
      );
      index += 1;
      continue;
    }

    if (isListLine(line)) {
      const ordered = isNumbered(line);
      const items = [];

      while (index < lines.length) {
        const listLine = lines[index].trim();
        if (!listLine || !isListLine(listLine) || isNumbered(listLine) !== ordered) {
          break;
        }

        const content = listLine.replace(/^\s*(?:[-*]|\d+\.)\s+/, "");
        items.push(content);
        index += 1;
      }

      const ListTag = ordered ? "ol" : "ul";
      blocks.push(
        <ListTag key={`list-${blocks.length}`}>
          {items.map((item, itemIndex) => (
            <li key={`item-${itemIndex}`}>
              {renderInlineMarkdown(item, `list-${blocks.length}-${itemIndex}`)}
            </li>
          ))}
        </ListTag>
      );
      continue;
    }

    const paragraphLines = [];
    while (index < lines.length) {
      const paragraphLine = lines[index].trim();
      if (!paragraphLine || isListLine(paragraphLine) || isHeading(paragraphLine)) {
        break;
      }
      paragraphLines.push(paragraphLine);
      index += 1;
    }

    const paragraphText = paragraphLines.join(" ");
    blocks.push(
      <p key={`paragraph-${blocks.length}`}>
        {renderInlineMarkdown(paragraphText, `paragraph-${blocks.length}`)}
      </p>
    );
  }

  if (!blocks.length) {
    return [
      <p key="paragraph-empty">
        {renderInlineMarkdown(text || "", "paragraph-empty")}
        {renderCitationMarkers(citations, citationIndexMap)}
      </p>,
    ];
  }

  const lastBlock = blocks[blocks.length - 1];
  blocks[blocks.length - 1] = (
    <div key="assistant-message-last-block" className="ask-message-lastBlock">
      {lastBlock}
      {renderCitationMarkers(citations, citationIndexMap)}
    </div>
  );

  return blocks;
}

function renderAssistantMessage(message) {
  const citations = normalizeCitations(message.citations);
  const blocks = normalizeAnswerBlocks(message.blocks, citations);
  const citationIndexMap = buildCitationIndexMap(citations);

  if (blocks.length) {
    return renderAssistantBlocks(blocks, citationIndexMap);
  }

  return renderAssistantText(message.text, citations, citationIndexMap);
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
      blocks: [],
    };

    setMessages((previous) => [...previous, userMessage]);
    setInput("");
    setIsResponding(true);
    setChatError("");

    try {
      const messageHistory = getMessageHistory(messages);
      const response = await authFetch(`${API_BASE}/api/textbooks/${textbook_id}/ask-flo/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: nextQuestion,
          history: messageHistory,
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
          buildAssistantMessage(`assistant-error-${Date.now()}`, errorMessage),
        ]);
        return;
      }

      if (payload.textbook_title) {
        setResolvedTextbookTitle(payload.textbook_title);
      }

      setMessages((previous) => [
        ...previous,
        buildAssistantMessage(
          `assistant-${Date.now()}`,
          payload.message || "I’m not sure this textbook clearly covers that.",
          payload.citations,
          payload.answer_blocks
        ),
      ]);
    } catch (error) {
      console.error("Ask Flo query failed:", error);
      setChatError("Flo could not answer that right now.");
      setMessages((previous) => [
        ...previous,
        buildAssistantMessage(`assistant-error-${Date.now()}`, "Flo could not answer that right now."),
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
                        <img src={raindrop} alt="" className="ask-flo-icon" />
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
                      {message.role === "assistant" ? (
                        <div className="ask-message-content">
                          {renderAssistantMessage(message)}
                        </div>
                      ) : (
                        <p>{message.text}</p>
                      )}
                      {message.role === "assistant" && message.citations?.length ? (
                        <div className="ask-citations">
                          {message.citations.map((citation, index) => (
                            <span key={`${message.id}-${citation}`} className="ask-citation-chip">
                              <span className="ask-citation-index">{index + 1}</span>
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
