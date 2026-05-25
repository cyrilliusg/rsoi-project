"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUser, logout } from "@/lib/auth";
import type { JwtClaims } from "@/lib/jwt";
import styles from "./Header.module.css";

export default function Header() {
  const [user, setUser] = useState<JwtClaims | null>(null);
  const router = useRouter();

  useEffect(() => {
    setUser(getCurrentUser());
    const onStorage = () => setUser(getCurrentUser());
    window.addEventListener("storage", onStorage);
    window.addEventListener("focus", onStorage);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("focus", onStorage);
    };
  }, []);

  const handleLogout = () => {
    logout();
    setUser(null);
    router.push("/");
    router.refresh();
  };

  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Link href="/" className={styles.brand}>
          Car Rental
        </Link>
        <nav className={styles.nav}>
          <Link href="/">Авто</Link>
          {user && <Link href="/rentals">Мои аренды</Link>}
          {user?.role === "ADMIN" && (
            <>
              <Link href="/admin/statistics">Статистика</Link>
              <Link href="/admin/users">Пользователи</Link>
            </>
          )}
        </nav>
        <div className={styles.user}>
          {user ? (
            <>
              <span className={styles.role}>{user.role}</span>
              <span>{user.preferred_username}</span>
              <button className="secondary" onClick={handleLogout}>
                Выйти
              </button>
            </>
          ) : (
            <Link href="/login">
              <button>Войти</button>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
