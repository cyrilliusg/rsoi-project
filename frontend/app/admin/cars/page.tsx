"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import { cars as carsApi, type CarsPage } from "@/lib/api";
import styles from "../admin.module.css";

const PAGE_SIZE = 20;

export default function AdminCarsPage() {
  const router = useRouter();
  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [data, setData] = useState<CarsPage | null>(null);
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [busyUid, setBusyUid] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const user = getCurrentUser();
    if (!user) {
      router.replace("/login");
      return;
    }
    setAllowed(user.role === "ADMIN");
  }, [router]);

  const reload = useCallback(async () => {
    try {
      setError(null);
      setData(await carsApi.list(page, PAGE_SIZE, true));
    } catch (e: unknown) {
      setError((e as Error).message ?? "Не удалось загрузить список");
    }
  }, [page]);

  useEffect(() => {
    if (allowed) void reload();
  }, [allowed, reload, reloadKey]);

  if (allowed === null) return <p className="muted">Загрузка…</p>;
  if (!allowed)
    return (
      <>
        <h1>403 — нет доступа</h1>
        <p className="muted">Эта страница доступна только администраторам.</p>
      </>
    );

  async function onDelete(uid: string, label: string) {
    if (!confirm(`Удалить автомобиль ${label}?`)) return;
    setBusyUid(uid);
    setError(null);
    try {
      await carsApi.remove(uid);
      setReloadKey((k) => k + 1);
    } catch (e: unknown) {
      setError((e as Error).message ?? "Не удалось удалить");
    } finally {
      setBusyUid(null);
    }
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.totalElements / PAGE_SIZE)) : 1;

  return (
    <>
      <h1>Автомобили</h1>

      <div style={{ marginBottom: "1rem", display: "flex", gap: "0.5rem" }}>
        <Link href="/admin/cars/new">
          <button>Создать</button>
        </Link>
        <button className="secondary" onClick={() => setReloadKey((k) => k + 1)}>
          Обновить
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      {data === null && <p className="muted">Загрузка…</p>}
      {data && data.items.length === 0 && <p className="muted">Список пуст.</p>}
      {data && data.items.length > 0 && (
        <>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Марка / модель</th>
                <th>Гос. номер</th>
                <th>Тип</th>
                <th>Мощность</th>
                <th>Цена / сутки</th>
                <th>Статус</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((car) => {
                const label = `${car.brand} ${car.model}`;
                return (
                  <tr key={car.carUid}>
                    <td>{label}</td>
                    <td>{car.registrationNumber}</td>
                    <td>
                      <span className={styles.eventType}>{car.type}</span>
                    </td>
                    <td>{car.power ? `${car.power} л.с.` : "—"}</td>
                    <td>{car.price} ₽</td>
                    <td>
                      {car.available ? (
                        <span className="muted">свободно</span>
                      ) : (
                        <span className="error">в резерве</span>
                      )}
                    </td>
                    <td style={{ display: "flex", gap: "0.4rem", justifyContent: "flex-end" }}>
                      <Link href={`/admin/cars/${car.carUid}/edit`}>
                        <button className="secondary">Изменить</button>
                      </Link>
                      <button
                        className="secondary"
                        disabled={busyUid === car.carUid}
                        onClick={() => onDelete(car.carUid, label)}
                      >
                        {busyUid === car.carUid ? "…" : "Удалить"}
                      </button>
                    </td>
                  </tr>
                );
              })}
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
