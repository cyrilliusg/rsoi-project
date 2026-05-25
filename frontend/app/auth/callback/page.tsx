"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { completeLogin } from "@/lib/auth";

function CallbackInner() {
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const oauthError = params.get("error");
    if (oauthError) {
      setError(`OAuth error: ${oauthError} — ${params.get("error_description") ?? ""}`);
      return;
    }
    const code = params.get("code");
    const state = params.get("state");
    if (!code || !state) {
      setError("Не получили code/state от Identity Provider");
      return;
    }
    completeLogin(code, state)
      .then(({ returnTo }) => {
        router.replace(returnTo || "/");
      })
      .catch((e) => setError(e.message ?? "Ошибка обмена кода на токен"));
  }, [params, router]);

  if (error) {
    return (
      <>
        <h1>Ошибка входа</h1>
        <p className="error">{error}</p>
      </>
    );
  }
  return <p className="muted">Завершаем вход…</p>;
}

export default function CallbackPage() {
  return (
    <Suspense fallback={<p className="muted">Загрузка…</p>}>
      <CallbackInner />
    </Suspense>
  );
}
