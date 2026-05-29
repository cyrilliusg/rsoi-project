"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getCurrentUser, logout } from "@/lib/auth";
import type { JwtClaims } from "@/lib/jwt";
import { ROLE_LABEL } from "@/lib/labels";
import styles from "./Header.module.css";

export default function Header() {
  const [user, setUser] = useState<JwtClaims | null>(null);

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
    // logout() clears local storage AND redirects through IdP to kill
    // its session cookie; the IdP then bounces back to "/".
    setUser(null);
    logout("/");
  };

  const isAdmin = user?.role === "ADMIN";
  const brandHref = isAdmin ? "/admin/cars" : "/";

  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Link href={brandHref} className={styles.brand}>
          Система аренды авто
        </Link>
        <nav className={styles.nav}>
          {!isAdmin && <Link href="/">Авто</Link>}
          {user && !isAdmin && <Link href="/rentals">Мои аренды</Link>}
          {isAdmin && (
            <>
              <Link href="/admin/cars">Автомобили</Link>
              <Link href="/admin/statistics">Статистика</Link>
              <Link href="/admin/users">Пользователи</Link>
            </>
          )}
        </nav>
        <div className={styles.user}>
          {user ? (
            <>
              <span className={styles.role}>
                {user.role ? ROLE_LABEL[user.role] : ""}
              </span>
              <span className={styles.username}>{user.preferred_username}</span>
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
