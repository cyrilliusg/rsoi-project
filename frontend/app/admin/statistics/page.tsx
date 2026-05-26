"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import { statistics, type EventsPage, type StatisticsSummary } from "@/lib/api";
import styles from "../admin.module.css";

const EVENT_TYPES = [
  "",
  "rental.created",
  "rental.canceled",
  "rental.finished",
  "rental.failed",
];

const PAGE_SIZE = 15;

function fmt(n: number): string {
  return new Intl.NumberFormat("ru-RU").format(n);
}

function fmtTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString("ru-RU", { timeZone: "UTC" });
  } catch {
    return iso;
  }
}

export default function StatisticsPage() {
  const router = useRouter();
  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [summary, setSummary] = useState<StatisticsSummary | null>(null);
  const [events, setEvents] = useState<EventsPage | null>(null);
  const [page, setPage] = useState(1);
  const [eventType, setEventType] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const user = getCurrentUser();
    if (!user) {
      router.replace("/login");
      return;
    }
    setAllowed(user.role === "ADMIN");
  }, [router]);

  const loadSummary = useCallback(async () => {
    try {
      setSummary(await statistics.summary());
    } catch (e: unknown) {
      setError((e as Error).message ?? "Не удалось загрузить summary");
    }
  }, []);

  const loadEvents = useCallback(async () => {
    try {
      setEvents(
        await statistics.events({
          eventType: eventType || undefined,
          page,
          size: PAGE_SIZE,
        })
      );
    } catch (e: unknown) {
      setError((e as Error).message ?? "Не удалось загрузить события");
    }
  }, [eventType, page]);

  useEffect(() => {
    if (!allowed) return;
    void loadSummary();
  }, [allowed, loadSummary, reloadKey]);

  useEffect(() => {
    if (!allowed) return;
    void loadEvents();
  }, [allowed, loadEvents, reloadKey]);

  if (allowed === null) return <p className="muted">Загрузка…</p>;
  if (!allowed)
    return (
      <>
        <h1>403 — нет доступа</h1>
        <p className="muted">Эта страница доступна только администраторам.</p>
      </>
    );

  const totalPages = events
    ? Math.max(1, Math.ceil(events.count / PAGE_SIZE))
    : 1;

  return (
    <>
      <h1>Статистика</h1>

      <div style={{ marginBottom: "1rem", display: "flex", gap: "0.5rem" }}>
        <button onClick={() => setReloadKey((k) => k + 1)} className="secondary">
          Обновить
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      {summary && (
        <>
          <div className={styles.cards}>
            <div className={styles.card}>
              <span className={styles.label}>Всего событий</span>
              <span className={styles.value}>{fmt(summary.totals.events)}</span>
            </div>
            <div className={styles.card}>
              <span className={styles.label}>Бронирований</span>
              <span className={styles.value}>{fmt(summary.totals.rentalsCreated)}</span>
            </div>
            <div className={styles.card}>
              <span className={styles.label}>Завершено</span>
              <span className={styles.value}>{fmt(summary.totals.rentalsFinished)}</span>
            </div>
            <div className={styles.card}>
              <span className={styles.label}>Отменено</span>
              <span className={styles.value}>{fmt(summary.totals.rentalsCanceled)}</span>
            </div>
            <div className={styles.card}>
              <span className={styles.label}>Ошибок саги</span>
              <span className={styles.value}>{fmt(summary.totals.rentalsFailed)}</span>
            </div>
            <div className={styles.card}>
              <span className={styles.label}>Выручка</span>
              <span className={styles.value}>{fmt(summary.totals.revenue)} ₽</span>
            </div>
            <div className={styles.card}>
              <span className={styles.label}>Уникальных пользователей</span>
              <span className={styles.value}>{fmt(summary.totals.uniqueUsers)}</span>
            </div>
          </div>

          <h2>По типам событий</h2>
          <div className={styles.bytypeList}>
            {Object.keys(summary.byEventType).length === 0 && (
              <p className="muted">Пока пусто</p>
            )}
            {Object.entries(summary.byEventType).map(([type, count]) => (
              <span key={type} className={styles.bytypeItem}>
                <code>{type}</code> <strong>{fmt(count)}</strong>
              </span>
            ))}
          </div>
        </>
      )}

      <h2>Лента событий</h2>
      <div className={styles.controls}>
        <label>
          Тип события
          <select
            value={eventType}
            onChange={(e) => {
              setEventType(e.target.value);
              setPage(1);
            }}
          >
            {EVENT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t || "Все"}
              </option>
            ))}
          </select>
        </label>
      </div>

      {events && events.results.length === 0 && (
        <p className="muted">Нет событий по выбранному фильтру.</p>
      )}

      {events && events.results.length > 0 && (
        <>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Время</th>
                <th>Тип</th>
                <th>Пользователь</th>
                <th>Correlation</th>
              </tr>
            </thead>
            <tbody>
              {events.results.map((e) => (
                <tr key={e.eventId}>
                  <td>{fmtTime(e.timestamp)}</td>
                  <td>
                    <span className={styles.eventType}>{e.eventType}</span>
                  </td>
                  <td>{e.username || e.userId.slice(0, 8)}</td>
                  <td>
                    <code style={{ fontSize: "0.8rem" }}>{e.correlationId.slice(0, 12)}…</code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className={styles.pagination}>
            <button
              className="secondary"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              ←
            </button>
            <span>
              Страница {page} из {totalPages} ({fmt(events.count)} событий)
            </span>
            <button
              className="secondary"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              →
            </button>
          </div>
        </>
      )}
    </>
  );
}
