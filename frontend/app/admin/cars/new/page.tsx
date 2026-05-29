"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getCurrentUser } from "@/lib/auth";
import CarForm from "../CarForm";

export default function AdminCarNewPage() {
  const router = useRouter();
  const [allowed, setAllowed] = useState<boolean | null>(null);

  useEffect(() => {
    const user = getCurrentUser();
    if (!user) {
      router.replace("/login");
      return;
    }
    setAllowed(user.role === "ADMIN");
  }, [router]);

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
      <h1>Новый автомобиль</h1>
      <CarForm mode="create" />
    </>
  );
}
