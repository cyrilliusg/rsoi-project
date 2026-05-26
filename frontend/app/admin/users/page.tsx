"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import { idpUsers, type IdpUser } from "@/lib/idp";
import styles from "../admin.module.css";

export default function AdminUsersPage() {
  const router = useRouter();
  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [users, setUsers] = useState<IdpUser[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [role, setRole] = useState<"USER" | "ADMIN">("USER");
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<string | null>(null);

  useEffect(() => {
    const user = getCurrentUser();
    if (!user) {
      router.replace("/login");
      return;
    }
    setAllowed(user.role === "ADMIN");
  }, [router]);

  const reload = useCallback(async () => {
    try {
      setUsers(await idpUsers.list());
    } catch (e: unknown) {
      setError((e as Error).message ?? "Не удалось загрузить список");
    }
  }, []);

  useEffect(() => {
    if (allowed) void reload();
  }, [allowed, reload]);

  if (allowed === null) return <p className="muted">Загрузка…</p>;
  if (!allowed)
    return (
      <>
        <h1>403 — нет доступа</h1>
        <p className="muted">Эта страница доступна только администраторам.</p>
      </>
    );

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setCreated(null);
    try {
      const user = await idpUsers.create({
        username,
        email,
        password,
        first_name: firstName,
        last_name: lastName,
        role,
      });
      setCreated(`Создан пользователь ${user.username} (${user.role})`);
      setUsername("");
      setEmail("");
      setPassword("");
      setFirstName("");
      setLastName("");
      setRole("USER");
      await reload();
    } catch (e: unknown) {
      setError((e as Error).message ?? "Не удалось создать пользователя");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1>Пользователи</h1>

      <h2>Создать пользователя</h2>
      <form className={styles.form} onSubmit={onSubmit}>
        <div className={styles.row}>
          <label>
            Логин
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              minLength={3}
              maxLength={150}
            />
          </label>
          <label>
            Роль
            <select value={role} onChange={(e) => setRole(e.target.value as "USER" | "ADMIN")}>
              <option value="USER">USER</option>
              <option value="ADMIN">ADMIN</option>
            </select>
          </label>
        </div>
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        <label>
          Пароль
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={4}
          />
        </label>
        <div className={styles.row}>
          <label>
            Имя
            <input type="text" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
          </label>
          <label>
            Фамилия
            <input type="text" value={lastName} onChange={(e) => setLastName(e.target.value)} />
          </label>
        </div>
        {error && <p className="error">{error}</p>}
        {created && <p className="success">{created}</p>}
        <button type="submit" disabled={busy}>
          {busy ? "Создаём…" : "Создать"}
        </button>
      </form>

      <h2>Все пользователи</h2>
      {users === null && <p className="muted">Загрузка…</p>}
      {users && users.length === 0 && <p className="muted">Список пуст.</p>}
      {users && users.length > 0 && (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Логин</th>
              <th>Имя</th>
              <th>Email</th>
              <th>Роль</th>
              <th>sub</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.sub}>
                <td>{u.username}</td>
                <td>
                  {[u.first_name, u.last_name].filter(Boolean).join(" ") || "—"}
                </td>
                <td>{u.email}</td>
                <td>
                  <span className={styles.eventType}>{u.role}</span>
                </td>
                <td>
                  <code style={{ fontSize: "0.8rem" }}>{u.sub.slice(0, 8)}…</code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
