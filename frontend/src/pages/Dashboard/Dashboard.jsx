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

import NavBar from "../../components/NavBar";
import "./Dashboard.css";

export default function Dashboard() {
  const navigate = useNavigate();

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
                      data={[
                        { value: "bio101", label: "BIO101 — Intro Biology" },
                        { value: "chem2045", label: "CHM2045 — General Chemistry" },
                        { value: "cop4600", label: "COP4600 — Operating Systems" },
                        { value: "cis4301", label: "CIS4301 — Database Systems" },
                      ]}
                      defaultValue="bio101"
                      searchable
                      className="dashboard-textbook-select"
                      comboboxProps={{ withinPortal: true }}
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
                      placeholder="3"
                      data={["1", "2", "3", "4", "5"]}
                    />
                    <Select
                      label="Difficulty"
                      placeholder="5"
                      data={["1", "2", "3", "4", "5"]}
                    />
                  </SimpleGrid>

                  <Group gap="sm" className="dashboard-actions">
                    <Button radius="xl" fullWidth
                    onClick={() => navigate("/Summarize")}>
                      Summarize
                    </Button>

                    <Button
                      variant="light"
                      radius="xl"
                      fullWidth
                      onClick={() => navigate("/flash")}
                    >
                      Flashcards
                    </Button>

                    <Button radius="xl" fullWidth
                    onClick={() => navigate("/quiz")}>


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
