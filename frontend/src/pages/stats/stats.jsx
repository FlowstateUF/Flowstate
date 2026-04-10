import {
  Container,
  Paper,
  Group,
  Stack,
  Title,
  Text,
  SimpleGrid,
  ThemeIcon,
  Divider,
  Table,
  Badge,
  Box,
  Loader,
  SegmentedControl,
  Tooltip,
} from "@mantine/core";
import {
  IconClipboard,
  IconCheck,
  IconMoodSad,
  IconFlame,
} from "@tabler/icons-react";
import { useLocation, useNavigate } from "react-router-dom";
import { useState, useEffect, useMemo } from "react";

import NavBar from "../../components/NavBar";
import "./stats.css";

const API_BASE = "http://127.0.0.1:5001";

function formatDurationSeconds(sec) {
  const s = Math.max(0, Number(sec) || 0);
  if (s < 3600) {
    const m = Math.floor(s / 60);
    const r = s % 60;
    return m ? `${m}m ${r}s` : `${r}s`;
  }
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return m ? `${h}h ${m}m` : `${h}h`;
}

function formatSessionAt(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return "—";
  }
}

function kindLabel(kind) {
  if (kind === "quiz") return "Quiz";
  if (kind === "flashcards") return "Flashcards";
  if (kind === "summary") return "Summary";
  return kind || "—";
}

function kindBadgeColor(kind) {
  if (kind === "quiz") return "blue";
  if (kind === "flashcards") return "violet";
  if (kind === "summary") return "teal";
  return "gray";
}

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

