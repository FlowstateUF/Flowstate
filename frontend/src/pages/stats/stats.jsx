import {
  Container,
  Paper,
  Group,
  Stack,
  Title,
  Text,
  SimpleGrid,
  ThemeIcon,
  ActionIcon,
  Divider,
  Table,
  Pagination,
  Badge,
  Box,
} from "@mantine/core";
import {
  IconClipboard,
  IconCheck,
  IconMoodSad,
  IconBook,
  IconSettings,
} from "@tabler/icons-react";

import NavBar from "../../components/NavBar";
import "./stats.css";

function StatCard({ title, value, icon, dark }) {
  return (
    <Paper
      withBorder
      radius="md"
      p="lg"
      className={`stats-kpi ${dark ? "stats-kpi-dark" : ""}`}
    >
      <Group justify="space-between" align="flex-start">
        <Stack gap={6}>
          <Text fw={700} size="sm" className={dark ? "stats-text-light" : ""}>
            {title}
          </Text>
          <Text fw={800} size="xl" className={dark ? "stats-text-light" : ""}>
            {value}
          </Text>
        </Stack>

        <ThemeIcon
          variant={dark ? "filled" : "light"}
          radius="md"
          size="lg"
          className={dark ? "stats-icon-dark" : ""}
        >
          {icon}
        </ThemeIcon>
      </Group>
    </Paper>
  );
}

function ActivityChart() {
  // Simple grouped bars per month (placeholder data)
  const months = ["Jan", "Feb", "Mar", "Apr", "May"];
  const series = [
    { label: "Q/A", values: [7, 3, 8, 3, 2] },
    { label: "Flashcards", values: [4, 12, 5, 10, 5] },
    { label: "Quiz", values: [6, 8, 3, 11, 0] },
    { label: "Games", values: [2, 5, 1, 7, 9] },
  ];

  // Draw simple SVG bars (no external deps)
  const W = 760;
  const H = 220;
  const padding = 40;
  const max = Math.max(...series.flatMap((s) => s.values));

  const groupCount = months.length;
  const barsPerGroup = series.length;
  const groupGap = 28;
  const barGap = 6;

  const groupWidth =
    (W - padding * 2 - groupGap * (groupCount - 1)) / groupCount;
  const barWidth = (groupWidth - barGap * (barsPerGroup - 1)) / barsPerGroup;

  return (
    <Box className="stats-chart-wrap">
      <Group justify="space-between" align="center" mb="sm">
        <Text fw={700}>Study Activity</Text>
        <ActionIcon variant="light" radius="md" aria-label="Settings">
          <IconSettings size={18} />
        </ActionIcon>
      </Group>

      <Group gap="xl" className="stats-legend" mb="sm">
        {series.map((s, idx) => (
          <Group key={s.label} gap={8}>
            <span className={`stats-dot stats-dot-${idx}`} />
            <Text size="xs" c="dimmed">
              {s.label}
            </Text>
          </Group>
        ))}
      </Group>

      <div className="stats-svg-scroll">
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="220">
          {/* bars */}
          {months.map((m, gi) => {
            const gx = padding + gi * (groupWidth + groupGap);
            return (
              <g key={m}>
                {/* month label */}
                <text
                  x={gx + groupWidth / 2}
                  y={H - 10}
                  textAnchor="middle"
                  fontSize="12"
                  fill="#7a7a7a"
                >
                  {m}
                </text>

                {series.map((s, bi) => {
                  const v = s.values[gi];
                  const barH = (v / max) * (H - 70);
                  const x = gx + bi * (barWidth + barGap);
                  const y = H - 30 - barH;

                  return (
                    <rect
                      key={s.label}
                      x={x}
                      y={y}
                      width={barWidth}
                      height={barH}
                      rx="4"
                      className={`stats-bar stats-bar-${bi}`}
                    />
                  );
                })}
              </g>
            );
          })}
        </svg>
      </div>
    </Box>
  );
}

