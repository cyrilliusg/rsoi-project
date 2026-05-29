"use client";

import Link from "next/link";
import type { Car } from "@/lib/api";
import { CAR_TYPE_LABEL } from "@/lib/labels";
import styles from "./CarCard.module.css";

export default function CarCard({ car, canBook }: { car: Car; canBook: boolean }) {
  return (
    <div className={styles.card}>
      <div className={styles.title}>
        {car.brand} {car.model}
      </div>
      <div className={styles.meta}>
        <span>{CAR_TYPE_LABEL[car.type]}</span>
        <span>№ {car.registrationNumber}</span>
        {car.power && <span>{car.power} л.с.</span>}
      </div>
      <div className={styles.price}>{car.price} ₽ / сутки</div>
      <div className={styles.actions}>
        {car.available ? (
          canBook ? (
            <Link href={`/rentals/new?carUid=${car.carUid}`}>
              <button>Забронировать</button>
            </Link>
          ) : (
            <Link href="/login">
              <button className="secondary">Войти, чтобы забронировать</button>
            </Link>
          )
        ) : (
          <span className={styles.unavailable}>В резерве</span>
        )}
      </div>
    </div>
  );
}
