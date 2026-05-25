"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { rentals, type Rental } from "@/lib/api";
import StatusBadge from "./StatusBadge";
import styles from "./rental.module.css";

export default function RentalsListPage() {
  const [items, setItems] = useState<Rental[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    rentals
      .list()
      .then(setItems)
      .catch((e) => setError(e.message ?? "Ошибка загрузки"));
  }, []);

  return (
    <>
      <h1>Мои аренды</h1>
      {error && <p className="error">{error}</p>}
      {!error && items === null && <p className="muted">Загрузка…</p>}
      {items?.length === 0 && <p className="muted">У вас пока нет аренд.</p>}
      <div className={styles.list}>
        {items?.map((r) => (
          <Link key={r.rentalUid} href={`/rentals/${r.rentalUid}`} className={styles.row}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <strong>
                {r.car.brand ?? "Автомобиль"} {r.car.model ?? ""}
              </strong>
              <StatusBadge status={r.status} />
            </div>
            <div className={styles.meta}>
              <span>
                {r.dateFrom} → {r.dateTo}
              </span>
              {r.payment.price !== undefined && <span>{r.payment.price} ₽</span>}
              {r.payment.status && <span>оплата: {r.payment.status}</span>}
            </div>
          </Link>
        ))}
      </div>
    </>
  );
}
