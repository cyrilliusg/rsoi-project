"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { cars, type CarsPage } from "@/lib/api";
import { getCurrentUser } from "@/lib/auth";
import CarCard from "./components/CarCard";
import styles from "./page.module.css";

const PAGE_SIZE = 12;

export default function HomePage() {
  const [page, setPage] = useState(1);
  const [showAll, setShowAll] = useState(false);
  const [data, setData] = useState<CarsPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isAuthed, setIsAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    setIsAuthed(getCurrentUser() !== null);
  }, []);

  useEffect(() => {
    if (!isAuthed) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    cars
      .list(page, PAGE_SIZE, showAll)
      .then((r) => {
        if (!cancelled) setData(r);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message ?? "Ошибка загрузки");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [page, showAll, isAuthed]);

  if (isAuthed === null) {
    return <p className="muted">Загрузка…</p>;
  }

  if (!isAuthed) {
    return (
      <>
        <h1>Car Rental</h1>
        <p className="muted">
          Войдите, чтобы посмотреть каталог автомобилей и забронировать поездку.
        </p>
        <Link href="/login">
          <button>Войти</button>
        </Link>
      </>
    );
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.totalElements / PAGE_SIZE)) : 1;

  return (
    <>
      <h1>Каталог автомобилей</h1>
      <div className={styles.controls}>
        <label className={styles.toggle}>
          <input
            type="checkbox"
            checked={showAll}
            onChange={(e) => {
              setShowAll(e.target.checked);
              setPage(1);
            }}
          />
          Показать все (включая забронированные)
        </label>
      </div>

      {loading && <p className="muted">Загрузка…</p>}
      {error && <p className="error">{error}</p>}

      {data && (
        <>
          <div className={styles.grid}>
            {data.items.map((car) => (
              <CarCard key={car.carUid} car={car} canBook />
            ))}
          </div>
          <div className={styles.pagination}>
            <button
              className="secondary"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              ←
            </button>
            <span>
              Страница {data.page} из {totalPages} ({data.totalElements} авто)
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
