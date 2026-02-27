import { useEffect, useState } from "react";
import { Container, Group, Title, Text, Paper, ActionIcon } from "@mantine/core";
import { IconInfoCircle, IconQuestionMark } from "@tabler/icons-react";
import NavBar from "../../components/NavBar";
import "./flash.css";

export default function Flash() {
  const [flipped, setFlipped] = useState(false);


  useEffect(() => {
    const onClick = (e) => {
      // If you click a link/button/input, don’t flip (helps with NavBar)
      const interactive = e.target.closest("a,button,input,textarea,select,label");
      if (interactive) return;
      setFlipped((f) => !f);
    };

    const onKeyDown = (e) => {
      if (e.key === " " || e.key === "Enter") {
        e.preventDefault();
        setFlipped((f) => !f);
      }
    };

    window.addEventListener("click", onClick);
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("click", onClick);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, []);

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

          {/* Card */}
          <Paper withBorder radius="lg" className="flipcard-outer">
            <div className={`flipcard ${flipped ? "is-flipped" : ""}`}>
              <div className="flipcard-face flipcard-front">
                  <Text fw={800} className="front-title">
                      Question
                  </Text>
                  <Text className="front-text">
                      Dummy text on the front of the flashcard.
                  </Text>
              </div>


              <div className="flipcard-face flipcard-back">
                <Text fw={800} className="back-title">
                  Answer
                </Text>
                <Text className="back-text">
                  Back of flashcard.
                </Text>
              </div>
            </div>
          </Paper>

          <Text ta="center" c="dimmed" mt="md" className="flip-hint">
            click anywhere to flip
          </Text>
        </Container>
      </main>
    </>
  );
}
