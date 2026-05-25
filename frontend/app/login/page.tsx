"use client";

import { useEffect } from "react";
import { beginLogin } from "@/lib/auth";

export default function LoginPage() {
  useEffect(() => {
    void beginLogin("/");
  }, []);

  return <p className="muted">Перенаправляем на страницу входа Identity Provider…</p>;
}
