"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getCurrentUser } from "@/lib/auth";
import { cars as carsApi, type Car } from "@/lib/api";
import CarForm from "../../CarForm";

export default function AdminCarEditPage() {
  const router = useRouter();
  const params = useParams<{ uid: string }>();
  const uid = params?.uid;
  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [car, setCar] = useState<Car | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const user = getCurrentUser();
    if (!user) {
      router.replace("/login");
      return;
    }
    setAllowed(user.role === "ADMIN");
  }, [router]);

  useEffect(() => {
    if (!allowed || !uid) return;
    let cancelled = false;
    carsApi
      .get(uid)
      .then((r) => {
        if (!cancelled) setCar(r);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message ?? "Не удалось загрузить");
      });
    return () => {
      cancelled = true;
    };
  }, [allowed, uid]);

  if (allowed === null) return <p className="muted">Загрузка…</p>;
  if (!allowed)
    return (
      <>
        <h1>403 — нет доступа</h1>
        <p className="muted">Эта страница доступна только администраторам.</p>
      </>
    );

  return (
    <>
      <p>
        <Link href="/admin/cars">← Назад к списку</Link>
      </p>
      <h1>Редактировать автомобиль</h1>
      {error && <p className="error">{error}</p>}
      {!car && !error && <p className="muted">Загрузка…</p>}
      {car && <CarForm mode="edit" initial={car} />}
    </>
  );
}
