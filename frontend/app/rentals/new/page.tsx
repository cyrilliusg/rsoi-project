"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { cars, rentals, type Car } from "@/lib/api";
import styles from "../rental.module.css";

function daysBetween(from: string, to: string): number {
  if (!from || !to) return 0;
  const d1 = new Date(from);
  const d2 = new Date(to);
  const ms = d2.getTime() - d1.getTime();
  return ms > 0 ? Math.round(ms / 86_400_000) : 0;
}

function NewRentalForm() {
  const router = useRouter();
  const params = useSearchParams();
  const carUid = params.get("carUid") ?? "";

  const [car, setCar] = useState<Car | null>(null);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!carUid) return;
    cars
      .list(1, 100, true)
      .then((r) => {
        const found = r.items.find((c) => c.carUid === carUid) ?? null;
        setCar(found);
      })
      .catch((e) => setError(e.message ?? "Не удалось загрузить авто"));
  }, [carUid]);

  const days = daysBetween(dateFrom, dateTo);
  const total = car && days > 0 ? car.price * days : 0;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!carUid || !dateFrom || !dateTo) return;
    setBusy(true);
    setError(null);
    try {
      const created = await rentals.create({ carUid, dateFrom, dateTo });
      router.push(`/rentals/${created.rentalUid}`);
    } catch (e: unknown) {
      setError((e as Error).message ?? "Ошибка бронирования");
      setBusy(false);
    }
  }

  if (!carUid) {
    return <p className="error">Автомобиль не выбран. Вернитесь в каталог и выберите авто.</p>;
  }

  return (
    <>
      <h1>Новая аренда</h1>
      {car && (
        <p className="muted">
          {car.brand} {car.model} — {car.price} ₽ / сутки
        </p>
      )}
      <form className={styles.form} onSubmit={submit}>
        <label>
          С
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            required
          />
        </label>
        <label>
          По
          <input
            type="date"
            value={dateTo}
            min={dateFrom || undefined}
            onChange={(e) => setDateTo(e.target.value)}
            required
          />
        </label>
        {days > 0 && car && (
          <div className={styles.summary}>
            {days} {days === 1 ? "сутки" : "суток"} × {car.price} ₽ = <strong>{total} ₽</strong>
          </div>
        )}
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={busy || !dateFrom || !dateTo || days <= 0}>
          {busy ? "Бронируем…" : "Забронировать"}
        </button>
      </form>
    </>
  );
}

export default function NewRentalPage() {
  return (
    <Suspense fallback={<p className="muted">Загрузка…</p>}>
      <NewRentalForm />
    </Suspense>
  );
}
