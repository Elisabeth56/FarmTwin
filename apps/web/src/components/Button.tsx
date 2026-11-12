import type { ButtonHTMLAttributes, ReactNode } from "react";

// primary is ink (one per view), secondary is the brand tint, quiet is a light ink wash
type Variant = "primary" | "secondary" | "quiet";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  children: ReactNode;
};

const VARIANTS: Record<Variant, string> = {
  primary: "bg-ink text-on-ink hover:bg-ink/90",
  secondary: "bg-brand-tint text-ink hover:brightness-95",
  quiet: "bg-ink/5 text-ink hover:bg-ink/10",
};

export default function Button({ variant = "primary", className = "", children, ...rest }: ButtonProps) {
  return (
    <button
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-pill px-5 text-small transition duration-150 ease-ui active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100 ${VARIANTS[variant]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}
