import type { RentalStatus } from "@/lib/api";
import { RENTAL_STATUS_LABEL } from "@/lib/labels";
import styles from "./rental.module.css";

export default function StatusBadge({ status }: { status: RentalStatus }) {
  const cls = status === "IN_PROGRESS" ? styles.in_progress : status === "FINISHED" ? styles.finished : styles.canceled;
  return <span className={`${styles.status} ${cls}`}>{RENTAL_STATUS_LABEL[status]}</span>;
}