function DonutChart() {
  // Simple donut segments (placeholder %)
  const parts = [
    { label: "Sorting", value: 35 },
    { label: "Structures", value: 25 },
    { label: "Dynamic Prog", value: 20 },
    { label: "Graphs", value: 20 },
  ];

  const r = 70;
  const cx = 90;
  const cy = 90;
  const circ = 2 * Math.PI * r;

  let offset = 0;

  return (
    <Box>
      <Group justify="space-between" align="center" mb="sm">
        <Text fw={700} ta="center" style={{ flex: 1 }}>
          Data Structures and Algorithms
          <br />
          Mastery Progression
        </Text>
      </Group>

      <Group justify="center" gap="md" mb="sm" className="stats-donut-legend">
        {parts.slice(0, 3).map((p, idx) => (
          <Group key={p.label} gap={8}>
            <span className={`stats-dot stats-dot-${idx}`} />
            <Text size="xs" c="dimmed">
              {p.label}
            </Text>
          </Group>
        ))}
      </Group>

      <Group justify="center">
        <svg width="180" height="180" viewBox="0 0 180 180">
          {/* background ring */}
          <circle
            cx={cx}
            cy={cy}
            r={r}
            fill="none"
            stroke="#e9ecef"
            strokeWidth="18"
          />
          {/* segments */}
          {parts.map((p, idx) => {
            const dash = (p.value / 100) * circ;
            const gap = circ - dash;
            const el = (
              <circle
                key={p.label}
                cx={cx}
                cy={cy}
                r={r}
                fill="none"
                strokeWidth="18"
                strokeLinecap="butt"
                strokeDasharray={`${dash} ${gap}`}
                strokeDashoffset={-offset}
                className={`stats-donut stats-donut-${idx}`}
              />
            );
            offset += dash;
            return el;
          })}
          {/* hole */}
          <circle cx={cx} cy={cy} r="45" fill="white" />
        </svg>
      </Group>
    </Box>
  );
}

export default function Stats() {
  const rows = [
    {
      title: "DSA Chapter 4",
      date: "13 Feb, 2026 : 10:10 AM",
      time: "2 hours",
      confidence: "High",
      finished: "Yes",
    },
    {
      title: "DSA Chapter 3",
      date: "31 Jan, 2026 : 3:12 PM",
      time: "30 mins",
      confidence: "Low",
      finished: "No",
    },
    {
      title: "DSA Chapter 2",
      date: "20 Jan, 2026 : 2:15 PM",
      time: "1 hour",
      confidence: "Medium",
      finished: "Yes",
    },
    {
      title: "DSA Chapter 1",
      date: "10 Jan, 2026 : 1:15 PM",
      time: "1 hour",
      confidence: "Medium",
      finished: "Yes",
    },
  ];

  const confidenceColor = (c) => {
    if (c === "High") return "green";
    if (c === "Medium") return "yellow";
    return "red";
  };

  return (
    <>
      <NavBar isAuthed={true} />

      <main className="stats-page">
        <Container size="xl">
          <Stack gap="xl">
            {/* KPI row */}
            <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="lg">
              <StatCard
                title="Total Study Points"
                value="21 324"
                icon={<IconClipboard size={18} />}
                dark
              />
              <StatCard
                title="Strengths"
                value="Arrays"
                icon={<IconCheck size={18} />}
              />
              <StatCard
                title="Weaknesses"
                value="Linked Lists"
                icon={<IconMoodSad size={18} />}
              />
              <StatCard
                title="Recommended Topic to Study"
                value="Linked Lists"
                icon={<IconBook size={18} />}
              />
            </SimpleGrid>

            {/* Charts row */}
            <SimpleGrid cols={{ base: 1, lg: 3 }} spacing="lg">
              <Paper withBorder radius="md" p="lg" className="stats-card lg-span-2">
                <ActivityChart />
              </Paper>

              <Paper withBorder radius="md" p="lg" className="stats-card">
                <DonutChart />
              </Paper>
            </SimpleGrid>

            {/* Table */}
            <Paper withBorder radius="md" p="lg" className="stats-card">
              <Group justify="space-between" align="center" mb="sm">
                <Text fw={800}>Recent Study Sessions</Text>
                <ActionIcon variant="light" radius="md" aria-label="Settings">
                  <IconSettings size={18} />
                </ActionIcon>
              </Group>

              <Divider mb="md" />

              <Table striped highlightOnHover withRowBorders={false}>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Title</Table.Th>
                    <Table.Th>Date</Table.Th>
                    <Table.Th>Time Studied</Table.Th>
                    <Table.Th>Confidence Rating</Table.Th>
                    <Table.Th>Finished?</Table.Th>
                    <Table.Th />
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>

                <Table.Tbody>
                  {rows.map((r) => (
                    <Table.Tr key={r.title}>
                      <Table.Td>
                        <Text fw={600}>{r.title}</Text>
                      </Table.Td>
                      <Table.Td>{r.date}</Table.Td>
                      <Table.Td>{r.time}</Table.Td>
                      <Table.Td>
                        <Badge color={confidenceColor(r.confidence)} variant="light">
                          {r.confidence}
                        </Badge>
                      </Table.Td>
                      <Table.Td>{r.finished}</Table.Td>
                      <Table.Td className="stats-link">Options</Table.Td>
                      <Table.Td className="stats-link">Details</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>

              <Group justify="center" mt="lg">
                <Pagination total={20} defaultValue={2} radius="md" />
              </Group>
            </Paper>
          </Stack>
        </Container>
      </main>
    </>
  );
}
