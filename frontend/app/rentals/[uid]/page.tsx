"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { rentals, type Rental } from "@/lib/api";
import StatusBadge from "../StatusBadge";
import styles from "../rental.module.css";

export default function RentalDetailPage() {
  const params = useParams<{ uid: string }>();
  const router = useRouter();
  const uid = params?.uid as string;

  const [rental, setRental] = useState<Rental | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!uid) return;
    rentals
      .get(uid)
      .then(setRental)
      .catch((e) => setError(e.message ?? "Не удалось загрузить аренду"));
  }, [uid]);

  const cancel = async () => {
    if (!uid) return;
    setBusy(true);
    try {
      await rentals.cancel(uid);
      router.push("/rentals");
    } catch (e: unknown) {
      setError((e as Error).message ?? "Не удалось отменить");
      setBusy(false);
    }
  };

  const finish = async () => {
    if (!uid) return;
    setBusy(true);
    try {
      await rentals.finish(uid);
      const refreshed = await rentals.get(uid);
      setRental(refreshed);
    } catch (e: unknown) {
      setError((e as Error).message ?? "Не удалось завершить");
    } finally {
      setBusy(false);
    }
  };

  if (error) return <p className="error">{error}</p>;
  if (!rental) return <p className="muted">Загрузка…</p>;

  return (
    <>
      <h1>Аренда {rental.rentalUid.slice(0, 8)}…</h1>
      <div className={styles.detail}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <strong>
            {rental.car.brand ?? "Автомобиль"} {rental.car.model ?? ""}
          </strong>
          <StatusBadge status={rental.status} />
        </div>
        <div className={styles.meta}>
          <span>
            {rental.dateFrom} → {rental.dateTo}
          </span>
          {rental.car.registrationNumber && <span>№ {rental.car.registrationNumber}</span>}
        </div>
        <div>
          Оплата:{" "}
          <strong>
            {rental.payment.status ?? "неизвестно"}
            {rental.payment.price !== undefined && ` — ${rental.payment.price} ₽`}
          </strong>
        </div>
        {rental.status === "IN_PROGRESS" && (
          <div className={styles.actions}>
            <button onClick={finish} disabled={busy}>
              Завершить
            </button>
            <button className="danger" onClick={cancel} disabled={busy}>
              Отменить
            </button>
          </div>
        )}
      </div>
    </>
  );
}
