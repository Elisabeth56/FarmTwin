import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  children: ReactNode;
};

export default function Button({
  variant = "primary",
  className = "",
  disabled,
  children,
  ...rest
}: ButtonProps) {
  const base =
    "rounded-xl px-5 py-2.5 font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-primary/40";
  const primary = "bg-primary text-white hover:bg-primary-hover";
  const secondary =
    "bg-white border border-border text-ink hover:bg-primary-tint";
  const disabledCls =
    "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-primary";
  const disabledSecondaryCls =
    "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-white";
  return (
    <button
      className={`${base} ${variant === "primary" ? `${primary} ${disabledCls}` : `${secondary} ${disabledSecondaryCls}`} ${className}`}
      disabled={disabled}
      {...rest}
    >
      {children}
    </button>
  );
}
