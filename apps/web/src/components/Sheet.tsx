import { useEffect, useRef, type ReactNode } from "react";

type SheetProps = {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
};

/** Bottom sheet on phones, centred panel from 640px. Esc and the backdrop close it. */
export default function Sheet({ open, title, onClose, children }: SheetProps) {
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    panel.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      previous?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40 flex items-end justify-center bg-ink/40 sm:items-center" onClick={onClose}>
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        className="max-h-[90dvh] w-full animate-sheet overflow-y-auto rounded-t-xl bg-raised p-6 shadow-float sm:max-w-lg sm:animate-rise sm:rounded-xl"
      >
        <h2 className="mb-4 text-h3">{title}</h2>
        {children}
      </div>
    </div>
  );
}
