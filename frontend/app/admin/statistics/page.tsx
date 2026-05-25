"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";

export default function StatisticsPage() {
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
      <h1>Статистика</h1>
      <p className="muted">
      </p>
    </>
  );
}
