"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { cars as carsApi, type Car, type CarType, type CarWriteRequest } from "@/lib/api";
import { CAR_TYPE_LABEL } from "@/lib/labels";
import styles from "../admin.module.css";

const CAR_TYPES: CarType[] = ["SEDAN", "SUV", "MINIVAN", "ROADSTER"];

interface Props {
  initial?: Car;
  mode: "create" | "edit";
}

export default function CarForm({ initial, mode }: Props) {
  const router = useRouter();
  const [brand, setBrand] = useState(initial?.brand ?? "");
  const [model, setModel] = useState(initial?.model ?? "");
  const [registrationNumber, setRegistrationNumber] = useState(
    initial?.registrationNumber ?? ""
  );
  const [power, setPower] = useState<string>(
    initial?.power != null ? String(initial.power) : ""
  );
  const [type, setType] = useState<CarType>(initial?.type ?? "SEDAN");
  const [price, setPrice] = useState<string>(
    initial?.price != null ? String(initial.price) : ""
  );
  const [available, setAvailable] = useState<boolean>(initial?.available ?? true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const priceNum = Number(price);
    const powerNum = power.trim() === "" ? null : Number(power);
    if (!Number.isFinite(priceNum) || priceNum < 0) {
      setError("Цена должна быть неотрицательным числом");
      setBusy(false);
      return;
    }
    if (powerNum !== null && (!Number.isFinite(powerNum) || powerNum < 0)) {
      setError("Мощность должна быть неотрицательным числом");
      setBusy(false);
      return;
    }
    const payload: CarWriteRequest = {
      brand: brand.trim(),
      model: model.trim(),
      registrationNumber: registrationNumber.trim(),
      power: powerNum,
      type,
      price: priceNum,
      available,
    };
    try {
      if (mode === "create") {
        await carsApi.create(payload);
      } else if (initial) {
        await carsApi.update(initial.carUid, payload);
      }
      router.push("/admin/cars");
    } catch (e: unknown) {
      setError((e as Error).message ?? "Не удалось сохранить");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={onSubmit}>
      <div className={styles.row}>
        <label>
          Марка
          <input
            type="text"
            value={brand}
            onChange={(e) => setBrand(e.target.value)}
            required
            maxLength={80}
          />
        </label>
        <label>
          Модель
          <input
            type="text"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            required
            maxLength={80}
          />
        </label>
      </div>
      <div className={styles.row}>
        <label>
          Гос. номер
          <input
            type="text"
            value={registrationNumber}
            onChange={(e) => setRegistrationNumber(e.target.value)}
            required
            maxLength={20}
          />
        </label>
        <label>
          Тип
          <select value={type} onChange={(e) => setType(e.target.value as CarType)}>
            {CAR_TYPES.map((t) => (
              <option key={t} value={t}>
                {CAR_TYPE_LABEL[t]}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className={styles.row}>
        <label>
          Мощность (л.с.)
          <input
            type="number"
            min={0}
            value={power}
            onChange={(e) => setPower(e.target.value)}
            placeholder="—"
          />
        </label>
        <label>
          Цена / сутки (₽)
          <input
            type="number"
            min={0}
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            required
          />
        </label>
      </div>
      <label style={{ flexDirection: "row", alignItems: "center", gap: "0.5rem" }}>
        <input
          type="checkbox"
          checked={available}
          onChange={(e) => setAvailable(e.target.checked)}
        />
        Доступен для аренды
      </label>

      {error && <p className="error">{error}</p>}

      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button type="submit" disabled={busy}>
          {busy ? "Сохраняем…" : mode === "create" ? "Создать" : "Сохранить"}
        </button>
        <button
          type="button"
          className="secondary"
          disabled={busy}
          onClick={() => router.push("/admin/cars")}
        >
          Отмена
        </button>
      </div>
    </form>
  );
}
