import type { RentalStatus } from "@/lib/api";
import styles from "./rental.module.css";

const LABEL: Record<RentalStatus, string> = {
  IN_PROGRESS: "В процессе",
  FINISHED: "Завершена",
  CANCELED: "Отменена",
};

export default function StatusBadge({ status }: { status: RentalStatus }) {
  const cls = status === "IN_PROGRESS" ? styles.in_progress : status === "FINISHED" ? styles.finished : styles.canceled;
  return <span className={`${styles.status} ${cls}`}>{LABEL[status]}</span>;
}