function ActivityChart({ activity, loading }) {
  const months = activity?.day_labels || [];
  const series = activity?.series || [];

  const W = 760;
  const H = 220;
  const padding = 40;
  const allVals = series.flatMap((s) => s.values || []);
  const max = Math.max(1, ...allVals);

  const groupCount = months.length || 7;
  const barsPerGroup = series.length || 3;
  const groupGap = 22;
  const barGap = 6;

  const groupWidth =
    (W - padding * 2 - groupGap * Math.max(0, groupCount - 1)) /
    Math.max(1, groupCount);
  const barWidth =
    (groupWidth - barGap * Math.max(0, barsPerGroup - 1)) /
    Math.max(1, barsPerGroup);

  if (loading) {
    return (
      <Box className="stats-chart-wrap">
        <Text fw={700} mb="md">
          Study activity
        </Text>
        <Group justify="center" py="xl">
          <Loader size="sm" />
        </Group>
      </Box>
    );
  }

  return (
    <Box className="stats-chart-wrap">
      <Text fw={700} mb="xs">
        Study activity
      </Text>
      <Text c="dimmed" size="xs" mb="sm">
        Sessions in the last 7 days
      </Text>

      <Group gap="xl" className="stats-legend" mb="sm">
        {series.map((s, idx) => (
          <Group key={s.key || s.label} gap={8}>
            <span className={`stats-dot stats-dot-${idx % 4}`} />
            <Text size="xs" c="dimmed">
              {s.label}
            </Text>
          </Group>
        ))}
      </Group>

      <div className="stats-svg-scroll">
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="220">
          {months.map((m, gi) => {
            const gx = padding + gi * (groupWidth + groupGap);
            return (
              <g key={m}>
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
                  const v = (s.values && s.values[gi]) || 0;
                  const barH = (v / max) * (H - 70);
                  const x = gx + bi * (barWidth + barGap);
                  const y = H - 30 - barH;
                  return (
                    <rect
                      key={`${s.key}-${bi}`}
                      x={x}
                      y={y}
                      width={barWidth}
                      height={Math.max(0, barH)}
                      rx="4"
                      className={`stats-bar stats-bar-${bi % 4}`}
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

function heatLevel(count, max) {
  if (!count) return 0;
  const t = count / max;
  if (t <= 0.25) return 1;
  if (t <= 0.5) return 2;
  if (t <= 0.75) return 3;
  return 4;
}

/** GitHub-style: columns = weeks, rows = Mon–Sun (top to bottom) */
function buildWeekColumns(days) {
  if (!days?.length) return { columns: [], maxCount: 0 };
  const maxCount = Math.max(1, ...days.map((d) => d.total || 0));
  const cells = [];
  const first = new Date(`${days[0].date}T12:00:00Z`);
  const dowMon0 = (first.getUTCDay() + 6) % 7;
  for (let i = 0; i < dowMon0; i++) cells.push(null);
  for (const d of days) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);
  const columns = [];
  for (let c = 0; c < cells.length / 7; c++) {
    const col = [];
    for (let r = 0; r < 7; r++) col.push(cells[c * 7 + r]);
    columns.push(col);
  }
  return { columns, maxCount };
}

function aggregateWeeksFromColumns(columns) {
  const weeks = columns.map((col) => {
    let t = 0;
    for (const cell of col) {
      if (cell) t += cell.total || 0;
    }
    return t;
  });
  const maxCount = Math.max(1, ...weeks);
  return { weeks, maxCount };
}

function aggregateMonths(days) {
  const map = new Map();
  for (const d of days) {
    const key = d.date.slice(0, 7);
    map.set(key, (map.get(key) || 0) + (d.total || 0));
  }
  const sorted = [...map.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  const last12 = sorted.slice(-12);
  const maxCount = Math.max(1, ...last12.map(([, v]) => v));
  return { months: last12, maxCount };
}

function StudyHeatmap({ days, mode }) {
  const { columns, maxCount: maxD } = useMemo(() => buildWeekColumns(days || []), [days]);
  const { weeks, maxCount: maxW } = useMemo(
    () => aggregateWeeksFromColumns(columns),
    [columns]
  );
  const { months, maxCount: maxM } = useMemo(
    () => aggregateMonths(days || []),
    [days]
  );

  const rowLabels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  if (mode === "week") {
    return (
      <Box className="stats-heatmap-week-wrap">
        <Group gap={4} wrap="nowrap" className="stats-heatmap-week-row">
          {weeks.map((cnt, i) => (
            <Tooltip key={i} label={`${cnt} session(s) this week`} withArrow>
              <div
                className={`stats-heat-cell stats-heat-w stats-heat-l${heatLevel(cnt, maxW)}`}
              />
            </Tooltip>
          ))}
        </Group>
        <Text size="xs" c="dimmed" mt="xs">
          Each column is one week (most recent on the right)
        </Text>
      </Box>
    );
  }

  if (mode === "month") {
    return (
      <Box>
        <Group gap="sm" wrap="wrap" justify="flex-start">
          {months.map(([ym, cnt]) => (
            <Tooltip key={ym} label={`${ym}: ${cnt} session(s)`} withArrow>
              <div className="stats-month-cell">
                <div
                  className={`stats-heat-cell stats-heat-m stats-heat-l${heatLevel(cnt, maxM)}`}
                />
                <Text size="10px" c="dimmed" ta="center" mt={4}>
                  {ym.slice(5)}
                </Text>
              </div>
            </Tooltip>
          ))}
        </Group>
        <Text size="xs" c="dimmed" mt="sm">
          Last 12 months with activity (calendar month totals)
        </Text>
      </Box>
    );
  }

  /* daily — GitHub grid */
  return (
    <Box className="stats-heatmap-daily">
      <Group gap={6} align="flex-start" wrap="nowrap" className="stats-heatmap-scroll">
        <Stack gap={4} className="stats-heatmap-dow" justify="flex-start">
          {rowLabels.map((lb) => (
            <Text key={lb} size="10px" c="dimmed" className="stats-heatmap-dow-label">
              {lb}
            </Text>
          ))}
        </Stack>
        <Group gap={3} wrap="nowrap" className="stats-heatmap-cols">
          {columns.map((col, ci) => (
            <Stack key={ci} gap={3}>
              {col.map((cell, ri) => (
                <Tooltip
                  key={ri}
                  label={
                    cell
                      ? `${cell.date}: ${cell.total} session(s)`
                      : "No data"
                  }
                  disabled={!cell}
                  withArrow
                >
                  <div
                    className={`stats-heat-cell stats-heat-d stats-heat-l${
                      cell ? heatLevel(cell.total || 0, maxD) : 0
                    } ${!cell ? "stats-heat-empty" : ""}`}
                  />
                </Tooltip>
              ))}
            </Stack>
          ))}
        </Group>
      </Group>
      <Group gap="md" mt="md" className="stats-heatmap-legend">
        <Text size="xs" c="dimmed">
          Less
        </Text>
        {[0, 1, 2, 3, 4].map((lv) => (
          <div key={lv} className={`stats-heat-cell stats-heat-d stats-heat-l${lv}`} />
        ))}
        <Text size="xs" c="dimmed">
          More
        </Text>
      </Group>
    </Box>
  );
}

function ChapterMasteryDonut({ chapters, chapterOrder }) {
  const ordered = useMemo(() => {
    const rows = [...(chapters || [])];
    if (!chapterOrder?.length) return rows.filter((c) => c.quizzes_with_attempts > 0).slice(0, 5);
    const rank = (id) => {
      const i = chapterOrder.indexOf(id);
      return i === -1 ? 9999 : i;
    };
    return [...rows]
      .sort((a, b) => rank(a.chapter_id) - rank(b.chapter_id))
      .filter((c) => c.quizzes_with_attempts > 0)
      .slice(0, 5);
  }, [chapters, chapterOrder]);

  const parts = useMemo(() => {
    if (!ordered.length) return [];
    const sum = ordered.reduce((s, p) => s + p.quiz_mastery_percent, 0) || 1;
    return ordered.map((p) => ({
      label: p.title.length > 22 ? `${p.title.slice(0, 20)}…` : p.title,
      frac: p.quiz_mastery_percent / sum,
      raw: p.quiz_mastery_percent,
    }));
  }, [ordered]);

  const r = 70;
  const cx = 90;
  const cy = 90;
  const circ = 2 * Math.PI * r;
  let offset = 0;

  if (!parts.length) {
    return (
      <Box>
        <Text fw={700} ta="center" mb="sm">
          Chapter quiz mastery
        </Text>
        <Text c="dimmed" size="sm" ta="center">
          Take chapter quizzes to see mastery split here.
        </Text>
      </Box>
    );
  }

  return (
    <Box>
      <Text fw={700} ta="center" mb="sm">
        Chapter quiz mastery
      </Text>
      <Text c="dimmed" size="xs" ta="center" mb="sm">
        Share of total mastery (up to 5 chapters with attempts)
      </Text>
      <Group justify="center" gap="md" mb="sm" className="stats-donut-legend" wrap="wrap">
        {parts.map((p, idx) => (
          <Group key={p.label} gap={8}>
            <span className={`stats-dot stats-dot-${idx % 4}`} />
            <Text size="xs" c="dimmed">
              {p.label} ({p.raw}%)
            </Text>
          </Group>
        ))}
      </Group>
      <Group justify="center">
        <svg width="180" height="180" viewBox="0 0 180 180">
          <circle
            cx={cx}
            cy={cy}
            r={r}
            fill="none"
            stroke="#e9ecef"
            strokeWidth="18"
          />
          {parts.map((p, idx) => {
            const dash = p.frac * circ;
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
                className={`stats-donut stats-donut-${idx % 4}`}
              />
            );
            offset += dash;
            return el;
          })}
          <circle cx={cx} cy={cy} r="45" fill="white" />
        </svg>
      </Group>
    </Box>
  );
}

export default function Stats() {
  const location = useLocation();
  const navigate = useNavigate();
  const stateTextbookId = location.state?.textbook_id;

  const [textbookId, setTextbookId] = useState(stateTextbookId || null);
  const [textbookLabel, setTextbookLabel] = useState(
    location.state?.textbook_label || ""
  );
  const [chapters, setChapters] = useState([]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [heatmapMode, setHeatmapMode] = useState("day");

  useEffect(() => {
    let cancelled = false;

    async function resolveTextbook() {
      const token = localStorage.getItem("access_token");
      if (!token) {
        setLoading(false);
        return;
      }

      let tid = stateTextbookId;
      if (!tid) {
        try {
          const res = await fetch(`${API_BASE}/api/textbooks`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          const j = await res.json();
          if (res.ok && j.textbooks?.length) {
            tid = j.textbooks[0].id;
            if (!cancelled) {
              setTextbookLabel(
                j.textbooks[0].display_title || j.textbooks[0].title || ""
              );
            }
          }
        } catch {
          /* ignore */
        }
      }

      if (!cancelled) setTextbookId(tid);
    }

    resolveTextbook();
    return () => {
      cancelled = true;
    };
  }, [stateTextbookId]);

  useEffect(() => {
    if (!textbookId) {
      setData(null);
      setLoading(false);
      return;
    }

    const token = localStorage.getItem("access_token");
    if (!token) {
      setLoading(false);
      return;
    }

    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const [dashRes, chRes] = await Promise.all([
          fetch(
            `${API_BASE}/api/textbooks/${textbookId}/dashboard?recent_limit=100`,
            { headers: { Authorization: `Bearer ${token}` } }
          ),
          fetch(`${API_BASE}/api/textbooks/${textbookId}/chapters`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ]);

        const dashJson = await dashRes.json();
        const chJson = await chRes.json();

        if (!cancelled) {
          if (dashRes.ok) setData(dashJson);
          else setData(null);
          if (chRes.ok) setChapters(chJson.chapters || []);
        }
      } catch {
        if (!cancelled) setData(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [textbookId]);

  const chapterOrder = useMemo(
    () => (chapters || []).map((c) => c.id),
    [chapters]
  );

  const masteryRows = useMemo(() => {
    const rows = data?.mastery?.chapters || [];
    if (!chapterOrder.length) return rows;
    const rank = (id) => {
      const i = chapterOrder.indexOf(id);
      return i === -1 ? 9999 : i;
    };
    return [...rows].sort((a, b) => rank(a.chapter_id) - rank(b.chapter_id));
  }, [data, chapterOrder]);

  const heatmapDays = data?.heatmap?.days || [];

  const weakest = data?.mastery?.weakest_chapter;
  const strongest = data?.mastery?.strongest_chapter;

  if (!textbookId && !loading) {
    return (
      <>
        <NavBar isAuthed={true} />
        <main className="stats-page">
          <Container size="xl">
            <Paper withBorder p="xl" radius="md">
              <Title order={3}>Stats</Title>
              <Text c="dimmed" mt="sm">
                No textbook selected. Open stats from the dashboard after choosing a textbook, or upload
                one from Courses.
              </Text>
              <Group mt="md">
                <Text
                  c="blue"
                  style={{ cursor: "pointer" }}
                  onClick={() => navigate("/dashboard")}
                >
                  Go to Dashboard
                </Text>
              </Group>
            </Paper>
          </Container>
        </main>
      </>
    );
  }

  return (
    <>
      <NavBar isAuthed={true} />

      <main className="stats-page">
        <Container size="xl">
          <Stack gap="xl">
            <Group justify="space-between" align="flex-start" wrap="wrap">
              <Box>
                <Title order={2}>Learning stats</Title>
                <Text c="dimmed" size="sm" mt={4}>
                  {textbookLabel || "Your textbook"}
                </Text>
              </Box>
            </Group>

            {loading ? (
              <Group justify="center" py="xl">
                <Loader />
              </Group>
            ) : !data ? (
              <Text c="red">Could not load stats for this textbook.</Text>
            ) : (
              <>
                <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="lg">
                  <StatCard
                    title="Total study time"
                    value={formatDurationSeconds(data.study?.total_study_seconds)}
                    icon={<IconClipboard size={18} />}
                    dark
                  />
                  <StatCard
                    title="Current streak"
                    value={`${data.study?.streak_current_days ?? 0} days`}
                    icon={<IconFlame size={18} />}
                  />
                  <StatCard
                    title="Strongest chapter (quiz)"
                    value={strongest?.title || "—"}
                    icon={<IconCheck size={18} />}
                  />
                  <StatCard
                    title="Needs practice (quiz)"
                    value={weakest?.title || "—"}
                    icon={<IconMoodSad size={18} />}
                  />
                </SimpleGrid>

                <Paper withBorder radius="md" p="lg" className="stats-card">
                  <Group justify="space-between" align="center" mb="md" wrap="wrap">
                    <Text fw={700}>Study heatmap</Text>
                    <SegmentedControl
                      value={heatmapMode}
                      onChange={setHeatmapMode}
                      data={[
                        { label: "Daily", value: "day" },
                        { label: "Weekly", value: "week" },
                        { label: "Monthly", value: "month" },
                      ]}
                      size="xs"
                    />
                  </Group>
                  <StudyHeatmap days={heatmapDays} mode={heatmapMode} />
                </Paper>

                <SimpleGrid cols={{ base: 1, lg: 3 }} spacing="lg">
                  <Paper withBorder radius="md" p="lg" className="stats-card lg-span-2">
                    <ActivityChart activity={data.activity} loading={false} />
                  </Paper>

                  <Paper withBorder radius="md" p="lg" className="stats-card">
                    <ChapterMasteryDonut
                      chapters={data.mastery?.chapters}
                      chapterOrder={chapterOrder}
                    />
                  </Paper>
                </SimpleGrid>

                <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
                  <Paper withBorder radius="md" p="lg" className="stats-card">
                    <Text fw={800} mb="sm">
                      Mastery by chapter
                    </Text>
                    <Text c="dimmed" size="xs" mb="md">
                      Average quiz score (best attempt per quiz), equal weight per chapter in the book.
                    </Text>
                    <Stack gap="sm">
                      {masteryRows.length === 0 ? (
                        <Text c="dimmed" size="sm">
                          No chapters in this textbook yet.
                        </Text>
                      ) : (
                        masteryRows.map((row) => (
                          <Box key={row.chapter_id}>
                            <Group justify="space-between" gap="xs" mb={4}>
                              <Text size="sm" lineClamp={1} style={{ flex: 1 }}>
                                {row.title}
                              </Text>
                              <Text size="xs" c="dimmed">
                                {row.quizzes_with_attempts
                                  ? `${row.quiz_mastery_percent}%`
                                  : "—"}
                              </Text>
                            </Group>
                            <Box className="stats-chapter-bar-wrap">
                              <div
                                className="stats-chapter-bar-fill"
                                style={{
                                  width: `${row.quiz_mastery_percent}%`,
                                  opacity: row.quizzes_with_attempts ? 1 : 0.35,
                                }}
                              />
                            </Box>
                          </Box>
                        ))
                      )}
                    </Stack>
                  </Paper>

                  <Paper withBorder radius="md" p="lg" className="stats-card">
                    <Text fw={800} mb="sm">
                      At a glance
                    </Text>
                    <Stack gap="sm">
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          Avg chapter quiz mastery
                        </Text>
                        <Badge size="lg" variant="light">
                          {data.mastery?.avg_chapter_mastery_percent ?? 0}%
                        </Badge>
                      </Group>
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          Best quiz score (avg over quizzes)
                        </Text>
                        <Text fw={600}>{data.mastery?.overall_quiz_percent ?? 0}%</Text>
                      </Group>
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          Longest streak
                        </Text>
                        <Text fw={600}>{data.study?.streak_longest_days ?? 0} days</Text>
                      </Group>
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          Session events (all time)
                        </Text>
                        <Text fw={600}>{data.study?.total_session_events ?? 0}</Text>
                      </Group>
                      <Group justify="space-between">
                        <Text size="sm" c="dimmed">
                          Active days (last 7)
                        </Text>
                        <Text fw={600}>{data.activity?.active_days_last_7 ?? 0} / 7</Text>
                      </Group>
                    </Stack>
                  </Paper>
                </SimpleGrid>

                <Paper withBorder radius="md" p="lg" className="stats-card">
                  <Group justify="space-between" align="center" mb="sm">
                    <Text fw={800}>Recent study sessions</Text>
                  </Group>

                  <Divider mb="md" />

                  <Table striped highlightOnHover withRowBorders={false}>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Type</Table.Th>
                        <Table.Th>Title</Table.Th>
                        <Table.Th>When</Table.Th>
                        <Table.Th>Time on task</Table.Th>
                        <Table.Th>Result</Table.Th>
                      </Table.Tr>
                    </Table.Thead>

                    <Table.Tbody>
                      {(data.recent_sessions || []).length === 0 ? (
                        <Table.Tr>
                          <Table.Td colSpan={5}>
                            <Text c="dimmed" size="sm" py="sm">
                              No sessions yet.
                            </Text>
                          </Table.Td>
                        </Table.Tr>
                      ) : (
                        data.recent_sessions.map((row, idx) => (
                          <Table.Tr key={`${row.kind}-${row.at}-${idx}`}>
                            <Table.Td>
                              <Badge
                                color={kindBadgeColor(row.kind)}
                                variant="light"
                                size="sm"
                              >
                                {kindLabel(row.kind)}
                              </Badge>
                            </Table.Td>
                            <Table.Td>
                              <Text size="sm" fw={500} lineClamp={2}>
                                {row.title}
                              </Text>
                            </Table.Td>
                            <Table.Td>
                              <Text size="sm">{formatSessionAt(row.at)}</Text>
                            </Table.Td>
                            <Table.Td>
                              <Text size="sm">
                                {formatDurationSeconds(row.duration_seconds)}
                              </Text>
                            </Table.Td>
                            <Table.Td>
                              <Text size="sm">{row.detail || "—"}</Text>
                            </Table.Td>
                          </Table.Tr>
                        ))
                      )}
                    </Table.Tbody>
                  </Table>
                </Paper>
              </>
            )}
          </Stack>
        </Container>
      </main>
    </>
  );
}
