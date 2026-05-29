/**
 * UI-нейминги для системных значений
 */
import type { CarType, RentalStatus } from "./api";

export const ROLE_LABEL: Record<"USER" | "ADMIN", string> = {
  USER: "Клиент",
  ADMIN: "Админ",
};

export const CAR_TYPE_LABEL: Record<CarType, string> = {
  SEDAN: "Седан",
  SUV: "Внедорожник",
  MINIVAN: "Минивэн",
  ROADSTER: "Родстер",
};

export const RENTAL_STATUS_LABEL: Record<RentalStatus, string> = {
  IN_PROGRESS: "В процессе",
  FINISHED: "Завершена",
  CANCELED: "Отменена",
};

export const PAYMENT_STATUS_LABEL: Record<"PAID" | "CANCELED", string> = {
  PAID: "Оплачено",
  CANCELED: "Отменено",
};

export const EVENT_TYPE_LABEL: Record<string, string> = {
  "rental.created": "Бронирование создано",
  "rental.finished": "Аренда завершена",
  "rental.canceled": "Бронирование отменено",
  "rental.failed": "Ошибка бронирования",
};

export function formatEventType(type: string): string {
  return EVENT_TYPE_LABEL[type] ?? type;
}
